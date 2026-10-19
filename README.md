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
sign, publish ─────────────────────────────────► R2 ──────────► sys update install
                                   or release  ─► USB disk ─────► sys update usb
```

Nothing is compiled on the laptop. A release is one verified root image plus two boot files (one
per slot). The laptop keeps two slots, A and B: an update writes the slot not in use and boots it
with three tries; if it is never marked good (healthy), the other slot boots again.

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
| this README | you install, update, build or test |
| [USAGE.md](USAGE.md) | you use the laptop: the sys tool, the bar, browsers, Wi-Fi, devices, backups, coming from Arch |
| [RECOVERY.md](RECOVERY.md) | something is broken: numbered recipes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | you change the system and need the reasons |

## Status

| | |
|---|---|
| Proven in QEMU | boot, unlock, health check and fallback; a corrupted image refused; an interrupted update harmless; firewalls, wan and svc provisioned; guest updates with failover and rollback; booting the disk image over USB |
| Proven on the laptop | boot, blind unlock, autogrow, automatic setup, graphics, sway and the bar, Wi-Fi, an online update (download, signature, slot switch) |
| Built, laptop test to finish | browsers, audio, Bluetooth, power |
| Not built | Secure Boot signing (Secure Boot stays off), guest images online, a recovery boot entry |

Branches: `bleeding-edge` gets every change once the QEMU tests pass; `stable` follows only
after a release has also run on the laptop. Releases are tags on `stable`.

## Install

### A disk image (USB disk or stick)

The builder makes the image ([Build a release](#build-a-release)). It is 30 GiB
(32,212,254,720 bytes) by default, so a stick sold as "32 GB" may be too small. Write it on any
Linux:

```sh
lsblk -o NAME,SIZE,MODEL,TRAN                        # find the disk: TRAN usb, the right size
zstd -dc <out.img>.zst | sudo dd of=/dev/sdX bs=4M iflag=fullblock oflag=direct conv=fsync status=progress
```

The image holds both slots (B empty), the encrypted state with the owner's account, and the guest
images. At each unlock the state grows to the end of its disk unless `state_max_gib` caps it.

### The laptop's own disk

From a Convergent USB disk booted in UEFI mode, as root, with a release directory:

```sh
convergent-install /path/to/release
```

It checks the release's signature against the booted system's key (`CONVERGENT_UNSIGNED=1` installs
an unsigned one). It needs the Intel GPU as `/dev/dri/renderD128`. It lists the disks and refuses
the boot disk, mounted disks and anything under 49 GiB plus 4 MiB, asks you to type the disk again
(or `ERASE` and its serial), then the owner name, and the password and LUKS passphrase twice each.
It writes and verifies slot A, registers a boot entry named from the release's `NAME` and powers
off. Remove the USB disk before booting. The guest images are not copied: put the guest directory at
`/var/lib/convergent/release-guests/guests` and run `sys guests setup`.

## First boot

Before it: in the firmware setup (Dell: F2) turn Secure Boot off and leave VT-d on. Plug the disk
into a port of the laptop itself, not a hub or dock, and pick it in the boot menu (Dell: F12).

The passphrase prompt uses the **US keyboard layout**, whatever the keys show (on a Slovak
keyboard `@` is Shift+2, and `y` and `z` are swapped). The console uses `console_keymap`, US by
default.

1. `Passphrase [1/3]:` appears; three wrong tries power it off. Done when: a login prompt.
   Keys pressed while it boots reappear as empty `host login:` prompts; ignore them.
2. Log in as the owner. Done when: the console prints `release <release> is good` (minutes).
3. Run `dbus-run-session sway`. On a disk image the bar shows `SETUP` (orange) for 10 to 30 minutes
   while the guests are created; `SETUP failed` (red): `sys guests setup` resumes (log:
   `/var/log/guests-setup.log`). Done when: `SETUP` is gone.
   Keys: Super+Enter terminal, Super+m settings menu, Super+d apps, Super+b browser,
   Super+Shift+t throwaway browser, Super+Escape lock. All keys: [USAGE, Keys](USAGE.md#keys);
   bar: [USAGE, The bar](USAGE.md#the-bar).
4. Replace the by-class USB policy with a per-device one, with every trusted device attached
   (built-in camera, Bluetooth and fingerprint reader count as attached):
   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```
   Done when: `sudo devices list` shows nothing you use as blocked.
5. Super+m, Wi-Fi, Scan, Connect (or `sys wifi connect`). Done when: `sys wifi status` shows an
   address.
6. Run `sys selftest` (owner's password once); it writes `~/selftest-YYYYmmdd-HHMMSS.txt`.
   Done when: no line says FAIL (SKIP is fine).

The bar's `alerts` shows `?` until svc runs, then counts (`1c 2w`). Expected with Secure Boot
off: SecureBootNotVerified, CheckerFailed; without an accepted baseline also FirewallRulesetDrift.
Details: `sys browser admin` (Grafana, user `owner`; password:
`sudo cat /var/lib/convergent/guests/tls/admin-password`). Anything else is real.

Something off: [RECOVERY.md](RECOVERY.md); logs: `sys logs`; every command: `sys help`.

## Update

**Online** (Wi-Fi up): `sys update check` prints `up to date: release …` or `release N is
available`. `sys update install` downloads the newest release of the image's channel (about 1 GB),
checks its signature and hashes, writes the other slot and offers the reboot. The same by hand:
`sudo fetch-release` (`check` only reports). The firewalls open the download addresses only while
it runs; if closing them fails, they expire within 4 hours. Failures: RECOVERY 12.

**From USB:** copy the release directory (`manifest`, `manifest.sig`, `slot.img`, both `.efi`
files) to a stick, FAT32 or exFAT. Allow the stick (`sudo devices list`, `sudo devices allow
<number>`); `sys update usb` mounts it and writes the release. By hand:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo slot write /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

`slot write` checks the manifest's signature against the key built into the image; an unsigned
release needs `sudo env CONVERGENT_UNSIGNED=1 slot write ...`; the menu offers that only on an image
without a key. It runs only on the release marked good, checks every hash, refuses a release that is
not newer than the booted one and the highest ever marked good, writes the other slot, reads it back
and gives it three boot tries. After the reboot the release runs its health checks and marks itself
good; `sudo slot status` shows both slots. If it fails three times, the previous slot boots again
with its own `/var`. During these counted boots the hardware watchdog, if the laptop has one, resets
a boot that is not good within about 13 minutes of unlocking; otherwise hold the power button.

Guests update separately, on a slot already marked good, with every browser closed. Copy the new
guest images to the laptop; `$g` is that directory. Each guest is exported first and restored if
the new one fails its checks:

```sh
sudo guests update fw  $g/fw      # fw2 first, then failover, then fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
```

To go back by hand, pick the other slot in the boot menu: see [RECOVERY.md](RECOVERY.md).

## Build a release

On the build host, as root, from the repository root. Needs Gentoo with KVM, loop devices and
network access; the guest builds also need `qemu-img`, OVMF, `signify`, `python3`, `jq` and
`curl`.

Settings live in `/etc/convergent/config.yaml` on the build host (or the file named by
`CONVERGENT_CONFIG`); keys and defaults are in `config.example.yaml`, validation rules in
`tools/config-get`. The image keys (host name, time zone, keyboard layouts, display scale,
Wi-Fi country, time servers, blocklist, CPU cap, idle lock, `state_max_gib` to stop the state
growing past a size) are built into the release; the install keys (owner login, an optional
password hash, partition and image sizes) are read by `build/stick` and
`convergent-install --config`. A typo or unknown key stops the build. The LUKS passphrase is never
in it, and the passphrase prompt stays US whatever `console_keymap` says.

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
build/stick <release> $g <out.img> [size]          # disk image; size: 30G by default
zstd -T0 <out.img>                                 # compress it for the copy
```

`build/stick` asks for the LUKS passphrase (12 characters or more) and, unless `owner_password_hash`
is set, the owner password. The owner login comes from `CONVERGENT_INSTALL_OWNER`, else
`owner_login` in the config, else it is asked. It runs the real installer on a loop device and
prints the image's SHA-256. A disk image holds the owner's account: never publish one.

### Sign and publish

Each channel (`CHANNEL` in `build/build.conf`: `bleeding-edge`, later `stable`) has an Ed25519
key pair in `/etc/convergent/keys/` on the build host. `build/image` builds `<channel>.pub` and the
download URL into the image, and signs the manifest (`manifest.sig`) when `<channel>.key` is
there. The stable key stays on offline media: `build/sign <release-dir> /media/offline/stable.key`
asks for its passphrase. Make the keys once:

```sh
install -d -m 700 /etc/convergent/keys && cd /etc/convergent/keys
openssl genpkey -algorithm ed25519 -out bleeding-edge.key
openssl pkey -in bleeding-edge.key -pubout -out bleeding-edge.pub
openssl genpkey -algorithm ed25519 -aes-256-cbc -out /media/offline/stable.key   # passphrase
openssl pkey -in /media/offline/stable.key -pubout -out stable.pub
```

A laptop trusts only the key its image was built with; without that key its next update comes
from USB with `CONVERGENT_UNSIGNED=1`.

`build/publish <release-dir>` uploads to the public R2 bucket named in
`/etc/convergent/r2-<channel>.env` (mode 600: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY` of a token limited to the bucket, `R2_BUCKET`, `R2_PUBLIC_URL`, and
`R2_ENDPOINT` for an EU bucket). Only the five release files go up, only with a valid signature, to
`<channel>/<release>/`; then the signed `<channel>/latest` points at it (`build/sign` writes it). A
mirror cannot forge the pointer, but can hold back newer releases by replaying an older signed one;
`fetch-release` shows how old the signature is. Two releases per channel stay; it refuses to grow
the bucket past about 9 GiB (R2's free tier is 10 GB).

## Test in QEMU

Each test boots the release on a throwaway disk in `builder/test/<release>-<mode>` and passes or
fails by itself. Tests can run side by side as far as memory allows (8 to 12 GiB each).

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

`--guests` and `--guests-update` also try the Internet path: wan gets an emulated uplink (QEMU
user networking, as a second NIC), then fw1 must reach 9.9.9.9:853 and the host must resolve a
name; otherwise the test fails. Both modes also smoke-test the web browser container without
Wayland and check signed online updates when configured after a successful uplink. They run the
booted selftest checks as root; only release, verity, nested and audit failures gate the test.

## Checks

Run `build/lint` before a push. On tracked files: shell syntax, shellcheck when installed, leaked
secrets or session and scratch paths, CRLF line endings; and that each simple backticked
repository path in the docs exists.

Once a week, as root, run `build/advisories <release-dir> $g` (pass both: the default guest
directory is not `$g`). It reads the upstream fixes and names what to rebuild (`host`, `kernel`,
`fw`, `svc`, `browser`, `wan`, or `guests` for the pins). The kernel version comes from the
release; the Gentoo packages from the builder's current `/staging`, which must match it. Exit 1:
something to rebuild (UNKNOWN lines may appear too); 2: only UNKNOWN, a source was not read.

## Repository

| Path | What |
|---|---|
| `build/` | builder chroot, packages, image, sign, publish, QEMU tests, lint, advisories, disk image |
| `portage/` | make.conf, USE flags, package sets, the image profile, two local ebuilds |
| `rootfs/` | the host's own files: `/etc`, `/usr/lib/convergent` (the `sys` areas), health checks |
| `initramfs/` | the dracut module: unlock, `/var` per release, watchdog |
| `install/` | the installer, shipped as `convergent-install` |
| `tools/` | `slot`, `fetch-release`, `apps`, `guests`, `browser`, `sys`, `bar`, `check`, `backup`, `devices`, `portal`, `dns-push`, `power`, `facts`, `account` |
| `guests/` | `fw` (OpenBSD), `wan`, `svc` and `browser` (Alpine) |
