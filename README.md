# Convergent

Single-owner laptop system: security first, still usable daily. Gentoo host (hardened, OpenRC) on a
read-only root that the kernel verifies on every read. Updates go to a second slot; a release that
does not come up healthy falls back to the previous one. The Wi-Fi card runs in its own VM. An
OpenBSD firewall pair routes everything. Services and browsers run in containers.

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

Nothing compiles on the laptop. A release is one verified root image, two boot files (one per slot),
and optional guest images and profiles. Slots A and B: an update writes the idle slot and boots it
with three tries. If it is never marked good (healthy), the other slot boots again.

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

- **Host:** verified EROFS image; `/etc` read-only except a few files; `/var` and `/home` on a LUKS2
  (Argon2id) Btrfs volume, unlocked by one passphrase at boot.
- **Network:** every segment goes through the firewall pair. The host has no route of its own to the
  Internet. One firewall can fail; wan cannot.
- **Hardening:** kernel lockdown (confidentiality), AppArmor, strict IOMMU, USBGuard, the NVIDIA card
  held by `vfio-pci` and powered down, audit to svc.

Full design: [ARCHITECTURE.md](ARCHITECTURE.md).

## Docs

| File | Read it when |
|---|---|
| this README | you install, update, build or test |
| [USAGE.md](USAGE.md) | you use the laptop: sys, the bar, browsers, Wi-Fi, devices, backups, coming from Arch |
| [RECOVERY.md](RECOVERY.md) | something is broken: numbered recipes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | you change the system and need the reasons |

## Status

| | |
|---|---|
| Proven in QEMU | boot, unlock, health check, fallback; corrupted image refused; interrupted update harmless; firewalls, wan and svc provisioned; guest updates with failover and rollback; booting the disk image over USB |
| Proven on the laptop | boot, unlock, autogrow, automatic setup, graphics, sway and the bar, Wi-Fi, online update (download, signature, slot switch), the def and int browsers |
| Built, laptop test to finish | tmp browsers and portal mode, audio, Bluetooth, power, online guest delivery |
| Implemented, QEMU and laptop tests pending | standalone rescue entry, independent of both slots; `build/test --rescue <release>` |
| Not built | Secure Boot signing, including rescue (Secure Boot stays off) |

Branches and channels: `dev` → `beta` → `stable`. `dev` is unpublished. `beta` is built, tested and
published. `stable` is rebuilt from a release candidate's exact commit with the stable channel and
offline key, then tested again. Release candidates are git tags on beta, such as `v0.1.0-rc1`, not a
channel. The final tag is `v0.1.0`.

## Install

### A disk image (USB disk or stick)

The builder makes the image ([Build a release](#build-a-release)). By default it is 30 GiB
(32,212,254,720 bytes), so a stick sold as "32 GB" may be too small. Write it on any Linux:

```sh
lsblk -o NAME,SIZE,MODEL,TRAN                        # find the disk: TRAN usb, the right size
if [ "$(sudo blockdev --getss /dev/sdX)" = 512 ]; then
    zstd -dc <out.img>.zst | sudo dd of=/dev/sdX bs=4M iflag=fullblock oflag=direct conv=fsync status=progress
else
    echo 'Image writing requires 512-byte logical sectors; target refused.' >&2
fi
```

For a 4Kn internal disk (4096-byte logical sectors), boot compatible USB media and use the physical
installer below.

The image holds both slots (B empty), the encrypted state with the owner's account, and the guest
images. Auto-sized state grows to the end of its disk at unlock. Fixed and percentage install sizes
stay bounded. See [install options](USAGE.md#install).

### The laptop's own disk

From a Convergent USB disk booted in UEFI mode, as root, with a release directory:

```sh
convergent-install /path/to/release
```

It checks the release's signature against the booted system's key (`CONVERGENT_UNSIGNED=1` installs
an unsigned one). It needs the Intel GPU as `/dev/dri/renderD128`. It lists the disks and refuses the
boot disk, mounted disks, and anything under 49 GiB plus 4 MiB. Retype the disk (or `ERASE` and its
serial), then the owner name, then the password and LUKS passphrase, twice each. It writes and
verifies slot A, adds a boot entry named from the release's `NAME`, and powers off. Remove the USB
disk before booting. Guest images are not copied. Put the guest directory at
`/var/lib/convergent/release-guests/guests` and run `sys guests setup`.

## First boot

In firmware setup (Dell: F2), turn Secure Boot off and leave VT-d on. Plug the disk into a laptop
port, not a hub or dock. Pick it in the boot menu (Dell: F12).

The passphrase prompt uses the **US keyboard layout**, whatever the keys show (on a Slovak keyboard,
`@` is Shift+2, and `y` and `z` are swapped). The console uses `console_keymap`, US by default.

1. `Passphrase [1/3]:` appears; three wrong tries power it off. Done when: the greeter (tuigreet)
   asks for a user name. Ctrl+Alt+F2 to F6 keep text console logins.
2. Log in as the owner: user name, then password. Sway starts. The release is marked good within
   minutes (the bar: `rel <release> good`).
3. On a disk image, the bar shows `SETUP` (orange) for 10 to 30 minutes while guests are created.
   `SETUP failed` (red): `sys guests setup` resumes (log: `/var/log/guests-setup.log`). Done when:
   `SETUP` is gone.
   Keys: Super+Enter terminal, Super+m settings menu, Super+d apps, Super+b browser, Super+Shift+t
   throwaway browser, Super+Escape lock. All keys: [USAGE, Keys](USAGE.md#keys); bar:
   [USAGE, The bar](USAGE.md#the-bar).
4. Replace the by-class USB policy with a per-device one, with every trusted device attached
   (built-in camera, Bluetooth and fingerprint reader count as attached):
   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```
   Done when: `sudo devices list` shows nothing you use as blocked.
5. Super+m, Wi-Fi, Scan, Connect (or `sys wifi connect`). Done when: `sys wifi status` shows an
   address.
6. Run `sys selftest` (owner's password once). It writes `~/selftest-YYYYmmdd-HHMMSS.txt`. Done
   when: no line says FAIL (SKIP is fine).

Files and Notes are in the app launcher (Super+d). The bar shows `? ? ?` until svc runs, then
red/orange/white firing alert counts. Click for details, or run `sys alerts`. With Secure Boot off,
expect SecureBootNotVerified and CheckerFailed; without an accepted baseline, also CollectorBroken.
FirewallRulesetDrift needs an expected hash and reports only a mismatch. Details: `sys browser int`
(Grafana, user `owner`; password: `sudo cat /var/lib/convergent/guests/tls/admin-password`). Inspect
the named alerts rather than inferring faults from the counts. NTS refreshes every minute and alerts
after five minutes with an uplink. Collector warnings allow five minutes for startup.

Something off: [RECOVERY.md](RECOVERY.md); logs: `sys logs`; every command: `sys help`.

**Recovery:** pick the release's `(Recovery)` boot entry and enter the usual LUKS passphrase. Before the system starts, a console menu offers a root shell, an owner password reset, continue, reboot or power off. The
encrypted data mounts read-write at `/run/cv-state`. Recovery shares the release's boot tries: on an
unblessed release, it uses one. See [RECOVERY.md](RECOVERY.md#recovery-boot-menu).

## Update

**Online** (Wi-Fi up): `sys update check` prints `up to date: release …` or `release N is
available`. `sys update install` downloads the newest host release for the image's channel (about
1 GB) and only the changed guests. After reboot and marking the host good, guests apply in order:
svc, wan, fw, browser. The bar shows GUESTS while applying and GUESTS failed on failure. A running
browser waits: close it, then run `sys guests update` to retry. The downloader checks the signature
and hashes, writes the other slot and offers the reboot. By hand: `sudo fetch-release` (`check` only
reports). Firewalls open download addresses only while it runs; if closing them fails, they expire
within 4 hours. Failures: RECOVERY 12.

**From USB:** copy the release directory (`manifest`, `manifest.sig`, `slot.img`, both `.efi` files,
`guests/`, `guests.manifest` and `guests.manifest.sig`) to a FAT32 or exFAT stick. Allow it
(`sudo devices list`, `sudo devices allow <number>`). `sys update usb` mounts it and writes the
release. From a release before v10, run `sys update usb` again after booting v10, with the same stick,
to install its guests. Updating from a stick without guests leaves the old browser image and web/admin objects intact. def/int and `tmp --portal` need `sys update install` or a USB release carrying guests. By
hand on v10:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo fetch-release usb /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

`slot write` checks the manifest's signature against the key built into the image. An unsigned
release needs `sudo env CONVERGENT_UNSIGNED=1 slot write ...`, which the menu offers only on an image
without a key. It runs only on the release marked good. It checks every hash and refuses a release
not newer than the booted one and the highest ever marked good. It writes the other slot, reads it
back and gives it three boot tries. After reboot, the release runs its health checks and marks itself
good; `sudo slot status` shows both slots. If it fails three times, the previous slot boots again with
its own `/var`. During these counted boots, the hardware watchdog (if the laptop has one) resets a
boot that is not good within about 13 minutes of unlocking. Otherwise, hold the power button.

Guests can also update manually, on a slot already marked good, with every browser closed. Copy the
new guest images to the laptop; `$g` is that directory. Each guest is exported first and restored if
the new one fails its checks:

```sh
sudo guests update fw  $g/fw      # fw2 first, then failover, then fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
```

To go back by hand, pick the other slot in the boot menu: see [RECOVERY.md](RECOVERY.md).

## Build a release

As root, on the build host, from the repository root. Needs Gentoo with KVM, loop devices and network
access. Guest builds also need `qemu-img`, OVMF, `signify`, `python3`, `jq` and `curl`.

Settings live in `/etc/convergent/config.yaml` on the build host, or in the file named by
`CONVERGENT_CONFIG`. Keys and defaults: `config.example.yaml`. Validation rules: `tools/config-get`.
The image keys (host name, time zone, keyboard layouts, display scale, Wi-Fi country, time servers,
blocklist, CPU cap and idle lock) are built into the release. `build/stick` and
`convergent-install --config` read the owner login, image size and `install` disk/state/swap options.
ESP, slots and encryption stay fixed by the release. A typo or unknown key stops the build. No secrets
or password hashes are allowed. The installer keeps `/var/lib/convergent/config.yaml` only as a
reference; runtime uses generated settings. The passphrase prompt stays US whatever `console_keymap`
says.

```sh
build/buildenv          # builder chroot from the pinned, signed stage3 and Portage snapshot
build/packages          # compile or fetch the image's packages (--pretend to preview)
build/image             # the release, named by UTC time: YYYYMMDDHHMM
```

Bump `VERSION` in `build/build.conf` each release, using semantic versions (`0.1.0` for this release;
`major.minor.patch`, optionally `-rcN`). It appears in the image, boot menu, signed manifest and owner
status. The timestamp release ID still names artifacts, orders the boot menu (`IMAGE_VERSION`) and
drives A/B updates.

The release lands in `/var/lib/convergent/builder/releases/<release>`. Guest images go into one
directory, `$g`:

```sh
g=/var/lib/convergent/out/guests
mkdir -p $g/fw $g/wan $g/svc $g/browser/incus
guests/fw/build $g/fw                              # OpenBSD 7.9 with its errata
WAN_COUNTRY=SK guests/wan/build $g/wan             # Wi-Fi regulatory country
guests/svc/build && cp guests/svc/out/* guests/svc/incus.yaml $g/svc/
guests/browser/build && cp guests/browser/out/* $g/browser/ && cp guests/browser/incus/*.yaml $g/browser/incus/
build/guests <release-dir> $g                     # add guests for online delivery; re-sign when the key is present
build/stick <release> $g <out.img> [size]          # disk image; size: 30G by default
zstd -T0 <out.img>                                 # compress it for the copy
```

`build/stick` asks for the owner password, then the LUKS passphrase (12 characters or more each). The
owner login comes from `CONVERGENT_INSTALL_OWNER`, else `owner_login` in the config, else it is asked.
It runs the real installer on a loop device and prints the image's SHA-256. A disk image holds the
owner's account: never publish one.

### Sign and publish

Each published channel (`CHANNEL` in `build/build.conf`, default `beta`) has an Ed25519 key pair in
`/etc/convergent/keys/` on the build host. `build/image` puts `<channel>.pub` and the download URL
into the image, and signs the manifest (`manifest.sig`) when `<channel>.key` is there.
`CHANNEL=stable` selects stable for signing and publishing. The stable key stays on offline media:
`CHANNEL=stable build/sign <release-dir> /media/offline/stable.key` asks for its passphrase. Make the
keys once:

```sh
install -d -m 700 /etc/convergent/keys && cd /etc/convergent/keys
openssl genpkey -algorithm ed25519 -out beta.key
openssl pkey -in beta.key -pubout -out beta.pub
openssl genpkey -algorithm ed25519 -aes-256-cbc -out /media/offline/stable.key   # passphrase
openssl pkey -in /media/offline/stable.key -pubout -out stable.pub
```

A laptop trusts only the key its image was built with. Without that key, its next update comes from
USB with `CONVERGENT_UNSIGNED=1`.

The build-host `provenance` file records `release-key` (SHA-256 of the embedded public key's canonical
PEM, including its final newline) and `update-channel` (from the embedded update URL), or `none` when
absent. Signing and publication require both to match the selected channel, except for the one-way
bridge below. Releases without this file need a rebuild first. It is not published or required by laptops. The
host manifest format is unchanged. Both steps also require exactly one checksum and an accurate size
for the slot image and each UKI.

`build/publish <release-dir>` uploads to the public R2 bucket named in
`/etc/convergent/r2-<channel>.env` (mode 600): `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID` and
`R2_SECRET_ACCESS_KEY` of a token limited to the bucket, `R2_BUCKET`, `R2_PUBLIC_URL`, and `R2_ENDPOINT`
for an EU bucket. Only the five host files, `guests.manifest` and the guest files it lists go up, with
a valid signature only, to `<channel>/<release>/`. The signed `<channel>/latest` then points at it
(`build/sign` writes it). A mirror cannot forge the pointer, but it can hold back newer releases by
replaying an older signed one; `fetch-release` shows how old the signature is. Two releases per
channel stay, and `build/publish` refuses to grow the bucket past about 9 GiB (R2's free tier is 10 GB). The pointer must
name the local guest manifest's SHA-256, or `none` when absent. The currently advertised release is
immutable: a retry compares the published file set and bytes (pointer and signatures included) and succeeds without
writes if identical. Changed files or a newly signed pointer need a new release ID. Each file
downloads in turn to a temporary file, so allow space for the largest payload.

For the temporary 0.1.0 bridge, keep the existing bleeding-edge signing key as the beta key on the
build host. `/etc/convergent/keys/beta.{key,pub}` must match `/etc/convergent/keys/bleeding-edge.{key,pub}`.
Keep both `/etc/convergent/r2-beta.env` and `/etc/convergent/r2-bleeding-edge.env` pointing at the
bucket. Publish the same signed directory and latest pointer twice, without re-signing:

```sh
build/publish <release-dir>
CHANNEL=bleeding-edge build/publish <release-dir>
```

Existing laptops find it under `bleeding-edge/`, then use the embedded `beta/` URL after booting this
release. New installs use `beta/`. Retire the bridge after those laptops have updated. Key and env
migration is a separate build-host operation.

To promote a candidate to stable, check out its tag and build it with `CHANNEL=stable` and the offline
stable key. Run the full test suite, then publish. The update URL and trusted key are part of the
verified root, so an image cannot be re-signed for another channel. The stable build differs from the
candidate only in its channel, its key and the absent debug tool.

Before any upload or pruning, `build/publish` runs `build/advisories --gate <release-dir>`. It fetches
current Gentoo GLSAs, [Alpine secdb](https://secdb.alpinelinux.org/) for each shipped Alpine branch,
and the firewall release's [OpenBSD errata](https://www.openbsd.org/errata.html). Known affected
versions, missing patches, missing inventories and fetch/parse failures block publication. Signing
stays offline. A previous successful check never authorizes a later publish. Only the build host
fetches advisories; Portage matching runs in the builder chroot. The gate needs `python3`, `git`,
`curl` and the builder's Portage.

Host package versions and slots are recorded before trimming, in the build-host-only `packages`
sidecar. `build/sign` signs it as `packages.sig` with the channel key, and the advisory scanner
verifies it before use. Neither file is published or put in the host manifest. Svc and browser
inventories come from their rootfs archives. WAN's `wan.manifest`, and the firewalls' `openbsd.version`
and per-node patch lists, travel in their checksummed, signed guest payloads. Older releases without
these inventories must be rebuilt. Only guests shipped in the release are gated. Kernel and pin
freshness stay in the separate weekly report.

For a reviewed advisory that does not apply, add a line to `build/advisories.exceptions`:
`target package advisory reason`. The reason must be concrete and fill the rest of the line. Targets
are `host`, `wan`, `svc`, `browser`, `fw1`, `fw2`. Package is Gentoo `category/name`, Alpine source
package (origin), or `base` for OpenBSD. IDs are `GLSA-YYYYMM-NN`, the secdb ID (usually a CVE), or,
for example, `OPENBSD-7.9-001_xserver`. Use one entry per target and advisory, including absent
OpenBSD sets such as X. No wildcards, and no exception for unreadable data. The gate output lists
accepted exceptions and reasons. Run `build/test --advisories` for the offline regression fixtures.

## Test in QEMU

Each test boots the release on a throwaway disk in `builder/test/<release>-<mode>`. It passes or fails
by itself. Tests can run side by side as memory allows (8 to 12 GiB each).

```sh
build/test <release>                                  # boots and marks itself good
build/test --recovery <release>                       # recovery profile, unlock, continue and bless
build/test --corrupt <release>                        # one flipped block: must refuse to boot
build/test --desktop <release>                        # sway, bar and sys: the session's programs and config
build/test --fallback <good> <newer>                  # broken newer slot: the good one returns
build/test --interrupt <good> <newer>                 # update cut off half-way: still boots
build/test --guests <release> $g                      # plus guests init: firewalls, wan, svc
build/test --guests-update <release> $g <broken-dir>  # plus guest updates and a rollback
```

`<broken-dir>` is a new path: the test builds a deliberately broken svc image there and checks that the
update is rolled back.

`--guests` and `--guests-update` also try the Internet path. wan gets an emulated uplink (QEMU user
networking, as a second NIC). fw1 must then reach 9.9.9.9:853, and the host must resolve a name, or the
test fails. Both modes also smoke-test the def browser container without Wayland, check tmp versus
portal policies and devices, and exercise portal expiry and closure. They probe PF's
web/admin/svc/host policy (`CV-PF ok/FAIL`, source, destination and port), including portal
reachability before, during and after portal mode. Temporary listeners give denied ports positive
controls. Both modes build the pre-1631544 browser layout from frozen YAML fixtures, then run
`guests update browser` normally and after SIGKILL at the rename journal. Both state-volume markers,
new profiles, and removal of old names/journals must pass. They check signed online updates, when configured, after a successful uplink. They also run the booted selftest checks as root. Only release, verity,
nested and audit failures gate the test.

## Checks

Run `build/lint` before a push. On tracked files it checks shell syntax, shellcheck (when installed),
leaked secrets or session and scratch paths, and CRLF line endings. It also checks that each simple
backticked repository path in the docs exists.

Once a week, as root, run `build/advisories <release-dir> $g` (pass both: the default guest directory
is not `$g`). It reads upstream fixes and names what to rebuild (`host`, `kernel`, `fw`, `svc`,
`browser`, `wan`, or `guests` for the pins). The kernel version comes from the release. Gentoo packages
come from its signed build-host inventory. Exit 1: something to rebuild (UNKNOWN lines may appear
too). Exit 2: only UNKNOWN; a source was not read.

## Repository

| Path | What |
|---|---|
| `build/` | builder chroot, packages, image, sign, publish, QEMU tests, lint, advisories, disk image |
| `portage/` | make.conf, USE flags, package sets, image profile, two local ebuilds |
| `rootfs/` | host files: `/etc`, `/usr/lib/convergent` (`sys` areas), health checks |
| `initramfs/` | the dracut module: unlock, `/var` per release, watchdog |
| `install/` | installer, shipped as `convergent-install` |
| `tools/` | `slot`, `fetch-release`, `apps`, `guests`, `browser`, `sys`, `bar`, `check`, `backup`, `devices`, `portal`, `dns-push`, `power`, `facts`, `account` |
| `guests/` | `fw` (OpenBSD), `wan`, `svc` and `browser` (Alpine) |
