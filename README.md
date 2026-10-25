# Convergent

Single-owner laptop system: security first, still usable daily. Gentoo host (hardened, OpenRC) on a
read-only root that the kernel verifies on every read. Updates go to a second slot; a release that
does not come up healthy falls back to the previous one. The Wi-Fi card runs in its own VM. An
OpenBSD firewall pair routes everything. Services and browsers run in containers.

> Writing an image or running the installer **erases the whole target disk**.

Target: UEFI laptop with Intel graphics (`/dev/dri/renderD128`), VT-d and a Wi-Fi function alone in
its IOMMU group; no ACS override. The NVIDIA card stays bound to `vfio-pci` and powered down.

## Docs

| File | Read it when |
|---|---|
| [USAGE.md](USAGE.md) | Daily use, install options and guest updates |
| [RECOVERY.md](RECOVERY.md) | Step-by-step repair |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design and reasons |
| [BUILD.md](BUILD.md) | Build, sign, publish and test |

## Status

See [build and hardware test status](BUILD.md#status).

## Install

### A disk image (USB disk or stick)

The disk image is 30 GiB by default (32,212,254,720 bytes), so a stick sold as "32 GB" may be too
small. Write it on any Linux:

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
an unsigned one). It lists the disks and refuses the boot disk, mounted disks, and anything under 49
GiB plus 4 MiB. Retype the disk (or `ERASE` and its serial), then the owner name, then the password
and LUKS passphrase, twice each. It writes and verifies slot A, adds a boot entry named from the
release's `NAME`, and powers off. Remove the USB disk before booting. Guest images are not copied.
Put the guest directory at `/var/lib/convergent/release-guests/guests` and run `sys guests setup`.

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
   `SETUP` is gone. Keys: [USAGE, Keys](USAGE.md#keys); bar: [USAGE, The bar](USAGE.md#the-bar).
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

Daily controls and alert interpretation: [USAGE, Keys](USAGE.md#keys) and
[Health and alerts](USAGE.md#health-and-alerts).

Something off: [RECOVERY.md](RECOVERY.md); logs: `sys logs`; every command: `sys help`.

Recovery menu: [RECOVERY, Recovery boot menu](RECOVERY.md#recovery-boot-menu).

## Update

**Online** (Wi-Fi up): `sys update check` prints `up to date: release …` or
`release N is available`. `sys update install` downloads the newest host release for the image's
channel (about 1 GB) and only the changed guests, checks the signature and hashes, writes the other
slot and offers the reboot. By hand: `sudo fetch-release` (`check` only reports). Guest application:
[USAGE, Releases and guests](USAGE.md#releases-and-guests); failures:
[RECOVERY 12](RECOVERY.md#12-an-online-update-fails).

**From USB:** copy the release directory (`manifest`, `manifest.sig`, `slot.img`, both `.efi` files,
`guests/`, `guests.manifest` and `guests.manifest.sig`) to a FAT32 or exFAT stick. Allow it
(`sudo devices list`, `sudo devices allow <number>`). `sys update usb` mounts it and writes the
release. From a release before v10, run `sys update usb` again after booting v10, with the same
stick, to install its guests. Updating from a stick without guests leaves the old browser image and
web/admin objects intact. def/int and `tmp --portal` need `sys update install` or a USB release
carrying guests. By hand on v10:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo fetch-release usb /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

`slot write` checks the manifest's signature against the key built into the image. An unsigned
release needs `sudo env CONVERGENT_UNSIGNED=1 slot write ...`, which the menu offers only on an
image without a key. Without that key, the next update comes from USB with `CONVERGENT_UNSIGNED=1`.
It runs only on the release marked good and refuses a release not newer than the booted one and the
highest ever marked good. `sudo slot status` shows both slots. Checks and boot tries:
[ARCHITECTURE 7.2](ARCHITECTURE.md#72-update); fallback and watchdog:
[RECOVERY 2](RECOVERY.md#2-a-new-release-does-not-boot-or-does-not-become-good).

Manual guest updates: [USAGE, Releases and guests](USAGE.md#releases-and-guests).

To go back by hand, pick the other slot in the boot menu: see [RECOVERY.md](RECOVERY.md).

## Build a release

See [BUILD.md](BUILD.md#build-a-release).

## Repository

See [ARCHITECTURE 13](ARCHITECTURE.md#13-repository-layout).
