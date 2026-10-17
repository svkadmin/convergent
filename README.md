# Convergent

Convergent is a single-owner laptop system built for security first and daily use second. The
host is Gentoo (hardened profile, OpenRC) with a read-only root verified by dm-verity on every
read, A/B update slots and automatic fallback to the previous slot. An OpenBSD firewall pair
routes every network segment, the Wi-Fi card lives in its own VM, and services and browsers run
in containers. Design: [ARCHITECTURE.md](ARCHITECTURE.md). Daily use: [USAGE.md](USAGE.md).

## Status

Proven in QEMU on the build host:

- The boot chain: UEFI, systemd-boot with boot counting, the UKI, the kernel's own dm-verity
  root, one passphrase for the LUKS2 state volume, the hardware watchdog, OpenRC, Incus, and the
  release marking itself good after its health checks.
- A corrupted root image refuses to boot; a release that fails three tries falls back to the
  good slot; an interrupted update leaves the good slot booting.
- All guest images build: the OpenBSD 7.9 firewall pair (unattended install, errata applied at
  build), wan, svc and the browser container (Alpine, Chromium).
- `guests init` provisions the firewalls, wan and svc inside the test host: seeded, host keys
  pinned, CARP up with fw1 master and fw2 backup.
- `guests update` replaces the firewalls one after the other with failover, and a broken
  svc image is rolled back by itself.

Written and built, not yet used on a desktop: `browser`, `check`, `backup`, `bar`, `menu`, and
`build/stick` with `install/install`.

Not done: release signing (UKIs and manifests are unsigned; `slot write` and `install/install`
refuse to run without `CONVERGENT_UNSIGNED=1`, and Secure Boot stays off); anything on the
laptop itself; fetching a release over the network; a recovery UKI; tools for the LUKS and
Secure Boot key backups.

## Requirements

- **Build host:** Gentoo with KVM, loop devices, network access, root. Disk: a sparse test disk of
  16 GiB (48 GiB for `--guests` and `--guests-update`), about 3 GiB for guest images and the Alpine
  cache, and the stick image (at least 50 GiB). The builder, package cache and releases live in
  `/var/lib/convergent/builder`; their size is not measured. The guest builds also need `qemu-img`,
  OVMF, `signify`, `python3`, `jq`, `curl` and a free loopback port 80 (firewall build).
- **Laptop:** UEFI x86-64, Intel CPU and iGPU (`/dev/dri/renderD128` must be Intel), VT-d, an Intel
  Wi-Fi card alone in its IOMMU group (without one, wan has no radio), a TCO watchdog, a whole disk
  of at least 49 GiB. Secure Boot off until signing exists.
- **USB stick:** at least 50 GiB (two 8 GiB slots, 1 GiB ESP, 32 GiB state minimum). Use 64 GB.

## Build a release

On the build host, as root, from the repository root. A release is named by its UTC time, digits
only (`YYYYMMDDHHMM`, the default of `build/image`); a later release has a larger number.

```sh
build/buildenv                     # builder chroot from the pinned, signed stage3 and Portage snapshot
build/packages                     # the image's packages into the staging root (--pretend to preview)
build/image 202610170000           # EROFS image, dm-verity, initramfs, one UKI per slot, manifest
```

The release is in `/var/lib/convergent/builder/releases/<release>`: `slot.img`,
`convergent-<release>-a.efi`, `convergent-<release>-b.efi`, `manifest`. The guest images go into
one directory (`g`, any path) in the layout the installer and `guests init` read:

```sh
g=/var/lib/convergent/out/guests
mkdir -p $g/fw $g/wan $g/svc $g/browser/incus
guests/fw/build $g/fw                              # OpenBSD 7.9 fw1 and fw2; needs KVM and OVMF
WAN_COUNTRY=SK guests/wan/build $g/wan             # two-letter regulatory country, required
guests/svc/build && cp guests/svc/out/* guests/svc/incus.yaml $g/svc/
guests/browser/build && cp guests/browser/out/* $g/browser/ && cp guests/browser/incus/*.yaml $g/browser/incus/
```

Optional variables: `CACHE_DIR` (Alpine cache, default `/var/cache/convergent/alpine`),
`IMAGE_SIZE` (wan disk, `1G`), `OVMF_CODE` and `OVMF_VARS` (fw build).

## Test in QEMU

`build/test` boots a release on a throwaway disk inside the builder. Run one at a time.

```sh
build/test 202610170000                                   # boots; passes when the release blesses itself
build/test --corrupt 202610170000                         # one root block flipped; passes if verity refuses it
build/test --fallback <good> <newer>                      # slot B corrupt; three failed tries, then A returns
build/test --interrupt <good> <newer>                     # B written half-way; A still boots and blesses
build/test --guests <release> $g                          # then runs guests init on the test host
build/test --guests-update <release> $g <broken-svc-dir>  # init, firewall update, a broken svc rolled back
```

`<broken-svc-dir>` must not exist; the test creates it.

## Install

### a) A stick image

```sh
build/stick <release> <guests-dir> <out.img> [size]
build/stick 202610170000 $g /var/tmp/convergent.img 56G
```

The size defaults to `56G`, which fits a 64 GB stick; the installer refuses less than about
50 GiB. It asks for `Owner login name:` (lowercase; or set `CONVERGENT_INSTALL_OWNER`), then
`Owner password:` and `LUKS passphrase:`, 12 characters or more each, typed once, not shown. It
runs the real installer on the image through a loop device, then prints the image path, its
SHA-256 and the write command:

```sh
dd if='/var/tmp/convergent.img' of=/dev/sdX bs=4M conv=fsync status=progress
```

Check `/dev/sdX` with `lsblk` first: `dd` overwrites the whole device. The image holds a 1 GiB
ESP, slot A with the release (three boot tries), an empty slot B, the encrypted state volume with
the owner's account, and the guest images in `/var/lib/convergent/release-guests/guests`. Boot the
laptop from the stick (UEFI, Secure Boot off); it then runs from the stick.

### b) The laptop's own disk

As root, from a booted Convergent stick, with a release directory (`manifest`, `slot.img`, both
`.efi` files):

```sh
CONVERGENT_UNSIGNED=1 convergent-install /path/to/release
```

It is `install/install` in this repository, shipped as `convergent-install`. It has not run on
the laptop yet. It asks, in order: the target
disk path, after listing the disks (it refuses the boot stick, mounted disks and anything under
49 GiB); `Type <disk> again, or ERASE followed by a space and serial <serial>:`; the owner login
name; the owner password and the LUKS passphrase, each entered twice.

It creates a GPT with a 1 GiB ESP, two 8 GiB slots and the rest as LUKS2 (Argon2id) with Btrfs;
writes slot A and reads it back against the manifest; creates the owner (yescrypt, root locked);
writes a USBGuard policy from the attached devices, leaving the stick out; installs systemd-boot
and the UKI with three tries; registers the boot entry `Convergent`; and powers off. Remove the
stick before booting. The guests are not installed.

### First boot

Before it: in the firmware setup (Dell: F2) turn Secure Boot off and leave VT-d on; plug the stick
into a port of the laptop itself, not a hub or dock; choose it in the one-time boot menu (Dell: F12).

The passphrase prompt and the console use the US keyboard layout, whatever the keys show (on a
Slovak keyboard `@` is Shift+2, and `y` and `z` are swapped).

1. `Convergent passphrase [1/3]:` appears on the console: three tries, then the machine powers off.
2. Log in on the console as the owner. Within a few minutes the console prints
   `convergent: release <release> is good`.
3. Create the guests (a stick image carries their images). This takes several minutes per guest; if
   it stops, run the same command again:
   ```sh
   sudo guests init /var/lib/convergent/release-guests
   ```
4. With only trusted devices attached (the stick included), regenerate the USBGuard policy. Built-in
   devices (camera, Bluetooth, fingerprint reader) are always attached, so they are allowed too:
   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```
5. Start the session with `sway`. Super+m opens the menu: **Wi-Fi: scan**, then **Wi-Fi: connect**.
   Wi-Fi exists only after step 3; each Wi-Fi action asks for the sudo password.

Until release signing exists, `check` reports Secure Boot off, so the bar always counts that alert.

## Update and roll back

Copy the new release directory to the laptop (for example on a USB disk; fetching over the
network is not built), then:

```sh
sudo env CONVERGENT_UNSIGNED=1 slot write /path/to/release
sudo reboot
```

`slot write` checks the manifest and hashes; refuses a release not newer than both the booted
one and the highest ever marked good; refuses unless the booted slot is marked good; writes the
inactive slot, reads it back, and installs its UKI with three tries. After the reboot the
`convergent-bless` service runs the health checks and marks the release good. A release that
fails three tries (a hang is caught by the watchdog after ten minutes) is skipped, and the
previous slot boots with its own `/var`. `sudo slot status` shows both slots.

Guests are updated separately, only on a slot already marked good, from a directory with the new
images. Each replacement exports the guest first; one that fails its checks is restored.

```sh
sudo guests update fw  $g/fw      # fw2 first, checked and soaked, failover, then fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
sudo check accept-fw $g/fw        # after a firewall update
```

Rollback by hand: choose the other slot's entry in the systemd-boot menu (shown for three seconds
at power-on). That slot's `/var` is from before its update, so changes made since are not in it.
The next update must be numbered above the highest release ever marked good. The design's
warning, and its refusal when guests were updated in between, are not built.

## Recovery

- If the booted slot fails, the other boots by itself or from the boot menu.
- If nothing on the laptop boots, boot the stick: it is a complete system with its own
  passphrase. The laptop's state partition can then be opened by hand with `cryptsetup open`.
- The design requires a second LUKS passphrase and a header backup on offline encrypted media. No
  tool makes them yet; by hand:
  ```sh
  cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
  cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
  ```
  After a keyslot change, delete `/var/lib/convergent/luks-header.sha256` and run `sudo facts boot`
  so the checker accepts the new header. There is no Secure Boot key to back up yet.
- A recovery UKI and RECOVERY.md are not written.

## Layout

```
build/        builder, packages, image assembly, the QEMU test, stick
portage/      make.conf, USE flags, package sets, the image profile, two local ebuilds
rootfs/       the host's /etc and /usr/lib/convergent files, including the menu actions
initramfs/    the dracut module: state volume, /var per release, watchdog
tools/        slot, guests, browser, portal, dns-push, devices, power, facts, check, backup, bar, menu
guests/       fw (OpenBSD), wan, svc and browser (Alpine)
install/      the installer
```
