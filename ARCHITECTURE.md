# Convergent architecture

Convergent is a single-owner laptop system built for security first and daily use second,
with no trade of one for the other. The machine converges on the state declared in this
repository: everything it runs is built from here, verified at boot, and replaced as a
whole on update.

This file is the design and the reasons for it. It describes the target; parts marked
*(planned)* are not built yet. What runs today is in the README's Status table. Section 14
compares Convergent with its predecessor, Archer.

---

## 1. Principles

1. **Verified, not trusted.** The kernel checks every block of the operating system as it is
   read. Signed boot *(planned)* would extend that to the firmware, the boot loader and the kernel
   image, so nothing on the laptop can change the operating system without the build key.
2. **Built elsewhere.** A build host compiles, assembles and signs. The laptop receives
   images; it has no compiler and no package manager at run time.
3. **Compartments with one policy point.** The radio, the firewalls, the services, the
   browsers and every guest sit in their own compartment. All traffic between compartments
   passes the firewall pair; network policy lives nowhere else.
4. **Fail closed.** With both firewalls down, nothing talks to anything.
5. **Replace, don't patch.** Updates swap a whole image. The previous image stays bootable.
6. **Plain files.** Configuration is kept as files and templates in this repository; build-time
   settings come from the validated config file.
7. **Small.** Every component earns its memory and its code. Idle target: under 3 GB with
   every guest running, to be measured, not assumed.

---

## 2. Overview

```
                        Wi-Fi card (VFIO)
                              |
                      +---------------+
                      |  wan    (VM)  |  Alpine. The radio, upstream DHCP, the one NAT.
                      +-------+-------+
                              | transit
            +-----------------+-----------------+
            |                                   |
    +-------+-------+     sync link     +-------+-------+
    |  fw1    (VM)  |-------------------|  fw2    (VM)  |  OpenBSD. pf, CARP, pfsync,
    +-------+-------+                   +-------+-------+  unbound. Route all segments.
            |  one CARP gateway address per segment     |  The gateway is the resolver.
  +---------+--------+-----------+------------+----------+-----------+
  | host             | svc       | web        | admin    | guests    |
 HOST              svc (ct)    browsers     admin       user containers
 Gentoo, OpenRC,   Alpine:     (Incus ct)   browser     and VMs (Incus)
 Sway, Incus;      metrics,    web, tmp,    (Incus ct)
 its only address  logs,       portal       for
 is on "host"      alerts                   Grafana
```

Segments are Layer-2 bridges on the host. The host holds an IP address only on the `host`
segment and ignores every other bridge (section 4.4). Every guest has a fixed address that
Incus binds to its virtual NIC, so it cannot send as anyone else (wan is the exception; section
4.1).

---

## 3. Components

### 3.1 Host

| Area | Design |
|---|---|
| Base | Gentoo, hardened profile, OpenRC, glibc |
| Kernel | Gentoo distribution kernel, hardened configuration plus a Convergent fragment: confidentiality lockdown; every module signed with a key that exists only during the build; no kexec; no hibernation; DM, DM_INIT, DM_VERITY, EROFS and the storage drivers built in; drivers for unused protocols, filesystems and buses (FireWire, legacy network protocols) left out of the build rather than blacklisted; the Wi-Fi driver left out, so the host cannot take the radio back |
| Kernel settings | One sysctl file, carried from Archer: ptrace, perf, BPF and kernel-pointer restrictions, dmesg restricted, protected links and FIFOs, TIOCSTI and line-discipline loading off, strict network settings (no redirects, no source routing, martians logged, reverse-path filtering), no core dumps |
| IOMMU and DMA | `intel_iommu=on iommu.strict=1 efi=disable_early_pci_dma`; Thunderbolt DMA protection *(planned:* verified at boot*)*; every NVIDIA function bound to vfio-pci before any driver probes it and left powered down; the Wi-Fi function must sit alone in its IOMMU group, with no ACS override |
| Mandatory access control | AppArmor enforcing; Incus generates and loads a profile per container and VM |
| Audit | auditd with immutable rules for identity files, the guests' SSH keys, the accepted check baseline, the DNS files, authentication, privilege changes, boot files, keys, module loading, policy changes and commands run as root; records forwarded to svc |
| Accounts | root locked; the owner in `wheel`, `seat`, `audio` and `video` only; `su` limited to `wheel`; sudo with a 5-minute ticket, a PTY and its own log; passwords hashed with yescrypt; faillock after 5 failures for 15 minutes; restrictive umask |
| Boot | systemd-boot (the boot loader only, from `systemd-utils`; no systemd init), editor disabled; one unified kernel image (UKI) per slot. *(Planned:* signing with the owner's key, a recovery UKI*)* |
| Root filesystem | A read-only EROFS image per slot, A and B. The kernel creates the dm-verity device from the UKI command line; the root hash will be covered by the Secure Boot signature *(planned)* |
| State | One LUKS2 volume (Argon2id) with Btrfs: `/var`, `/home`, a short list of machine-specific `/etc` files, the Incus pool; `/home`, `/tmp` and the state mounts `nodev`, `nosuid`, and `noexec` where nothing needs to run from them |
| Memory | No disk swap; zram swap of 32 GiB (a ceiling, not a reservation; its index costs about 128 MiB), zswap off *(planned)* |
| Seat and session | seatd; Sway, foot, bemenu, mako, swaylock, swayidle; PipeWire and WirePlumber started by the session; sof-firmware and alsa-ucm-conf for the SoundWire audio |
| Virtualisation | Incus: QEMU/KVM for VMs, LXC for containers |
| Devices | USBGuard, default deny, including devices present at boot; an allow-list for the internal keyboard, touchpad and the owner's devices, changed only by root from the menu, plus a recovery-stick entry. Thunderbolt PCIe tunnels need approval from the menu where the firmware asks; DisplayPort over USB-C works without approval. Bluetooth off; switched on from the menu |
| Power | Never suspends. CPU energy preference and a clock cap (`cpu_cap_khz`, 4.2 GHz by default) set per power source by a small handler on AC events; runtime power management for the NVIDIA GPU and audio functions; thermal control left to the firmware; a known-noisy ACPI event masked, never the embedded controller's *(planned)* |
| Host firewall | nftables: input accepted only on the `host` interface and only from the listed sources (section 4.2); forwarding off |
| Logs | syslog-ng, forwarded to svc over TLS; a bounded local buffer for when svc is down |
| Crashes | Kernel crash records from pstore archived at boot by `facts`, run from cron, and reported to svc |
| Time | chrony with NTS from three sources, needing two to agree; starts without waiting for the network; serves NTP to the firewalls |
| Listening on the host | chrony (UDP 123, from the firewalls only), node_exporter (TCP 9100, from svc only) and Incus' metrics endpoint (TCP 8444, TLS with a client certificate, from svc only). Nothing else |

### 3.2 wan (VM)

Alpine with its LTS kernel. Owns the Wi-Fi card by VFIO passthrough, joins networks with iwd,
takes the upstream address by DHCP and performs the only NAT in the system.

- **Privacy on the air:** a random MAC address per network, the regulatory country set,
  protected management frames where the network offers them, a DHCP client that sends no host
  name, no mDNS or LLMNR.
- **Networks:** join, forget, hidden networks and roaming between known networks, all from the
  menu. Credentials are sent over SSH on standard input and live only in wan. A replaced wan keeps
  its predecessor's saved networks (section 7.2).
- **Wired uplink:** a USB network adapter approved in USBGuard can be passed to wan as an
  uplink. No other role.
- **Egress:** wan's own traffic is limited to DHCP and the NAT; it starts nothing toward the
  inside except syslog to svc.
- **Management:** no Incus agent and no guest API; SSH from the host only, on its transit address.
- **Overlap:** refuses an upstream lease that overlaps the internal range and raises an alert.
- **Captive portals:** DNS to wan's transit address is passed to the upstream resolver (a NAT
  rule, no forwarder process), only from the portal browser and only while portal mode is on;
  portal mode ends by itself after 30 minutes.
- **Time:** from the host clock (PTP over KVM, disciplined by chrony in the VM).
- **Size:** memory capped at 512 MiB; the emulated HPET off and free page reporting on, both
  measured on Archer.

### 3.3 fw1, fw2 (VMs)

OpenBSD. Each has one interface per segment and a dedicated sync link to the other. The image build
applies signify-verified syspatches on a temporary DHCP boot, verifies the patched kernel on the
offline smoke boot, and records each node's installed patches in `<node>.syspatch`.

- **CARP:** one virtual host ID per segment, the same on both; fw1 with skew 0, fw2 with skew
  100; `net.inet.carp.preempt=1`, so all addresses move together; advertisements unicast to the
  peer (`carppeer`), so the Linux bridges' multicast handling plays no part.
- **pfsync** on the sync link, with `defer`, so a failover keeps established connections.
- **ifstated** demotes the whole CARP group when the wan VM stops answering (a probe of wan's
  transit address, not the interface's carrier, which a virtual NIC never loses).
- **pf** routes and filters between all segments (section 4.2), with state limits per source,
  MSS clamping toward wan, and a ruleset hash the checker compares with the release.
- **unbound**, from OpenBSD's base system, answers DNS on every segment's gateway address, so a
  failover carries DNS with it (section 4.5).
- **Routes:** default via wan's transit address; every internal segment is directly connected.
- **Also:** an NTP client of the host, node_exporter, syslog to svc, SSH from the host only.
- **No DHCP:** every address is static (section 4.1).
- **Size:** 384 MiB each.

Either firewall can be updated, rebooted or broken while the other carries everything. Each has
its own kernel: a firewall kernel bug is not a host kernel bug, and the reverse. A silent
failure is detected in about three seconds.

### 3.4 svc (container)

Alpine in an unprivileged Incus container on its own segment.

| Service | Role | Bounds |
|---|---|---|
| VictoriaMetrics | Metrics; scrapes the host, the firewalls and wan | Cache, retention and query concurrency capped |
| VictoriaLogs | Logs; receives syslog over TLS from the host, the firewalls and wan | Cache, retention and query concurrency capped |
| vmalert | Evaluates the alert rules (section 8); the status bar reads its alerts API | |
| Grafana | Dashboards. Started only while viewed, bound to svc's address, login required, anonymous access off | Stopped when not in use |

While svc restarts or is replaced, the status bar shows the alert counts as unknown rather than
stale, and the host buffers its logs. DNS does not depend on svc.

### 3.5 Browsers

Chromium runs in unprivileged Incus containers built from one browser image:

- **web:** the everyday browser, with a persistent profile volume.
- **tmp:** an ephemeral container from the same image, gone when closed.
- **portal:** an ephemeral container used only for captive portals.
- **admin:** a persistent container on the `admin` segment, the only browser that reaches Grafana.

Each container gets: the GPU render node, a Wayland socket created through Sway's security
context (no screen capture, no input injection, no other Wayland socket, no Sway IPC, no X11),
a dedicated Pulse socket from its own `pipewire-pulse` instance: playback only, recording blocked
for every role. Its own download directory. No D-Bus, so no portals and no screen sharing.

Chromium policies are part of the image: DNS-over-HTTPS off (the gateway resolves), telemetry,
studies and captive-portal probes off, and each mode labelled in its window title so the owner
always knows which browser is in front. Links opened from other programs go to `tmp` by default
*(planned)*.

### 3.6 User guests *(planned)*

Incus containers and VMs on the `guests` segment, in the owner's own Incus project, so the
owner's guests never touch the infrastructure's instances, networks or profiles.

- Each guest has a fixed address bound to its NIC and is port-isolated from the others; what it
  may reach is pf's decision, by default the resolver and the internet on web ports.
- Containers run unprivileged with their own ID range and a process limit; every guest has a
  memory limit.
- VMs use UEFI with a virtual TPM; the menu creates them from an installer image and opens their
  console.
- Infrastructure instances (fw1, fw2, wan, svc, the browsers) are protected from deletion and
  started in order at boot; a crashed one is restarted.
- A guest that needs a VPN runs it inside itself.

---

## 4. Network

### 4.1 Addressing

Internal addresses come from one /16: 100.80.0.0/16. It lies in the shared address space of RFC
6598, which carrier-grade NAT also uses; wan refuses an upstream lease that overlaps it. The range
is repeated in host, wan, firewall and tool configuration, so changing it needs coordinated edits.

| Segment | Prefix | Gateway and resolver (CARP) | fw1 | fw2 | Members |
|---|---|---|---|---|---|
| transit | 100.80.0.0/28 | .1 | .2 | .3 | wan .10 |
| sync | 100.80.0.16/30 | none | .17 | .18 | none |
| host | 100.80.1.0/28 | .1 | .2 | .3 | host .10 |
| svc | 100.80.2.0/28 | .1 | .2 | .3 | svc .10 |
| web | 100.80.3.0/24 | .1 | .2 | .3 | web .10, portal .11, tmp .20 to .99 |
| admin | 100.80.4.0/28 | .1 | .2 | .3 | admin browser .10 |
| guests | 100.80.8.0/22 | .1 | .2 | .3 | guests from .10, assigned by the menu |

Every address is static. Incus binds each guest's address and MAC to its NIC (IP and MAC
filtering on), except on the firewalls' NICs (CARP's shared MAC: unfiltered and unisolated) and on
wan's transit NIC (IPv4 filtering off; MAC filtering and port isolation on). Incus' own DHCP, DNS
and NAT are off on every bridge. IPv6 is off
everywhere.

### 4.2 Flows

Everything not listed is dropped. DNS to a segment's own gateway address is allowed on every
segment except transit and sync; it is not repeated below.

| From | To | Ports | Why |
|---|---|---|---|
| host | internet | NTP 123, NTS-KE 4460 | Time |
| host | update source | HTTPS 443 | Releases: the download server's addresses, opened by `fetch-release` only while it runs (a failed close expires within 4 hours) |
| host | blocklist source | HTTPS 443 | Weekly blocklist download |
| host | svc | syslog 6514, vmalert 8880, VictoriaLogs query 9428 | Logs, alert counts, the menu's log view |
| host | fw1, fw2, wan | SSH 22 | Management, Wi-Fi credentials, blocklist and record pushes |
| fw1, fw2 | host | NTP 123 | Time |
| fw1, fw2 | internet | DoT 853 to the forwarders | Resolution |
| svc | host, fw1, fw2, wan | 9100 | Metrics scrape |
| svc | host | Incus metrics 8444 | Instance state |
| fw1, fw2, wan | svc | syslog 6514 | Logs |
| web (web, tmp) | internet | 80, 443 (TCP and UDP) | Browsing |
| web | upstream LAN | IPP 631, only when printing is switched on *(planned)* | Printing |
| web (portal) | wan | DNS 53, only in portal mode | Captive portal resolution |
| web (portal) | upstream LAN | 80, 443, only in portal mode | The portal page |
| admin | svc | Grafana 3000 | Dashboards |
| guests | internet | per guest; default 80, 443 | Guest work |
| wan | anything internal | nothing it starts, except syslog to svc | Untrusted |

"Internet" means public addresses; the upstream LAN's private ranges are not part of it. Both the
firewalls and wan enforce that: wan forwards to private ranges only from the portal browser, and
only in portal mode.

### 4.3 Failover

The active firewall answers on every CARP address. If it stops, the other takes every address
within about three seconds and already holds the connection state. NAT happens only in wan, so
the outside address never changes during a failover. The resolver moves with the gateway. If
both stop, every segment is cut off.

### 4.4 The host and the bridges

A bridge without an address is still an interface of the host, so the host is made to ignore
them explicitly: nftables drops input on every interface but the `host` one, ARP is ignored on
the other bridges, reverse-path filtering is strict, and forwarding is off. The host is never a
router; the firewalls are.

### 4.5 DNS

- **Resolution:** unbound on both firewalls forwards over DNS-over-TLS to forwarders given by
  address and certificate name, validates DNSSEC, and answers only internal segments.
- **IPv4 only:** DNS transport is IPv4 only; AAAA answers are not suppressed. The DNS-over-HTTPS
  canary domain answers NXDOMAIN, so applications fall back to the system resolver.
- **Local names:** built-in names and reverse records come from the `local-names.conf` template,
  filled with the address prefixes when the firewall image is built. Other names are the owner's
  records: one file, validated and pushed to both firewalls together with the blocklist.
- **Blocklist:** an RPZ zone. The host downloads it weekly, retries on failure, validates it,
  and pushes the same file to both firewalls over SSH; the last good copy stays in force until
  a new one validates. A short allow-list file holds the owner's exceptions.

---

## 5. Storage and boot

### 5.1 Disk

| Partition | Content |
|---|---|
| ESP | systemd-boot, the UKIs of both slots, the recovery UKI *(planned)* |
| slot A, slot B | EROFS images with their dm-verity hash trees |
| state | LUKS2 (Argon2id), Btrfs: `/var` (with a snapshot per slot generation), `/home`, `/etc` entries, the Incus pool |

Btrfs is trimmed weekly and scrubbed monthly. Selected custom volumes have size limits; a pool-wide
quota *(planned)* would keep guests and logs from filling the space `/var` and `/home` need.

### 5.2 Boot

1. Firmware verifies systemd-boot with the owner's key *(planned)*.
2. systemd-boot picks the slot (section 7.3) and starts its UKI.
3. The kernel creates the dm-verity device for the slot from the UKI command line.
4. The initramfs mounts the verity device read-only as the new root. It refuses to boot while more
   than one disk has a `cv-state` partition, asks for the LUKS passphrase and opens the state
   volume. When the state partition is the last one and more than 1 GiB is free, it grows the
   volume to the end of the disk, or to the `state_max_gib` cap (partition, LUKS, then Btrfs on every
   boot); an interrupted grow
   finishes on a later boot. It selects the `/var` that belongs to this slot, takes a cold snapshot
   of it on the first boot of a new slot, mounts `/var` and `/home`, bind-mounts the listed `/etc`
   entries, mounts `/run` and `/tmp` as tmpfs, arms the hardware watchdog, and switches to the real
   root.
5. OpenRC starts the host, then Incus, then the guests: fw1, fw2, wan, svc. Nothing in the start
   sequence needs a name before the firewalls' resolvers answer.

Verity checks every block when it is read: a tampered block fails to read, at boot or later.

### 5.3 What is writable

Everything under `/usr` and the rest of `/etc` comes from the verified image. The writable `/etc`
entries are an explicit list: `machine-id`, `passwd`, `shadow`, `group`, `gshadow`, `subuid`,
`subgid` and `usbguard/rules.conf`. Incus and guest SSH keys live under `/var/lib`. `/home`, those
`/etc` entries and the guests' volumes are where an attacker could persist; the checker watches
selected files there, not guest-volume contents.

---

## 6. Build and keys

The build host is a dedicated machine (a VM today) that does nothing else. It holds:

- a build environment: a signed Gentoo stage3 chroot;
- a Portage snapshot pinned by date and verified by signature;
- `/etc/portage` from this repository;
- a binary package cache: Gentoo's official hardened binary packages where they match, our own
  builds where USE flags differ;
- the outputs of each release.

`portage/overlay` holds the two packages Gentoo does not offer as needed: `aa-exec` alone, with
which Incus confines its image unpacker (the stock apparmor-utils would bring Python into the
image), and `way-secure`, which gives each browser a restricted Wayland security context.

Releases are signed per channel with Ed25519 (OpenSSL): the image carries its channel's public
key, and `slot write` takes only a manifest signed with it, unless `CONVERGENT_UNSIGNED=1` overrides
the check. The `bleeding-edge` key lives on the
build host, so releases sign and publish unattended; it protects against a changed download or a
stolen bucket token, not against a compromised build host. The `stable` key is an encrypted file on
offline media, attached only to sign a release after the owner checked its manifest. Signatures
prove origin, not that a build is benign. The owner's Secure Boot key *(planned)* is kept the
same way.

A release is built in these steps (the commands are in the README):

1. Sync the pinned snapshot; refuse an unsigned one.
2. Build the `@convergent` set, and the owner's `@convergent-apps` set, into a staging root,
   from binaries where possible.
3. Copy `rootfs/` from this repository over it.
4. Use the staged kernel to build the initramfs, the EROFS image, the dm-verity tree and the
   UKIs.
5. Write the manifest: release, kernel version, root hash, file hashes.
6. Build the guest images, each with its own build: wan (Alpine), fw (OpenBSD), svc (Alpine),
   browser (Alpine).
7. Sign the manifest with the channel key (`manifest.sig`); signing the UKIs for Secure Boot is
   planned.
8. Publish: the five release files to `<channel>/<release>/` in a public object store (Cloudflare
   R2 today), then `<channel>/latest`, signed too. The manifest gives each file's size, so a
   download stops there. Two releases per channel; the bucket stays under about 9 GiB.
   Disk images (they hold the owner's account) and guest images are not published.

---

## 7. Install, update, roll back, recover

### 7.1 Install

From a Convergent USB disk carrying one release, or as a disk image (README, Install). Partition,
create LUKS and Btrfs, write slot A, install systemd-boot and slot A's UKI, register the boot entry
(physical install only) (and the removable-media path), create the owner's account. A disk image
also carries the guest images, and its first boot creates the guests. No network needed. *(Planned:*
in Setup Mode, enrolling the owner's keys and the option ROM hashes, otherwise
checking them; the stick as the recovery path when nothing on the laptop boots.*)*

`guests init` creates the management key, the TLS credentials and one shared CARP password on
the laptop; `/var/lib/convergent/guests/` keeps the last two across guest replacements. Images
hold none of them and no SSH host keys. Each guest gets only its own credentials, on a read-only
FAT16 disk labelled `CVSEED`, records once that it applied them, and ignores the disk afterwards.
The host checks that record, pins fw's and wan's first SSH host keys from the Incus console,
checks health and detaches the disk (svc has no SSH; Incus mounts its seed). Without a seed, fw
keeps CARP and its dependent daemons off and the Alpine guests keep credential-dependent services
stopped, so the fw build's seedless smoke boot leaves the release unpersonalised.

### 7.2 Update

1. Take a release, downloaded by `fetch-release` (the URL is in the image) or from a USB
   stick, and check its signature against the image's key and every hash. Refused: an update
   from a slot not yet marked good (it would overwrite the only good one), and any release not
   newer than the highest ever marked good (kept on the state volume, so a rollback by hand
   does not reopen the way to older releases).
2. Write the image to the inactive slot; read it back and verify.
3. Install its UKI with a boot counter: systemd-boot gives it three tries.
4. Reboot. The initramfs snapshots `/var` cold before anything starts.
5. After the health checks pass (no service crashed; the default runlevel running; from the boot
   runlevel the host firewall, USBGuard, audit and AppArmor running; Incus answering; the guest
   firewalls, wan, svc and the session: planned), the slot is marked good and becomes the default:
   first the highest release is recorded, then the boot counter is dropped, then the release is
   named good, so a crash at any point is safe. Every boot runs the checks. On a counted boot the
   initramfs arms a 180-second hardware watchdog that is fed for ten minutes, then left to reset the
   board; passing the checks disarms it, even after feeding stopped. A release already good disarms
   it before the checks.

Guests are updated only on a host slot already marked good, one at a time, each after an instance
export and snapshots of its custom state volumes; the last three backups per guest are kept. The
firewalls go one at a time: fw2 first, checked (CARP state, pfsync, pf ruleset hash, a resolution
through it, traffic over it for a short soak), then a failover to it, then fw1. A firewall that
fails its checks is put back to its previous image before the other is touched. A new firewall
copies nothing from the old one; after `guests update fw`, the host pushes its stored blocklist and
records (`dns-push local`, when a blocklist is stored). A new wan gets the saved Wi-Fi networks of
the old one: they are read in userspace from a copy of the old disk's partition (debugfs as an
unprivileged user, keeping only the iwd network files `.psk`, `.open` and `.8021x`); the old disk is
never mounted.

Firmware updates use signed capsules only, applied from the menu *(planned)*.

### 7.3 Roll back

- **Automatic:** a slot that fails three tries (including a hang caught by the watchdog after the
  passphrase) is skipped; the previous slot boots, and the initramfs selects the `/var` that
  belongs to it, so the Incus database matches its Incus version.
- **By hand, after a slot was marked good:** the boot menu offers the previous slot. Its `/var`
  is from before the update, so changes since then are rolled back with it. The guests are not:
  they stay as they are. *(Planned:* the menu warns before booting, and refuses when the guests
  were updated in between.*)*
- `/home` is never rolled back. *(Planned:* its own snapshots, daily for a week and weekly for a
  month.*)*

### 7.4 Recovery and backups

- **Keys:** a second LUKS passphrase, the recovery key, kept offline with the LUKS header backup and
  the Secure Boot key backup on encrypted media. *(Planned:* a menu reminder to refresh the header
  backup after any keyslot change.*)*
- **Backups:** from the menu, an export of `/home`, the writable `/etc` entries, the owner's
  guests and the custom volumes to LUKS-encrypted external media. Not in it: the infrastructure
  instances and `/var/lib/convergent`.
- **Recovery:** RECOVERY.md, numbered recipes for the failures known so far; each failure found on
  the laptop adds one. *(Planned:* the recovery UKI, restoring a guest snapshot, a restore tool
  for the backups.*)*

---

## 8. Observability

- **Metrics:** VictoriaMetrics scrapes node_exporter on the host, the firewalls and wan, and
  Incus' own metrics endpoint for instance state. Time and synchronisation come from
  node_exporter's time collector; staleness of any extra figure from the file's own age, which
  node_exporter reports. The few figures nothing else provides are written as small text files
  by the scripts of section 12: on each firewall its CARP, pf and unbound state; on the host,
  once per boot, the release numbers, Secure Boot, lockdown, the LUKS header hash and crash records,
  daily the NVMe health and NTS state. Guest updates record their timestamps in the update journal
  (`/var/lib/convergent/guests/updates`), not in the metrics.
- **Logs:** VictoriaLogs receives syslog over TLS from the host, the firewalls and wan, including
  forwarded host audit records.
  Retention is bounded by size and age.
- **Alerts:** vmalert evaluates the rules; the status bar shows the counts, or "unknown" when svc
  does not answer; Grafana shows the details. Rules, carried from Archer and adapted:

| Area | Alerts |
|---|---|
| Path | FirewallDown, CarpSplit (both masters or none), CarpFlapping, NoDefaultRoute, FirewallRulesetDrift, StateTableHigh, WanReservedLeak, UpstreamOverlap |
| DNS | ResolverDown, ResolverStale, BlocklistStale |
| Compartments | GuestStopped, GuestRestarted, ServiceDown, PassthroughDeviceMissing, HostNetdevUnexpected, GuestRouteInjected |
| Hardware and capacity | NvmeSpareLow, NvmeErrors, BatteryLow, StateVolumeHigh, IncusPoolHigh |
| Currency | ReleaseOld, GuestImageOld, GuestReleaseEOL |
| Security and time | SecureBootNotVerified, LockdownOff, KernelTainted, LuksHeaderChanged, AuditEvent, CertExpiry, ClockOffsetHigh, NtsUnauthenticated, CrashRecorded |
| Monitoring itself | CollectorStale, CollectorBroken, CheckerFailed, CheckerStale |

*(Planned:* WanReservedLeak, PassthroughDeviceMissing, HostNetdevUnexpected, GuestRouteInjected,
IncusPoolHigh, ReleaseOld, GuestImageOld, GuestReleaseEOL; the rest are in
`guests/svc/rootfs/etc/vmalert/alerts.yaml`.*)*

- **Dashboards:** four views (overview, compartments, network path, security), with firewall
  failover transitions marked on the timelines (update marks *(planned)*); opened from the menu in
  the admin browser.
- **Checker:** runs after every boot, after every update and daily; it compares the running system
  with the release (verity, pf ruleset hashes, Incus settings, the writable `/etc` entries, device
  ownership) and checks host and internal guest state. Upstream connectivity is not part of it:
  `check status` polls Wi-Fi separately. Its results become the CheckerFailed and CheckerStale
  alerts.

---

## 9. Daily use

How the owner uses it is in USAGE.md. The design points:

- **Status bar:** the path (wan, which firewall is active, svc), alert counts or "unknown", the
  release state, the idle-lock state, and the usual system figures.
- **Locking:** after 10 minutes idle by default (`idle_lock_minutes`) and when the lid closes;
  the idle lock can be paused from the bar. Never suspends.
- **Menu (`sys`):** one place for every owner action; each prints the command it runs.
- **Captive portals:** portal mode starts the portal browser and opens its two pf rules; it ends
  when the browser closes, when turned off, or after 30 minutes. The only time DNS goes anywhere
  but the firewalls.
- *(Planned:* guest and firewall actions in the menu, printing (off by default; IPP printers on
  the upstream network for the web browsers), display profiles, clipboard clearing.*)*

---

## 10. Security model

| Threat | Defence |
|---|---|
| Hostile network, rogue access point | The radio and Wi-Fi stack run in wan, with a random MAC per network; the host never parses Wi-Fi frames or upstream DHCP |
| Network attacks on the host | The host answers only chrony (to the firewalls), and node_exporter and authenticated Incus metrics (to svc), each only on its own segment |
| Malicious website | The browser runs in an unprivileged container under AppArmor, on its own segment, with a restricted Wayland socket, restricted audio and no D-Bus |
| Compromised guest | Its own fixed address bound to its NIC (not on wan, section 4.1), port isolation, pf, AppArmor; the host ignores its bridge |
| Compromised wan | Reaches only transit; the firewalls trust nothing from it; no Incus agent or guest API in it |
| Local privilege escalation on the host | Hardened kernel settings, AppArmor, sudo policy, audit records shipped off the host |
| DMA from devices | IOMMU strict; Thunderbolt PCIe tunnels need approval where the firmware asks; the NVIDIA card held by vfio-pci |
| Malicious USB device | USBGuard, default deny |
| Tampered operating system on disk | dm-verity: a changed block fails to read; the signed UKI that protects the root hash *(planned)* |
| Stolen laptop, powered off | LUKS2 with Argon2id; Secure Boot with the owner's keys *(planned)* |
| Bad update | A/B slots, boot counting, watchdog after unlock, automatic fallback with matching `/var` |
| Supply chain | Signed stage3 and snapshots pinned by date; releases signed per channel, stable with the owner's offline key |

Not defended: a compromised host (it controls every compartment, both firewalls included); a
compromised build host whose release the owner signs; an attacker with physical access while the
laptop is unlocked; firmware below Secure Boot. Persistence remains possible in `/home`, the
writable `/etc` entries and guest volumes; the checker watches selected files there, not the guest
volume contents. Logs are shipped to svc as
they are written, so an attacker on the host cannot quietly rewrite what was already sent.

Option ROMs: the firmware's own GPU driver is part of the firmware, and add-in option ROMs (the
NVIDIA card, Thunderbolt devices) are to be allowed by their exact hashes taken from the TPM event
log *(planned)*, not by enrolling Microsoft's third-party certificate.

---

## 11. Resource budget (estimates, measured in a later phase)

| Item | MiB |
|---|---|
| Host: kernel, Sway, PipeWire, status bar | 700 |
| incusd | 200 |
| wan (512 cap, plus QEMU overhead) | 500 |
| fw1 + fw2 (384 each, plus QEMU overhead, unbound with the blocklist) | 1 000 |
| svc | 350 |
| zram index for 32 GiB | 130 |
| Total, idle, browsers closed | about 2 880 |

The margin to 3 GB is small. If measurement shows it is crossed, the first levers are the zram
size and the firewalls' memory caps.

---

## 12. Our own code

Convergent writes as little as it can:

- **No daemons of our own.** Each piece is a short script started by OpenRC, cron, acpid or the
  owner, and exits when done; the bar and the watchdog feeder are the long-running exceptions.
- **Existing tools first.** What an exporter, Incus, OpenRC or a base-system tool already does is
  not written again.
- **POSIX shell** where it suffices; nothing that needs a runtime of its own.
- **A budget.** Target: the bar and every periodic script together under 1 % of one core at idle
  (Archer's equivalents used about 12 %).

| Piece | Runs | Does |
|---|---|---|
| `build/` | on the build host | Builds and tests a release (section 6) |
| `install/install` | from a Convergent USB disk | Installs a release (section 7.1) |
| `initramfs/` | at every boot | Section 5.2, step 4 |
| `slot` | by hand; once after each boot | Writes a release to the inactive slot; after the health checks, marks the booted slot good |
| `fetch-release` | from the menu (`sys system update`) | Downloads the newest signed release of the image's channel and hands it to `slot write` |
| `guests` | at first boot; by hand | Creates the guests; updates one guest, or the firewall pair in order, with checks and rollback |
| `check` | cron: after boot and updates, daily | The checker (section 8) |
| `bar` | in the session | The status bar; asks vmalert every 30 seconds |
| `sys` | from a key binding | The menu: one file per area in `/usr/lib/convergent/sys` |
| `browser` | from the menu or a key | Starts a browser container with its restricted Wayland and audio sockets |
| `facts` | at boot; hourly cron | Writes the host's extra figures for node_exporter, archives pstore records |
| `dns-push` | weekly; by hand | Downloads, validates and pushes the blocklist and the owner's records to both firewalls |
| `portal`, `devices`, `backup` | from the menu | Captive-portal mode; USB and Thunderbolt approval; the backup (section 7.4) |
| `account` | by hand; from the menu (`sys security password`) | Changes a login password on the state volume and rebinds `/etc/shadow` |
| `power` | at boot; acpid, on AC events | Sets the CPU energy preference and clock cap |
| `fw-facts` | cron on each firewall | Writes CARP, pf and unbound state for node_exporter |

---

## 13. Repository layout

The directories are in the README's Repository table. The guest images, as `guests init` and
`guests update` read them (each directory also holds the `SHA256SUMS` checked first):

- `RELEASE/guests/fw/`: `fw{1,2}.qcow2`, `fw{1,2}.{pf,rules}.sha256`.
- `RELEASE/guests/wan/`: `wan.qcow2`, `wan-metadata.tar.xz`.
- `RELEASE/guests/svc/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus.yaml`.
- `RELEASE/guests/browser/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus/{base,web,tmp,portal,admin}.yaml`.

---

## 14. From Archer

**Kept or improved:** the radio in a VM; the firewall pair (now with its own kernels, shared
connection state and DNS that fails over with it); the hardened kernel and lockdown (signed boot
*(planned)*); IOMMU and DMA rules; AppArmor, audit, account and sudo policy; USBGuard; LUKS2 and
offline header backups; NTS time; the alert set; the status bar, menu, locking and power behaviour;
browser modes with a restricted Wayland socket; the owner's Incus project and VM support
*(planned)*; the checker; the recovery recipes. Stronger: verified root and A/B updates instead of package-level
rollback; static bound addresses instead of DHCP inside; one policy point instead of firewalld
zones on the host; one monitoring copy instead of two.

**Dropped, and why:**

| Archer item | Why it goes |
|---|---|
| BIRD and BFD routing; ActiveFirewallMismatch, BFDFlapping | CARP and pfsync replace them |
| The WAN handover at install and its rollback | wan owns the radio from the first boot |
| firewalld zones and policies | pf on the firewalls; nftables on the host for its own input |
| snapper and kernel-keep | The previous slot is a complete previous system |
| LVM thin pool and XFS tiers; ThinPoolHigh, VgFreeLow | Btrfs, with a pool quota *(planned)* |
| Weekly host file-integrity scans; HostFilesModified, UKIChanged | dm-verity checks every block; the UKI signature is *(planned)* |
| DHCP lease names in DNS | Static addresses; built-in names come from the `local-names.conf` template |
| Second svc copy; TwinDown, PeerDown | DNS moved to the firewall pair; one monitoring copy |
| TuneD | A small handler, run by cron at boot and on AC events, sets the same values |
| journald and its sealing | syslog-ng shipping records off the host as they are written |
| Developer mode, management VLAN, branch staging, re-runs, pacman hooks | The build host and signed releases replace them |
| HTTP/3 blocking | No longer needed with the browser on its own segment |
