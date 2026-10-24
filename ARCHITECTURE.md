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
 HOST              svc (ct)    browsers      int        user containers
 Gentoo, OpenRC,   Alpine:     (Incus ct)   browser     and VMs (Incus)
 Sway, Incus;      metrics,    def, tmp     (Incus ct)
 its only address  logs,      (+ portal)     for
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
| Kernel | Gentoo distribution kernel, hardened configuration plus a Convergent fragment: confidentiality lockdown; every module signed with a key that exists only during the build; no kexec; no hibernation; DM, DM_INIT, DM_VERITY, EROFS and the storage drivers built in; FireWire, X.25, TIPC, RDS and CAN left out of the build, other unused protocols and filesystems never loaded (`modprobe.d`; out of the build *(planned)*); setuid, setgid and file capabilities stripped from all but sudo, su, passwd, unix_chkpwd and the D-Bus helper; hardening on the command line (init_on_alloc, slab_nomerge, page shuffling, stack offset randomization, no vsyscall, no debugfs); the Wi-Fi driver left out, so the host cannot take the radio back |
| Kernel settings | One sysctl file, carried from Archer: ptrace, perf, BPF and kernel-pointer restrictions, dmesg restricted, protected links and FIFOs, TIOCSTI and line-discipline loading off, strict network settings (no redirects, no source routing, martians logged, reverse-path filtering), no core dumps |
| IOMMU and DMA | `intel_iommu=on iommu.strict=1 efi=disable_early_pci_dma`; Thunderbolt DMA protection *(planned:* verified at boot*)*; every NVIDIA function bound to vfio-pci before any driver probes it and left powered down; the Wi-Fi function must sit alone in its IOMMU group, with no ACS override |
| Mandatory access control | AppArmor enforcing; Incus generates and loads a profile per container and VM |
| Audit | auditd with immutable rules for identity files, the guests' SSH keys, the accepted check baseline, the DNS files, authentication, privilege changes, boot files, keys, module loading, policy changes and commands run as root; records forwarded to svc |
| Accounts | root locked; the owner in `wheel`, `seat`, `audio`, `video` and `dialout`; `su` limited to `wheel`; sudo with a 5-minute ticket, a PTY and its own log; passwords hashed with yescrypt (SHA-512 crypt for an initramfs recovery reset); faillock after 5 failures for 15 minutes; restrictive umask |
| Boot | systemd-boot (the boot loader only, from `systemd-utils`; no systemd init), editor disabled; one UKI per slot with normal and recovery profiles, plus a standalone rescue UKI. *(Planned:* signing with the owner's key*)* |
| Root filesystem | A read-only EROFS image per slot, A and B. The kernel creates the dm-verity device from the UKI command line; the root hash will be covered by the Secure Boot signature *(planned)* |
| State | One LUKS2 volume (Argon2id) with Btrfs: `/var`, `/home`, a short list of machine-specific `/etc` files, the Incus pool; `/home`, `/tmp` and the state mounts `nodev`, `nosuid`, and `noexec` where nothing needs to run from them |
| Memory | Install selects no swap (default), zram, or a swapfile on LUKS2 state; no hibernation |
| Seat and session | seatd; greetd with tuigreet on tty1 (user name typed every time); Sway, foot, bemenu, mako, swaylock, swayidle; PipeWire and WirePlumber started by the session; sof-firmware and alsa-ucm-conf for the SoundWire audio |
| Virtualisation | Incus: QEMU/KVM for VMs, LXC for containers |
| Devices | USBGuard, default deny; `sys usb enrol` reviews each generated per-device rule before replacing the current policy, `review` lists named rules and live decisions, `revoke` removes an allowance and denies that device even against overlapping rules. Existing `allow` remains. Policy changes use USBGuard IPC because the rules file is state-bound; enrol/revoke restart the daemon to apply policy to present devices. Thunderbolt PCIe tunnels still require separate approval where firmware asks. Bluetooth off; switched on from the menu. Camera drivers gated by modprobe install rules and an explicit persistent owner choice, off by default |
| Power | Never suspends. CPU energy preference and an optional clock cap (`cpu_cap_khz`, none by default) set at boot and per power source on AC events; runtime power management for NVIDIA GPU/audio. Optional battery charge end/start thresholds (off by default: 100/95), and firmware `platform_profile` selection (quiet/balanced/performance only if offered). Firmware retains fan control. A known-noisy ACPI event masked, never the embedded controller's *(planned)* |
| Host firewall | nftables: input accepted only on the `host` interface and only from the listed sources (section 4.2); forwarding off |
| Logs | syslog-ng, forwarded to svc over TLS; a bounded local buffer for when svc is down |
| Crashes | Oops panics; panic reboots after 10 s. Built-in EFI pstore records are verified, synced and cleared at boot by `facts` into root-only `/var/lib/convergent/crash/<timestamp>/`; `cv_crash_records` drives svc's `CrashRecorded` alert |
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
  `sys wifi connect` without an SSID reuses the sys fzf picker with scanned security and signal;
  hidden SSIDs remain typed. Wan replies are sanitized and explained; after association the
  host polls for wan's Wi-Fi IPv4 address six times at five-second intervals before reporting
  DHCP failure.
- **Wired uplink:** a USB network adapter approved in USBGuard can be passed to wan as an
  uplink. `sys wired attach` uses `devices wired attach` to require the approved 0bda:8153
  identity and a unique nonempty serial, then adds `wired-uplink` to wan as an Incus `usb`
  device with vendorid, productid, serial and required=false. Incus handles matching hotplug
  and unplug; removing the role removes the device configuration. The guest-operation lock
  serializes assignment with guest updates. The host does not configure the NIC or run DHCP;
  wan's image includes Realtek NIC firmware and retains its existing eth1 DHCP/default-route
  preference. Wan clears stale ifup state
  after removal or an addressless replug, restarting DHCP at the next minute's check.
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
These lists and the OpenBSD version are included in the signed guest payload. Before publishing,
the advisory gate checks every published erratum, including gaps in the installed patch list;
non-applicable errata need an explicit reason in `build/advisories.exceptions`.

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
- **Owner maintenance:** `sys firewall` (`fw`) reports each segment's CARP state, PF state
  count, Unbound status and the last successful DNS push to both. Maintenance requires a
  six-segment MASTER/BACKUP pair and healthy PF, pfsync with defer and local DNS on both.
  It adds a dedicated `sysmaint` group to all six CARP interfaces on the master and demotes
  that group by 128, then checks peer takeover. Failure removes that group; successful
  maintenance stays until `sys fw undo`. A persistent host journal makes interrupted actions
  recoverable without decrementing health/upgrade counters. Undo checks both nodes and the
  normal fw1-master pair. Guest and DNS push locks serialize the operation; finish maintenance
  before performing guest updates.
- **Routes:** default via wan's transit address; every internal segment is directly connected.
- **Also:** an NTP client of the host, node_exporter, syslog to svc, SSH from the host only.
- **No DHCP:** every address is static (section 4.1).
- **Size:** 1 GiB each: every boot relinks the kernel (KARL) beside the loaded blocklist.

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

- **def:** the default browser on the `web` segment, with a persistent profile volume.
- **tmp:** an ephemeral container on `web`, gone when closed; `--portal` selects captive portal mode.
- **int:** a persistent container on the `admin` segment, the only browser that reaches Grafana.

Each container gets: the GPU render node (except tmp in portal mode), a Wayland socket created through Sway's security
context (no screen capture, no input injection, no other Wayland socket, no Sway IPC, no X11),
a dedicated Pulse socket from its own `pipewire-pulse` instance: playback only, recording blocked
for every role. Its own download directory. No D-Bus, so no portals and no screen sharing.

Portal mode uses the tmp profile with instance overrides: fixed address 100.80.3.11 (`a_portal`),
no render device, 512 MiB, wan's resolver and the captive-page policies. Normal tmp instances
use .20–.99 and never receive those policies or that address. Portal mode defaults to NeverSSL,
allows HTTP, and disables capture, extensions and search.

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
| web | 100.80.3.0/24 | .1 | .2 | .3 | def .10, tmp in portal mode .11, normal tmp .20 to .99 |
| admin | 100.80.4.0/28 | .1 | .2 | .3 | int browser .10 |
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
| web (def, tmp) | internet | 80, 443 (TCP and UDP) | Browsing |
| web | upstream LAN | IPP 631, only when printing is switched on *(planned)* | Printing |
| web (tmp in portal mode) | wan | DNS 53, only in portal mode | Captive portal resolution |
| web (tmp in portal mode) | upstream LAN | 80, 443, only in portal mode | The portal page |
| admin (int) | svc | Grafana 3000 | Dashboards |
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
- **Owner editor:** `sys dns` lists records and exceptions, adds/removes IPv4 A records and
  allow-list names through `dns-push`. The helper holds the push lock through validation, a
  proposed diff, confirmation and activation. It rejects duplicate names, malformed names or
  IPv4 addresses and conflicts with either firewall's built-in names. Other manually maintained
  record types remain supported by the push but are not edited by this interface. An edit
  journals the previous owner inputs on encrypted state; recovery restores those and both
  firewalls. A commit marker prevents a completed push from being rolled back during journal
  cleanup. `last-push` records the UTC time for full and local pushes; the weekly-download
  stamp remains separate.

---

## 5. Storage and boot

### 5.1 Disk

| Partition | Content |
|---|---|
| ESP | systemd-boot, one UKI per slot with normal and recovery profiles |
| slot A, slot B | EROFS images with their dm-verity hash trees |
| state | LUKS2 (Argon2id), Btrfs: `/var` (with a snapshot per slot generation), `/home`, `/etc` entries, the Incus pool |

Encrypted state has discard disabled on purpose: discard reveals free-space patterns.
Btrfs is scrubbed monthly. Selected custom volumes have size limits; a pool-wide
quota *(planned)* would keep guests and logs from filling the space `/var` and `/home` need.

### 5.2 Boot

1. Firmware verifies systemd-boot with the owner's key *(planned)*.
2. systemd-boot picks the slot (section 7.3) and starts profile 0 of its UKI. Each UKI also has
   profile 1, `ID=recovery`, `TITLE=Recovery`, selectable in the menu with the same kernel,
   initramfs and verity root. Its command line adds only `convergent.recovery=1` before `init=`.
3. The kernel creates the dm-verity device for the slot from the UKI command line.
4. The initramfs mounts the verity device read-only as the new root. It refuses to boot while more
   than one disk has a `cv-state` partition, asks for the LUKS passphrase and opens the state
   volume. Auto-sized installs grow the last state partition when more than 1 GiB is free
   (partition, LUKS, then Btrfs); fixed/percentage installs retain their size through the
   install-written `install-state-size` marker on state. Installs without that marker never
   grow; `state-max-gib` only caps growth when the marker says `auto`. An interrupted grow
   finishes on a later boot. It selects the `/var` that belongs to this slot, takes a cold snapshot
   of it on the first boot of a new slot, mounts `/var` and `/home`, bind-mounts the listed `/etc`
   entries after merging missing image system accounts (IDs below 1000, preserving existing entries
   and warning on ID collisions) and adding the existing owner to `dialout` in group/gshadow,
   mounts `/run` and `/tmp` as tmpfs, arms the hardware watchdog,
   and switches to the real root.
5. OpenRC starts the host, then Incus, then the guests: fw1, fw2, wan, svc. Nothing in the start
   sequence needs a name before the firewalls' resolvers answer.

Verity checks every block when it is read: a tampered block fails to read, at boot or later.

With the recovery flag, after LUKS unlock and the state mount, the initramfs offers a console
menu before binding `/etc` or switching root: root shell (exit returns), owner password reset,
continue, reboot, power off. It shows the release, slot and read-write state path `/run/cv-state`.
The reset finds uid 1000 in the state's passwd, hashes two matching password entries with
`openssl passwd -6`, and atomically replaces the owner's shadow field with root:shadow 0640.
The watchdog is armed after leaving recovery. No network or daemon is started; `rd.shell=0`,
`rd.emergency=poweroff`, lockdown, verity and the disabled boot editor stay in force.

The normal title names version, kernel, release and slot, e.g. `SLOT A | Gentoo 0.1.0 - 6.18.57` (the release id orders the entries); recovery appends
`(Recovery)`. Entry IDs are `convergent-<release>-a.efi` and
`convergent-<release>-a.efi@recovery`, with boot counters stripped from both IDs.
In systemd-boot 260.1, entries sort by descending IMAGE_VERSION and filename, then profiles
retain their discovery order (0 first) in its stable sort. Thus `default convergent-[0-9]*`
selects the newest non-exhausted UKI's normal profile. Both profiles use the same counted
file, e.g. `convergent-<release>-a+3.efi`: entering recovery on an unblessed release consumes
one try. Continuing runs the usual health checks; `slot bless` renames that shared file to
`convergent-<release>-a.efi`, blessing both profiles.

Ukify 260 creates profile 0 in the final build (`--profile 'ID=main'`); only the recovery
fragment is joined. Joining separate p0 and p1 fragments would add a third profile because
ukify automatically supplies a base profile. Fragments live in a temporary directory and are
removed: release files, manifest entries and installed UKI names stay the same. Kernel and
initrd occur once; the profiles add only metadata and the recovery command line. The
installer's ESP check uses the actual UKI size, including these sections.

The standalone rescue UKI is independent of both slots: the release kernel, Intel microcode,
and a separate dracut initramfs with `convergent` and `convergent-rescue`. Its command line has
`convergent.rescue=1`, no verity table and no slot root. A cmdline hook claims a synthetic root;
the pre-mount hook unlocks state using the same code and US keyboard rules as normal boot, then
runs the rescue console menu without ever reaching root mounting or pivot. It neither grows
state nor prepares a release `/var`. The slot pre-pivot hook and watchdog drivers are omitted;
no network services or guest daemons run. The menu shares Recovery's password reset code.

Rescue includes cryptsetup, Btrfs, OpenSSL, `slot`, USB filesystem support and the small console,
disk, checksum and archive tools they need, with their libraries and i915 firmware. It mounts
release USB media read-only and requires the embedded channel key's manifest signature.
`slot rescue-write` is gated to rescue, permits an explicitly confirmed reinstall or downgrade,
and reuses normal write/readback and counted UKI installation while preserving `/var`, `good`
and `highest`. `slot rescue-next` sets the normal entry ID in `LoaderEntryOneShot`; logs can be
exported without starting guests. There is no continue-to-host path or rescue blessing.

Build rescue before EROFS and put it at `/usr/lib/convergent/rescue.efi`, covered by the slot's
verity hash. Release files and manifest fields stay unchanged, so update 7 clients can still
write the release. After health checks and blessing, `slot` compares that file with the ESP's
`EFI/Linux/convergent-rescue.efi`, copies to `.new`, checks, syncs, renames and syncs when it
differs. Existing rescue survives a failed copy; a later bless retries. The installer also copies
it and reserves space for two release UKIs, both systemd-boot paths, rescue and an extra rescue
for atomic replacement. Older releases without rescue remain installable.

Rescue's `IMAGE_ID=zz-convergent-rescue` sorts after bootable releases; systemd-boot 260 moves
exhausted entries below it regardless of sort key. The numbered default pattern excludes rescue,
including when both slots are exhausted. Bless migrates the old `default convergent-*` line.
Rescue is a normal, currently unsigned UKI and can be signed for Secure Boot later. Its ESP copy
is independent of slot corruption, but is not authenticated by firmware while Secure Boot is off.
`build/test --rescue` uses the existing QEMU/OVMF console driver and the actual embedded UKI,
with both slot roots empty; it checks unlock, menu, poweroff and unchanged counters/blessing state.

### 5.3 What is writable

Everything under `/usr` and the rest of `/etc` comes from the verified image. The writable `/etc`
entries are an explicit list: `machine-id`, `passwd`, `shadow`, `group`, `gshadow`, `subuid`,
`subgid` and `usbguard/rules.conf`. Incus and guest SSH keys live under `/var/lib`. `/home`, those
`/etc` entries and the guests' volumes are where an attacker could persist; the checker watches
selected files there, not guest-volume contents.

The image's `rootfs/etc/apparmor.d/` profiles confine chronyd, node_exporter, bluetoothd,
way-secure and pipewire-pulse. chronyd and node_exporter enforce; bluetoothd, way-secure and
pipewire-pulse complain (log, do not block) until real-hardware use shows no denials. Chronyd can adjust time and use the RTC and its
NTS state; the exporter reads kernel metrics and its textfiles; BlueZ uses system D-Bus, Bluetooth
sockets and pairing state. Browser helpers can use the owner's Wayland/PipeWire sockets and
their named session sockets; Pulse also supports the owner's ordinary session server.
`build/image` checks profile syntax. The boot AppArmor service loads them before default-runlevel
daemons, caching under `/var/cache/apparmor` (never the read-only `/etc`); a new release drops
the previous cache. `build/test --desktop` checks enforce labels, clock queries, a metrics scrape,
BlueZ D-Bus and browser sockets under headless Sway. Bluetooth pairing and audio devices still
need laptop testing.

---

## 6. Build and keys

The build host is a dedicated machine (a VM today) that does nothing else. It holds:

- a build environment: a signed Gentoo stage3 chroot;
- a Portage snapshot pinned by date and verified by signature;
- `/etc/portage` from this repository;
- a binary package cache: Gentoo's official hardened binary packages where they match, our own
  builds where USE flags differ;
- the outputs of each release.

`portage/overlay` holds packages Gentoo does not offer as needed: `aa-exec` alone, with
which Incus confines its image unpacker (the stock apparmor-utils would bring Python into the
image), and `way-secure`, which gives each browser a restricted Wayland security context.
It also pins GURU's `net-dialup/tio` 3.7 with its distfile hashes for serial consoles.
The image keeps and checks FTDI, CP210x, PL2303, CH341 and CDC ACM drivers; Gentoo udev
uses `dialout` for their device nodes. Files runs MC (internal editor, terminal-background
skin via env.d); Notes runs Vim in `~/Documents/notes`. Both use foot.

Branches and channels follow `dev` → `beta` → `stable`. Dev is unpublished work; beta is
built, tested and published. Release candidates are git tags on beta (`v0.1.0-rc1`), not a
channel. Stable is rebuilt from a candidate's exact commit with CHANNEL=stable and the offline key,
then tested again: the update URL and trusted key belong to the verified root, so a channel
is never switched by re-signing. Only beta builds carry the debug tool.

`VERSION` in `build/build.conf` is bumped per release using semver: `0.1.0` here, with optional
`-rcN`. `/usr/lib/convergent/version`, the per-slot `CONVERGENT_VERSION`, boot titles and the
signed manifest carry it. The timestamp release ID remains in `IMAGE_VERSION`, artifact names
and all A/B ordering and rollback checks.

Releases are signed per channel with Ed25519 (OpenSSL): the image carries its channel's public
key, and `slot write` takes only a manifest signed with it, unless `CONVERGENT_UNSIGNED=1` overrides
the check. The `beta` key lives on the
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
5. Write the manifest: release ID, semantic version, kernel version, root hash, file hashes.
6. Build the guest images, each with its own build: wan (Alpine), fw (OpenBSD), svc (Alpine),
   browser (Alpine).
7. Sign the manifest with the channel key (`manifest.sig`); signing the UKIs for Secure Boot is
   planned.
8. Publish: the five release files to `<channel>/<release>/` in a public object store (Cloudflare
   R2 today), then `<channel>/latest`, signed too. The manifest gives each file's size, so a
   download stops there. Two releases per channel; the bucket stays under about 9 GiB.
   Guest images go up too, listed in `guests.manifest` (7.2). Disk images (they hold the owner's
   account) are not published.

---

## 7. Install, update, roll back, recover

### 7.1 Install

From a Convergent USB disk carrying one release, or as a disk image (README, Install). Partition,
create LUKS and Btrfs, write slot A, install systemd-boot and slot A's UKI, register the boot entry
(physical install only) (and the removable-media path), create the owner's account. A disk image
also carries the guest images, and its first boot creates the guests. No network needed. *(Planned:*
in Setup Mode, enrolling the owner's keys and the option ROM hashes, otherwise
checking them; the stick as the recovery path when nothing on the laptop boots.*)*

The build/install YAML has no secrets and is saved at `/var/lib/convergent/config.yaml` only
for reference. Its `install` mapping selects a unique internal SSD/NVMe or explicit by-id disk,
auto/percentage/GiB state, and none/zram/encrypted-state swap; both stick build and install
validate it. ESP and A/B sizes stay release constants. The installer seeds `/var` and writes
small runtime settings; nothing reads YAML at runtime. OpenRC starts swap before Incus.
Disk swap uses a separate top-level Btrfs subvolume, mounted under `/var/lib/convergent/swap`,
so release snapshots exclude its active file ([Btrfs swapfile constraints](https://btrfs.readthedocs.io/en/latest/Swapfile.html)).
See [USAGE, Install](USAGE.md#install) for ranges and capacity checks.

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

Releases carry guest images and their Incus profiles in `guests.manifest`, signed with the same
key beside the host manifest, which stays unchanged, so older releases and the installer that read
only the host manifest are unaffected; the signed `latest` names its hash (or `none`), so a mirror
can neither withhold nor swap it. Online updates download only guests whose identity (their
SHA256SUMS and delivered profiles) changed. After reboot and marking the host good, staged guests
apply in order: svc, wan, fw, browser; the bar shows GUESTS (red on failure). Nothing is applied
while a browser is open: it waits for `sys guests update`. When the booted release is already the
newest but its guests are not installed (it came as a host-only update), `sys update install`
downloads and applies them at once. Host-only releases remain valid.

Guests are updated only on a host slot already marked good, one at a time, each after an instance
export and snapshots of its custom state volumes; the last three backups per guest are kept. The
firewalls go one at a time: fw2 first, checked (CARP state, pfsync, pf ruleset hash, a resolution
through it, traffic over it for a short soak), then a failover to it, then fw1. A firewall that
fails its checks is put back to its previous image before the other is touched. A new firewall
copies nothing from the old one; after `guests update fw`, the host pushes its stored blocklist and
records (`dns-push local`, when a blocklist is stored). A new wan gets the saved Wi-Fi networks of
the old one: they are read in userspace from a copy of the old disk's partition (debugfs as an
unprivileged user, keeping only the iwd network files `.psk`, `.open` and `.8021x`); the old disk is
never mounted. Browser updates retain both def/int backups until both replacements pass, then
advance the image used for new tmp instances, including portal mode. A failed replacement restores both browsers
and their shared profiles, except during the one-time role migration below.

The browser update (also through `guests apply`, or init recovery) renames `web` to `def` and
`admin` to `int`, along with their state volumes. Under `browser-update.lock`, it stops old
containers, preserves the profile snapshots in `profiles.before`, and durably records the new
profiles in `browser.rename` before renaming anything. Each retry checks which old objects
remain; conflicting old/new names are refused. Instances receive the new profiles and keep
the same state volumes, including bookmarks and logins. The rename journal rolls forward:
`profiles_restore` leaves it intact, and browser launches stay blocked until both image
replacements pass. The existing `pending` journal still restores failed replacements.
`browser.ready` commits the image alias, removes unused old profiles and clears both profile
and rename journals. The `web` and `admin` networks and firewall addresses do not change.

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
- **Recovery:** each slot UKI's recovery profile and the standalone rescue entry (section 5.2), plus RECOVERY.md's numbered recipes
  for the failures known so far; each failure found on the laptop adds one. *(Planned:* restoring
  a guest snapshot, a restore tool for the backups.*)*

---

## 8. Observability

- **Metrics:** VictoriaMetrics scrapes node_exporter on the host, the firewalls and wan, and
  Incus' own metrics endpoint for instance state, every 30 seconds; retention is 14 days.
  Time and synchronisation come from
  node_exporter's time collector; staleness of any extra figure from the file's own age, which
  node_exporter reports. The few figures nothing else provides are written as small text files
  by the scripts of section 12: on each firewall its CARP, pf and unbound state; on the host,
  once per boot, the release numbers, Secure Boot, lockdown, the LUKS header hash and crash records,
  at boot and daily the NVMe health and certificate expiry; every minute the NTS state.
  NTS alerts allow five minutes to synchronise while an uplink is up; collector alerts allow
  five minutes for boot collection. Guest updates record their timestamps in the update journal
  (`/var/lib/convergent/guests/updates`), not in the metrics.
- **Logs:** VictoriaLogs receives syslog over TLS from the host, the firewalls and wan, including
  forwarded host audit records.
  Retention is seven days or 4 GiB, within a 6 GiB volume quota. Authentication, audit and firewall
  logging remain enabled. USBGuard uses LinuxAudit so device decisions reach audit.log and the
  existing audit syslog forwarder. Local messages also retain authentication and selected
  security programs below warning level. Guest update summaries and failures use syslog;
  slot bless records exhausted-newer-slot fallback, and the minute status probe logs observed
  firewall takeovers only when the last known coherent master changes.
- **Alerts:** vmalert evaluates the rules every 30 seconds; the status bar shows the counts, or "unknown" when svc
  does not answer; Grafana shows the details. Rules, carried from Archer and adapted:

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

- **Dashboards:** Overview (path and attention), Network (six CARP segments, pf and DNS), Guests
  (Incus state and resources) and Security (boot facts, trust and recent events), opened in the int
  browser. Stdlib Python generators in `guests/svc/dashboards` share Archer's palette, type scale,
  Canvas path and first-screen sizing; current state uses instant queries. CARP role-change
  annotations start off; actionable syslog panels link to all records in Explore. Footers name
  collection gaps. `build/lint` checks JSON drift; `build/test --guests-update` checks every metric
  panel query against real svc scrapes, allowing explicitly optional hardware and quiet alerts,
  and every LogsQL target. Security has one bounded event list; `sys security events` filters
  the two local host logs without svc (USAGE describes its bounds).
- **Checker:** runs after every boot, after every update and daily; it compares the running system
  with the release (verity, pf ruleset hashes, Incus settings, the writable `/etc` entries, device
  ownership) and checks host and internal guest state. Upstream connectivity is not part of it:
  `check status` polls Wi-Fi separately. Its results become the CheckerFailed and CheckerStale
  alerts.

---

## 9. Daily use

How the owner uses it is in USAGE.md. The design points:

- **Status bar:** the path (wan, which firewall is active, svc), alert counts or "unknown"
  (click for `sys security alerts` in foot), the
  release state, the idle-lock state, the default microphone's mute state, applied CPU power
  profile, camera enabled/remaining driver warning, and the usual system figures. Camera
  indication is availability, not recording.
- **Displays:** `sys display save` stores JSON under `~/.config/convergent/displays`, keyed by
  a hash of sorted make/model/serial triples for all connected outputs, including disabled ones.
  Duplicate identities are refused. A Sway output/tick subscriber applies profiles at login and
  on hotplug, mapping identities to current connectors; layout-only events do not reapply them.
  Unknown sets enable preferred modes with laptop scale 1.3, external scale 1. `set` previews for
  15 seconds; a separate rollback worker and exit traps restore the previous layout unless the
  owner types `yes`. A session lock serializes hotplug, saves and previews. If original screens
  disappear during rollback, remaining screens are enabled as a fallback. Profiles are data,
  never sourced as shell or Sway configuration. Saving retires the old connector-based file.
- **Power and camera state:** root writes choices under `/var/lib/convergent/power` and
  `/var/lib/convergent/devices/camera`; these follow the existing per-release `/var` snapshot.
  The boot/AC handler serializes updates, publishes the successfully applied CPU profile under
  `/run`, and restores optional charge/thermal choices. Charge start is five percentage points
  below end, with write order preserving a valid pair; absent sysfs controls are skipped.
  Dell's separate `charge_types` control selects Custom for a limit and Standard for off when
  present; writing thresholds alone does not activate them. Sysfs values are read back after writes.
  It also retries camera probing once after state is mounted. The video core and retained camera
  controllers have modprobe install gates that deny loading unless the choice is `on`.
  `on` loads UVC and matching Intel PCI camera drivers immediately; `off` denies new loads before
  trying to unload existing drivers, without force. Busy drivers cause an error and `CAM!`.
  USBGuard approval is independent. Camera drivers must remain modules in the laptop kernel;
  verify this and the actual camera/controller IDs on the laptop. Meeting compartments and
  screen sharing remain deferred.
- **Locking:** after 10 minutes idle by default (`idle_lock_minutes`) and when the lid closes;
  the idle lock can be paused from the bar. Never suspends.
- **Menu (`sys`):** `sys AREA [ACTION] [ARGS]`; each area's first action is its default.
  Short aliases work at the command line; the fzf menu (Archer's look) shows long names, status and command
  previews. Each action prints its commands; bemenu remains the quick picker.
- **Screenshots:** Print selects an area; Shift+Print captures the focused output after one second.
  Both use `sys screenshot`, save timestamped PNGs in `~/Pictures/screenshots` (created as needed),
  copy the image to the clipboard and send a three-second mako notification with the file name.
  libnotify supplies `notify-send`; mako's stock or owner-configured look applies.
- **Touchpad:** `sys touchpad set` validates and applies Sway's libinput options live: pointer speed,
  acceleration profile, tap, natural scrolling, disable while typing, scroll method and multiplier,
  middle emulation. It saves each change in the owner's `~/.config/sway/config.d/touchpad` include,
  keeping other touchpad choices and the separate keyboard and output includes. Hardware support varies.
- **Microphone:** present in firmware; the Sway session retries muting the default PipeWire source
  until it appears or the session ends. This runs at login only. `sys audio mic on|off` controls it;
  the mic key toggles when unlocked and only mutes when locked, using separate Sway bindings.
  The bar polls the default source every five seconds: orange `MIC` means unmuted, grey `MIC?`
  means unknown, and muted is hidden. This is mute state, not a recording detector; other sources
  and later default-source changes are not automatically muted. Browser audio remains playback-only.
- **Bluetooth:** off at boot (`AutoEnable=false`), enabled explicitly from `sys`. Pairing without
  a MAC scans for ten seconds; device actions offer known and discovered devices through fzf in
  a terminal or bemenu in Sway. Picker output must match a listed row and pass MAC validation;
  explicit MAC arguments and the confirmation before forgetting are retained.
- **Captive portals:** portal mode starts tmp with `--portal` and opens its two pf rules; it ends
  when the browser closes, when turned off, or after 30 minutes. The only time DNS goes anywhere
  but the firewalls.
  The browser launcher owns activation under its session lock and closes stale rules on all
  three guests before a new opening. Failure to close any side prevents opening. The portal
  tool journals closure before remote changes, retries partial closures each minute and records
  a reason for `sys portal status`. Expiry is checked by cron and by the browser session loop;
  remote mode checks use the minute status cache, refusing results stale for three minutes.
  An orphaned session without a browser lock is closed after a one-minute startup allowance.
- *(Planned:* owner guest actions in the menu, printing (off by default; IPP printers on
  the upstream network for the def/tmp browsers), clipboard clearing.*)*

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
| fw1 + fw2 (1 GiB each, plus QEMU overhead, unbound with the blocklist) | 2 200 |
| svc | 350 |
| Total, idle, browsers closed; excludes optional zram | about 3 950 |

On the laptop 384 MiB firewalls ran out of memory at boot (the kernel relink beside the
blocklist), killing sshd and unbound while CARP kept the master role. Keep both firewalls at
1 GiB. The other limits stay at wan 512 MiB, svc 350 MiB (768 MiB with Grafana), def/tmp 2 GiB,
int 1 GiB and tmp in portal mode 512 MiB. Container limits are ceilings, not idle reservations; lowering
them without measured peaks risks OOM without proving an idle saving.

### 11.1 Work removed without changing sampling intervals

These are work counts from the code, not measured watts or battery minutes.

| Change | Expected saving |
|---|---|
| `tools/bar`: cache an unchanged Sway layout name | About 24 helper launches/minute (awk and grep at five-second intervals), plus repeated reads of the XKB rules list; a failed Sway query invalidates the cache |
| `tools/bar`: read the booted release once; share chip-name reads within each frame | 60 command-line reads/minute and all but one chip-name read per sensor chip per frame; temperature, clock, lock-health and input polling stay unchanged |
| `tools/check status`: combine CARP and portal-table reads on each firewall; serialize wan sessions | Five SSH sessions/minute instead of seven, no concurrent connection creation to the same guest within this run, and four fewer remote wc processes/minute; existing pinned keys and 60-second multiplexing remain |
| `tools/facts`: parse each slot status in shell | Four awk processes removed per boot-status attempt; no change to boot, daily or hourly checks |
| `tools/power`: read sysfs with shell builtins; log only changes or failures | Up to four cat processes per CPU policy removed per AC event, plus supply/config reads; duplicate events produce no power log to store or forward |

Status probes still run every minute, with bounded requests and one worker per guest. Portal
reads hold the existing action lock; a busy lock, failed query or inconsistent sides yields
unknown. Failed Incus inventory still ages out rather than publishing false down states. The
WAN's three sequential probes share a 25-second budget plus kill grace, measured with monotonic
uptime; healthy requests reuse one SSH connection. The bar's 180-second stale limit and WAN's
forced-command allowlist are unchanged.

No cron interval was lengthened: the minute jobs enforce portal expiry, publish fresh network
facts or notice boot/update changes. `check auto` already gates expensive successful scans to
daily and failed scans to five minutes. Host facts already run hourly/daily. The firewall's
two-second wan-watch probe is a failover control, not merely a dashboard refresh.

### 11.2 Proposals, not enabled

| Proposal | Saving and trade-off | Recommendation |
|---|---|---|
| USB autosuspend except HID/audio | May let USB devices/controllers idle; composite devices, approved uplinks and storage can still stall or fail on resume | Test an explicit device allowlist first, including every interface of composite devices; keep USBGuard and HID/audio exclusions |
| PCIe ASPM powersave policy | May reduce link idle power; resume latency and firmware/device compatibility need measurement | Keep firmware/kernel defaults until tested; never force ASPM or change IOMMU isolation |
| SATA link PM / NVMe APST tuning | SATA has no demonstrated target here; deeper NVMe states trade exit latency and device reliability for idle power | Keep driver defaults and quirks; inspect the actual NVMe power states before tuning, never force APST |
| HDA audio power saving | May idle the codec/controller; wake delay and clicks are possible | Test speaker, headset, microphone and PipeWire resume first; do not apply an HDA option blindly to another audio driver |
| Disable NMI watchdog | Removes hard-lockup detector activity, but loses hard-lockup diagnostics; the boot hardware watchdog is a different mechanism | Keep it until that diagnostic loss is explicitly accepted |
| Longer dirty writeback/expiry intervals | Can batch writes, but leaves more recent data vulnerable to sudden power loss and can increase write bursts | Keep defaults, especially for logs and guest disks; read-only root does not make writable state disposable |
| KSM across fw1/fw2 | Potential shared-page RAM saving, at scanning CPU cost and with cross-guest deduplication side channels | Do not enable; the two firewalls remain separate trust compartments |
| Lower CPU caps, disable turbo or stronger EPP | Can lower load power at the cost of burst response and throughput; idle savings are not established | Keep the existing configurable 4.2 GHz cap and source-specific EPP; compare energy per task before further caps |
| Static hugepages or different THP policy | Possible TLB benefit, but reservations/fragmentation or compaction can hurt memory flexibility and latency | Keep current defaults; benchmark VM throughput and desktop tail latency first |
| Disable mitigations or relax hardening | Possible CPU saving by removing protections | Reject; keep mitigations, strict IOMMU, lockdown, verity, audit and guest confinement |
| Longer bar, scrape/eval or health intervals | A 60-second scrape/eval interval roughly halves those operations but delays detection and reduces history resolution; slower CARP probes delay failover | Keep the current cadences. All vmalert groups explicitly set 30s, so changing only its command-line default would not help |
| Shorter retention or suppress routine SSH/cron logs | Less disk use and query work, but less incident/debug history | Keep 14-day metrics and seven-day/4-GiB logs; keep auth/audit/firewall logs. Only redundant power messages are suppressed at source |
| Smaller guest limits or zram | Lower VM RAM may help, but KARL already disproved small firewalls; container caps do not reserve their full size. Zram adds metadata and compression work and changes OOM behaviour | Keep guest limits. Zram's old 32-GiB budget was only a plan: there is no enabled device here to shrink. Measure peak memory/pressure before choosing a size; do not claim a RAM saving from a documentation change |

The kernel documents the limitations of [USB runtime PM](https://docs.kernel.org/driver-api/usb/power-management.html),
[audio power saving](https://docs.kernel.org/sound/designs/powersave.html),
[writeback intervals](https://docs.kernel.org/admin-guide/sysctl/vm.html),
[lockup detection](https://docs.kernel.org/admin-guide/lockup-watchdogs.html) and
[zram allocation](https://docs.kernel.org/admin-guide/blockdev/zram.html).
Incus documents [memory ceilings](https://linuxcontainers.org/incus/docs/main/reference/instance_options/),
and vmalert documents [group evaluation intervals](https://docs.victoriametrics.com/victoriametrics/vmalert/).

On the laptop, compare the same display brightness, radio connection and closed-browser workload
on battery before/after: battery energy over a long idle window, CPU time/context switches,
package idle residency, SSH sessions and log bytes. Also exercise layout changes, missing guests,
portal transitions, AC changes and browser load. No laptop wattage or runtime gain has been
measured from this checkout.

---

## 12. Our own code

Convergent writes as little as it can:

- **No daemons of our own.** Each piece is a short script started by OpenRC, cron, acpid or the
  owner, and exits when done; the bar, watchdog feeder and Sway display-event subscriber are
  the long-running exceptions.
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
| `fetch-release` | from the menu (`sys update install`) | Downloads the newest signed release of the image's channel and hands it to `slot write` |
| `guests` | at first boot; by hand | Creates the guests; updates one guest, or the firewall pair in order, with checks and rollback |
| `check` | cron: after boot and updates, daily | The checker (section 8) |
| `bar` | in the session | The status bar; asks vmalert every 30 seconds |
| `sys` | from a key binding | The menu: one file per area in `/usr/lib/convergent/sys` |
| `apps` | Super+d | Lists the graphical apps from their desktop entries in bemenu and starts the chosen one; a failed start shows why |
| `browser` | from the menu or a key | Starts a browser container with its restricted Wayland and audio sockets |
| `facts` | at boot; hourly cron | Writes the host's extra figures for node_exporter, archives pstore records |
| `dns-push` | weekly; by hand | Downloads, validates and pushes the blocklist and the owner's records to both firewalls |
| `portal`, `devices`, `backup` | from the menu | Captive-portal mode; USB and Thunderbolt approval; the backup (section 7.4) |
| `account` | by hand; from the menu (`sys security password`) | Changes a login password on the state volume and rebinds `/etc/shadow` |
| `power` | at boot; acpid and udev, on AC and USB-C supply changes; sys actions | Sets CPU preference/cap, publishes profile, restores optional battery/thermal settings and camera choice |
| `fw-facts` | cron on each firewall | Writes CARP, pf and unbound state for node_exporter |

---

## 13. Repository layout

The directories are in the README's Repository table. The guest images, as `guests init` and
`guests update` read them (each directory also holds the `SHA256SUMS` checked first):

- `RELEASE/guests/fw/`: `fw{1,2}.qcow2`, `fw{1,2}.{pf,rules}.sha256`.
- `RELEASE/guests/wan/`: `wan.qcow2`, `wan-metadata.tar.xz`.
- `RELEASE/guests/svc/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus.yaml`.
- `RELEASE/guests/browser/`: `metadata.tar.gz`, `rootfs.tar.gz`, `incus/{base,def,tmp,int}.yaml`.

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
