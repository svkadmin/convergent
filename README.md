# Convergent

A security-first operating system for one owner's laptop: a verified, read-only Gentoo host
with A/B updates, an encrypted state disk, and everything else (firewalls, uplink, monitoring,
browsers) in isolated Incus guests.

## No stable release yet

This branch will carry stable releases once one has been promoted. There is none yet.

Convergent is in its first release cycle. Work happens on `dev`; builds that pass every test
are published on `beta`. A beta that is meant for stable is tagged as a release candidate
(`v0.1.0-rc1`, `v0.1.0-rc2`, ...). When a candidate has proven itself in daily use, the same
images are promoted here unchanged and the release is tagged `v0.1.0`.

Until then:

- Source, install and update instructions: the [`beta`](https://codeberg.org/svkadmin/convergent/src/branch/beta) branch.
- Release candidates: the [tags](https://codeberg.org/svkadmin/convergent/tags) named `vX.Y.Z-rcN`.

Release candidates are testing builds. They can change in incompatible ways between
candidates and are not meant for anyone else's daily use.
