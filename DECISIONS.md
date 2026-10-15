# Decisions

Each decision has a status: **proposed** until the owner accepts it, then **accepted**.
An accepted decision is changed by adding a new entry that supersedes it, not by editing it.

| # | Decision | Status | Why |
|---|---|---|---|
| 1 | Host on Gentoo, hardened profile, OpenRC | accepted | OpenRC, full control over hardening and features; the owner's chosen endgame |
| 2 | The laptop never compiles; a dedicated build host builds images | accepted | Verified, reproducible releases; no toolchain on the laptop |
| 3 | Radio in an Alpine VM (wan) that does the only NAT | accepted | Linux has the Wi-Fi 7 driver; the host never touches untrusted networks |
| 4 | Firewall pair as two OpenBSD VMs with CARP and pfsync | accepted | Each has its own kernel, so one can be patched or broken while the other carries traffic |
| 5 | The firewall pair routes between every segment; the host has an address only on its own segment and ignores the other bridges | proposed | One policy point; the host is never a router and never reachable from a guest's bridge |
| 6 | glibc rather than musl on the host | proposed | Simpler for toolchains and binary packages |
| 7 | Read-only EROFS root per A/B slot; the kernel creates dm-verity from the signed UKI command line; the initramfs mounts it and prepares the state | proposed | Verified to the last block, with no verity code of our own; one place for the boot steps |
| 8 | systemd-boot (boot loader only) with boot counting; our own OpenRC service marks a slot good | proposed | The only maintained boot loader with boot counting and UKI support; works without systemd init |
| 9 | `/etc` from the image, with an explicit short list of writable entries; no whole-`/etc` overlay | proposed | A writable overlay would undo the verified root |
| 10 | A cold `/var` snapshot per slot generation, taken and restored by the initramfs; guest images updated only on a slot marked good | proposed | Incus migrates its database on upgrade; the slot and its `/var` must match |
| 11 | LUKS passphrase now; TPM2 with a PIN later | proposed | No maintained TPM2-plus-PIN unlock without systemd; that hook would be security-sensitive code of our own |
| 12 | Browsers as unprivileged Incus containers from one Alpine image with Firefox: web, tmp, portal, admin | proposed | Reuses Incus networking and address binding; no privileged helper of our own; policy in pf like every other compartment |
| 13 | One svc container: unbound, VictoriaMetrics, VictoriaLogs, vmalert, Grafana on demand | proposed | Replaces Archer's two copies of Prometheus, Loki and Grafana |
| 14 | DNS in svc, not on the firewalls; resolution pauses while svc restarts | proposed | Keeps the firewalls minimal |
| 15 | Blocklist: hagezi pro.mini | proposed | About 110 MiB in unbound, against 260 MiB for pro |
| 16 | iwd in wan | proposed | Smaller than NetworkManager; roams between known networks |
| 17 | Status bar, menu and collector in shell for the first release | proposed | Ports Archer's proven tools; a single daemon can replace them later |
| 18 | Static addresses everywhere, bound to each NIC by Incus; no DHCP inside the system | proposed | DHCP on a CARP pair has no clean way to choose which firewall answers; bound addresses stop spoofing |
| 19 | IPv6 disabled everywhere | proposed | No upstream need; one address family to reason about |
| 20 | Internal addresses from one /16, default 100.80.0.0/16, set in one place; wan refuses an overlapping upstream lease | proposed | Carrier-grade NAT uses the same space; overlap must be detected, not assumed away |
| 21 | CARP advertisements unicast to the peer (`carppeer`), preempt on, one demotion group | proposed | No dependence on the bridges' multicast handling; all addresses move together |
| 22 | No Incus agent or guest API in wan; the host manages wan and the firewalls over SSH | proposed | The Incus agent is a path into the host's Incus; SSH through pf is narrower and logged |
| 23 | IOMMU strict, Thunderbolt PCIe tunnels by approval, NVIDIA held by vfio-pci, USBGuard default deny | proposed | DMA and USB were the open attack surfaces |
| 24 | Option ROMs allowed by exact hash from the TPM event log, not by Microsoft's third-party certificate | proposed | Keeps the boot chain to the owner's key plus the exact ROMs present |
| 25 | The Secure Boot signing key on a hardware token or offline media, never on the build host; key and LUKS header backups offline | proposed | The build host is the root of trust; the key must outlive and outrank it |
| 26 | Watchdog armed by the initramfs after the passphrase | proposed | A slow passphrase must not consume boot tries; a hang after it must |
| 27 | Upstream LAN not part of "internet"; printing to it switched on from the menu | proposed | The upstream network is untrusted too |
