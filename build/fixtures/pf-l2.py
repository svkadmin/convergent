#!/usr/bin/env python3
"""Raw frames through real owner-profile NICs; no guest packages or IP stack needed."""
import ctypes
import json
import os
import select
import socket
import struct
import subprocess
import sys
import time


def checksum(data):
    words = struct.unpack("!%dH" % (len(data) // 2), data)
    total = sum(words)
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return total ^ 65535


def frame(mac, source, kind, tags, token):
    smac = bytes.fromhex(mac.replace(":", ""))
    src = socket.inet_aton(source)
    dst = socket.inet_aton("255.255.255.255")
    ethertype = 0x0800
    if kind == "arp":
        ethertype = 0x0806
        payload = struct.pack("!HHBBH", 1, 0x0800, 6, 4, 2) + smac + src + bytes(6) + dst + token
    elif kind == "ipv6":
        ethertype = 0x86DD
        udp = struct.pack("!HHHH", 46991, 46991, 8 + len(token), 0) + token
        src6, dst6 = socket.inet_pton(socket.AF_INET6, "fd00::10"), socket.inet_pton(socket.AF_INET6, "ff02::1")
        pseudo = src6 + dst6 + struct.pack("!I3xB", len(udp), 17)
        udp = udp[:6] + struct.pack("!H", checksum(pseudo + udp)) + udp[8:]
        payload = struct.pack("!IHBB", 6 << 28, len(udp), 17, 64) + src6 + dst6 + udp
    else:
        protocol = 112 if kind == "carp" else 17
        if kind == "carp":
            payload = bytes.fromhex("2101000700010000") + bytes(28) + token
            payload = payload[:6] + struct.pack("!H", checksum(payload)) + payload[8:]
        else:
            if kind == "dhcp":
                # BOOTP offer with a test transaction ID; no legitimate client's MAC is used.
                bootp = struct.pack("!BBBBIHH", 2, 1, 6, 0, 0x43564C32, 0, 0x8000)
                bootp += bytes(4) + socket.inet_aton(source.rsplit(".", 1)[0] + ".12") + src + bytes(4)
                bootp += bytes.fromhex("020000ffff01") + bytes(202)
                token = bootp + bytes.fromhex("638253633501023604") + src + b"\xff" + token
            payload = struct.pack("!HHHH", 67 if kind == "dhcp" else 46991,
                                  68 if kind == "dhcp" else 46991, 8 + len(token), 0) + token
        header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 0, 0, 255, protocol, 0, src, dst)
        payload = header[:10] + struct.pack("!H", checksum(header)) + header[12:] + payload
    ethernet = b"\xff" * 6 + smac
    for tpid, vid in tags:
        ethernet += struct.pack("!HH", tpid, vid)
    return ethernet + struct.pack("!H", ethertype) + payload


def query(path):
    return json.loads(subprocess.check_output(["incus", "--force-local", "query", path], timeout=10))


def packet_socket(pid, interface):
    original = os.open("/proc/self/ns/net", os.O_RDONLY)
    target = os.open(f"/proc/{pid}/ns/net", os.O_RDONLY)
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        if libc.setns(target, 0) != 0:
            raise OSError(ctypes.get_errno(), "setns")
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
        sock.bind((interface, 0))
        sock.setblocking(False)
    finally:
        if libc.setns(original, 0) != 0:
            raise OSError(ctypes.get_errno(), "restore setns")
        os.close(target)
        os.close(original)
    return sock


def exchange(sender, monitors, packet, token):
    for sock in monitors:
        while select.select([sock], [], [], 0)[0]:
            sock.recv(65535)
    received = set()
    for _ in range(3):
        assert sender.send(packet) == len(packet), "short injection"
        until = time.monotonic() + 0.2
        while time.monotonic() < until:
            for sock in select.select(monitors, [], [], max(0, until - time.monotonic()))[0]:
                if token in sock.recv(65535):
                    received.add(sock)
    return received


def cases(vlan, others, infra):
    for tagname, tags in (("native", []), ("tagged", [(0x8100, vlan)])):
        for source in infra:
            for kind in ("ip", "arp"):
                yield f"{tagname}-{kind}-{source}", kind, tags, source
        for kind in ("dhcp", "carp", "ipv6"):
            yield f"{tagname}-{kind}", kind, tags, None
    for other in others:
        yield f"wrong-vlan-{other}", "ip", [(0x8100, other)], None
        for outer in (vlan, 0):
            for first, second in ((0x8100, 0x8100), (0x8100, 0x88A8), (0x88A8, 0x8100)):
                yield f"stacked-{first:x}-{second:x}-{outer}-{other}", "ip", [(first, outer), (second, other)], None
    yield "service-tag", "ip", [(0x88A8, vlan)], None
    yield "mac-spoof", "mac", [], None


def main():
    rows = [line.split() for line in open(sys.argv[1]) if line.split()[-1:] in (["dev"], ["jhn"])]
    infra = [row[4].split(".")[0:3] + [str(last)] for row in rows for last in (49, 50, 62)]
    infra = [".".join(address) for address in infra]
    assert open("/sys/class/net/work/bridge/vlan_filtering").read().strip() == "1", "VLAN filtering disabled"
    peers = {}
    for row in rows:
        vlan = int(row[2][4:])
        name = f"pf-work-l2-{vlan}"
        instance = query(f"/1.0/instances/{name}?project=owner")
        nic = instance["expanded_devices"]["eth0"]
        assert nic["vlan"] == str(vlan) and nic["security.mac_filtering"] == "true", nic
        print("CV-PF L2 NIC", name, json.dumps({k: v for k, v in nic.items() if k.startswith("security.") or k.startswith("vlan")}), flush=True)
        pid = query(f"/1.0/instances/{name}/state?project=owner")["pid"]
        peers[vlan] = packet_socket(pid, "eth0")
    count = 0
    for row in rows:
        vlan = int(row[2][4:])
        name = f"pf-work-{vlan}"
        instance = query(f"/1.0/instances/{name}?project=owner")
        nic = instance["expanded_devices"]["eth0"]
        assert nic["vlan"] == str(vlan) and nic["security.mac_filtering"] == "true", nic
        mac = instance["expanded_config"]["volatile.eth0.hwaddr"]
        pid = query(f"/1.0/instances/{name}/state?project=owner")["pid"]
        sender, emitted = packet_socket(pid, "eth0"), packet_socket(pid, "eth0")
        monitors = [emitted] + list(peers.values())
        source = row[4].rsplit(".", 1)[0] + ".10"

        def check(label, kind, tags, address, allowed):
            nonlocal count
            started = time.monotonic()
            count += 1
            token = f"CV-L2-{os.getpid():08d}-{count:08d}".encode().ljust(32, b"!")
            packet = frame("02:00:00:ff:ff:ff" if kind == "mac" else mac, address or source, kind, tags, token)
            try:
                got = exchange(sender, monitors, packet, token)
                assert emitted in got, f"{label}: no local delivery control"
                want = {emitted, peers[vlan]} if allowed else {emitted}
                assert got == want, f"{vlan}/{label}: delivered to {[v for v, s in peers.items() if s in got]}, want {'local VLAN' if allowed else 'none'}"
                print(f"CV-PF L2 ok vlan={vlan} case={label}", flush=True)
            finally:
                print(f"CV-TIME pf-l2-{vlan}-{count}-duration {int(time.monotonic() - started)}", flush=True)

        for label, kind, tags, address in cases(vlan, [v for v in peers if v != vlan], infra):
            check("delivery-before", "ip", [], source, True)
            check(label, kind, tags, address, False)
            check("delivery-after", "ip", [], source, True)
        check("assigned-tag-delivery", "ip", [(0x8100, vlan)], source, True)
        sender.close()
        emitted.close()
    for name in ("fw1work", "fw2work"):
        ports = json.loads(subprocess.check_output(["bridge", "-j", "vlan", "show", "dev", name], timeout=10))
        assert len(ports) == 1 and ports[0]["vlans"], ports
        assert all(not entry.get("flags") for entry in ports[0]["vlans"]), "native VLAN on firewall trunk"


def selftest():
    token = b"test" * 8
    for name, kind, tags, source in cases(320, [330, 360, 370], ["100.80.32.62"]):
        data = frame("00:16:3e:80:00:10", source or "100.80.32.10", kind, tags, token)
        assert data.endswith(token), name
        offset = 12
        for tpid, vid in tags:
            assert struct.unpack_from("!HH", data, offset) == (tpid, vid)
            offset += 4
        if kind not in ("arp", "ipv6"):
            assert checksum(data[offset + 2:offset + 22]) == 0
    assert len(list(cases(320, [330, 360, 370], ["100.80.32.62"]))) == 33
    print("CV-PF L2 packet fixtures passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        main()
