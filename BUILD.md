# Building Convergent

Build, test and publish. Design: [ARCHITECTURE 6](ARCHITECTURE.md#6-build-and-keys);
installation: [USAGE](USAGE.md#install).

## How it works

Build/cache packages → assemble → test in QEMU → create private disk image or sign/publish.
The laptop installs the image/USB release or downloads from its channel.

## Status

| State | Coverage |
|---|---|
| Proven in QEMU | Boot/unlock/bless/fallback, corrupt image refusal, interrupted update, infrastructure setup, guest failover/rollback, USB image boot |
| Proven on laptop | Boot/unlock/autogrow/setup, Sway/bar, Wi-Fi, online host update, def/int |
| Laptop testing incomplete | tmp/portal, audio, Bluetooth, power, online guests |
| QEMU/laptop tests pending | Standalone rescue; build/test --rescue |
| Not built | Secure Boot signing, including rescue; leave Secure Boot off |

Branches/channels: dev → beta → stable. Dev is unpublished; beta built/tested/published.
Candidates are beta git tags such as v0.1.0-rc1; final v0.1.0. [Promotion](#sign-and-publish).

## Build a release

As root from the repository root on Gentoo with KVM, loop devices and network. Guest builds also
need qemu-img, OVMF, signify, python3, jq and curl.

Config: `/etc/convergent/config.yaml` or CONVERGENT_CONFIG; defaults `config.example.yaml`;
validation `tools/config-get`. Unknown/invalid keys stop builds. Image settings are baked in;
owner/disk/state/swap inputs apply only to install/stick. [Input rules](USAGE.md#install-options).

```sh
build/buildenv          # signed pinned stage3 and Portage snapshot chroot
build/packages          # image packages; --pretend previews
build/image             # UTC release ID: YYYYMMDDHHMM
```

`build/buildenv` keeps what upstream prunes in verified caches, so they outlive a rebuilt builder. The
stage3 pair stays in /var/cache/convergent/stage3: its signature and pin are checked on every use, and
a cached pair that fails is removed; its download has the Alpine bounds below. Gentoo distfiles stay in
/var/cache/convergent/distfiles, bound into the builder as its DISTDIR; Portage checks each against its
Manifest. The Portage snapshot is kept in that DISTDIR and checked against its digest and signature
again.

Patched packages compile and rebuild on patch changes. Bump VERSION in `build/build.conf` per
release: major.minor.patch, optional -rcN. Version appears
in /usr/lib/convergent/version, CONVERGENT_VERSION, boot titles, manifest and status; timestamp ID
names artifacts, orders IMAGE_VERSION and controls updates/rollback.

Output: `/var/lib/convergent/builder/releases/<release>`. Assemble guests in $g:

```sh
g=/var/lib/convergent/out/guests
mkdir -p $g/fw $g/wan $g/svc $g/browser/incus $g/remmina
guests/fw/build $g/fw                              # OpenBSD 7.9 plus errata
WAN_COUNTRY=SK guests/wan/build $g/wan             # regulatory country
guests/svc/build && cp guests/svc/out/* guests/svc/incus.yaml $g/svc/
guests/browser/build && cp guests/browser/out/* $g/browser/ && cp guests/browser/incus/*.yaml $g/browser/incus/
sh guests/remmina/build && cp guests/remmina/out/* $g/remmina/
build/guests <release-dir> $g                     # signed guest delivery when key present
build/stick <release> $g <out.img> [size]          # default 30G
zstd -T0 <out.img>
```

Alpine builds keep the pinned minirootfs, the Remmina source and patch, the Grafana VictoriaLogs plugin
and svc's edge apks in /var/cache/convergent/alpine (CACHE_DIR). Each pinned download and edge apk is
checked against its pin on every use; a copy that no longer matches is removed and fetched again. Keep
it: edge serves only its newest build. Alpine downloads get a 30-second connect timeout, an hour per
try and two retries; apk network failures get three tries. The browser image takes any Alpine Chromium
at or above 156.0.8078.79-r0, since Alpine deletes a build when it ships the next.

Stick asks for owner password then LUKS passphrase, 12–256 bytes each.
The LUKS passphrase must use printable ASCII (space through `~`). Owner selection:
CONVERGENT_INSTALL_OWNER, owner_login, then prompt. It installs on a loop device and
prints SHA-256. Images contain the owner's account: never publish them.

Use the same config for host/fw/WAN/svc. build/networks renders registry, topology hash, profiles,
DHCP/DNS and rules; fw/WAN checksums bind topology. Host installs pinned Zabbly UI assets at
/usr/share/incus-ui without Debian scripts/Node build. Browser nss-tools imports session
certificates; WAN has the fixed endpoint diagnostic. Keep these images together.

Remmina builds as root on native x86_64 Linux: compile patched 1.4.43 for Secret Service-only
password storage, retain Alpine plugins, remove build dependencies. Inventory, executable hash and
patch ship in the image; the advisory gate scans it. Separate remmina.manifest binds delivery.
Any Alpine rebuild of 1.4.43 supplies the plugins; another upstream version stops the build. The
advisory gate judges the source-built binary as r0, so an advisory fixed only in a later Alpine
rebuild is reported as affected until the source pin moves.

### Firewall images

Signify verifies inputs/syspatches; pkg_add verifies packages. Build patches the installed kernel on
a temporary DHCP boot, runs pkg_add -u, then verifies an offline smoke boot under the test sandbox.
Per-node .syspatch lists and openbsd.version enter signed payloads. The advisory gate checks all
errata, including gaps; non-applicable entries need reasons in `build/advisories.exceptions`.

### Sign and publish

CHANNEL defaults to beta; each published channel uses Ed25519 keys in /etc/convergent/keys.
Build/image embeds <channel>.pub/update URL and signs when <channel>.key exists. Stable's encrypted
key stays offline: `CHANNEL=stable build/sign <release-dir> /media/offline/stable.key`. Create keys
once:

```sh
install -d -m 700 /etc/convergent/keys && cd /etc/convergent/keys
openssl genpkey -algorithm ed25519 -out beta.key
openssl pkey -in beta.key -pubout -out beta.pub
t=$(mktemp -d /dev/shm/stable.XXXXXX)                 # stable: plaintext only in tmpfs
openssl genpkey -algorithm ed25519 -out "$t/stable.key"
openssl pkcs8 -topk8 -v2 aes-256-cbc -iter 1000000 -in "$t/stable.key" -out /media/offline/stable.key   # passphrase
openssl pkey -in "$t/stable.key" -pubout -out stable.pub
rm -r "$t"
```

Return to the repository root. [Owner trust/unsigned updates](USAGE.md#host-updates). OpenSSL's
default for an encrypted key is 2048 PBKDF2 rounds: rewrap an older stable key with the same
`pkcs8` command and the old file as `-in` (it asks for the old passphrase, then the new one).

Rotating a channel key, or replacing a leaked one: create a new pair as above, then build, sign and
publish with it. Laptops trust only the key their release embeds and refuse the new signatures.
Move each laptop over from USB with a release you built yourself: mount the stick as in
[USB updates](USAGE.md#host-updates), run `sudo env CONVERGENT_UNSIGNED=1 slot write
/run/usb/<release>`, reboot, then run `sys update usb` again for its guests. Rescue trusts the new
key once that release is good. Until moved, a laptop accepts whatever a leaked key signs.

Build-host-only provenance records release-key (SHA-256 of canonical public PEM with final newline)
and update-channel (embedded URL), or none. Signing/publication require channel/key agreement except
the compatibility bridge below. Missing provenance requires rebuild. Each slot/UKI needs exactly one
hash and accurate size; the host manifest format is unchanged.

`build/publish <release-dir>` uses mode-600 `/etc/convergent/r2-<channel>.env`: R2_ACCOUNT_ID,
R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL, and R2_ENDPOINT for EU. Limit the
token to the bucket. Verified host/guest/Remmina payloads upload to <channel>/<release>/; signed
<channel>/latest binds release and guest-manifest hashes (none if absent). Download sizes are
bounded. Signed-pointer replay can withhold releases; the client reports age.

Signatures upload before their documents; an interruption between uploads leaves a pair readers reject, and rerunning the publisher repairs it.

At most two releases/channel remain, with a 9-GiB bucket cap. Already-advertised releases are
immutable: retries compare file sets/bytes including pointer/signatures and write nothing if
identical. New content or re-signed pointers require a new ID. Retry comparisons download
one file at a time; reserve space for the largest payload.

For clients still using bleeding-edge, beta.{key,pub} must match bleeding-edge.{key,pub}; retain
both r2-beta.env/r2-bleeding-edge.env. Publish the same signed directory twice without re-signing:

```sh
build/publish <release-dir>
CHANNEL=bleeding-edge build/publish <release-dir>
```

Clients switch to the embedded beta URL after boot; then retire the bridge. To promote stable,
check out the candidate tag's exact commit, rebuild with CHANNEL=stable and its public key,
sign offline, run the full suite and publish. Embedded URL/key prevent cross-channel
re-signing; stable omits debug.

Before uploads/pruning, publish runs `build/advisories --gate <release-dir>` against Gentoo GLSAs,
each shipped Alpine branch's secdb and OpenBSD errata. Affected packages, missing
patches/inventories, and fetch/parse failures block publication; previous successful scans do not
authorize publishing. Only the builder fetches feeds; Portage matching runs in its chroot. Needs
python3, git, curl/Portage and coreutils timeout; signing remains offline-capable. GLSA clone has
a 120-second deadline per try, forced termination 10 seconds later, and one retry from an empty tree
after 5 seconds. Each feed fetch is bounded at 60 seconds per try, with two retries.

Host packages/slots are inventoried before trimming in build-host-only packages/packages.sig;
build/image binds them to the host manifest digest; build/sign and the scanner enforce the binding.
They are not published or in the host manifest. Retained releases through signed version 0.1.4
still get scans/status without bindings or apk-imports, with coverage notes; 0.1.5 builds require both.
Svc/browser/Remmina inventories are in rootfs; WAN's wan.manifest and firewall version/patch lists
are in signed guest payloads. Missing inventories need rebuild. Gate covers shipped guests only;
kernel/pin freshness is weekly. Svc records edge imports in its rootfs. Missing or malformed
provenance blocks publication. Accepted imports without supported advisory coverage
(including edge/testing VictoriaLogs) are marked UNKNOWN per package in reports and signed status;
they do not block publication or skip checks for covered packages.

Exceptions use `target package advisory reason` in build/advisories.exceptions, one per target/ID:

| Field | Values |
|---|---|
| target | host, wan, svc, browser, remmina, fw1, fw2 |
| package | Gentoo category/name; Alpine source origin; OpenBSD base |
| advisory | GLSA-YYYYMM-NN, secdb ID (usually CVE), or OPENBSD-7.9-001_xserver |
| reason | Concrete text, including absent OpenBSD sets; no wildcards/unreadable-data exceptions |

Gate output lists accepted reasons. Offline fixtures: `build/test --advisories`.

### Daily advisory status

After publication and daily as root: `CHANNEL=beta sh build/advisories-publish`. Requires channel
keys/R2 environment, including stable key for stable. Keep retained release directories, signed host
inventories and guest payloads until pruning; scans verify published manifests, not builder
packages.

It signs/uploads advisories.json plus signature per release: ID/time, versions,
advisories/exceptions. Failed/incomplete scans preserve previous status and fail. Mutable sidecars
are excluded from release identity. Bucket-listed Remmina requires its retained manifest and
payloads. Daily/weekly reports also compare pinned Gentoo
`www-apps/incus-ui` (upstream `incus-ui-canonical`) against Zabbly lts-7.0, verifying InRelease with
4EFC590696CB15B87C73A3AD82CC8797C838DCFD; the publish gate excludes that freshness check. [Laptop
evidence](USAGE.md#release-and-network-evidence).

### Diagnostics

Pin `sudo debug key` from the laptop as `/etc/convergent/keys/debug-laptop.pub` on the builder.
Beta-only `build/debug send <script-file> <purpose>` embeds a 24-hour upload link for a random key;
`build/debug fetch [id]` verifies laptop signature/request binding, rejects replay/corruption and
decrypts, then deletes the output and, for the last request sent, the published script.
[Owner execution/consent/output limits](USAGE.md#health-and-alerts).

The maintained field check is builder-only: `build/debug send build/diagnostics/field-check "<purpose>"`.
It reads release, services, check status lines (no diffs), guest logs, firewalls, wan and Incus state,
never keys, seeds or TLS state; `build/image` fails a non-beta image that carries it or the debug tool.

## Test in QEMU

`build/test --desktop` checks enforce labels, clock queries, metrics scrape, BlueZ D-Bus and browser
sockets under headless Sway. Bluetooth pairing and audio devices still need laptop testing.

Each test boots a throwaway disk in `builder/test/<release>-<mode>` and reports pass/fail.
Tests can run concurrently with 8–12 GiB each.

QEMU runs as unprivileged `convergent-qemu` (created on first use), in `/dev/kvm`'s group, under
`-sandbox on` with seccomp. Tests fail if QEMU retains root
IDs, effective capabilities, or lacks seccomp filtering.

```sh
build/test <release>                                  # boots and marks itself good
build/test --recovery <release>                       # recovery profile, unlock, continue and bless
build/test --rescue <release>                         # standalone rescue UKI, empty slots
build/test --corrupt <release>                        # one flipped block: must refuse to boot
build/test --desktop <release>                        # sway, bar and sys: the session's programs and config
build/test --fallback <good> <newer>                  # broken newer slot: the good one returns
build/test --interrupt <good> <newer>                 # update cut off half-way: still boots
build/test --update <good> <newer>                    # signed slot write and reboot
build/test --guests <release> $g                      # plus guests init: firewalls, wan, svc
build/test --guests-maint <release> $g                # plus maintenance, DNS and handoff recovery
build/test --guests-update <release> $g <broken-dir>  # plus guest updates and a rollback
build/test --online <release> $g                      # once published: its guests from the channel
build/test --install-options                          # installer config, sizing, disks; no root
```

`<broken-dir>` must be new: the test builds a broken svc image there and verifies update rollback.

`--guests` and `--guests-update` test Internet access through wan's second NIC (QEMU user networking).
fw1 must reach 9.9.9.9:853 and the host must resolve a name. Both modes smoke-test def without
Wayland, check tmp versus portal policies/devices, and exercise portal expiry and closure. They probe PF's
web/admin/svc/host policy (`CV-PF ok/FAIL`, source, destination and port), including portal
reachability before, during and after portal mode. Temporary listeners give denied ports positive
controls. Both modes build legacy web/admin from frozen YAML fixtures, then run
`guests update browser` normally and after SIGKILL at the rename journal. Both state-volume markers,
new profiles, and removal of old names/journals must pass. They check signed online updates, when
configured, after a successful uplink. They also run the booted selftest checks as root. Only
release, verity, nested and audit failures gate the test.

All guest modes (`--guests`, `--guests-maint`, `--guests-update`, `--online`) also inject L2 frames
on the work networks (`build/test-pf`, `build/fixtures/pf-l2`), run a real Remmina session through
the production launcher (`build/fixtures/remmina-session`), and check ordered shutdown
(`build/fixtures/shutdown`). The drain must stop browsers, Remmina and the temporary container
first, then svc, wan and both firewalls, restore prior autorestart overrides/holds, and end in guest
poweroff.

`build/test --rescue <release>` boots the rescue UKI through QEMU/OVMF with both slots empty.
It unlocks, checks the menu, powers off, and verifies unchanged UKI names/content and blessing state.
USB writes, password reset, next-slot selection and log export need separate testing.

## Checks

`build/image` checks AppArmor profile syntax, refuses a release ID later than the builder's UTC clock,
and fails if a USB network driver remains in the image. `build/lint` checks dashboard JSON drift. `build/test
--guests-update` checks every metric panel query against real svc scrapes, allowing explicitly
optional hardware and quiet alerts, every LogsQL target, and that forged hostnames cannot move log
records to another host. `build/test-debug` checks diagnostic output authentication offline.
`build/test-diag` checks the collector in `build/diag/` (system data only: personal log lines,
serial numbers, MAC and most IP addresses are removed) and the error severity of check, facts and
power failures, also offline.

Run `build/lint` before a push. On tracked files it checks shell syntax, shellcheck (when
installed), leaked secrets or session and scratch paths, and CRLF line endings. It also checks that
each simple backticked repository path in README, USAGE, RECOVERY and ARCHITECTURE exists.

Once a week, as root, run `build/advisories <release-dir> $g` (pass both: the default guest
directory is not `$g`). It reads upstream fixes and names what to rebuild (`host`, `kernel`, `fw1`,
`fw2`, `svc`, `browser`, `wan`, `remmina`, or `guests` for the pins). The kernel version comes from
the release. Gentoo packages come from its signed build-host inventory. Exit 1: something to
rebuild (UNKNOWN lines may appear too). Exit 2: only UNKNOWN; a source was not read.

Offline feature checks (also run by `build/lint`; require `python3`, `jq` and OpenSSL):

| Command | Coverage |
|---|---|
| `sh build/test --networks` | Work configuration and rendering |
| `sh build/test-topology` | Firewall pair journal replay |
| `sh build/test --remmina-unit` | Keyring handling and artifact paths |
| `sh build/test --observability` | Status ingestion, capture, parsers, dashboards, wan diagnostics and pflogd state |
| `sh build/test-incus-ui --offline` | UI credential and session fixtures |

`build/lint` also runs the install-options, VM runner, bootstrap, boot privacy, account, leases and
firewall-heal fixtures.

`--guests`, `--guests-maint` and `--guests-update` exercise live PF/session/lifecycle checks;
see their test scripts for assertions and hardware-only limits.
