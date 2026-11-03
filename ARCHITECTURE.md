# Convergent architecture

Design and security boundaries. Commands: [USAGE](USAGE.md); repairs: [RECOVERY](RECOVERY.md);
build and hardware-test status: [BUILD](BUILD.md#status). Planned features are marked explicitly.

## 1. Principles

- **Verified root:** dm-verity checks OS blocks on read. Secure Boot signing is planned; until then,
  firmware does not authenticate the UKI or its root hash.
- **Built elsewhere:** the laptop receives whole images, without a compiler or package manager.
- **Compartments:** separate radio, firewall, service, browser and work guests limit exposure.
  PF controls routing; host bridge/input rules and WAN egress rules protect the edges.
- **Fail closed:** both firewalls down stops routed traffic. Same-VLAN work traffic remains local.
- **A/B replacement:** the previous image stays bootable with its matching `/var`.
- **Declared configuration:** validated build inputs and repository files define the image.

## 2. Overview

```text
                         Wi-Fi card (VFIO)
                                |
                         wan (Alpine VM)       upstream DHCP, NAT
                                | transit
                    +-----------+-----------+
                    |                       |
              fw1 (OpenBSD VM) --- sync --- fw2 (OpenBSD VM)
                    |      CARP, pfsync, Unbound      |
             +------+------+-------+-------+---------+-------+
             | host | svc  | web   | admin | guests  | work  |
             |      |      | def   | int   |         | VLANs |
             |      |      | tmp   |       |         |       |
             |      |      |Remmina|       |         |       |
```

Incus bridges provide L2. Only `host` has a host address. Infrastructure NIC filtering binds
addresses to guests; work VLANs use MAC filtering and infrastructure anti-spoofing because Incus
cannot combine VLANs with IP filtering. Routing policy is in section 4.

## 3. Components

### 3.1 Host

| Area | Implementation and reason |
|---|---|
| Base | Gentoo hardened profile, OpenRC, glibc; systemd-utils supplies boot tools |
| Kernel | Gentoo kernel plus `build/kernel.config`: confidentiality lockdown, enforced module signatures with an ephemeral build key, built-in verity/EROFS/storage/KVM; no kexec, suspend, hibernation, host Wi-Fi, FireWire, X.25, SCTP, MPTCP, TIPC, RDS or CAN |
| Image trimming | Unused modules/filesystems removed or blocked; setuid/setgid retained only for sudo, su, passwd, unix_chkpwd and the D-Bus helper; all file capabilities removed |
| Command line | `init_on_alloc`, `slab_nomerge`, page/stack randomization, no vsyscall/debugfs; fbcon=nodefer applies the console font at boot |
| Kernel interfaces | Restricted ptrace, perf, BPF, pointers and dmesg; protected links/FIFOs; no TIOCSTI, automatic line disciplines, redirects, source routing or core dumps; martian-packet logging; strict reverse-path filtering |
| DMA | intel_iommu=on iommu.strict=1 efi=disable_early_pci_dma; NVIDIA functions claimed by vfio-pci and runtime power management; Wi-Fi alone in its IOMMU group, no ACS override. Boot verification of Thunderbolt protection is planned |
| Confinement | AppArmor plus Incus-generated guest profiles; host profile modes in section 5.3 |
| Audit | Immutable rules watch identity files, USB policy, guest keys, checker baseline, DNS state and the sudo log, and record root commands and module changes; authentication logging is separate from file watches; forwarded to svc |
| Accounts | Root locked; owner in wheel/seat/audio/video/dialout; su restricted to wheel; sudo PTY, own log and five-minute ticket; yescrypt passwords; five failures lock login for 15 minutes; restrictive umask |
| Session | seatd, greetd/tuigreet on tty1, Sway, foot, bemenu, mako, swaylock/swayidle, session PipeWire/WirePlumber; SOF firmware and ALSA UCM for SoundWire |
| Virtualization | Incus uses QEMU/KVM for VMs and LXC for containers; UI assets pinned for Incus 7.0.1 |
| Devices | USBGuard uses state-bound rules changed through IPC. Disk images initially allow HID/storage/hub classes; [first-boot enrollment](USAGE.md#first-boot) restricts individual devices. Camera loading needs a saved choice (section 9) |
| Power | No suspend; CPU preference/cap applied at boot and power-source events. Optional charge/thermal controls leave fan control to firmware. ACPI-event masking is planned |
| Time | chrony uses configured NTS sources (three by default), requiring two; starts without network and serves firewall NTP |
| Network | nftables input restrictions and no host forwarding (section 4.4) |

`INCUS_SKIP_INSTANCE_TYPES=true` prevents downloading instance-type definitions. Storage/boot:
section 5; logs/crashes: section 8 and [RECOVERY
13](RECOVERY.md#13-a-kernel-panic-or-crashrecorded-alert).

### 3.2 wan (VM)

Alpine LTS kernel, ext4 root and e2fsprogs. Owns the VFIO radio, runs iwd/upstream DHCP and performs
NAT. A passed-through USB Ethernet adapter provides the optional wired uplink via
`devices wired attach`, with Incus USB `required=false` and included Realtek NIC firmware.

- Wi-Fi: random MAC per network, regulatory country, protected management frames where offered;
  no DHCP hostname, mDNS or LLMNR, to reduce upstream identification. The wired uplink sends no
  hostname either, but keeps the adapter's fixed MAC and udhcpc's default vendor class.
- Credentials arrive over SSH stdin and are stored in wan; replies are sanitized. Replacement also
  stages root-only copies on encrypted host storage, which can remain until recovery or cleanup
  completes. The host checks Wi-Fi IPv4 six times, five seconds apart after association. Saved
  networks survive replacement.
- No Incus agent/guest API; host-only SSH on transit uses OpenSSH's default key exchange.
- Upstream output allows DHCP; transit output allows replies/syslog. Input allows management,
  metrics and firewall probes. Private forwarding is limited by section 4.2.
- Overlapping upstream leases are refused and raise UpstreamOverlap.
- Wired DHCP clears stale state after removal, addressless replug, identity or carrier changes,
  including cable loss/regain between checks. Assignment shares the guest-operation lock.
- PTP over KVM disciplines guest chrony without a network time listener.
- HPET off, free-page reporting on. Limits: section 11.

Controls: [Wi-Fi](USAGE.md#wi-fi), [Devices](USAGE.md#devices), [Captive
portals](USAGE.md#captive-portals). Diagnostic log: [RECOVERY 8](RECOVERY.md#8-where-the-logs-are).

### 3.3 fw1, fw2 (VMs)

OpenBSD with dedicated system interfaces, a work VLAN trunk and sync link. Separate kernels isolate
firewall failures from host kernel failures.

- **CARP:** One VHID/segment; fw1 skew 0, fw2 skew 100; `net.inet.carp.preempt=1`; unicast carppeer
  avoids bridge multicast dependence
- **pfsync:** Sync link with defer preserves established connections across failover
- **wan-watch:** rc.d service demotes wanwatch by 128 after two lost WAN probe rounds or ten rounds
  without local DNS or IPv4 forwarding; three good rounds recover. Each WAN probe round sends three
  probes 300 ms apart, bounded to one second; any reply passes. Group counter survives restarts
- **PF:** Routing/filtering, per-source state limits, transit MSS clamp and release ruleset hashes
- **Unbound:** Resolver on CARP gateways, so DNS follows failover
- **DHCP:** Work VLANs only; synchronized leases checkpointed across replacement
- **Management:** Host-only SSH, NTP from host, exporter and TLS syslog to svc; default route via
  wan
- **Maintenance:** Separate `sysmaint` demotion by 128 across registered CARP interfaces preserves
  health/upgrade counters; host journal survives interruptions; guest/DNS locks serialize operations

Remote mutations use base Perl's nonblocking `flock` on `/var/run/convergent-maintenance.lock`,
held across exec/children. Never unlink it: the PID is informational and work can outlive SSH.
The kernel releases it when its last holder closes; reboot clears `/var/run`. Rebuild records
replacement/seeding durably before skipping completed work on retry.
Procedures: [USAGE, Firewall maintenance](USAGE.md#firewall-maintenance).

The minute checker restarts a firewall after three minutes of failed checks only if its peer is
healthy and MASTER on every registered segment. It waits ten minutes after host boot or its own
restart, permits three attempts/hour, and is inhibited by guest journals, DNS pushes, maintenance
and shutdown.
A QEMU unreadable by Incus is killed using its pid file after verifying the instance in its command
line, then restarted; guest replacement uses the same stop procedure. Attempts appear in
syslog and the checker report.

On shutdown, `convergent-setup` drains work guests, browsers/Remmina, svc, wan, then firewalls, with
20 seconds per guest for graceful stop before forcing. Autorestart is held during stopping; previous
overrides are restored after a confirmed stop, while failures retain the hold.

### 3.4 svc (container)

Unprivileged Alpine container on its own segment.

| Service | Role |
|---|---|
| VictoriaMetrics | Scrapes host/firewall/WAN metrics; bounded cache, retention and queries |
| VictoriaLogs | TLS syslog; bounded cache, retention and queries |
| vmalert | Alert evaluation and bar API |
| vmauth | Query proxy |
| Grafana | Authenticated dashboards on svc's address; anonymous access off; runs while a plain int browser is open, not for the Incus session |

During replacement the host buffers logs and the bar reports unknown alert counts. DNS is
independent of svc. Retention/collection: section 8; memory: section 11.

### 3.5 Browsers

One Alpine Chromium image supplies unprivileged def/tmp/int containers. Roles, persistence and
commands: [USAGE, Browsers](USAGE.md#browsers). Each gets:

- A restricted Sway security-context socket: no capture, injection, other Wayland sockets, Sway IPC
  or X11, to isolate host interaction.
- Its own playback-only pipewire-pulse socket; no recording or D-Bus/desktop portals.
- A private download directory and Intel render node; portal mode uses software rendering.
- Image policies disabling DoH (gateway DNS), telemetry, studies and captive-portal probes.
  Window titles identify roles. External links opening in tmp remain planned.

Stopped temporary containers left by crashes are deleted only after taking their slot lock.
Portal overrides use a_portal, 512 MiB, WAN DNS, no render device, HTTP-enabled captive-page
policies, and no capture, extensions or search. Addresses: section 4.1.

#### Incus management

Int alone reaches the full-administration UI/API. PF admits int; host nftables drops other TCP
8443 traffic before loopback/established accepts. Metrics use a separate identity on 8444.

`tools/incus-ui` creates a 90-day client certificate through sudo. Only the AES-256 encrypted
PKCS#12 and public certificate persist in root-only TLS state. Each session prompts in a host
terminal, verifies the fingerprint and imports as UID 1000 into fresh tmpfs NSS state. Both
persistent NSS locations are masked, even for plain int. Import precedes trust; closing int stops
it and removes session trust/data. Boot and check auto clean orphans; interrupted rotation restores
a complete credential directory. Grafana-only launches receive no key.
Commands/endpoint: [USAGE, Incus management](USAGE.md#incus-management).

#### Remmina

Separate unprivileged Alpine container on web; restricted Wayland/playback audio and browser
session/update lock. No GPU, host D-Bus, SSH agent or host-directory mount. Software-rendered Cage
isolates its clipboard. Only numeric work destinations are reachable (section 4.2).

Shifted remmina-state mounts at /home/remmina. Its private session bus unlocks GNOME Keyring;
cancellation, locked or plaintext keyrings abort. The patched client clears credentials if Secret
Service fails rather than saving locally. A compromised unlocked client can read its credentials.

Shifted share mounts at /share; explicit VM attachments permit cross-domain file transfer.
Updates restore only remmina-state, never shared work. The minute checker stops orphan sessions.
Sizes: section 11; commands/sharing: [USAGE, Remote desktops](USAGE.md#remote-desktops).

### 3.6 User guests

`guests init` creates project owner with NIC-only work profiles and shared managed networks,
keeping profiles separate. The owner supplies disks/resources in Incus; sys guest creation is
planned. Configuration: [USAGE, Work VMs](USAGE.md#work-vms).

## 4. Network

### 4.1 Addressing

Internal space is 100.80.0.0/16 (RFC 6598 shared space). WAN rejects overlapping upstream leases.
Changing it requires coordinated host, WAN, firewall and tool configuration.

| Segment | Prefix | CARP gateway/DNS | fw1 | fw2 | Members |
|---|---|---|---|---|---|
| transit | 100.80.0.0/28 | .1 | .2 | .3 | wan .10 |
| sync | 100.80.0.16/30 | none | .17 | .18 | none |
| host | 100.80.1.0/28 | .1 | .2 | .3 | host .10 |
| svc | 100.80.2.0/28 | .1 | .2 | .3 | svc .10 |
| web | 100.80.3.0/24 | .1 | .2 | .3 | def .10, portal .11, Remmina .12, tmp .20–.99 |
| admin | 100.80.4.0/28 | .1 | .2 | .3 | int .10 |
| guests | 100.80.8.0/22 | .1 | .2 | .3 | Reserved; menu assignment planned |
| dom-dev-a / b | 100.80.32.0/26 / 100.80.33.0/26 | .62 | .49 | .50 | Static .1–.48; DHCP .51–.61 |
| dom-jhn-a / b | 100.80.36.0/26 / 100.80.37.0/26 | .62 | .49 | .50 | Static .1–.48; DHCP .51–.61 |

System addresses are static; work supports static/DHCP. System NICs use IP/MAC filtering and port
isolation except firewall NICs (CARP shared MAC, unfiltered/unisolated) and WAN transit (no IPv4
filtering, because it forwards other sources). Incus DHCP/DNS/NAT and IPv6 are disabled.

Addressless work carries VLANs 320/330/360/370 on firewall vio7 via fw1work/fw2work.
Family names/prefixes are defaults from `config.example.yaml`. Each VLAN is an L2 trust domain.
MAC/bridge rules block infrastructure IP/ARP spoofing, guest DHCP/CARP servers, IPv6 and stacked
VLANs. DHCP synchronizes over vio1; replacement checkpoints and reseeds leases.

`build/networks` renders topology into each image. `/etc/convergent/segments` lists CARP interfaces,
VHIDs, parents, labels, prefixes, gateways and families; carp.awk checks exact membership/coherent
roles. Work opens after host, WAN and both firewall hashes agree with a healthy MASTER. Validated
topology can serve without its standby. A responding node with PF disabled closes work immediately;
two masters close it but retain validation. The checker reconciles only while the guests lock is
free. Replacements receive stored DNS policy before promotion.

### 4.2 Flows

Allowed IPv4 flows; application replies use state. TCP/UDP DNS 53 to the local gateway is allowed on
host/svc/web/admin/guests/work except Remmina.

| From | To | Ports | Reason |
|---|---|---|---|
| host | Internet | UDP 123, TCP 4460 | NTP/NTS |
| host | Update source | TCP 443 | Temporary download addresses; failed close expires, with its states, within 4 h 15 min (15-minute check) |
| host | Blocklist source | TCP 443 | Weekly download; temporary addresses, same expiry |
| host | svc | TCP 6514, 8880, 9428 | Logs, alerts, log queries |
| host | fw1/fw2/wan | TCP 22 | Management and configuration |
| fw1/fw2 | host | UDP 123 | Time |
| fw1/fw2 | DoT forwarders | TCP 853 | Resolution |
| svc | host/fw1/fw2/wan | TCP 9100 | Exporters |
| svc | host | TCP 8444 | Certificate-authenticated Incus metrics |
| fw1/fw2/wan | svc | TCP 6514 | Logs |
| def/tmp | Public Internet | TCP/UDP 80, 443 | Browsing |
| def/tmp | Upstream printers | TCP 631 | Printing table; enabling control planned |
| portal tmp | wan | TCP/UDP 53 in portal mode | Upstream DNS |
| portal tmp | Portal destinations | TCP 80, 443 in portal mode | Captive page |
| int | svc | TCP 3000 | Grafana |
| int | host | TCP 8443 | Session-certificate Incus administration |
| Remmina | Work clients, excluding nodes/gateways | TCP 22, 3389, 5900–5999; UDP 3389; ICMP echo | Remote access; all else blocked |
| work | Own VLAN only (L2) | IPv4 | Other work VLANs (same family or not) and system segments blocked |
| work | Public Internet; configured home prefixes | IPv4 | Work egress and explicit RFC1918 access |
| work | Local gateway | ICMP echo | Gateway check |
| work ↔ firewalls | Work VLAN | UDP 68 ↔ 67; firewall echo to clients | DHCP |
| fw1 ↔ fw2 | Peers; sync | CARP; pfsync, UDP 8067 on sync | Gateway/state/lease synchronization |
| fw1/fw2 | wan | ICMP echo | Uplink probe |
| guests | Public Internet | TCP 80, 443; pf.guests overrides | Reserved guest egress |
| wan | Internal | Only initiated syslog to svc | Treat radio as untrusted |

PF excludes nonpublic destinations from Internet rules. WAN permits private egress only for active
portal sources and work targeting configured home_lan_prefixes; PF further limits portal
DNS/HTTP/HTTPS destinations.

### 4.3 Failover

The active firewall owns all CARP addresses. Failure transfers gateways, DNS and synchronized state
to its peer in about three seconds. WAN retains NAT and the external address. Both firewalls down
stops routing; same-VLAN work continues. WAN is a single point of failure.

### 4.4 The host and the bridges

Addressless bridges still expose host interfaces. Host nftables restricts new input to host
and section 4.2's sources, with loopback/established exceptions and the earlier 8443 gate. Other
bridges ignore ARP; strict reverse-path filtering and disabled forwarding prevent host routing.

### 4.5 DNS

- Unbound serves internal segments, validates DNSSEC and forwards over IPv4 DoT with
  address/certificate-name pairs. AAAA answers remain. The DoH canary returns NXDOMAIN to encourage
  system resolution.
- Rebinding protection strips configured private/shared/loopback IPv4 and IPv4-mapped IPv6 answers.
- Built-in names/reverse records come from local-names.conf at build time. Owner records and RPZ
  blocklist are validated/pushed together over SSH. Failed weekly downloads retain the last good
  list; owner exceptions exempt subdomains.
- dns-push holds its lock through validation, diff, confirmation and activation. Encrypted-state
  journals restore previous inputs and both firewalls; a commit marker prevents undoing completed
  pushes. Recovery stays pending until both nodes answer. last-push is separate from weekly stamp.
- Activation/rollback uses `unbound-control reload_keep_cache`, retaining cache when sizes/thread
  count stay unchanged (OpenBSD 7.9's Unbound 1.24.2).

Commands/files/editor validation: [USAGE, DNS](USAGE.md#dns-blocklist-and-own-records).

## 5. Storage and boot

### 5.1 Disk

| Partition | Content |
|---|---|
| ESP | systemd-boot, A/B UKIs with normal/recovery profiles, standalone rescue |
| A/B slots | EROFS images and dm-verity trees |
| State | LUKS2/Argon2id, Btrfs: per-release var, shared home/etc/pool, optional swap |

Discard is disabled to hide free-space patterns. Monthly Btrfs scrub checks data. Selected custom
volumes have quotas; a pool-wide quota is planned to protect home/var from aggregate guest growth.
Install sizing/swap: [USAGE, Install](USAGE.md#install).

### 5.2 Boot

1. Firmware starts systemd-boot; owner-key verification is planned.
2. The loader selects a slot (section 7.3), UKI profile 0. Profile 1 (`ID=recovery`,
   `TITLE=Recovery`) shares kernel/initramfs/verity, adding `convergent.recovery=1` before `init=`.
3. The kernel creates dm-verity from the UKI command line; initramfs mounts verified root read-only.
4. Unlock refuses ambiguous cv-state partitions. After unlock, normal boot arms the watchdog before
   state mounting; Recovery waits until Continue. Auto state grows partition, LUKS and Btrfs when
   over 1 GiB is available. Fixed/percentage installs or absent install-state-size disable growth.
   Legacy state-max-gib caps auto growth. Interrupted growth resumes later.
5. Initramfs cold-snapshots the last good var for a new release, or seeds it from the image on
   first installation. It mounts var/home/pool, merges missing system accounts below ID 1000
   (preserving existing entries and warning on collisions), adds the owner to dialout, and binds
   listed etc state. Var/home use nodev,nosuid; pool uses nodev; tmp is an 8-GiB
   nodev,nosuid,noexec tmpfs. Optional swap is separate. Intel MEI/GSC proxy modules are included.
6. OpenRC starts host and Incus. fw1/fw2/wan/svc autostart in bulk, with concurrency
   `max(floor(CPU threads/4), 1)` when priority/delay are unset. Startup needs no DNS before
   Unbound.

Changed verity blocks fail reads at boot or later. Recovery runs after state mounts but before
etc binds/pivot, without services/network. `rd.shell=0`, `rd.emergency=poweroff`, lockdown, verity
and the disabled editor remain enforced. Reset uses UID 1000, `openssl passwd -6` and atomic
root:shadow 0640 replacement. Procedures: [RECOVERY](RECOVERY.md#recovery-boot-menu).

UKI titles are `SLOT A | <NAME> <version> - <kernel>` with `(Recovery)` on profile 1. Entry IDs are
`convergent-<release>-a.efi` and `convergent-<release>-a.efi@recovery` (similarly b). Systemd-boot
260.1 sorts descending IMAGE_VERSION, then filename, preserving profile discovery order. `default
convergent-[0-9]*` selects the newest non-exhausted normal profile. Both profiles share
`convergent-<release>-a+3.efi`; Recovery consumes a try. `slot bless` removes the shared counter.
Ukify creates main with `--profile 'ID=main'` in the final build and joins only the recovery
fragment, avoiding a third profile and duplicate kernel/initrd. Temporary fragments are removed;
manifest/installed filenames stay unchanged. ESP capacity checks include actual UKI sizes.

Standalone rescue uses the release kernel/microcode and separate dracut initramfs, with
`convergent.rescue=1`, no verity table or slot root. Its synthetic-root/pre-mount hooks unlock state
and run the menu without growth, preparing release var, pivoting or arming a watchdog. No network/
guest services or host continuation; password reset shares Recovery code.

Rescue includes cryptsetup, Btrfs, OpenSSL, slot, USB filesystem/disk/archive tools, libraries and
i915 firmware. It mounts release USB read-only and requires the embedded channel signature. `slot
rescue-write` is gated to rescue and permits confirmed reinstall/downgrade with normal
size/hash/readback checks and counted UKIs, preserving var/good/highest. `slot rescue-next` sets
normal LoaderEntryOneShot. Log export starts no guests. Procedures: [RECOVERY,
Rescue](RECOVERY.md#standalone-rescue-entry).

The rescue UKI is built before EROFS at `/usr/lib/convergent/rescue.efi`, protected by slot verity.
It adds no host manifest fields. After blessing, slot updates ESP EFI/Linux/convergent-rescue.efi
via checked/synced .new and atomic rename; a failed release cannot replace it. Refresh failure logs
a warning and retries on the next bless; blessing succeeds and staged guest updates can proceed.
The installer reserves space for two slot UKIs, two loader paths and two rescue copies. Releases
without rescue remain installable.
IMAGE_ID=zz-convergent-rescue sorts below bootable slots, above exhausted entries; the numbered
default excludes it. Bless migrates the old `default convergent-*` setting. Secure Boot is off, so
ESP rescue is independent of slot corruption but unauthenticated.

### 5.3 What is writable

Verified usr/etc have eight state-bound exceptions: machine-id, passwd, shadow, group, gshadow,
subuid, subgid and usbguard/rules.conf. Incus and guest SSH keys live in var/lib. Home, etc and pool
are shared across slots; var is per release. Persistence boundaries: section 10.

Host AppArmor profiles in `rootfs/etc/apparmor.d/` enforce chronyd, node_exporter, bluetoothd and
pipewire-pulse. way-secure complains pending hardware validation. Chrony may adjust time/use RTC/NTS
state; exporter reads metrics/textfiles; BlueZ uses D-Bus/Bluetooth/pairing state; browser helpers
use named session sockets. Pulse also supports the owner's server. AppArmor loads before
default-runlevel daemons, caching in `/var/cache/apparmor`; new release snapshots drop old caches.
[Checks](BUILD.md#checks).

## 6. Build and keys

The dedicated builder holds a signed stage3 chroot, dated/signed Portage snapshot, repository
`/etc/portage` configuration, official hardened binary packages, locally compiled variants and
release outputs. Packages patched via `portage/patches/<category>/<package>/` always compile and
rebuild on patch changes; Sway's patch makes idle inhibition privileged so browsers cannot prevent
locking.

`portage/overlay` supplies aa-exec without the Python-dependent utilities, way-secure for restricted
Wayland, pinned tio/serial drivers and static Incus UI assets. Inputs/commands/release ordering:
[BUILD](BUILD.md#build-a-release).

The online beta key protects against download/bucket compromise, not builder compromise. Stable's
encrypted key stays offline until the owner checks the manifest and attaches it for signing. Signatures
establish origin, not benign contents. Offline owner Secure Boot keys are planned.
Channel/provenance/publication: [BUILD](BUILD.md#sign-and-publish).

Build steps (commands in [BUILD](BUILD.md#build-a-release)):

1. Verify the pinned Portage snapshot signature.
2. Assemble @convergent and @convergent-apps packages into staging.
3. Overlay rootfs files.
4. Remove modules not owned by `gentoo-kernel` before `depmod`; build initramfs, rescue,
   EROFS/verity and A/B UKIs.
5. Record release/version/kernel/root hash and file hashes in manifest.
6. Build WAN, firewall, svc, browser and Remmina images separately.
7. Sign manifests with the channel key; UKI signing remains planned.
8. Publish payloads and signed latest pointer.

### Build-time hardware support

`net-dialup/tio` 3.7 and its distfiles are pinned in the overlay. Image checks retain FTDI, CP210x,
PL2303, CH341 and CDC ACM drivers; Gentoo udev grants device access through dialout. Module and
firmware retention is configured in `build/build.conf`; VLAN and bridge nftables support is built
into the kernel.

## 7. Install, update, roll back, recover

### 7.1 Install

The installer partitions/encrypts state, writes A, installs systemd-boot/UKI and removable path,
registers physical-install boot entry and creates the owner. Disk images also carry guests for
network-free setup. Swap starts before Incus; disk swap mounts its subvolume at
`/var/lib/convergent/swap`. Firmware key/option-ROM enrollment is planned. Commands: [USAGE,
Install](USAGE.md#install).

`guests init` generates management keys, TLS credentials and a shared CARP password on the laptop.
TLS credentials/CARP password persist under `/var/lib/convergent/guests/` across replacements.
Images contain no credentials or SSH host keys. Read-only FAT16 CVSEED supplies credentials once.
Host verifies application, pins fw/WAN SSH keys from Incus console, checks health and detaches the
disk. Svc uses a mounted seed without SSH. Seedless firewalls keep CARP/dependent services off;
Alpine guests stop credential-dependent services.

Infrastructure starts together; pinning/checks remain sequential. With browsers closed, guest apply
renews CA/service certificates that are not yet valid or expire within 30 days, reusing their keys
and installing trust before consumers restart.

### 7.2 Update

1. Verify the release signature against the embedded key and all hashes. Signed latest more than
   five minutes ahead is refused; over 30 days old warns. Host writes require a good booted slot
   and a release newer than booted/highest-good IDs, protecting the only good slot and preventing
   old releases after manual rollback.
2. Write inactive slot, read back and verify; install its UKI with three tries.
3. Reboot and cold-snapshot var before daemons start.
4. Bless after host health checks: no crashed services, default runlevel running, boot-runlevel
   firewall/USBGuard/audit/AppArmor running and Incus answering. Guest/session gates are planned.
   Record highest, remove boot counter, then record good, so interruptions stay safe.
5. Each boot checks health. Counted boots use the 180-second watchdog, fed for ten minutes from
   the feeder's start, then left armed. Passing checks disarms it even after feeding stops;
   already-good releases disarm before checks.

Signed latest binds guests.manifest and separate remmina.manifest hashes; the latter preserves
older readers. Host manifests remain unchanged; host-only releases are valid. Guest identity is
SHA256SUMS plus profiles. Delivery/retry/staleness: [USAGE](USAGE.md#releases-and-guests).

Guest replacements require a good host and serialize operations. Snapshot custom state before
rebuilding in place; retain the old image until checks pass. Failure/interruption rebuilds/reseeds
the old image and restores snapshots; keep three snapshots/volume. Remmina excludes share.

With unchanged topology, replace fw2, check CARP/pfsync/rules/DNS/traffic, fail over, then replace
fw1. Failure restores the target before touching its peer. Reseed DHCP leases and push stored DNS
when available. Topology changes stop both firewalls under a durable journal; failure restores both
roots before either boots. Work stays closed until validation.
[Recovery](RECOVERY.md#4-guests-init-or-guests-update-stopped).

WAN networks are extracted from the old partition in userspace by unprivileged debugfs, keeping
only iwd .psk/.open/.8021x files; never mount the old disk. Browser replacement keeps both def/int
backups until both pass, then advances the tmp alias. Failure restores both and shared profiles.

Legacy web/admin objects migrate to def/int under browser-update.lock. profiles.before and durable
browser.rename precede renames; conflicts refuse migration. State/bookmarks/logins persist. The
rename journal rolls forward; pending replacement failures roll back. browser.ready commits the
alias, prunes unused profiles and clears journals only after both replacements pass. Launches stay
blocked until completion; network names/addresses remain web/admin. Signed firmware capsules/menu
updates are planned.

### 7.3 Roll back

Three failed counted boots skip the new slot; post-unlock hangs can consume tries via watchdog.
The previous slot selects its matching var/Incus database. Manual rollback also reverts var changes;
guest pool contents remain current, so guest updates can make old metadata incompatible. A menu
warning/block is planned. Home never rolls back; automatic home snapshots are planned.

### 7.4 Recovery and backups

Keep a second LUKS passphrase, recovery key and header backup offline on encrypted media, with
future Secure Boot key backups. Header-refresh reminders and a backup restore tool are planned.
Commands: [RECOVERY 10](RECOVERY.md#10-second-passphrase-and-header-backup);
backup scope: [USAGE](USAGE.md#backups); complete repair/restore recipes: [RECOVERY](RECOVERY.md).

## 8. Observability

- **Exporter profiling:** node_exporter's profiling endpoints remain reachable from svc only.
- **Exporters, monitoring self-metrics:** 30 seconds; bounded collectors/series and var/host
  selectors, PSI/diskstats
- **Incus:** 60 seconds; seven CPU/memory/network/disk resource families
- **facts:** Boot; minute NTS/audit; hourly storage/scrub/qgroups; daily NVMe/certificates, failed
  boot/daily collections retry hourly; virtio absence expected
- **observe:** Minute rule API, ages, guest pressure/update phases, host DNS; verified HTTPS to
  `example.com` only through running def's network namespace, never starts a guest or affects
  recovery
- **Firewall/WAN:** Minute CARP labels/counts, parent traffic, Unbound recursion/SERVFAIL, radio
  signal/bitrate/roams without SSID/BSSID labels; sampled transit RTT/loss
- **check:** After boot/update and daily; failed scans retry after five minutes; minute status
  probes
- **Rules:** Path/DNS 30 seconds; monitoring/compartments/capacity/logs/security-time one minute;
  boot/certificates/NVMe/scrub five minutes

Metrics retain 14 days without dedup. Recent scrapes cannot make old textfiles healthy. Closed def
means no HTTPS evidence, not failure; WAN probes measure transit, not Internet reachability.
VictoriaMetrics and VictoriaLogs flush every 30 s: at most 30 s of monitoring data is lost on a crash.

VictoriaLogs receives host/firewall/WAN TLS syslog plus host audit, with minute sender heartbeats.
Svc local warnings use loopback UDP without replay. Retention is seven days with a 2 GiB pruning
threshold within a 6-GiB quota; size pruning preserves the newest two daily partitions. Metrics have
no total-size retention cap. Host qgroup usage alerts above 85%; filesystem free-space guards do not
see quotas. Bounded host buffering covers svc outages. Authentication/audit/firewall logging remains
enabled; USBGuard LinuxAudit flows through audit syslog. Local messages also retain selected
security/auth records below warning.

Log stream fields are `remote_ip` and `app_name`; dashboard host identity comes from the connection;
app/message remain sender claims. Guest updates, bless/fallback and observed coherent-master changes
are logged; minute probes miss brief transitions. Incus UI setup/unlock/revoke uses the buffered
path; native events enter loopback UDP 1514 with identity/protocol/action/resource or method/path
only, queries stripped. No bodies, commands, tokens or daemon debug. A svc administrator or
compromised host can alter svc logs.

pflog_stream forwards sampled logged packet headers over TLS, capped at five/second/node with
suppression summaries. Local pflogd stays enabled; `convergent_pflogd_up` and
`convergent_pflogd_suspended` report running/suspended state. For an absent or suspended writer,
or a pflog file at least 1 MiB, fw-facts stops pflogd, removes any existing `pflog.bad`, rotates
through newsyslog and restarts pflogd. Ordinary rotation retains three compressed archives,
as enforced by install.site. Rankings
count samples, not all drops. On-demand capture holds a shared guest lock and bounds time, packets,
snaplen and transfer; no continuous upload. [Commands](USAGE.md#release-and-network-evidence).

fetch-release check verifies signed advisory status for installed/latest releases, including schema,
release, clock and prior generation, then atomically publishes metrics. Missing/invalid/pruned
status is unknown; no notification. Builder operation: [BUILD](BUILD.md#daily-advisory-status).

Zero alerts requires fresh healthy rule API evidence; unavailable svc yields unknown bar counts.
Implemented rules: `guests/svc/rootfs/etc/vmalert/alerts.yaml`.

| Area | Alerts |
|---|---|
| Path | FirewallDown, WanWatchDown, WanWatchProbeFailed, WanWatchLocalFailed, CarpSplit (both masters or none), CarpFlapping, CarpMixedRoles, PfsyncNotReady, NoDefaultRoute, FirewallRulesetDrift, StateTableHigh, UpstreamOverlap |
| DNS | ResolverDown, ResolverStale, BlocklistStale, InternetProbeFailed |
| Compartments | GuestStopped, ServiceDown, GuestOOM |
| Hardware and capacity | NvmeSpareLow, NvmeErrors, BatteryLow, StateVolumeHigh, StateReadOnly, BtrfsDeviceErrors, VolumeQuotaHigh, ScrubNeedsAttention |
| Security and time | SecureBootNotVerified, LockdownOff, KernelTainted, LuksHeaderChanged, AuditEvent, AuditRecordsLost, CertExpiry, ClockOffsetHigh, NtsUnauthenticated, CrashRecorded |
| Monitoring itself | CollectorStale, CollectorBroken, CheckerFailed, CheckerStale, RuleEvaluationUnhealthy, ObservationStale, MonitoringWriteErrors, MonitoringReadOnly, MonitoringSignalsMissing, per-sender log heartbeat |

Planned: GuestRestarted, WanReservedLeak, PassthroughDeviceMissing, HostNetdevUnexpected,
GuestRouteInjected, IncusPoolHigh, ReleaseOld, GuestImageOld and GuestReleaseEOL.

The checker compares verity, firewall hashes, Incus/tmp/Remmina profiles, writable etc,
autostart/SUID inventories, VFIO/device ownership and CARP against an accepted release; upstream
connectivity is excluded. Results feed CheckerFailed/Stale.
[Baseline commands](USAGE.md#health-and-alerts). Dashboard generators own shipped JSON in
`guests/svc/dashboards`; its README describes checks and collection boundaries. [Operator
views](USAGE.md#health-and-alerts).

## 9. Daily use

[USAGE](USAGE.md) owns controls. Implementation constraints:

- **Bar:** monotonic deadlines; input/alert caches expire after 180 seconds.
- **Displays:** hash sorted make/model/serial sets; subscriber maps them to connectors, ignoring
  layout-only events. Locks serialize save/hotplug/preview; worker/traps restore unconfirmed layouts,
  enabling surviving screens if originals disappear. Profiles are data, never sourced configuration.
- **Power/camera:** root-owned choices follow per-release var snapshots. Serialized boot/AC handler
  publishes successful CPU settings, restores optional controls and retries camera probing after
  state mount. Sysfs writes are read back; charge writes preserve valid thresholds. Modprobe gates
  video/controller loads unless enabled; disable records denial before non-forced unload. Busy
  drivers leave CAM!. Camera drivers must remain modules; modules/hardware IDs need laptop
  validation. USB approval is separate; meeting/screen sharing remains deferred.
- **Microphone:** session retries default-source mute until available; locked mic key only mutes.
  Other sources/later default changes are not automatically muted.
- **Bluetooth:** AutoEnable=false; picker selection must match an enumerated device.
- **Portals:** browser lock owns activation. All three guests must close stale rules before opening.
  Closure journal/retries survive interruption; cron/session loop enforce expiry. Cached remote
  state older than three minutes is refused. Orphans get one minute to acquire their browser lock;
  unavailable WAN/resolver closes all sides on refresh.
- Owner guest menu actions, printing controls and clipboard clearing remain planned.

## 10. Security model

| Threat | Boundary and reason |
|---|---|
| Rogue upstream | Radio/Wi-Fi/DHCP stay in wan, so host does not parse them |
| Network attacks | Section 4.2 restricts flows; only int with a session certificate administers Incus |
| Malicious website | Unprivileged AppArmor container, filtered network, restricted Wayland/audio and no D-Bus limit host access |
| Compromised guest | NIC/L2 anti-spoofing and PF limit cross-segment access; same-VLAN work shares trust |
| Compromised wan | Transit-only attachment, forced SSH, no agent/guest API; PF filters traffic |
| Host privilege escalation | Kernel hardening, AppArmor, sudo and audit reduce exposure and record actions |
| DMA/USB | Strict IOMMU, firmware-requested tunnel approval and USBGuard gate devices |
| Modified disk OS | dm-verity rejects changed blocks; signed-UKI authentication of root hash planned |
| Powered-off theft | LUKS2/Argon2id protects state; owner-key Secure Boot planned |
| Bad update | A/B counting, watchdog and matching var permit fallback |
| Supply chain | Signed dated inputs and channel signatures establish provenance; stable key offline |

Outside these boundaries: compromised host (controls every guest), signed malicious builder output,
unlocked physical access and firmware below Secure Boot. Home, writable etc and guest volumes can
persist compromise; checker coverage is selected files, not guest contents. Exact-hash option-ROM
allowance from TPM evidence is planned instead of Microsoft's third-party certificate enrollment.

## 11. Resource budget (unmeasured estimates)

| Item | MiB estimate |
|---|---|
| Host kernel/session/audio/bar | 700 |
| incusd | 200 |
| wan including QEMU overhead | 500 |
| fw1 + fw2 including QEMU/Unbound | 2,200 |
| svc | 350 |
| Idle total, browsers closed, no zram | About 3,950 |

| Configured ceiling | Limit |
|---|---|
| fw1, fw2 | 1 GiB each; KARL relink plus blocklist exhausted 384 MiB on the laptop |
| wan | 512 MiB |
| svc | 350 MiB; 768 MiB while Grafana runs |
| def/tmp | 2 GiB; portal tmp 512 MiB |
| int / Remmina | 1 GiB each |
| browser-def-state / browser-int-state | 4 GiB / 512 MiB |
| remmina-state / share | 512 MiB / 4 GiB creation default |

Container ceilings are not idle reservations. Lowering limits without peak measurements risks OOM.

### 11.1 Periodic work

Bar caches release/layout/sensor data; status combines firewall queries and serializes WAN SSH;
facts parses slot state in shell; power avoids redundant sysfs processes/logs. Sampling: section 8
and [USAGE, The bar](USAGE.md#the-bar). No wattage/runtime saving is established.

Minute probes retain bounded requests and one worker/guest. WAN's three sequential requests share 25
seconds plus kill grace, using monotonic uptime and 60-second SSH multiplexing. Portal reads hold
the action lock after waiting up to 30 seconds; longer contention leaves the previous portal sample
to age out, while failed/inconsistent queries yield unknown; failed Incus inventory ages out.
Safety probes retain failover timing.

### 11.2 Proposals, not enabled

| Proposal | Constraint/reason |
|---|---|
| USB autosuspend | Test device/composite allowlists, preserving HID/audio and approved uplinks/storage |
| ASPM, NVMe APST/SATA link PM, HDA savings | Keep defaults until latency/reliability tests; never force ASPM/APST or apply HDA options to another driver |
| Disable NMI watchdog | Retain hard-lockup diagnostics; boot hardware watchdog is separate |
| Longer dirty writeback | Keep defaults to avoid losing more recent state/logs on power loss |
| KSM across firewalls | Reject deduplication side channels and scanning cost |
| More CPU caps/turbo/EPP changes | Measure energy/task and responsiveness; current cap stays optional |
| Hugepages/THP changes | Measure throughput/tail latency before reservations or compaction changes |
| Relax hardening | Reject loss of mitigations, IOMMU, lockdown, verity, audit or confinement |
| Slower safety probes | Retain failure-detection timing |
| Shorter retention/log suppression | Preserve incident history and authentication/audit/firewall records |
| Smaller limits/zram | Measure pressure/compression cost; zram is opt-in, not an idle saving claim |

Compare battery energy at the same brightness/radio/workload, plus CPU/context switches, idle
residency, SSH/log counts. Exercise layouts, guest failure, portals, AC changes and browser load.

## 12. Our own code

OpenRC, cron, acpid and owner actions run scripts. Long-running pieces include bar, watchdog feeder,
display subscriber, guest session supervisors, wan-watch and pflog-stream. Incus, exporters and
system tools supply underlying mechanisms. Periodic host scripts/bar target under 1% of one core
at idle; unmeasured.

| Piece | Responsibility |
|---|---|
| slot / fetch-release | Slot integrity, blessing, delivery (section 7) |
| guests / browser / remote / incus-ui | Guest lifecycle and sessions (section 3) |
| check / facts / observe / firewall-capture | Checker, hardware/boot, monitoring and capture evidence (section 8); firewalls run fw-facts |
| sys / apps / notes / bar | Controls, launchers and status ([USAGE](USAGE.md)) |
| dns-push / portal / devices | DNS activation, portal rules and device approval |
| account / power / backup | Accounts, hardware choices and backup export |

## 13. Repository layout

| Path | Content |
|---|---|
| build/ | Builder, images, signing/publication, QEMU/offline checks, advisories and diagnostics |
| portage/ | Profile, sets, flags, patches and overlay |
| rootfs/ | Host configuration, `/usr/lib/convergent/sys` actions, health checks and lifecycle helpers |
| initramfs/ | Unlock, state, recovery and standalone rescue modules |
| install/install | Physical/disk-image installer, shipped as convergent-install |
| tools/ | Runtime commands from section 12 |
| guests/ | OpenBSD fw; Alpine wan/svc/browser/remmina builds and configuration |

Guest build inputs carry SHA256SUMS. build/guests compresses qcow2 files to .qcow2.zst for
publication; fetch-release expands them before applying:

- **guests/fw:** fw{1,2}.qcow2, fw{1,2}.{pf,rules}.sha256, fw{1,2}.syspatch, openbsd.version,
  segments, topology.sha256
- **guests/wan:** wan.qcow2, wan-metadata.tar.xz, wan.manifest, topology.sha256
- **guests/svc:** metadata.tar.gz, rootfs.tar.gz, incus.yaml
- **guests/browser:** metadata.tar.gz, rootfs.tar.gz, incus/{base,def,tmp,int}.yaml
- **guests/remmina:** metadata.tar.gz, rootfs.tar.gz, incus.yaml, packages.txt
