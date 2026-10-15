# Convergent

A security-first laptop system for one owner, built to be used every day.

- **Verified to the last block:** Secure Boot with the owner's keys, a signed kernel image,
  and a read-only operating system checked by dm-verity on every read.
- **Built elsewhere:** a build host compiles and signs; the laptop only receives images.
- **Compartments:** the Wi-Fi radio in its own VM, a pair of OpenBSD firewalls routing every
  segment, services and guests each on their own network.
- **Updates you can trust:** A/B system slots, automatic fallback after a failed boot.
- **Gentoo with OpenRC** on the host, hardened profile, no systemd init.

Status: design. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DECISIONS.md](DECISIONS.md).
