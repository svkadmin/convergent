# Convergent architecture

Convergent is a single-owner laptop system: security first, daily use second, with no trade-off. The
machine converges on the state declared in this repository. It runs only what is built here,
verified at boot, replaced whole on update.

This file gives design and reasons. It describes the target; *(planned)* marks parts not yet built.
Today's state: [BUILD, Status](BUILD.md#status). Section 14 compares Convergent with predecessor,
Archer.

---

## 1. Principles

1. **Verified, not trusted.** Kernel checks every OS block as read. Signed boot *(planned)* would
   extend this to firmware, boot loader and kernel: nothing on the laptop changes OS without the
   build key.
2. **Built elsewhere.** Build host compiles, assembles and signs. The laptop gets images only: no
   compiler or package manager at run time.
3. **Compartments with one policy point.** The radio, each firewall, each service, each browser and
   every guest have their own compartment. All traffic between them passes firewall pair. Network
   policy lives nowhere else.
4. **Fail closed.** With both firewalls down, nothing talks to anything.
5. **Replace, don't patch.** Updates swap whole image. Previous image stays bootable.
6. **Plain files.** Configuration is files and templates here. Build settings come from validated
   config file.
7. **Small.** Each component earns its memory and code. Idle target: under 3 GB with all guests
   running, to be measured, not assumed.

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
 HOST              svc (ct)    browsers      int        user containers
 Gentoo, OpenRC,   Alpine:     (Incus ct)   browser     and VMs (Incus)
 Sway, Incus;      metrics,    def, tmp     (Incus ct)
 its only address  logs,      (+ portal)     for
 is on "host"      alerts                   Grafana
```

Segments are Layer-2 bridges on host. Host holds an address only on `host`, ignores rest (section
4.4). Incus binds each guest's fixed address to its NIC, so each guest cannot send as anyone else;
wan is the exception (section 4.1).

---

## 3. Components

### 3.1 Host

| Area | Design |
|---|---|
| Base | Gentoo, hardened profile, OpenRC, glibc |
| Kernel | Gentoo distribution kernel, hardened, plus Convergent fragment: confidentiality lockdown; modules signed with a key that exists only during the build; no kexec or hibernation; DM, DM_INIT, DM_VERITY, EROFS and storage drivers built in; FireWire, X.25, TIPC, RDS, CAN left out; unused protocols and filesystems never loaded (`modprobe.d`; out of build *(planned)*); setuid, setgid, file capabilities stripped except sudo, su, passwd, unix_chkpwd, D-Bus helper; command-line hardening (init_on_alloc, slab_nomerge, page shuffling, stack offset randomization, no vsyscall, no debugfs); no Wi-Fi driver, so host cannot take radio back |
| Kernel settings | One sysctl file from Archer: ptrace, perf, BPF and kernel-pointer restrictions; dmesg restricted; protected links and FIFOs; TIOCSTI and line-discipline loading off; no redirects or source routing; martians logged; reverse-path filtering; no core dumps |
| IOMMU and DMA | `intel_iommu=on iommu.strict=1 efi=disable_early_pci_dma`; Thunderbolt DMA protection *(planned:* verified at boot*)*; NVIDIA functions bound to vfio-pci before any driver probes them and kept powered down; Wi-Fi function must sit alone in its IOMMU group, no ACS override |
| Mandatory access control | AppArmor enforcing; Incus generates and loads a profile per container and VM |
| Audit | auditd immutable rules: identity files, guests' SSH keys, accepted check baseline, DNS files, authentication, privilege changes, boot files, keys, module loading, policy changes, root-run commands; records forwarded to svc |
| Accounts | Root locked. Owner in `wheel`, `seat`, `audio`, `video`, `dialout`; `su` limited to `wheel`; sudo: 5-minute ticket, PTY, own log; passwords hashed with yescrypt (SHA-512 crypt for initramfs recovery reset); faillock after 5 failures for 15 minutes; restrictive umask |
| Boot | systemd-boot (boot loader only, from `systemd-utils`; no systemd init), editor disabled; one UKI per slot (normal and recovery profiles) plus a standalone rescue UKI; *(Planned:* signing with owner's key*)* |
| Root filesystem | Read-only EROFS image per slot, A and B; kernel creates dm-verity device from UKI command line; root hash to be covered by Secure Boot signature *(planned)* |
| State | One LUKS2 volume (Argon2id), Btrfs: `/var`, `/home`, short list of machine-specific `/etc` files, Incus pool; `/home`, `/tmp`, state mounts `nodev`, `nosuid`, `noexec` where nothing needs to run from them |
| Memory | Install selects no swap (default), zram, or swapfile on LUKS2 state; no hibernation |
| Seat and session | seatd; greetd with tuigreet on tty1 (user name typed each time); Sway, foot, bemenu, mako, swaylock, swayidle; PipeWire and WirePlumber started by session; sof-firmware and alsa-ucm-conf for SoundWire audio |
| Virtualisation | Incus: QEMU/KVM for VMs, LXC for containers |
| Devices | USBGuard, default deny. Policy changes use USBGuard IPC (rules file is state-bound). Device controls and policy review: [USAGE, Devices](USAGE.md#devices). Camera module gates: section 9 |
| Power | Never suspends. CPU energy preference and optional clock cap (`cpu_cap_khz`, none by default) set at boot and per power source on AC events. Runtime power management for NVIDIA GPU and audio. Optional battery charge end/start thresholds (off by default: 100/95). Optional firmware `platform_profile` selection (quiet/balanced/performance, only if offered); firmware keeps fan control. A known-noisy ACPI event masked, never the embedded controller's *(planned)* |
| Host firewall | nftables: input only on `host` and only from listed sources (section 4.2); no forwarding |
| Logs | syslog-ng over TLS to svc; bounded local buffer for when svc is down |
| Crashes | `/var/lib/convergent/crash/<timestamp>/`; EFI pstore collection and panic recovery: [RECOVERY 13](RECOVERY.md#13-a-kernel-panic-or-crashrecorded-alert) |
| Time | chrony, NTS from three sources, two must agree; starts without waiting for network; serves NTP to firewalls |
| Listening on the host | chrony (UDP 123, firewalls only), node_exporter (TCP 9100, svc only), Incus metrics (TCP 8444, TLS with client certificate, svc only). Nothing else |

### 3.2 wan (VM)

Alpine, LTS kernel. Owns Wi-Fi card by VFIO passthrough, joins networks with iwd, takes upstream
address by DHCP, performs the system's only NAT.

- **Privacy on the air:** random MAC per network; regulatory country set; protected management
  frames where offered; DHCP sends no host name; no mDNS or LLMNR.
- **Networks:** credentials travel over SSH on standard input and stay in wan; replacement keeps
  saved networks (section 7.2). Replies are sanitized. After association, the host polls wan's Wi-Fi
  IPv4 address six times, five seconds apart, before reporting DHCP failure. Controls, hidden
  networks and roaming: [USAGE, Wi-Fi](USAGE.md#wi-fi).
- **Wired uplink:** `sys wired attach` calls `devices wired attach`. The Incus `usb` device uses
  vendorid, productid, serial and required=false. Guest-operation lock serializes assignment with
  guest updates. wan's image has Realtek NIC firmware; after removal or addressless replug, it
  clears stale ifup state before retrying DHCP. Identity checks, hotplug and routing:
  [USAGE, Devices](USAGE.md#devices).
- **Egress:** own traffic limited to DHCP and NAT; starts nothing inward except syslog to svc.
- **Management:** no Incus agent or guest API; SSH from host only, on transit address, with
  OpenSSH's default (post-quantum hybrid) key exchange.
- **Overlap:** refuses upstream lease overlapping internal range; raises alert.
- **Captive portals:** portal DNS uses the selected default-route uplink's first nameserver; it
  must be IPv4 outside 100.80.0.0/16. Later usable nameservers are not tried. DNS to wan's transit
  address reaches it by NAT rule, no forwarder process. Only from portal browser, only in portal
  mode. If that nameserver is unusable, portal mode fails closed. Portal mode ends by itself after
  30 minutes.
- **Time:** host clock (PTP over KVM, disciplined by chrony in VM).
- **Size:** memory capped at 512 MiB; emulated HPET off, free page reporting on (both measured on
  Archer).

### 3.3 fw1, fw2 (VMs)

OpenBSD. One interface per segment, plus dedicated sync link. Image construction and advisory
checks: [BUILD, Firewall images](BUILD.md#firewall-images).

- **CARP:** one virtual host ID per segment, same on both. fw1 skew 0, fw2 skew 100.
  `net.inet.carp.preempt=1` moves all addresses together. Advertisements unicast to peer
  (`carppeer`), so Linux bridge multicast plays no part.
- **pfsync** on sync link, with `defer`, so failover keeps established connections.
- **wan-watch** runs under rc.d. Demotes CARP by 128 if unbound dies or wan's transit address stops
  answering. Each round sends three probes 300 ms apart, bounded to one second; one reply passes.
  Two lost rounds in a row (about 2 s) demote; three consecutive good rounds clear it. Kernel's
  `wanwatch` group counter tracks ownership across watcher restarts.
- **pf** routes and filters between all segments (section 4.2); per-source state limits, MSS
  clamping toward wan, ruleset hash checker compares with release.
- **unbound** (OpenBSD base) answers DNS on every gateway address, so failover carries DNS (section
  4.5).
- **Owner maintenance:** adds `sysmaint` group to all six CARP interfaces on master and demotes it
  by 128. Failed runs remove the group; successful runs keep it until `sys fw undo`. Persistent host
  journal makes interrupted actions recoverable without decrementing health or upgrade counters.
  Guest and DNS push locks serialize operations. Each remote mutation takes base Perl's nonblocking
  `flock` on `/var/run/convergent-maintenance.lock`, held across exec and inherited by children.
  File created if missing, never unlinked; PID informational. Kernel frees lock when last holder
  closes it, even if remote work outlives SSH. Rebuild reuses guest journals, seeding, handback and
  DNS push. Durable marker records completed replacement and seeding before resume can skip them.
  Procedures and checks: [USAGE, Firewall maintenance](USAGE.md#firewall-maintenance).
- **Routes:** default via wan's transit address; every internal segment directly connected.
- **Also:** NTP client of host, node_exporter, syslog to svc, SSH from host only.
- **No DHCP:** every address static (section 4.1).
- **Size:** 1 GiB each; every boot relinks kernel (KARL) beside loaded blocklist.

Either firewall can be updated, rebooted or broken while other carries everything. Each has own
kernel: firewall kernel bug is not host kernel bug, and reverse. Silent failure detected in about
three seconds.

The minute checker restarts a firewall that has failed its checks for three minutes, only while
its peer is healthy and MASTER on all six segments, never during the first ten minutes after host
boot or after its own restart, and at most three times an hour. Guest journals, maintenance and
shutdown inhibit it; attempts go to syslog and the checker report.

On shutdown, `convergent-setup` stops browsers, svc, wan, then both firewalls before Incus stops:
20 seconds each to stop gracefully, then a forced stop under an autorestart hold.

### 3.4 svc (container)

Alpine in unprivileged Incus container on own segment.

| Service | Role | Bounds |
|---|---|---|
| VictoriaMetrics | Metrics; scrapes host, firewalls and wan | Cache, retention and query concurrency capped |
| VictoriaLogs | Logs; syslog over TLS from host, firewalls and wan | Cache, retention and query concurrency capped |
| vmalert | Evaluates alert rules (section 8); status bar reads its alerts API | |
| Grafana | Dashboards. Started only while viewed; bound to svc's address; login required; anonymous access off | Stopped when not in use |

While svc restarts or is replaced, status bar shows alert counts as unknown, not stale; host buffers
logs. DNS does not depend on svc.

### 3.5 Browsers

Chromium runs in unprivileged Incus containers built from one browser image:

- **def:** default browser on `web`, persistent profile volume.
- **tmp:** ephemeral container on `web`, gone when closed; `--portal` selects captive portal mode.
- **int:** persistent container on `admin`, only browser that reaches Grafana.

Each container gets: GPU render node (except tmp in portal mode); Wayland socket from Sway's
security context (no screen capture, input injection, other Wayland sockets, Sway IPC or X11); own
Pulse socket from its `pipewire-pulse` instance, playback only, recording blocked for every role;
own download directory. No D-Bus, so no portals or screen sharing.

Portal mode uses tmp profile with overrides: fixed address 100.80.3.11 (`a_portal`), no render
device, 512 MiB, wan's resolver, captive-page policies. Normal tmp instances use 100.80.3.20–99 and never
get those policies or that address. Portal mode defaults to NeverSSL, allows HTTP, disables capture,
extensions and search.

Chromium policies are part of image: DNS-over-HTTPS off (gateway resolves); telemetry, studies and
captive-portal probes off; each mode labelled in window title, so owner always knows which browser
is in front. Links opened from other programs go to `tmp` by default *(planned)*.

### 3.6 User guests *(planned)*

Incus containers and VMs on `guests` segment, in owner's own Incus project, so they never touch
infrastructure instances, networks or profiles.

- Fixed address bound to each NIC, port-isolated from others. pf decides reach: by default, resolver
  and internet on web ports.
- Containers unprivileged, own ID range, process limit. Every guest has memory limit.
- VMs use UEFI with virtual TPM. Menu creates them from installer image, opens console.
- fw1, fw2, wan and svc autostart and restart after crashes (section 5.2). Browsers launch on
  demand; def/int are deletion-protected, tmp is ephemeral.
- Guest needing VPN runs it inside itself.

---

## 4. Network

### 4.1 Addressing

Internal addresses come from one /16, 100.80.0.0/16, in RFC 6598 shared space that carrier-grade NAT
also uses. wan refuses upstream lease overlapping it. Range repeated in host, wan, firewall and tool
configuration, so changing it needs coordinated edits.

| Segment | Prefix | Gateway and resolver (CARP) | fw1 | fw2 | Members |
|---|---|---|---|---|---|
| transit | 100.80.0.0/28 | .1 | .2 | .3 | wan .10 |
| sync | 100.80.0.16/30 | none | .17 | .18 | none |
| host | 100.80.1.0/28 | .1 | .2 | .3 | host .10 |
| svc | 100.80.2.0/28 | .1 | .2 | .3 | svc .10 |
| web | 100.80.3.0/24 | .1 | .2 | .3 | def .10, tmp in portal mode .11, normal tmp .20 to .99 |
| admin | 100.80.4.0/28 | .1 | .2 | .3 | int browser .10 |
| guests | 100.80.8.0/22 | .1 | .2 | .3 | guests from .10, assigned by menu |

All addresses static. Incus binds each guest's address and MAC to NIC (IP and MAC filtering on).
Exceptions: firewall NICs (CARP's shared MAC: unfiltered, unisolated) and wan's transit NIC (IPv4
filtering off; MAC filtering and port isolation on). Incus' own DHCP, DNS and NAT off on every
bridge. IPv6 off everywhere.

### 4.2 Flows

Everything not listed is dropped. DNS to a segment's own gateway is allowed on every segment except
transit and sync; not repeated below.

| From | To | Ports | Why |
|---|---|---|---|
| host | internet | NTP 123, NTS-KE 4460 | Time |
| host | update source | HTTPS 443 | Releases: download server addresses, opened by `fetch-release` only while it runs (failed close expires within 4 hours) |
| host | blocklist source | HTTPS 443 | Weekly blocklist download |
| host | svc | syslog 6514, vmalert 8880, VictoriaLogs query 9428 | Logs, alert counts, menu log view |
| host | fw1, fw2, wan | SSH 22 | Management, Wi-Fi credentials, blocklist and record pushes |
| fw1, fw2 | host | NTP 123 | Time |
| fw1, fw2 | internet | DoT 853 to forwarders | Resolution |
| svc | host, fw1, fw2, wan | 9100 | Metrics scrape |
| svc | host | Incus metrics 8444 | Instance state |
| fw1, fw2, wan | svc | syslog 6514 | Logs |
| web (def, tmp) | internet | 80, 443 (TCP and UDP) | Browsing |
| web | upstream LAN | IPP 631, only when printing is switched on *(planned)* | Printing |
| web (tmp in portal mode) | wan | DNS 53, only in portal mode | Captive portal resolution |
| web (tmp in portal mode) | upstream LAN | 80, 443, only in portal mode | Portal page |
| admin (int) | svc | Grafana 3000 | Dashboards |
| guests | internet | per guest; default 80, 443 | Guest work |
| wan | anything internal | nothing it starts, except syslog to svc | Untrusted |

"Internet" means public addresses; upstream LAN's private ranges excluded. Firewalls and wan both
enforce this. wan forwards to private ranges only from portal browser, and only in portal mode.

### 4.3 Failover

Active firewall answers on every CARP address. If it stops, other takes every address within about
three seconds and already holds connection state. NAT happens only in wan, so outside address never
changes during failover. Resolver moves with gateway. If both stop, every segment is cut off. One
firewall can fail; wan cannot.

### 4.4 The host and the bridges

Bridge without address is still host interface, so host ignores them explicitly: nftables drops
input on every interface but `host`; ARP ignored on other bridges; reverse-path filtering strict;
forwarding off. The host is never a router; the firewalls are.

### 4.5 DNS

- **Resolution:** unbound on both firewalls forwards over DNS-over-TLS to forwarders given by
  address and certificate name. Validates DNSSEC; answers internal segments only.
- **IPv4 only:** DNS transport IPv4 only; AAAA answers not suppressed. DNS-over-HTTPS canary domain
  answers NXDOMAIN, so applications fall back to system resolver.
- **Rebinding:** configured IPv4 private, shared-space and loopback ranges, plus IPv4-mapped IPv6
  addresses, are stripped.
- **Local names:** built-in names and reverse records from `local-names.conf` template, filled with
  address prefixes at firewall image build. Owner records in one file, validated, pushed to both
  firewalls with blocklist.
- **Blocklist:** RPZ zone. Host downloads weekly, retries on failure, validates, pushes same file to
  both firewalls over SSH. Last good copy stays in force until new one validates. Short allow-list
  holds owner's exceptions.
- **Owner editor:** `sys dns` lists records and exceptions; adds/removes IPv4 A records and
  allow-list names through `dns-push`. Helper holds push lock through validation, proposed diff,
  confirmation, activation. Rejects duplicate names, malformed names or IPv4 addresses, and
  conflicts with either firewall's built-in names. Other manually maintained record types stay
  supported by push, not editable here. Edit journals previous owner inputs on encrypted state;
  recovery restores those and both firewalls. Commit marker prevents completed push being rolled
  back during journal cleanup. `last-push` records UTC time for full and local pushes;
  weekly-download stamp stays separate.

---
## 5. Storage and boot

### 5.1 Disk

| Partition | Content |
|---|---|
| ESP | systemd-boot; one UKI per slot, normal and recovery profiles |
| slot A, slot B | EROFS images, dm-verity hash trees |
| state | LUKS2 (Argon2id); Btrfs: `/var` (snapshot per slot generation), `/home`, `/etc` entries, Incus pool |

Encrypted state has discard disabled on purpose: discard reveals free-space patterns. Btrfs is
scrubbed monthly. Selected custom volumes have size limits. A pool-wide quota *(planned)* stops
guests and logs filling the space `/var` and `/home` need.

### 5.2 Boot

1. Firmware verifies systemd-boot with owner's key *(planned)*.
2. systemd-boot picks slot (section 7.3), starts UKI profile 0. Profile 1 (`ID=recovery`,
   `TITLE=Recovery`, selectable in menu) shares kernel, initramfs and verity root; adds only
   `convergent.recovery=1` before `init=`.
3. Kernel creates slot's dm-verity device from UKI command line.
4. Initramfs mounts it read-only as root. Refuses to boot if more than one disk has `cv-state`
   partition; asks for LUKS passphrase; opens state. Auto-sized installs grow last state partition
   when over 1 GiB is free (partition, LUKS, then Btrfs). Fixed/percentage installs keep size via
   install-written `install-state-size` marker on state; without it, no growth. `state-max-gib` caps
   growth only if marker says `auto`. Interrupted grows finish on later boot. Selects slot's `/var`;
   cold-snapshots it on new slot's first boot; mounts `/var` and `/home`; bind-mounts listed `/etc`
   entries after merging missing image system accounts (IDs below 1000; keeps existing entries,
   warns on ID collisions) and adding existing owner to `dialout` in group/gshadow. Mounts `/run`
   and `/tmp` as tmpfs, arms hardware watchdog, switches to real root.
5. OpenRC starts host, then Incus. Incus autostarts fw1, fw2, wan and svc. With priority/delay unset,
   instances use bulk startup, limited to `max(floor(CPU threads/4), 1)` concurrent starts. No start
   step needs name before firewalls' resolvers answer.

Verity checks every block when read. Tampered block fails to read, at boot or later.

With recovery flag, after LUKS unlock and state mount, initramfs offers console menu before binding
`/etc` or switching root: root shell (exit returns), owner password reset, continue, reboot, power
off. Shows release, slot and read-write state path `/run/cv-state`. Reset finds uid 1000 in state's
passwd, hashes two matching password entries with `openssl passwd -6`, and atomically replaces
owner's shadow field with root:shadow 0640. Watchdog armed after leaving recovery. No network or
daemon starts. `rd.shell=0`, `rd.emergency=poweroff`, lockdown, verity and disabled boot editor stay
in force.

Normal titles name version, kernel, release and slot, e.g. `SLOT A | Gentoo 0.1.0 - 6.18.57`
(release id orders entries). Recovery appends `(Recovery)`. Entry IDs: `convergent-<release>-a.efi`
and `convergent-<release>-a.efi@recovery`, boot counters stripped from both.

systemd-boot 260.1 sorts entries by descending IMAGE_VERSION, then descending filename; profiles
keep discovery order (0 first) in that stable sort. So `default convergent-[0-9]*` selects newest
non-exhausted UKI's normal profile. Both profiles share one counted file, e.g.
`convergent-<release>-a+3.efi`. Entering recovery on unblessed release uses one try. Continuing runs
usual health checks. `slot bless` renames that shared file to `convergent-<release>-a.efi`, blessing
both profiles.

Ukify 260 creates profile 0 in final build (`--profile 'ID=main'`); only recovery fragment is
joined. Separate p0 and p1 fragments would add third profile, since ukify automatically supplies
base profile. Fragments live in a temporary directory and are removed: release files, manifest
entries and installed UKI names stay the same. Kernel and initrd occur once; profiles add only
metadata and recovery command line. Installer's ESP check uses actual UKI size, including these
sections.

Standalone rescue UKI, independent of both slots: release kernel, Intel microcode, separate dracut
initramfs with `convergent` and `convergent-rescue`. Command line: `convergent.rescue=1`, no verity
table, no slot root. Cmdline hook claims synthetic root. Pre-mount hook unlocks state (same code and
US keyboard rules as normal boot), runs rescue console menu, and never reaches root mounting or
pivot. Neither grows state nor prepares release `/var`. Slot pre-pivot hook and watchdog drivers
omitted. No network services or guest daemons run. Menu shares Recovery's password reset code.

Rescue includes cryptsetup, Btrfs, OpenSSL, `slot`, USB filesystem support, and small console, disk,
checksum and archive tools, with libraries and i915 firmware. Mounts release USB media read-only;
requires embedded channel key's manifest signature. `slot rescue-write` gated to rescue. Permits
explicitly confirmed reinstall or downgrade, reuses normal write/readback and counted UKI
installation, keeps `/var`, `good` and `highest`. `slot rescue-next` sets normal entry ID in
`LoaderEntryOneShot`. Logs export without starting guests. No continue-to-host path or rescue
blessing.

Build rescue before EROFS, at `/usr/lib/convergent/rescue.efi`, under slot's verity hash. Release
files and manifest fields stay unchanged, so update 7 clients can still write release. After health
checks and blessing, `slot` compares that file with ESP's `EFI/Linux/convergent-rescue.efi`; if
different, copies to `.new`, checks, syncs, renames, syncs. A failed release cannot replace rescue.
Failed copy keeps existing rescue; later bless retries. Installer also copies it and reserves
space for two release UKIs, both systemd-boot paths, rescue and extra rescue for atomic replacement.
Older releases without rescue stay installable.

`IMAGE_ID=zz-convergent-rescue` sorts after bootable releases; systemd-boot 260 moves exhausted
entries below it regardless of sort key. Numbered default pattern excludes rescue, even when both
slots are exhausted. Bless migrates old `default convergent-*` line. Rescue is a normal, currently
unsigned UKI; can be signed for Secure Boot later. ESP copy is unaffected by slot corruption, but
firmware does not authenticate it while Secure Boot is off. Rescue test coverage:
[BUILD, Test in QEMU](BUILD.md#test-in-qemu).

### 5.3 What is writable

Everything under `/usr` and rest of `/etc` comes from verified image. Writable `/etc` entries are
explicit list: `machine-id`, `passwd`, `shadow`, `group`, `gshadow`, `subuid`, `subgid` and
`usbguard/rules.conf`. Incus and guest SSH keys live under `/var/lib`. Persistence limits:
[section 10](#10-security-model).

Image's `rootfs/etc/apparmor.d/` profiles confine chronyd, node_exporter, bluetoothd, way-secure and
pipewire-pulse. chronyd, node_exporter, bluetoothd and pipewire-pulse enforce. way-secure only
complains (log, do not block) until real-hardware use shows no denials. Chronyd can adjust time and
use RTC and its NTS state. Exporter reads kernel metrics and its textfiles. BlueZ uses system D-Bus,
Bluetooth sockets and pairing state. Browser helpers can use owner's Wayland/PipeWire sockets and
named session sockets; Pulse also supports owner's ordinary session server. Profile syntax and
runtime checks: [BUILD, Checks](BUILD.md#checks). Boot AppArmor service loads them before
default-runlevel daemons, caching under `/var/cache/apparmor` (never read-only `/etc`); new release
drops old cache. Desktop coverage: [BUILD, Test in QEMU](BUILD.md#test-in-qemu).

---

## 6. Build and keys

Build host is dedicated machine (VM today) that does nothing else. It holds:

- build environment: signed Gentoo stage3 chroot;
- Portage snapshot pinned by date, verified by signature;
- `/etc/portage` from this repository;
- binary package cache: Gentoo's official hardened binary packages where they match, our own builds
  where USE flags differ;
- outputs of each release.

`portage/overlay` holds packages Gentoo does not offer as needed: `aa-exec` alone, which Incus uses
to confine its image unpacker (stock apparmor-utils would pull Python into image), and `way-secure`,
giving each browser restricted Wayland security context. Also pins GURU's `net-dialup/tio` 3.7 and
its distfile hashes for serial consoles. Image keeps and checks FTDI, CP210x, PL2303, CH341 and CDC
ACM drivers; Gentoo udev uses `dialout` for their device nodes. MC's terminal-background skin is set
via env.d; Files and Notes controls: [USAGE, Keys](USAGE.md#keys).

Channels and promotion: [BUILD, Status](BUILD.md#status).

Version fields and release ordering: [BUILD, Build a release](BUILD.md#build-a-release).

The `beta` key on the build host permits unattended signing and publication. It guards against a
changed download or stolen bucket token, not a compromised build host. The `stable` key is attached
only after the owner checks the manifest. Signatures prove origin, not that the build is benign.
Owner's Secure Boot key *(planned)* stays on offline media like the stable key. Key setup and
publication: [BUILD, Sign and publish](BUILD.md#sign-and-publish).

A release is one verified root image, two boot files (one per slot), and optional guest images and
profiles.

Release is built in these steps (commands in [BUILD.md](BUILD.md#build-a-release)):

1. Sync pinned snapshot; refuse unsigned one.
2. Build `@convergent` and owner's `@convergent-apps` sets into staging root, from binaries where
   possible.
3. Copy `rootfs/` from this repository over it.
4. Use staged kernel to build initramfs, EROFS image, dm-verity tree and UKIs.
5. Write manifest: release ID, semantic version, kernel version, root hash, file hashes.
6. Build guest images, each in own build: wan (Alpine), fw (OpenBSD), svc (Alpine), browser
   (Alpine).
7. Sign manifest with channel key (`manifest.sig`); signing UKIs for Secure Boot planned.
8. Publish the signed release and latest pointer; see
   [BUILD, Sign and publish](BUILD.md#sign-and-publish).

---

## 7. Install, update, roll back, recover

### 7.1 Install

From Convergent USB disk carrying one release, or as disk image (README, Install). Partition, create
LUKS and Btrfs, write slot A, install systemd-boot and slot A's UKI, register boot entry (physical
install only) (and removable-media path), create owner's account. Disk image also carries guest
images; first boot creates guests. No network needed. *(Planned:* in Setup Mode, enrolling owner's
keys and option ROM hashes, otherwise checking them; stick as recovery path when nothing on laptop
boots.*)*

Install configuration and capacity checks: [USAGE, Install](USAGE.md#install). Installer seeds
`/var` and writes small runtime settings. OpenRC starts swap before Incus. Disk swap uses a separate
top-level Btrfs subvolume, mounted under `/var/lib/convergent/swap`, so release snapshots skip its
active file ([Btrfs swapfile constraints](https://btrfs.readthedocs.io/en/latest/Swapfile.html)).

`guests init` creates management key, TLS credentials and one shared CARP password on laptop.
`/var/lib/convergent/guests/` keeps last two across guest replacements. Images hold none of them,
nor SSH host keys. Each guest gets only its own credentials on read-only FAT16 disk labelled
`CVSEED`; it records once it applied them, then ignores disk. Host checks that record, pins fw's and
wan's first SSH host keys from Incus console, checks health and detaches disk (svc has no SSH; Incus
mounts its seed). Without seed, fw keeps CARP and dependent daemons off, and Alpine guests keep
credential-dependent services stopped, so fw build's seedless smoke boot leaves release
unpersonalised.

First boot starts fw1, fw2, wan and svc together; their pinning and checks still run one at a time,
in order. Service certificates (`server`, `incus-server`, `incus-client`) with at most 30 days
remaining renew during the next successful guest apply after all browsers close. They are reissued
from their existing keys and the CA, installing new trust before consumers restart.

### 7.2 Update

1. Take release from `fetch-release` (URL in image) or USB stick. Check signature against image's
   key and every hash. The signed `latest` may be at most five minutes ahead of the clock; over 30
   days old, it is reported as stale, not refused. Refused: update from slot not yet marked good
   (would overwrite only good one), and any release not newer than highest ever marked good (kept on
   state volume, so rollback by hand does not reopen way to older releases).
2. Write image to inactive slot; read back and verify.
3. Install its UKI with boot counter: systemd-boot gives it three tries.
4. Reboot. Initramfs snapshots `/var` cold before anything starts.
5. After health checks pass (no service crashed; default runlevel running; from boot runlevel host
   firewall, USBGuard, audit and AppArmor running; Incus answering; guest firewalls, wan, svc and
   session: planned), slot is marked good and becomes default. Order: record highest release, drop
   boot counter, then name release good, so crash at any point is safe. Every boot runs checks. On
   counted boot, initramfs arms 180-second hardware watchdog, fed for ten minutes, then left to
   reset board. Passing checks disarms it, even after feeding stopped. Release already good disarms
   it before checks.

Releases carry guest images and Incus profiles in `guests.manifest`, signed with same key beside
host manifest. Host manifest stays unchanged, so older releases and installer (reads only it) are
unaffected. Signed `latest` names the hash of `guests.manifest` (or `none`), so a mirror can neither
withhold nor swap it. Guest identity is SHA256SUMS plus delivered profiles. Delivery and
application: [USAGE, Releases and guests](USAGE.md#releases-and-guests). Host-only releases remain
valid.

Guests update only on host slot already marked good, one at a time, each after snapshots of custom
state volumes. The guest is rebuilt in place from the release image; the image it ran on stays in
the store until the checks pass, so a failed or interrupted update rebuilds it from that image,
re-seeds it and restores the snapshots (wan's saved networks wait in host state meanwhile). Last
three state snapshots per volume kept. Firewalls update one at a
time: fw2 first, checked (CARP state, pfsync, pf ruleset hash, resolution and short traffic soak
through it), then failover to it, then fw1. Firewall failing checks returns to previous image before
other is touched. New firewall copies nothing from old one; after `guests update fw`, host pushes
stored blocklist and records (`dns-push local`, when a blocklist is stored). New wan takes old one's
saved Wi-Fi networks, read in userspace from copy of old disk's partition (debugfs as unprivileged
user; keeping only the iwd network files `.psk`, `.open` and `.8021x` files). Old disk never
mounted. Browser updates keep both def/int backups until both replacements pass, then advance image
for new tmp instances, including portal mode. Failed replacement restores both browsers and shared
profiles, except during one-time role migration below.

Browser update (also through `guests apply`, or init recovery) renames `web` to `def` and `admin` to
`int`, with state volumes. Under `browser-update.lock`, stops old containers, preserves profile
snapshots in `profiles.before`, and durably records new profiles in `browser.rename` before renaming
anything. Retries check which old objects remain; conflicting old/new names are refused. Instances
get new profiles and keep state volumes, including bookmarks and logins. Rename journal rolls
forward: `profiles_restore` leaves it intact, and browser launches stay blocked until both image
replacements pass. Existing `pending` journal still restores failed replacements. `browser.ready`
commits image alias, removes unused old profiles and clears both profile and rename journals. `web`
and `admin` networks and firewall addresses do not change.

Firmware updates use signed capsules only, applied from menu *(planned)*.

### 7.3 Roll back

- **Automatic:** slot that fails three tries (including hang caught by watchdog after passphrase) is
  skipped. Previous slot boots; initramfs selects its `/var`, so Incus database matches its Incus
  version.
- **By hand, after slot was marked good:** boot menu offers previous slot. Its `/var` predates
  update, so changes since then roll back with it. Guests are not rolled back; they stay as they
  are. *(Planned:* menu warns before booting, and refuses when guests were updated in between.*)*
- `/home` is never rolled back. *(Planned:* its own snapshots, daily for week and weekly for a
  month.*)*

### 7.4 Recovery and backups

- **Keys:** second LUKS passphrase, recovery key, kept offline with LUKS header backup and Secure
  Boot key backup on encrypted media. *(Planned:* menu reminder to refresh header backup after any
  keyslot change.*)*
- **Backups:** contents and exclusions: [USAGE, Backups](USAGE.md#backups).
- **Recovery:** each slot UKI's recovery profile, standalone rescue entry (section 5.2), and
  RECOVERY.md's numbered recipes for failures known so far. Each failure found on laptop adds one.
  *(Planned:* restoring guest snapshot, restore tool for backups.*)*

---
## 8. Observability

- **Metrics:** VictoriaMetrics scrapes node_exporter (host, firewalls, wan) and Incus metrics
  (instance state) every 30 seconds. Retention: 14 days. Only the seven Incus series the dashboards
  query are kept, and the vmalert job keeps just its scrape health. Host node_exporter leaves out
  the netstat, vmstat, diskstats, schedstat and softnet collectors. Time and synchronisation come
  from node_exporter's time collector. Extra figures go stale by file age, which node_exporter
  reports. Figures nothing else provides are small text files written by section 12's scripts: per
  firewall, CARP, pf and unbound state; on the host, once per boot, release numbers, Secure Boot,
  lockdown, LUKS header hash and crash records; at boot and daily, NVMe health and certificate
  expiry; every minute, NTS state. NTS alerts allow five minutes to synchronise while an uplink is
  up. Collector alerts allow five minutes for boot collection. Guest update timestamps go to the
  update journal (`/var/lib/convergent/guests/updates`), not the metrics.
- **Logs:** VictoriaLogs receives syslog over TLS from the host, firewalls and wan, including
  forwarded host audit records. Retention: seven days or 4 GiB, within a 6 GiB volume quota.
  Authentication, audit and firewall logging stay enabled. USBGuard uses LinuxAudit, so device
  decisions reach audit.log and the existing audit syslog forwarder. Local messages keep
  authentication and selected security programs below warning level. Dashboards take each record's
  host from the sending connection's address; app name and message stay the sender's claims. Guest
  update summaries and failures go to syslog. Slot bless records exhausted-newer-slot fallback. The
  minute status probe logs observed firewall takeovers only when the last known coherent master
  changes.
- **Alerts:** vmalert evaluates rules every 30 seconds, watching metrics and logs from every
  compartment. The status bar shows counts, or "unknown"
  when svc does not answer. Grafana shows details. Rules carried from Archer and adapted:

| Area | Alerts |
|---|---|
| Path | FirewallDown, CarpSplit (both masters or none), CarpFlapping, NoDefaultRoute, FirewallRulesetDrift, StateTableHigh, WanReservedLeak, UpstreamOverlap |
| DNS | ResolverDown, ResolverStale, BlocklistStale |
| Compartments | GuestStopped, GuestRestarted *(planned)*, ServiceDown, PassthroughDeviceMissing, HostNetdevUnexpected, GuestRouteInjected |
| Hardware and capacity | NvmeSpareLow, NvmeErrors, BatteryLow, StateVolumeHigh, IncusPoolHigh |
| Currency | ReleaseOld, GuestImageOld, GuestReleaseEOL |
| Security and time | SecureBootNotVerified, LockdownOff, KernelTainted, LuksHeaderChanged, AuditEvent, AuditRecordsLost, CertExpiry, ClockOffsetHigh, NtsUnauthenticated, CrashRecorded |
| Monitoring itself | CollectorStale, CollectorBroken, CheckerFailed, CheckerStale |

*(Planned:* WanReservedLeak, PassthroughDeviceMissing, HostNetdevUnexpected, GuestRouteInjected,
IncusPoolHigh, ReleaseOld, GuestImageOld, GuestReleaseEOL; the rest are in
`guests/svc/rootfs/etc/vmalert/alerts.yaml`.*)*

- **Dashboards:** Overview (path, attention), Network (six CARP segments, pf, DNS), Guests (Incus
  state, resources) and Security (boot facts, trust, recent events), opened in the int browser.
  Stdlib Python generators in `guests/svc/dashboards` share Archer's palette, type scale, Canvas
  path and first-screen sizing. Current state uses instant queries. CARP role-change annotations
  start off. Actionable syslog panels link to all records in Explore. Footers name collection gaps.
  Dashboard checks: [BUILD, Checks](BUILD.md#checks). Security has one bounded event list;
  `sys security events` filters the two local host logs without svc (USAGE describes its bounds).
- **Checker:** runs after every boot, update and daily. It compares the running system with the
  accepted release (verity, pf ruleset hashes, Incus settings and the temporary browser's profile,
  writable `/etc` entries, autostart and SUID inventories, radio VFIO binding, device ownership,
  CARP on both firewalls) and checks host and internal guest state. Upstream connectivity is
  excluded; `check status` polls Wi-Fi separately. Results feed the CheckerFailed and CheckerStale
  alerts.

---

## 9. Daily use

[USAGE.md](USAGE.md) covers daily use. Design points:

- **Status bar:** [USAGE, The bar](USAGE.md#the-bar).
- **Displays:** profile keys hash sorted make/model/serial triples. A Sway output/tick subscriber
  maps identities to current connectors; layout-only events do not reapply profiles. A separate
  rollback worker and exit traps restore the previous layout unless the owner confirms. A session
  lock serializes hotplug, saves and previews. If original screens vanish during rollback, remaining
  screens are enabled as fallback. Profiles are data, never sourced as shell or Sway configuration.
  Controls and defaults: [USAGE, The sys tool](USAGE.md#the-sys-tool).
- **Power and camera state:** root writes choices under `/var/lib/convergent/power` and
  `/var/lib/convergent/devices/camera`, which follow the per-release `/var` snapshot. The boot/AC
  handler serializes updates, publishes the successfully applied CPU profile under `/run`, and
  restores optional charge and thermal choices. Charge start is five percentage points below end;
  write order keeps a valid pair. Absent sysfs controls are skipped. Dell's separate `charge_types`
  control selects Custom for a limit and Standard for off, when present. Writing thresholds alone
  does not activate them. Sysfs values are read back after writes. It also retries camera probing
  once after state is mounted. Modprobe install gates on the video core and retained camera
  controllers deny loading unless the choice is `on`. `on` loads UVC and matching Intel PCI camera
  drivers at once. `off` denies new loads before trying to unload existing drivers, without force.
  Busy drivers cause an error and `CAM!`. USBGuard approval is independent. Camera drivers must stay
  modules in the laptop kernel; verify this and the actual camera and controller IDs on the laptop.
  Meeting compartments and screen sharing remain deferred.
- **Locking:** [USAGE, Power and locking](USAGE.md#power-and-locking).
- **Menu (`sys`):** each action prints its commands; bemenu stays the quick picker. Syntax and menu:
  [USAGE, The sys tool](USAGE.md#the-sys-tool).
- **Screenshots:** libnotify supplies `notify-send`; mako's stock or owner-configured look applies.
  Keys and output: [USAGE, Keys](USAGE.md#keys) and [The sys tool](USAGE.md#the-sys-tool).
- **Touchpad:** changes preserve other touchpad choices and the keyboard and output includes.
  Controls, saved settings and hardware limits: [USAGE, The sys tool](USAGE.md#the-sys-tool).
- **Microphone:** the Sway session retries muting until the default PipeWire source appears or the
  session ends. Separate Sway bindings enforce the mic key's behaviour while locked. Other sources
  and later default-source changes are not automatically muted. Controls, login behaviour and
  indicator: [USAGE, The sys tool](USAGE.md#the-sys-tool).
- **Bluetooth:** `AutoEnable=false`; picker output must match a listed row. Power, pairing,
  validation and confirmation: [USAGE, Devices](USAGE.md#devices).
- **Captive portals:** portal mode starts tmp with `--portal` and opens its two pf rules. It ends
  when the browser closes, when turned off, or after 30 minutes. DNS reaches the active uplink's
  resolver only in portal mode (section 3.2). The browser launcher owns activation under its session
  lock. It closes stale rules on all three guests before any new opening; failure to close any side
  prevents opening. The portal tool journals closure before remote changes, retries partial closures
  each minute and records a reason for `sys portal status`. Cron and the browser session loop check
  expiry. Remote mode checks use the minute status cache, refusing results stale for three minutes.
  An orphaned session without a browser lock is closed after a one-minute startup allowance.
- *(Planned:* owner guest actions in the menu, printing (off by default; IPP printers on the
  upstream network for the def/tmp browsers), clipboard clearing.*)*

---

## 10. Security model

| Threat | Defence |
|---|---|
| Hostile network, rogue access point | Radio and Wi-Fi stack in wan, random MAC per network; host never parses Wi-Fi frames or upstream DHCP |
| Network attacks on the host | Host answers only chrony (to the firewalls), node_exporter and authenticated Incus metrics (to svc), each only on its own segment |
| Malicious website | Browser runs in an unprivileged container under AppArmor, on its own segment, with a restricted Wayland socket, restricted audio and no D-Bus |
| Compromised guest | Own fixed address bound to its NIC (not on wan, section 4.1), port isolation, pf, AppArmor; host ignores its bridge |
| Compromised wan | Reaches only transit; firewalls trust nothing from it; no Incus agent or guest API in it |
| Local privilege escalation on the host | Hardened kernel settings, AppArmor, sudo policy, audit records shipped off the host |
| DMA from devices | IOMMU strict; Thunderbolt PCIe tunnels need approval where firmware asks; NVIDIA card held by vfio-pci |
| Malicious USB device | USBGuard, default deny |
| Tampered operating system on disk | dm-verity: a changed block fails to read; signed UKI protects the root hash *(planned)* |
| Stolen laptop, powered off | LUKS2 with Argon2id; Secure Boot with the owner's keys *(planned)* |
| Bad update | A/B slots, boot counting, watchdog after unlock, automatic fallback with matching `/var` |
| Supply chain | Signed stage3 and snapshots pinned by date; releases signed per channel, stable with owner's offline key |

Not defended: a compromised host (it controls every compartment, both firewalls included); a
compromised build host whose release the owner signs; an attacker with physical access while the
laptop is unlocked; firmware below Secure Boot. Persistence stays possible in `/home`, the writable
`/etc` entries and guest volumes. The checker watches selected files there, not guest volume
contents. Logs ship to svc as written, so an attacker on the host cannot quietly rewrite what was
already sent.

Option ROMs: firmware's own GPU driver is part of the firmware. Add-in option ROMs (NVIDIA card,
Thunderbolt devices) are to be allowed by exact hashes from the TPM event log *(planned)*, not by
enrolling Microsoft's third-party certificate.

---

## 11. Resource budget (estimates, measured in a later phase)

| Item | MiB |
|---|---|
| Host: kernel, Sway, PipeWire, status bar | 700 |
| incusd | 200 |
| wan (512 cap, plus QEMU overhead) | 500 |
| fw1 + fw2 (1 GiB each, plus QEMU overhead, unbound with the blocklist) | 2 200 |
| svc | 350 |
| Total, idle, browsers closed; excludes optional zram | about 3 950 |

On the laptop, 384 MiB firewalls ran out of memory at boot (kernel relink beside the blocklist),
killing sshd and unbound while CARP kept the master role. Keep both firewalls at 1 GiB. Other
limits: wan 512 MiB, svc 350 MiB (768 MiB with Grafana), def/tmp 2 GiB, int 1 GiB, tmp in portal
mode 512 MiB. Container limits are ceilings, not idle reservations; lowering them without measured
peaks risks OOM without proving an idle saving.

### 11.1 Work removed without changing sampling intervals

These are work counts from the code, not measured watts or battery minutes.

| Change | Expected saving |
|---|---|
| `tools/bar`: cache an unchanged Sway layout name | About 24 helper launches/minute (awk and grep at five-second intervals), plus repeated XKB rules-list reads; a failed Sway query invalidates the cache |
| `tools/bar`: read the booted release once; share chip-name reads within each frame | 60 command-line reads/minute; all but one chip-name read per sensor chip per frame; temperatures read at most every 5 s; clock, lock-health and input polling unchanged |
| `tools/check status`: combine CARP and portal-table reads on each firewall; serialize wan sessions | Five SSH sessions/minute instead of seven; no concurrent connection creation to the same guest within this run; four fewer remote wc processes/minute; existing pinned keys and 60-second multiplexing remain |
| `tools/facts`: parse each slot status in shell | Four awk processes removed per boot-status attempt; boot, daily and hourly checks unchanged |
| `tools/power`: read sysfs with shell builtins; log only changes or failures | Up to four cat processes per CPU policy removed per AC event, plus supply/config reads; duplicate events write no power log to store or forward |
| `rootfs/etc/conf.d/node_exporter` and the `svc` scrape config: five unused host collectors off; only the Incus series in use and vmalert scrape health kept | Less collector work per scrape and fewer stored series; scrape intervals unchanged (section 8) |

Status probes still run every minute, with bounded requests and one worker per guest. Portal reads
hold the existing action lock; a busy lock, failed query or inconsistent sides yields unknown.
Failed Incus inventory still ages out rather than publishing false down states. The WAN's three
sequential probes share a 25-second budget plus kill grace, measured with monotonic uptime; healthy
requests reuse one SSH connection. The bar's 180-second stale limit and WAN's forced-command
allowlist are unchanged.

No cron interval was lengthened. The minute jobs enforce portal expiry, publish fresh network facts
or notice boot/update changes. `check auto` gates expensive successful scans to daily and failed
scans to five minutes. Host facts already run hourly/daily. The firewall's continuous wan-watch loop
demotes after two lost one-second rounds and recovers after three good ones. It is a failover
control, not merely a dashboard refresh.

### 11.2 Proposals, not enabled

| Proposal | Saving and trade-off | Recommendation |
|---|---|---|
| USB autosuspend except HID/audio | May idle USB devices/controllers; composite devices, approved uplinks and storage can still stall or fail on resume | Test an explicit device allowlist first, covering every interface of composite devices; keep USBGuard and HID/audio exclusions |
| PCIe ASPM powersave policy | May reduce link idle power; resume latency and firmware/device compatibility need measurement | Keep firmware/kernel defaults until tested; never force ASPM or change IOMMU isolation |
| SATA link PM / NVMe APST tuning | No demonstrated SATA target here; deeper NVMe states trade exit latency and device reliability for idle power | Keep driver defaults and quirks; inspect actual NVMe power states before tuning; never force APST |
| HDA audio power saving | May idle the codec/controller; wake delay and clicks possible | Test speaker, headset, microphone and PipeWire resume first; do not apply an HDA option blindly to another audio driver |
| Disable NMI watchdog | Removes hard-lockup detector activity but loses hard-lockup diagnostics; the boot hardware watchdog is a different mechanism | Keep it until that diagnostic loss is explicitly accepted |
| Longer dirty writeback/expiry intervals | Can batch writes, but leaves more recent data vulnerable to sudden power loss and can increase write bursts | Keep defaults, especially for logs and guest disks; read-only root does not make writable state disposable |
| KSM across fw1/fw2 | Possible shared-page RAM saving, at scanning CPU cost, with cross-guest deduplication side channels | Do not enable; the two firewalls stay separate trust compartments |
| Lower CPU caps, disable turbo or stronger EPP | Can lower load power at the cost of burst response and throughput; idle savings are not established | Keep the configurable cap (`cpu_cap_khz`; none by default, set per laptop) and source-specific EPP; compare energy per task before more caps |
| Static hugepages or different THP policy | Possible TLB benefit; reservations, fragmentation or compaction can hurt memory flexibility and latency | Keep current defaults; benchmark VM throughput and desktop tail latency first |
| Disable mitigations or relax hardening | Possible CPU saving by removing protections | Reject; keep mitigations, strict IOMMU, lockdown, verity, audit and guest confinement |
| Longer bar, scrape/eval or health intervals | A 60-second scrape/eval interval roughly halves those operations but delays detection and reduces history resolution; slower CARP probes delay failover | Keep current cadences. All vmalert groups explicitly set 30s, so changing only the command-line default would not help |
| Shorter retention or suppress routine SSH/cron logs | Less disk use and query work, but less incident/debug history | Keep 14-day metrics, seven-day/4-GiB logs and auth/audit/firewall logs; only redundant power messages are suppressed at source |
| Smaller guest limits or zram | Lower VM RAM may help, but KARL already disproved small firewalls; container caps do not reserve full size; zram adds metadata and compression work and changes OOM behaviour | Keep guest limits. Zram's old 32-GiB budget was only a plan; no enabled device here to shrink. Measure peak memory/pressure before choosing a size; do not claim a RAM saving from a documentation change |

The kernel documents limits for
[USB runtime PM](https://docs.kernel.org/driver-api/usb/power-management.html),
[audio power saving](https://docs.kernel.org/sound/designs/powersave.html),
[writeback intervals](https://docs.kernel.org/admin-guide/sysctl/vm.html),
[lockup detection](https://docs.kernel.org/admin-guide/lockup-watchdogs.html) and
[zram allocation](https://docs.kernel.org/admin-guide/blockdev/zram.html). Incus documents
[memory ceilings](https://linuxcontainers.org/incus/docs/main/reference/instance_options/), and
vmalert documents
[group evaluation intervals](https://docs.victoriametrics.com/victoriametrics/vmalert/).

On the laptop, compare before and after on battery with the same display brightness, radio
connection and closed-browser workload: battery energy over a long idle window, CPU time and context
switches, package idle residency, SSH sessions and log bytes. Also exercise layout changes, missing
guests, portal transitions, AC changes and browser load. No laptop wattage or runtime gain has been
measured from this checkout.

---

## 12. Our own code

Convergent writes as little as it can:

- **No daemons of our own.** Each piece is a short script started by OpenRC, cron, acpid or the
  owner, and exits when done. The bar, watchdog feeder and Sway display-event subscriber are the
  long-running exceptions.
- **Existing tools first.** Nothing an exporter, Incus, OpenRC or a base-system tool already does is
  written again.
- **POSIX shell** where it suffices; nothing that needs a runtime of its own.
- **A budget.** Target: the bar and every periodic script together under 1 % of one core at idle
  (Archer's equivalents used about 12 %).

| Piece | Runs | Does |
|---|---|---|
| `build/` | on the build host | Builds and tests a release (section 6) |
| `install/install` | from a Convergent USB disk | Installs a release (section 7.1) |
| `initramfs/` | at every boot | Section 5.2, step 4 |
| `slot` | by hand; once after each boot | Writes a release to the inactive slot; after the health checks, marks the booted slot good |
| `fetch-release` | from the menu (`sys update install`) | Downloads the newest signed release of the image's channel and hands it to `slot write` |
| `guests` | at first boot; by hand | Creates the guests; updates one guest, or the firewall pair in order, with checks and rollback |
| `check` | cron: after boot and updates, daily | The checker (section 8) |
| `bar` | in the session | The status bar; asks vmalert every 30 seconds |
| `sys` | from a key binding | The menu: one file per area in `/usr/lib/convergent/sys` |
| `apps` | Super+d | Lists graphical apps from their desktop entries in bemenu and starts the chosen one; a failed start shows why |
| `browser` | from the menu or a key | Starts a browser container with its restricted Wayland and audio sockets |
| `facts` | at boot; hourly cron | Writes the host's extra figures for node_exporter; archives pstore records |
| `dns-push` | weekly; by hand | Downloads, validates and pushes the blocklist and the owner's records to both firewalls |
| `portal`, `devices`, `backup` | from the menu | Captive-portal mode; USB and Thunderbolt approval; the backup (section 7.4) |
| `account` | by hand; from the menu (`sys security password`) | Changes a login password on the state volume and rebinds `/etc/shadow` |
| `power` | at boot; acpid and udev, on AC and USB-C supply changes; sys actions | Sets CPU preference and cap, publishes profile, restores optional battery and thermal settings and camera choice |
| `fw-facts` | cron on each firewall | Writes CARP, pf and unbound state for node_exporter |

---

## 13. Repository layout

| Path | What |
|---|---|
| `build/` | builder chroot, packages, image, sign, publish, QEMU tests, lint, advisories, disk image |
| `portage/` | make.conf, USE flags, package sets, image profile, two local ebuilds |
| `rootfs/` | host files: `/etc`, `/usr/lib/convergent` (`sys` areas), health checks |
| `initramfs/` | the dracut module: unlock, `/var` per release, watchdog |
| `install/` | installer, shipped as `convergent-install` |
| `tools/` | `slot`, `fetch-release`, `apps`, `guests`, `browser`, `sys`, `bar`, `check`, `backup`, `devices`, `portal`, `dns-push`, `power`, `facts`, `account` |
| `guests/` | `fw` (OpenBSD), `wan`, `svc` and `browser` (Alpine) |

The guest images, as `guests init` and `guests update` read them (each directory also holds the
`SHA256SUMS` checked first):

- `RELEASE/guests/fw/`: `fw{1,2}.qcow2`, `fw{1,2}.{pf,rules}.sha256`.
- `RELEASE/guests/wan/`: `wan.qcow2`, `wan-metadata.tar.xz`.
- `RELEASE/guests/svc/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus.yaml`.
- `RELEASE/guests/browser/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus/{base,def,tmp,int}.yaml`.

---

## 14. From Archer

**Kept or improved:** radio in a VM; the firewall pair, with its own kernels, shared connection
state and DNS that fails over with it; hardened kernel and lockdown (signed boot *(planned)*); IOMMU
and DMA rules; AppArmor, audit, account and sudo policy; USBGuard; LUKS2 and offline header backups;
NTS time; the alert set; status bar, menu, locking and power behaviour; browser modes with a
restricted Wayland socket; the owner's Incus project and VM support *(planned)*; the checker;
recovery recipes. Stronger: verified root and A/B updates instead of package-level rollback; static
bound addresses instead of DHCP inside; one policy point instead of firewalld zones on the host; one
monitoring copy instead of two.

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
