# Convergent

Convergent is a security-first laptop OS for a single owner. A verified, read-only Gentoo host runs
the network, monitoring and browsers in separate Incus guests.

## What you get

- **A verified A/B host.** Gentoo and OpenRC on a dm-verity EROFS root, one UKI per slot, and
  state on LUKS2 and Btrfs.
- **Compartments.** Incus separates `wan` (an Alpine VM that owns the radio), the OpenBSD
  `fw1`/`fw2` CARP pair, `svc`, the `def`, `tmp` and `int` browsers, Remmina and work VMs.
- **Monitoring.** `svc` runs VictoriaMetrics, VictoriaLogs, alert rules and Grafana.
- **Recoverability.** A release that does not become good falls back to the previous one, which
  keeps its own `/var`. Recovery and Rescue boot entries cover the rest; data is copied by hand.

PF on the firewalls decides what passes between guests. The Incus UI opens through `int`.

Updates come as signed releases from a channel, online or from USB; the laptop checks them with
the key its release embeds ([USAGE, Host updates](USAGE.md#host-updates)). This repository is the
product: its build inputs and files define every image.

## Hardware

| Part | Requirement |
|---|---|
| Firmware | UEFI boot |
| Graphics | Intel, render node at `/dev/dri/renderD128` |
| IOMMU | Intel VT-d enabled |
| Wi-Fi | Alone in its IOMMU group; no ACS override |
| NVIDIA GPU, if present | Held on vfio-pci with runtime power management |

Not built: Secure Boot signing ([BUILD, Status](BUILD.md#status)).

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

> [!CAUTION]
> Writing an image or installing erases the target disk.
