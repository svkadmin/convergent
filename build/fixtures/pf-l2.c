#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <poll.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

enum { IP, ARP, DHCP, CARP, IPV6, MAC, MAX_PEERS = 4094 };
struct tag { unsigned tpid, vid; };
struct peer { int vlan, pid, receiver; uint8_t source[4], mac[6]; };
static struct peer peers[MAX_PEERS];
static struct pollfd monitors[MAX_PEERS + 1];
static uint8_t infra[MAX_PEERS * 3][4];
static int npeers, ninfra, current, sender, count, offline;
static int timing;
static double started;
static uint64_t fixture_hash = UINT64_C(14695981039346656037);
static const char *kinds[] = { "ip", "arp", "dhcp", "carp", "ipv6", "mac" };

static void require(int ok, const char *message)
{
    if (!ok) {
        fprintf(stderr, "pf-l2: %s\n", message);
        exit(1);
    }
}

static void system_ok(int ok, const char *message)
{
    if (!ok) {
        perror(message);
        exit(1);
    }
}

static void put16(uint8_t *p, unsigned value)
{
    p[0] = value >> 8;
    p[1] = value;
}

static unsigned get16(const uint8_t *p)
{
    return (unsigned)p[0] * 256 + p[1];
}

static unsigned checksum(const uint8_t *p, size_t n)
{
    unsigned sum = 0;
    for (; n > 1; n -= 2, p += 2)
        sum += get16(p);
    if (n) sum += (unsigned)*p << 8;
    while (sum >> 16) sum = (sum & 65535) + (sum >> 16);
    return sum ^ 65535;
}

static size_t frame(uint8_t *packet, const uint8_t *mac, const uint8_t *source,
                    int kind, const struct tag *tags, int ntags, const uint8_t *token)
{
    uint8_t *p, *udp;
    size_t offset = 12, length;
    memset(packet, 0, 512);
    memset(packet, 255, 6);
    memcpy(packet + 6, mac, 6);
    for (int i = 0; i < ntags; i++, offset += 4) {
        put16(packet + offset, tags[i].tpid);
        put16(packet + offset + 2, tags[i].vid);
    }
    put16(packet + offset, kind == ARP ? 0x0806 : kind == IPV6 ? 0x86dd : 0x0800);
    offset += 2;
    p = packet + offset;
    if (kind == ARP) {
        put16(p, 1);
        put16(p + 2, 0x0800);
        p[4] = 6;
        p[5] = 4;
        put16(p + 6, 2);
        memcpy(p + 8, mac, 6);
        memcpy(p + 14, source, 4);
        memset(p + 24, 255, 4);
        length = 28;
    } else if (kind == IPV6) {
        uint8_t pseudo[80] = {0};
        p[0] = 0x60;
        put16(p + 4, 40);
        p[6] = 17;
        p[7] = 64;
        p[8] = 0xfd;
        p[23] = 0x10;
        p[24] = 0xff;
        p[25] = 2;
        p[39] = 1;
        udp = p + 40;
        put16(udp, 46991);
        put16(udp + 2, 46991);
        put16(udp + 4, 40);
        memcpy(udp + 8, token, 32);
        memcpy(pseudo, p + 8, 32);
        pseudo[35] = 40;
        pseudo[39] = 17;
        memcpy(pseudo + 40, udp, 40);
        put16(udp + 6, checksum(pseudo, sizeof(pseudo)));
        length = 48;
    } else {
        p[0] = 0x45;
        p[8] = 255;
        p[9] = kind == CARP ? 112 : 17;
        memcpy(p + 12, source, 4);
        memset(p + 16, 255, 4);
        if (kind == CARP) {
            memcpy(p + 20, "\x21\x01\x00\x07\x00\x01\x00\x00", 8);
            memcpy(p + 56, token, 32);
            put16(p + 26, checksum(p + 20, 68));
            length = 56;
        } else {
            udp = p + 20;
            put16(udp, kind == DHCP ? 67 : 46991);
            put16(udp + 2, kind == DHCP ? 68 : 46991);
            length = 28;
            if (kind == DHCP) {
                uint8_t *bootp = udp + 8;
                memcpy(bootp, "\x02\x01\x06\x00\x43\x56\x4c\x32", 8);
                put16(bootp + 10, 0x8000);
                memcpy(bootp + 16, source, 4);
                bootp[19] = 12;
                memcpy(bootp + 20, source, 4);
                memcpy(bootp + 28, "\x02\x00\x00\xff\xff\x01", 6);
                memcpy(bootp + 236, "\x63\x82\x53\x63\x35\x01\x02\x36\x04", 9);
                memcpy(bootp + 245, source, 4);
                bootp[249] = 255;
                length += 250;
            }
            put16(udp + 4, length + 32 - 20);
        }
        put16(p + 2, length + 32);
        put16(p + 10, checksum(p, 20));
    }
    memcpy(p + length, token, 32);
    return offset + length + 32;
}

static double monotonic(void)
{
    struct timespec now;
    system_ok(clock_gettime(CLOCK_MONOTONIC, &now) == 0, "clock_gettime");
    return now.tv_sec + now.tv_nsec / 1e9;
}

static void duration(void)
{
    if (!timing) return;
    timing = 0;
    printf("CV-TIME pf-l2-%d-%d-duration %d\n", peers[current].vlan, count,
           (int)(monotonic() - started));
}

static void hash_fixture(const uint8_t *data, size_t length)
{
    for (size_t i = 0; i < length; i++)
        fixture_hash = (fixture_hash ^ data[i]) * UINT64_C(1099511628211);
}

static int packet_socket(int pid)
{
    char path[64];
    int original, target, fd;
    struct sockaddr_ll address = {0};
    original = open("/proc/self/ns/net", O_RDONLY | O_CLOEXEC);
    snprintf(path, sizeof(path), "/proc/%d/ns/net", pid);
    target = open(path, O_RDONLY | O_CLOEXEC);
    system_ok(original >= 0 && target >= 0, "open netns");
    system_ok(setns(target, 0) == 0, "setns");
    fd = socket(AF_PACKET, SOCK_RAW | SOCK_NONBLOCK | SOCK_CLOEXEC, htons(3));
    system_ok(fd >= 0, "socket");
    address.sll_family = AF_PACKET;
    address.sll_protocol = htons(3);
    address.sll_ifindex = if_nametoindex("eth0");
    system_ok(address.sll_ifindex != 0, "eth0");
    system_ok(bind(fd, (struct sockaddr *)&address, sizeof(address)) == 0, "bind");
    system_ok(setns(original, 0) == 0, "restore setns");
    close(target);
    close(original);
    return fd;
}

static int exchange(const uint8_t *packet, size_t length, const uint8_t *token, int allowed)
{
    uint8_t buffer[65535], received[MAX_PEERS + 1] = {0};
    ssize_t n;
    for (int i = 0; i <= npeers; i++) {
        do { n = recv(monitors[i].fd, buffer, sizeof(buffer), 0); } while (n >= 0);
        system_ok(errno == EAGAIN || errno == EWOULDBLOCK, "drain");
    }
    for (int attempt = 0; attempt < 3; attempt++) {
        system_ok(send(sender, packet, length, 0) == (ssize_t)length, "injection");
        double until = monotonic() + 0.2, remaining;
        while ((remaining = until - monotonic()) > 0) {
            system_ok(poll(monitors, npeers + 1, (int)(remaining * 1000) + 1) >= 0, "poll");
            for (int i = 0; i <= npeers; i++) {
                system_ok(!(monitors[i].revents & (POLLERR | POLLHUP | POLLNVAL)), "monitor");
                if (!(monitors[i].revents & POLLIN)) continue;
                n = recv(monitors[i].fd, buffer, sizeof(buffer), 0);
                system_ok(n >= 0, "recv");
                if (memmem(buffer, (size_t)n, token, 32)) received[i] = 1;
            }
        }
    }
    if (!received[0]) {
        fprintf(stderr, "pf-l2: no local delivery control\n");
        return 0;
    }
    for (int i = 0; i < npeers; i++) {
        if (received[i + 1] != (allowed && i == current)) {
            fprintf(stderr, "pf-l2: delivered to [");
            const char *separator = "";
            for (int j = 0; j < npeers; j++) {
                if (!received[j + 1]) continue;
                fprintf(stderr, "%s%d", separator, peers[j].vlan);
                separator = ", ";
            }
            fprintf(stderr, "], want %s\n", allowed ? "local VLAN" : "none");
            return 0;
        }
    }
    return 1;
}

static void check(const char *label, int kind, const struct tag *tags, int ntags,
                  const uint8_t *source, int allowed)
{
    uint8_t packet[512], token[33];
    const uint8_t spoof[6] = {2, 0, 0, 255, 255, 255};
    int ok, n;
    started = monotonic();
    count++;
    if (offline) {
        memcpy(token, "testtesttesttesttesttesttesttest", 32);
    } else {
        n = snprintf((char *)token, sizeof(token), "CV-L2-%08ld-%08d", (long)getpid(), count);
        require(n >= 0 && n <= 32, "token too long");
        memset(token + n, '!', 32 - n);
    }
    size_t length = frame(packet, kind == MAC ? spoof : peers[current].mac,
                          source, kind, tags, ntags, token);
    if (offline) {
        size_t offset = 12;
        require(memcmp(packet + length - 32, token, 32) == 0, label);
        for (int i = 0; i < ntags; i++, offset += 4)
            require(get16(packet + offset) == tags[i].tpid &&
                    get16(packet + offset + 2) == tags[i].vid, label);
        if (kind != ARP && kind != IPV6)
            require(checksum(packet + offset + 2, 20) == 0, label);
        hash_fixture((const uint8_t *)label, strlen(label) + 1);
        hash_fixture(packet, length);
        return;
    }
    timing = 1;
    ok = exchange(packet, length, token, allowed);
    if (ok) printf("CV-PF L2 ok vlan=%d case=%s\n", peers[current].vlan, label);
    duration();
    if (!ok) {
        fprintf(stderr, "pf-l2: %d/%s failed\n", peers[current].vlan, label);
        exit(1);
    }
}

static void blocked(const char *label, int kind, const struct tag *tags, int ntags,
                    const uint8_t *source)
{
    if (!offline) check("delivery-before", IP, NULL, 0, peers[current].source, 1);
    check(label, kind, tags, ntags, source ? source : peers[current].source, 0);
    if (!offline) check("delivery-after", IP, NULL, 0, peers[current].source, 1);
}

static void cases(void)
{
    int vlan = peers[current].vlan;
    struct tag tags[2] = {{0x8100, vlan}, {0, 0}};
    char label[96];
    const unsigned tpids[][2] = {{0x8100, 0x8100}, {0x8100, 0x88a8}, {0x88a8, 0x8100}};
    for (int tagged = 0; tagged < 2; tagged++) {
        const char *name = tagged ? "tagged" : "native";
        for (int i = 0; i < ninfra; i++) {
            for (int kind = IP; kind <= ARP; kind++) {
                snprintf(label, sizeof(label), "%s-%s-%u.%u.%u.%u", name, kinds[kind],
                         infra[i][0], infra[i][1], infra[i][2], infra[i][3]);
                blocked(label, kind, tags, tagged, infra[i]);
            }
        }
        for (int kind = DHCP; kind <= IPV6; kind++) {
            snprintf(label, sizeof(label), "%s-%s", name, kinds[kind]);
            blocked(label, kind, tags, tagged, NULL);
        }
    }
    for (int i = 0; i < npeers; i++) {
        int other = peers[i].vlan;
        if (other == vlan) continue;
        tags[0] = (struct tag){0x8100, other};
        snprintf(label, sizeof(label), "wrong-vlan-%d", other);
        blocked(label, IP, tags, 1, NULL);
        for (int outer = 0; outer < 2; outer++) {
            for (int pair = 0; pair < 3; pair++) {
                tags[0] = (struct tag){tpids[pair][0], outer ? 0 : vlan};
                tags[1] = (struct tag){tpids[pair][1], other};
                snprintf(label, sizeof(label), "stacked-%x-%x-%u-%d",
                         tags[0].tpid, tags[1].tpid, tags[0].vid, other);
                blocked(label, IP, tags, 2, NULL);
            }
        }
    }
    tags[0] = (struct tag){0x88a8, vlan};
    blocked("service-tag", IP, tags, 1, NULL);
    blocked("mac-spoof", MAC, NULL, 0, NULL);
}

int main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IOLBF, 0);
    require(atexit(duration) == 0, "atexit");
    require(argc == 2, "usage: pf-l2-bin <peers> | --selftest");
    if (strcmp(argv[1], "--selftest") == 0) {
        offline = 1;
        npeers = 4;
        peers[0].vlan = 320;
        peers[1].vlan = 330;
        peers[2].vlan = 360;
        peers[3].vlan = 370;
        memcpy(peers[0].mac, "\x00\x16\x3e\x80\x00\x10", 6);
        inet_pton(AF_INET, "100.80.32.10", peers[0].source);
        inet_pton(AF_INET, "100.80.32.62", infra[0]);
        ninfra = 1;
        cases();
        require(count == 33, "case count");
        /* Original Python frames and labels, with the live spoofed MAC. */
        require(fixture_hash == UINT64_C(0x7b7066e88bea1d11), "packet fixture bytes");
        puts("CV-PF L2 packet fixtures passed");
        return 0;
    }
    FILE *input = fopen(argv[1], "r");
    char line[256], source[16], extra;
    system_ok(input != NULL, "open peers");
    while (fgets(line, sizeof(line), input)) {
        unsigned mac[6];
        require(npeers < MAX_PEERS, "too many peers");
        struct peer *p = &peers[npeers];
        require(sscanf(line, "%d %15s %d %x:%x:%x:%x:%x:%x %d %c", &p->vlan, source,
                       &p->pid, &mac[0], &mac[1], &mac[2], &mac[3], &mac[4], &mac[5],
                       &p->receiver, &extra) == 10, "invalid peer row");
        require(p->vlan > 0 && p->vlan <= 4094 && p->pid > 0 && p->receiver > 0 &&
                inet_pton(AF_INET, source, p->source) == 1, "invalid peer");
        for (int i = 0; i < npeers; i++) require(peers[i].vlan != p->vlan, "duplicate VLAN");
        for (int i = 0; i < 6; i++) {
            require(mac[i] <= 255, "invalid MAC");
            p->mac[i] = mac[i];
        }
        const int last[] = {49, 50, 62};
        for (int i = 0; i < 3; i++) {
            memcpy(infra[ninfra], p->source, 4);
            infra[ninfra++][3] = last[i];
        }
        npeers++;
    }
    require(!ferror(input), "read peers");
    fclose(input);
    require(npeers > 0, "no peers");
    for (int i = 0; i < npeers; i++) {
        monitors[i + 1].fd = packet_socket(peers[i].receiver);
        monitors[i + 1].events = POLLIN;
    }
    for (current = 0; current < npeers; current++) {
        struct peer *p = &peers[current];
        sender = packet_socket(p->pid);
        monitors[0].fd = packet_socket(p->pid);
        monitors[0].events = POLLIN;
        cases();
        struct tag tag = {0x8100, p->vlan};
        check("assigned-tag-delivery", IP, &tag, 1, p->source, 1);
        close(sender);
        close(monitors[0].fd);
    }
    for (int i = 1; i <= npeers; i++) close(monitors[i].fd);
    return 0;
}
