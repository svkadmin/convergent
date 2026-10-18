# Convergent

A single-owner laptop system, security first and still usable every day. The host is Gentoo
(hardened, OpenRC) running from a read-only root that the kernel verifies on every read. Updates
go to a second slot, and a release that does not come up healthy falls back to the previous one
by itself. The Wi-Fi card lives in its own VM, an OpenBSD firewall pair routes everything, and
services and browsers run in containers.

> Writing an image or running the installer **erases the whole target disk**.

## How it works

```text
build host                         your PC                      laptop
──────────                         ───────                      ──────
compile packages (once, cached)
build a release ─► test in QEMU ─► disk image ─► write to disk ─► boot, unlock, log in
                                   or release  ─► USB disk ─────► sudo slot write (update)
```

Nothing is compiled on the laptop. A release is one verified root image plus two boot files (one
per slot). The laptop keeps two slots, A and B: an update writes the slot not in use and boots it
with three tries; if it never reports healthy, the other slot boots again.

## The design in one page

```text
Wi-Fi card ─► wan        Alpine VM; owns the radio; the only NAT
                │
              fw1, fw2   OpenBSD VMs; pf, DNS over TLS with a blocklist; CARP failover
                │
     ┌──────────┼──────────────┐
    host       svc          browsers
 read-only   logs, metrics,  Chromium, one Alpine
 root, sway  alerts          container per role
```

- **Host:** boots from a verified EROFS image; `/etc` is read-only except a few files;
  `/var` and `/home` live on a LUKS2 (Argon2id) Btrfs volume, one passphrase at boot.
- **Network:** every segment goes through the firewall pair; the host has no route to the
  Internet of its own. One firewall can fail; wan cannot.
- **Hardening:** kernel lockdown (confidentiality), AppArmor, strict IOMMU, USBGuard, the NVIDIA
  card held by `vfio-pci` and powered down, audit to svc.

The full design is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Docs

| File | Read it when |
|---|---|
| this README | you build, test, install or update |
| [USAGE.md](USAGE.md) | you use the laptop: the sys tool, browsers, Wi-Fi, devices, backups, coming from Arch |
| [RECOVERY.md](RECOVERY.md) | something is broken: numbered recipes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | you change the system and need the reasons |

## Status

| | |
|---|---|
| Proven in QEMU | boot, unlock, health check and fallback; a corrupted image refused; an interrupted update harmless; firewalls, wan and svc provisioned; guest updates with failover and rollback; booting the disk image over USB |
| Built, first laptop test now | graphics, audio, Bluetooth, Wi-Fi in wan, browsers, bar, sys, power |
| Not built | release signing (Secure Boot stays off), updates over the network, a recovery boot entry |

Branches: `bleeding-edge` gets every change once the QEMU tests pass; `stable` follows only
after a release has also run on the laptop. Releases are tags on `stable`.

## Build a release

On the build host, as root, from the repository root. Needs Gentoo with KVM, loop devices and
network access; the guest builds also need `qemu-img`, OVMF, `signify`, `python3`, `jq` and
`curl`.

```sh
build/buildenv          # builder chroot from the pinned, signed stage3 and Portage snapshot
build/packages          # compile or fetch the image's packages (--pretend to preview)
build/image             # the release, named by UTC time: YYYYMMDDHHMM
```

The release lands in `/var/lib/convergent/builder/releases/<release>`. The guest images go into
one directory, here `$g`:

```sh
g=/var/lib/convergent/out/guests
mkdir -p $g/fw $g/wan $g/svc $g/browser/incus
guests/fw/build $g/fw                              # OpenBSD 7.9 with its errata
WAN_COUNTRY=SK guests/wan/build $g/wan             # Wi-Fi regulatory country
guests/svc/build && cp guests/svc/out/* guests/svc/incus.yaml $g/svc/
guests/browser/build && cp guests/browser/out/* $g/browser/ && cp guests/browser/incus/*.yaml $g/browser/incus/
```

## Test in QEMU

Run one test at a time. Each boots the release on a throwaway disk and passes or fails by itself.

```sh
build/test <release>                                  # boots and marks itself good
build/test --corrupt <release>                        # one flipped block: must refuse to boot
build/test --desktop <release>                        # sway, bar and sys: the session's programs and config
build/test --fallback <good> <newer>                  # broken newer slot: the good one returns
build/test --interrupt <good> <newer>                 # update cut off half-way: still boots
build/test --guests <release> $g                      # plus guests init: firewalls, wan, svc
build/test --guests-update <release> $g <broken-dir>  # plus guest updates and a rollback
```

`<broken-dir>` is a new path: the test builds a deliberately broken svc image there and checks
that the update is rolled back.

`--guests` and `--guests-update` also check the Internet path. The test gives wan an emulated
uplink (QEMU user networking, as a second NIC), then checks that fw1 reaches DNS over TLS and
that the host resolves a name through the firewalls.

## Checks

Run `build/lint` before a push: shell syntax, shellcheck when installed, leaked secrets or session
and scratch paths, CRLF line endings, and that every path the docs name exists. Once a week, as
root, run `build/advisories [release-dir] [guests-dir]` (by default the newest release): it reads
the upstream fixes for the kernel, the OpenBSD firewalls, the Alpine guests and the Gentoo
packages, and names what to rebuild (`host`, `kernel`, `fw`, `svc`, `browser`, `wan`, or `guests` for the
pins). Exit status 1 means something needs a rebuild, 2 means a source could not be read.

## Install

### A disk image (USB disk or stick)

```sh
build/stick <release> $g <out.img> [size]            # size: 56G by default, fits 64 GB
```

It asks for the owner password and the LUKS passphrase (12 characters or more; owner login from
`CONVERGENT_INSTALL_OWNER`, else asked), runs the real installer on a loop device and prints the
image's SHA-256. Compress it for the copy, then write it on any Linux:

```sh
zstd -T0 <out.img>                                   # on the build host
lsblk -o NAME,SIZE,MODEL,TRAN                        # find the disk: TRAN usb, the right size
zstd -dc <out.img>.zst | sudo dd of=/dev/sdX bs=4M iflag=fullblock oflag=direct conv=fsync status=progress
```

Use a USB 3 port and cable: on USB 2 a large image takes hours. The image holds both slots
(B empty), the encrypted state with the owner's account, and the guest images.

### The laptop's own disk

From a booted Convergent disk, as root, with a release directory:

```sh
CONVERGENT_UNSIGNED=1 convergent-install /path/to/release
```

It lists the disks and refuses the boot disk, mounted disks and anything under 49 GiB, asks you
to type the disk again (or `ERASE` and its serial), then the owner name, and the password and
LUKS passphrase twice each. It writes and verifies slot A, sets up the boot entry `Convergent`
and powers off. Remove the USB disk before booting. The guest images are not copied: put the
guest directory at `/var/lib/convergent/release-guests/guests`, then do first boot step 3.

## First boot

Before it: in the firmware setup (Dell: F2) turn Secure Boot off and leave VT-d on. Plug the disk
into a port of the laptop itself, not a hub or dock, and pick it in the boot menu (Dell: F12).

The passphrase prompt and the console use the **US keyboard layout**, whatever the keys show (on
a Slovak keyboard `@` is Shift+2, and `y` and `z` are swapped).

1. `Passphrase [1/3]:` appears. Three wrong tries power the laptop off.
2. Log in as the owner. Within a few minutes the console prints
   `release <release> is good`.
3. Create the guests. Several minutes per guest; if it stops, run it again:
   ```sh
   sudo guests init /var/lib/convergent/release-guests
   ```
4. With only trusted devices attached, allow them. Built-in devices (camera, Bluetooth,
   fingerprint reader) are always attached, so they are allowed too:
   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```
5. Run `sway`. Super+m opens `sys`: choose Network, then **Scan Wi-Fi networks** and
   **Connect to Wi-Fi** (or `sys network wifi-connect` in a terminal).
6. Run `sys selftest run` and keep the report it writes to `~/selftest-YYYYmmdd-HHMM.txt`. It asks
   for the owner's password once. Send the report with any FAIL.

Until signing exists the bar always counts two alerts: Secure Boot off, and the health checker
that fails because of it.

## Update

Copy the release directory (`manifest`, `slot.img`, both `.efi` files; about 1 GB) to a USB
stick, FAT32 or exFAT. On the laptop allow the stick (`sudo devices list`, `sudo devices allow
<number>`) and mount it under `/run`, since the root is read-only:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo env CONVERGENT_UNSIGNED=1 slot write /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

`slot write` checks every hash, refuses a release that is not newer than the booted one and the
highest ever marked good, writes the other slot, reads it back and gives it three boot tries.
After the reboot the release runs its health checks and marks itself good; `sudo slot status`
shows both slots. If it fails three times, the previous slot boots again with its own `/var`. A
hang after unlock is reset by the hardware watchdog after ten minutes, if the laptop has one;
otherwise hold the power button.

Guests update separately, on a slot already marked good, with every browser closed. Copy the new
guest images to the laptop; `$g` is that directory. Each guest is exported first and restored if
the new one fails its checks:

```sh
sudo guests update fw  $g/fw      # fw2 first, then failover, then fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
```

To go back by hand, pick the other slot in the boot menu: see [RECOVERY.md](RECOVERY.md).

## Repository

| Path | What |
|---|---|
| `build/` | builder chroot, packages, image, QEMU tests, lint, advisories, disk image |
| `portage/` | make.conf, USE flags, package sets, the image profile, two local ebuilds |
| `rootfs/` | the host's own files: `/etc`, `/usr/lib/convergent` (the `sys` areas), health checks |
| `initramfs/` | the dracut module: unlock, `/var` per release, watchdog |
| `install/` | the installer, shipped as `convergent-install` |
| `tools/` | `slot`, `guests`, `browser`, `sys`, `bar`, `check`, `backup`, `devices`, `portal`, `dns-push`, `power`, `facts` |
| `guests/` | `fw` (OpenBSD), `wan`, `svc` and `browser` (Alpine) |
