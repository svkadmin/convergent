# Convergent

A security-first laptop system for one owner, built to be used every day.

- **Verified to the last block:** Secure Boot with the owner's keys, a signed kernel image,
  and a read-only operating system checked by dm-verity on every read.
- **Built elsewhere:** a build host compiles and signs; the laptop only receives images.
- **Compartments:** the Wi-Fi radio in its own VM, a pair of OpenBSD firewalls routing every
  segment, services and guests each on their own network.
- **Updates you can trust:** A/B system slots, automatic fallback after a failed boot.
- **Gentoo with OpenRC** on the host, hardened profile, no systemd init.

Design: [ARCHITECTURE.md](ARCHITECTURE.md). Decisions and their reasons: [DECISIONS.md](DECISIONS.md).

## Status

Proven in QEMU on the build host:

- The boot chain: UEFI, systemd-boot with boot counting, the UKI, the kernel's own dm-verity
  root, one passphrase for the LUKS2 state volume, the hardware watchdog, OpenRC, Incus, and the
  release marking itself good after its health checks.
- A corrupted root image refuses to boot; a release that fails three tries falls back to the
  good slot; an interrupted update leaves the good slot booting.
- All guest images build: the OpenBSD firewall pair (unattended install), wan, svc and the
  browser container (Alpine).
- `guests init` provisions the firewalls, wan and svc inside the test host: seeded, host keys
  pinned, CARP up with fw1 master and fw2 backup.
- `guests update` replaces the firewalls one after the other with failover, and a broken
  svc image is rolled back by itself.

Written and built, not yet used on a desktop: `browser`, `check`, `backup`, `bar`, `menu`.
Not yet: release signing, errata in the firewall images, anything on the laptop itself.

## Build and test

On the build host, as root (Gentoo with KVM). A release is named by its UTC time, digits only.

```sh
build/buildenv                     # the builder chroot, pinned stage3 and Portage snapshot
build/packages                     # the image's packages into the staging root
build/image 202610160000           # EROFS image, dm-verity, initramfs, one UKI per slot
build/test 202610160000            # boot it in QEMU; passes when the release blesses itself
```

Boot chain proofs: `build/test --corrupt <rel>`, `--fallback <good> <bad>`,
`--interrupt <good> <new>`. Platform: `build/test --guests <rel> <guests-dir>` and
`--guests-update <rel> <guests-dir> <broken-svc-dir>`.

Guest images, each from its own directory: `guests/fw/build <out>`,
`WAN_COUNTRY=SK guests/wan/build <out>`, `guests/svc/build`, `guests/browser/build`.

## Layout

```
build/        builder, packages, image assembly, the QEMU test
portage/      make.conf, USE flags, package sets, the image profile, one local ebuild
rootfs/       the host's own /etc and /usr/lib/convergent files
initramfs/    the dracut module: state volume, /var per release, watchdog
tools/        slot, guests, portal, dns-push, devices, power, facts
guests/       fw (OpenBSD), wan, svc and browser (Alpine)
install/      the installer
```
