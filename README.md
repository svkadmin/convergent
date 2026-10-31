# Convergent

Single-owner, security-first laptop OS. Gentoo/OpenRC runs a dm-verity EROFS root, A/B UKIs and
LUKS2+Btrfs state. Incus isolates an Alpine WAN VM, OpenBSD fw1/fw2 CARP pair, svc
(VictoriaMetrics/Logs and Grafana), def/tmp/int browsers, Remmina and work guests. Incus UI is
accessed through int.

Target: UEFI, Intel `/dev/dri/renderD128` graphics, VT-d and Wi-Fi alone in its IOMMU group; no ACS
override. NVIDIA stays on vfio-pci with runtime power management. Secure Boot signing is not
implemented.

> Writing an image or installing **erases the target disk**.

## Docs

| Document | Purpose |
|---|---|
| [USAGE](USAGE.md) | Installation, daily controls and updates |
| [RECOVERY](RECOVERY.md) | Ordered repair and restore procedures |
| [ARCHITECTURE](ARCHITECTURE.md) | Components, security boundaries and reasons |
| [BUILD](BUILD.md) | Build, test, sign and publish |

## Start

- Install: [write a disk image](USAGE.md#disk-image) or [run the installer](USAGE.md#internal-disk)
- [First boot](USAGE.md#first-boot) and [updates](USAGE.md#releases-and-guests)
- [Build a release](BUILD.md#build-a-release); [implementation and test status](BUILD.md#status)
- [Repository layout](ARCHITECTURE.md#13-repository-layout)
