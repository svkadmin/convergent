# Building Convergent

Build and release operations. Design and numbered build steps:
[ARCHITECTURE 6](ARCHITECTURE.md#6-build-and-keys). Owner installation and updates:
[README](README.md#install).

## How it works

```text
build host                         your PC                      laptop
──────────                         ───────                      ──────
compile packages (once, cached)
build a release ─► test in QEMU ─► disk image ─► write to disk ─► boot, unlock, log in
sign, publish ─────────────────────────────────► R2 ──────────► sys update install
                                   or release  ─► USB disk ─────► sys update usb
```

## Status

| | |
|---|---|
| Proven in QEMU | boot, unlock, health check, fallback; corrupted image refused; interrupted update harmless; firewalls, wan and svc provisioned; guest updates with failover and rollback; booting the disk image over USB |
| Proven on the laptop | boot, unlock, autogrow, automatic setup, graphics, sway and the bar, Wi-Fi, online update (download, signature, slot switch), the def and int browsers |
| Built, laptop test to finish | tmp browsers and portal mode, audio, Bluetooth, power, online guest delivery |
| Implemented, QEMU and laptop tests pending | standalone rescue entry, independent of both slots; `build/test --rescue <release>` |
| Not built | Secure Boot signing, including rescue (Secure Boot stays off) |

Branches and channels: `dev` → `beta` → `stable`. `dev` is unpublished. `beta` is built, tested and
published. Stable promotion: [Sign and publish](#sign-and-publish). Release candidates are git tags
on beta, such as `v0.1.0-rc1`, not a channel. The final tag is `v0.1.0`.

## Build a release

As root, on the build host, from the repository root. Needs Gentoo with KVM, loop devices and
network access. Guest builds also need `qemu-img`, OVMF, `signify`, `python3`, `jq` and `curl`.

Settings live in `/etc/convergent/config.yaml` on the build host, or in the file named by
`CONVERGENT_CONFIG`. Keys and defaults: `config.example.yaml`. Validation rules: `tools/config-get`.
The image keys (host name, time zone, keyboard layouts, display scale, Wi-Fi country, time servers,
blocklist, CPU cap and idle lock) are built into the release. `build/stick` and
`convergent-install --config` read the owner login, image size and `install` disk/state/swap
options. A typo or unknown key stops the build. Install settings, fixed disk layout and secret-input
rules: [USAGE, Install](USAGE.md#install). Passphrase keyboard:
[README, First boot](README.md#first-boot).

```sh
build/buildenv          # builder chroot from the pinned, signed stage3 and Portage snapshot
build/packages          # compile or fetch the image's packages (--pretend to preview)
build/image             # the release, named by UTC time: YYYYMMDDHHMM
```

Bump `VERSION` in `build/build.conf` each release, using semantic versions (`0.1.0` for this
release; `major.minor.patch`, optionally `-rcN`). `/usr/lib/convergent/version`, per-slot
`CONVERGENT_VERSION`, boot titles, signed manifest and owner status carry it. The timestamp release
ID still names artifacts, orders the boot menu (`IMAGE_VERSION`) and drives A/B updates and rollback
checks.

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

`build/stick` asks for the owner password, then the LUKS passphrase (12 characters or more each).
The owner login comes from `CONVERGENT_INSTALL_OWNER`, else `owner_login` in the config, else it is
asked. It runs the real installer on a loop device and prints the image's SHA-256. A disk image
holds the owner's account: never publish one.

### Firewall images

Install applies signify-verified syspatches, then runs `pkg_add -u` from the OpenBSD mirror. Image
build patches the real kernel on a temporary DHCP boot and verifies it on an offline smoke boot. Its
QEMU runs under the same sandbox as the tests: [Test in QEMU](#test-in-qemu). Each node's installed
patches are recorded in `<node>.syspatch`. Lists and OpenBSD version go into the signed guest
payload. Before publishing, the advisory gate checks every published erratum, including gaps in the
patch list. Non-applicable errata need an explicit reason in `build/advisories.exceptions`.

### Sign and publish

Each published channel (`CHANNEL` in `build/build.conf`, default `beta`) has an Ed25519 key pair
(OpenSSL) in `/etc/convergent/keys/` on the build host. `build/image` puts `<channel>.pub` and the
download URL into the image, and signs the manifest (`manifest.sig`) when `<channel>.key` is there.
`CHANNEL=stable` selects stable for signing and publishing. The stable key stays on offline media:
`CHANNEL=stable build/sign <release-dir> /media/offline/stable.key` asks for its passphrase. Make
the keys once:

```sh
install -d -m 700 /etc/convergent/keys && cd /etc/convergent/keys
openssl genpkey -algorithm ed25519 -out beta.key
openssl pkey -in beta.key -pubout -out beta.pub
openssl genpkey -algorithm ed25519 -aes-256-cbc -out /media/offline/stable.key   # passphrase
openssl pkey -in /media/offline/stable.key -pubout -out stable.pub
```

Owner update trust and unsigned USB updates: [README, Update](README.md#update).

The build-host `provenance` file records `release-key` (SHA-256 of the embedded public key's
canonical PEM, including its final newline) and `update-channel` (from the embedded update URL), or
`none` when absent. Signing and publication require both to match the selected channel, except for
the one-way bridge below. Releases without this file need a rebuild first. It is not published or
required by laptops. The host manifest format is unchanged. Both steps also require exactly one
checksum and an accurate size for the slot image and each UKI.

`build/publish <release-dir>` uploads to the public Cloudflare R2 bucket named in
`/etc/convergent/r2-<channel>.env` (mode 600): `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID` and
`R2_SECRET_ACCESS_KEY` of a token limited to the bucket, `R2_BUCKET`, `R2_PUBLIC_URL`, and
`R2_ENDPOINT` for an EU bucket. Only the five host files, `guests.manifest` and the guest files it
lists go up, with a valid signature only, to `<channel>/<release>/`. The signed `<channel>/latest`
then points at it (`build/sign` writes it). Manifest sizes bound each download. A mirror cannot
forge the pointer, but it can hold back newer releases by replaying an older signed one;
`fetch-release` reports stale signatures ([README, Update](README.md#update)). Two releases per
channel stay, and `build/publish` refuses to grow the bucket past about 9 GiB (R2's free tier is 10
GB). The pointer must name the local guest manifest's SHA-256, or `none` when absent. The currently
advertised release is immutable: a retry compares the published file set and bytes (pointer and
signatures included) and succeeds without writes if identical. Changed files or a newly signed
pointer need a new release ID. Each file downloads in turn to a temporary file, so allow space for
the largest payload.

For the temporary 0.1.0 bridge, keep the existing bleeding-edge signing key as the beta key on the
build host. `/etc/convergent/keys/beta.{key,pub}` must match
`/etc/convergent/keys/bleeding-edge.{key,pub}`. Keep both `/etc/convergent/r2-beta.env` and
`/etc/convergent/r2-bleeding-edge.env` pointing at the bucket. Publish the same signed directory and
latest pointer twice, without re-signing:

```sh
build/publish <release-dir>
CHANNEL=bleeding-edge build/publish <release-dir>
```

Existing laptops find it under `bleeding-edge/`, then use the embedded `beta/` URL after booting
this release. New installs use `beta/`. Retire the bridge after those laptops have updated. Key and
env migration is a separate build-host operation.

To promote a candidate to stable, check out its tag's exact commit and rebuild with `CHANNEL=stable`
and the offline stable key. Run the full test suite, then publish. The update URL and trusted key
are part of the verified root, so an image cannot be re-signed for another channel. The stable build
differs from the candidate only in its channel, its key and the absent debug tool.

Before any upload or pruning, `build/publish` runs `build/advisories --gate <release-dir>`. It
fetches current Gentoo GLSAs, [Alpine secdb](https://secdb.alpinelinux.org/) for each shipped Alpine
branch, and the firewall release's [OpenBSD errata](https://www.openbsd.org/errata.html). Known
affected versions, missing patches, missing inventories and fetch/parse failures block publication.
Signing stays offline. A previous successful check never authorizes a later publish. Only the build
host fetches advisories; Portage matching runs in the builder chroot. The gate needs `python3`,
`git`, `curl` and the builder's Portage.

Host package versions and slots are recorded before trimming, in the build-host-only `packages`
sidecar. `build/sign` signs it as `packages.sig` with the channel key, and the advisory scanner
verifies it before use. Neither file is published or put in the host manifest. Svc and browser
inventories come from their rootfs archives. WAN's `wan.manifest`, and the firewalls'
`openbsd.version` and per-node patch lists, travel in their checksummed, signed guest payloads.
Older releases without these inventories must be rebuilt. Only guests shipped in the release are
gated. Kernel and pin freshness stay in the separate weekly report.

For a reviewed advisory that does not apply, add a line to `build/advisories.exceptions`:
`target package advisory reason`. The reason must be concrete and fill the rest of the line. Targets
are `host`, `wan`, `svc`, `browser`, `fw1`, `fw2`. Package is Gentoo `category/name`, Alpine source
package (origin), or `base` for OpenBSD. IDs are `GLSA-YYYYMM-NN`, the secdb ID (usually a CVE), or,
for example, `OPENBSD-7.9-001_xserver`. Use one entry per target and advisory, including absent
OpenBSD sets such as X. No wildcards, and no exception for unreadable data. The gate output lists
accepted exceptions and reasons. Run `build/test --advisories` for the offline regression fixtures.

## Test in QEMU

`build/test --desktop` checks enforce labels, clock queries, metrics scrape, BlueZ D-Bus and browser
sockets under headless Sway. Bluetooth pairing and audio devices still need laptop testing.

Each test boots the release on a throwaway disk in `builder/test/<release>-<mode>`. It passes or
fails by itself. Tests can run side by side as memory allows (8 to 12 GiB each).

QEMU runs as the unprivileged `convergent-qemu` user, in the group that owns `/dev/kvm`, under
`-sandbox on` with seccomp. The user is created on first use. The test fails if QEMU retains root
IDs, effective capabilities, or lacks seccomp filtering.

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

`<broken-dir>` is a new path: the test builds a deliberately broken svc image there and checks that
the update is rolled back.

`--guests` and `--guests-update` also try the Internet path. wan gets an emulated uplink (QEMU user
networking, as a second NIC). fw1 must then reach 9.9.9.9:853, and the host must resolve a name, or
the test fails. Both modes also smoke-test the def browser container without Wayland, check tmp
versus portal policies and devices, and exercise portal expiry and closure. They probe PF's
web/admin/svc/host policy (`CV-PF ok/FAIL`, source, destination and port), including portal
reachability before, during and after portal mode. Temporary listeners give denied ports positive
controls. Both modes build the pre-1631544 browser layout from frozen YAML fixtures, then run
`guests update browser` normally and after SIGKILL at the rename journal. Both state-volume markers,
new profiles, and removal of old names/journals must pass. They check signed online updates, when
configured, after a successful uplink. They also run the booted selftest checks as root. Only
release, verity, nested and audit failures gate the test.

`build/test --rescue <release>` boots the shipped rescue UKI in the existing QEMU/OVMF console
driver with both slots empty. It unlocks, checks the menu, selects power off, and checks that UKI
names, content and blessing state are unchanged. The `build/test --rescue` mode leaves USB writes,
password reset, next-slot selection and log export for separate testing.

## Checks

`build/image` checks AppArmor profile syntax. `build/lint` checks dashboard JSON drift.
`build/test --guests-update` checks every metric panel query against real svc scrapes, allowing
explicitly optional hardware and quiet alerts, every LogsQL target, and that forged hostnames cannot
move log records to another host. `build/test-debug` checks diagnostic output authentication
offline.

Run `build/lint` before a push. On tracked files it checks shell syntax, shellcheck (when
installed), leaked secrets or session and scratch paths, and CRLF line endings. It also checks that
each simple backticked repository path in the docs exists.

Once a week, as root, run `build/advisories <release-dir> $g` (pass both: the default guest
directory is not `$g`). It reads upstream fixes and names what to rebuild (`host`, `kernel`, `fw`,
`svc`, `browser`, `wan`, or `guests` for the pins). The kernel version comes from the release.
Gentoo packages come from its signed build-host inventory. Exit 1: something to rebuild (UNKNOWN
lines may appear too). Exit 2: only UNKNOWN; a source was not read.

### Work topology qualification

Use the same `CONVERGENT_CONFIG` for host, fw, wan and svc builds.
`build/networks` emits the registry, topology hash, work NIC profiles, DHCP/DNS
and packet policy into staging trees; fw and wan publish the topology hash in
SHA256SUMS. The host build requires VLAN and bridge nftables kernel support.

Run `sh build/test --networks` and `sh build/test-topology` for offline
schema/rendering, CARP corruption and pair journal replay fixtures. On the rig,
run `build/test --guests`, `--guests-maint` and `--guests-update`: the PF
matrix checks all work VLANs, synchronized DHCP pools/options, both CARP masters,
family isolation, internet and configured home access; update tests inject
failures after each replacement and check both-root rollback ordering.
Repeat the home-LAN matrix with an empty list and with 10.0.2.0/24 (the rig LAN).
Also qualify a real 0.1.3→0.1.4 pair migration and power loss at each journal
boundary; verify tagged/native/stacked traffic, IP/ARP/CARP spoofing and IPv6
with VLAN offload both enabled and disabled on the laptop.

### Incus UI (W2)

The overlay pins Zabbly's prebuilt `incus-ui-canonical_7.5.1-debian12-202610211642_amd64.deb`;
the LTS index was inaccessible during implementation, so a matching 7.0.1 artifact could not
be confirmed. The exact URL is in the ebuild and Manifest placeholder. On the build host,
authenticate Zabbly's InRelease and Packages SHA256, then generate the Portage Manifest's size,
BLAKE2B and SHA512 with `ebuild <ebuild-path> manifest`. Keep a verified distfile mirror. The
placeholder is a release blocker: do not bypass digest checks. Only `/opt/incus/ui` is installed
into `/usr/share/incus-ui`; no Debian maintainer scripts, Node or Yarn run.

Rebuild host, browser (nss-tools) and wan (fixed management-endpoint diagnostic) images. Run `build/test --guests`,
`--guests-maint` and `--guests-update`. Delimited W2 sections run the 8443 PF matrix and
`build/test-incus-ui`: server verification, absent/wrong/revoked client identities, wrong/cancelled
unlock, NSS permissions, repeated sessions, close/orphan/reboot cleanup and interrupted rotation.
The audit tests require native lifecycle/request delivery (without global daemon debug) and reject
query/command leakage. The builder checks syslog-ng syntax; the rig must verify its wire format
and forwarding/buffering through a svc outage before release.
The PF matrix probes the actual agentless WAN VM through its fixed SSH diagnostic, plus a
separate transit source. Qualify offline assets, Chromium certificate selection, console/WebSockets,
all projects, network/profile/storage management and VM device editing against Incus 7.0.1.
Also verify a pre-existing disallowed 8443 connection is cut by reloading host nftables, Sway
session/terminal death, and revocation during a live console. These require the rig or laptop.

### Remmina image and qualification (0.1.4)

On the native Linux builder run **sudo sh guests/remmina/build**; stage
guests/remmina/out/* as `<guests-dir>/remmina/`. The image uses Alpine 3.24
Remmina 1.4.43-r0 and its bundled protocol plugins. It rebuilds the executable
from the SHA512-pinned upstream tarball with Alpine's pinned DSO patch and
secret-service-only.patch; build dependencies are removed. Cache/mirror those
two pinned source inputs for offline rebuilds. No Chromium is installed.
build/guests, build/publish, fetch-release and build/stick carry/check
the Remmina image, profile and inventory through the signed guest manifest.
The advisory gate includes Remmina's Alpine package database.

Merge W1 before building firewalls: W3 deliberately references, but never
defines, the work_nets and work_infra tables. Run **build/test --guests**,
**--guests-maint**, **--guests-update** with the Remmina artifacts present.
The offline command **sh build/test --remmina-unit** checks cancellation, empty/wrong passwords, locked/unavailable service, plaintext refusal and artifact paths. The new delimited sections exercise work TCP bounds, responding UDP, ICMP,
DNS/system/home/public denial, share mounting, encrypted keyring persistence
and failed/successful image replacement without share rollback.
Run the PF matrix with each firewall as master and again after live handoff.

On the laptop, qualify Remote under Sway: type into RDP/VNC/SSH, play audio,
and confirm microphone/monitor capture fails. Copy distinct host/remote
sentinels in both directions: only Remmina-to-remote transfer may work; host
clipboard must remain unchanged (also test primary selection). Cancel the
keyring prompt, submit empty/wrong passwords, then unlock/save/reopen.
Kill Secret Service after unlock and save a new connection: no local password
may appear in its profile; restart must either retrieve the encrypted secret
or ask again. Check launcher TERM/KILL cleanup, UI share attach/detach and RDP
redirection against representative Linux/Windows guests. These GUI/protocol
checks require the rig/laptop and are release qualification gates.
