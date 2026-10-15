# Decisions

Each decision has a status: **proposed** until the owner accepts it, then **accepted**.
An accepted decision is changed by adding a new entry that supersedes it, not by editing it.

| # | Decision | Status | Why |
|---|---|---|---|
| 1 | Host on Gentoo, hardened profile, OpenRC | accepted | OpenRC, full control over hardening and features; the owner's chosen endgame |
| 2 | The laptop never compiles; a dedicated build host builds images | accepted | Verified, reproducible releases; no toolchain on the laptop |
| 3 | Radio in an Alpine VM (wan) that does the only NAT | accepted | Linux has the Wi-Fi 7 driver; the host never touches untrusted networks |
| 4 | Firewall pair as two OpenBSD VMs with CARP and pfsync | accepted | Each has its own kernel, so one can be patched or broken while the other carries traffic |
| 5 | The firewall pair routes between every segment; the host has an address only on its own segment and ignores the other bridges | accepted | One policy point; the host is never a router and never reachable from a guest's bridge |
| 6 | glibc rather than musl on the host | accepted | Simpler for toolchains and binary packages |
| 7 | Read-only EROFS root per A/B slot; the kernel creates dm-verity from the signed UKI command line; the initramfs mounts it and prepares the state | accepted | Verified to the last block, with no verity code of our own; one place for the boot steps |
| 8 | systemd-boot (boot loader only) with boot counting; our own OpenRC service marks a slot good | accepted | The only maintained boot loader with boot counting and UKI support; works without systemd init |
| 9 | `/etc` from the image, with an explicit short list of writable entries; no whole-`/etc` overlay | accepted | A writable overlay would undo the verified root |
| 10 | A cold `/var` snapshot per slot generation, taken and restored by the initramfs; guest images updated only on a slot marked good | accepted | Incus migrates its database on upgrade; the slot and its `/var` must match |
| 11 | LUKS passphrase now; TPM2 with a PIN later | accepted | No maintained TPM2-plus-PIN unlock without systemd; that hook would be security-sensitive code of our own |
| 12 | Browsers as unprivileged Incus containers from one Alpine image with Firefox: web, tmp, portal, admin | accepted | Reuses Incus networking and address binding; no privileged helper of our own; policy in pf |
| 13 | One svc container: VictoriaMetrics, VictoriaLogs, vmalert, Grafana on demand | accepted | Replaces Archer's two copies of Prometheus, Loki and Grafana |
| 14 | ~~DNS in svc~~ superseded by 28 | superseded | |
| 15 | Blocklist: hagezi pro.mini | accepted | About 110 MiB in unbound, against 260 MiB for pro; now held twice, on each firewall |
| 16 | iwd in wan | accepted | Smaller than NetworkManager; roams between known networks |
| 17 | Status bar, menu and collectors in shell for the first release | accepted | Ports Archer's proven tools; a single daemon can replace them later |
| 18 | Static addresses everywhere, bound to each NIC by Incus; no DHCP inside the system | accepted | DHCP on a CARP pair has no clean way to choose which firewall answers; bound addresses stop spoofing |
| 19 | IPv6 disabled everywhere | accepted | No upstream need; one address family to reason about |
| 20 | Internal addresses from one /16, default 100.80.0.0/16, set in one place; wan refuses an overlapping upstream lease | accepted | Carrier-grade NAT uses the same space; overlap must be detected, not assumed away |
| 21 | CARP advertisements unicast to the peer (`carppeer`), preempt on, one demotion group | accepted | No dependence on the bridges' multicast handling; all addresses move together |
| 22 | No Incus agent or guest API in wan; the host manages wan and the firewalls over SSH | accepted | The Incus agent is a path into the host's Incus; SSH through pf is narrower and logged |
| 23 | IOMMU strict, Thunderbolt PCIe tunnels by approval, NVIDIA held by vfio-pci, USBGuard default deny | accepted | DMA and USB were the open attack surfaces |
| 24 | Option ROMs allowed by exact hash from the TPM event log, not by Microsoft's third-party certificate | accepted | Keeps the boot chain to the owner's key plus the exact ROMs present |
| 25 | The Secure Boot signing key on a hardware token or offline media, never on the build host; key and LUKS header backups offline | accepted | The build host is the root of trust; the key must outlive and outrank it |
| 26 | Watchdog armed by the initramfs after the passphrase | accepted | A slow passphrase must not consume boot tries; a hang after it must |
| 27 | Upstream LAN not part of "internet"; printing to it switched on from the menu | accepted | The upstream network is untrusted too |
| 28 | DNS on the firewall pair: OpenBSD's unbound answers on every segment's gateway address; the host fetches and pushes the blocklist | accepted | DNS fails over with the gateway; svc stops being a single point; the firewalls get no HTTPS egress |
| 29 | zram only, 32 GiB; no disk swap | accepted | A ceiling, not a reservation: headroom for VM-heavy work at the price of about 128 MiB of index; 62 GB of RAM and no hibernation make disk swap unnecessary |
| 30 | User namespaces allowed for the owner (Firefox's own sandbox needs them inside its container) | accepted | The host user runs almost nothing besides the session; blocking them weakens the browsers more than it protects the host |
| 31 | No journal-style log sealing; logs leave the host as they are written | accepted | Shipping to svc gives the tamper evidence that mattered, with no extra mechanism |
| 32 | A USB network adapter can only be a wired uplink of wan; Archer's other roles (lab network, off) are dropped | accepted | One role covers the real use; the others were network policy for rare cases |
| 33 | Blocklist exceptions through one allow-list file; no unfiltered segments | accepted | Exceptions stay visible and few |
| 34 | The idle lock can be paused from the bar until the next lock | accepted | Archer's NL switch was used; it ends at the next lock, so it cannot be forgotten forever |
| 35 | Fingerprint for the lock screen only, off by default, if the reader is supported | accepted | Convenience on the lock screen; never for login or sudo |
| 36 | A `@convergent-apps` set the owner edits for personal programs (file manager, theme, editors) | accepted | Personal tools stay out of the infrastructure set and the review |
| 37 | VMs with UEFI and a virtual TPM, Windows supported; nested virtualisation off unless switched on per guest | accepted | Keeps Archer's VM support; nested KVM is attack surface most guests do not need |
| 38 | No LUKS header copy on the laptop's disk; offline backups only | accepted | Archer's on-disk header vault was a convenience; the offline copies are the real recovery |
| 39 | Our own code: no daemons, existing tools first, shell, under 1 % of one core at idle; every piece listed in ARCHITECTURE section 12 | accepted | The owner asked for minimal custom services; Archer's status bar and collector alone used about 12 % of a core |
