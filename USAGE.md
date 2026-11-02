# Using Convergent

Tools live in `/usr/local/sbin`. `sys`, `browser` and the bar run as owner; `sys` uses `sudo` as
needed. Others (`slot`, `fetch-release`, `guests`, `check`, `devices`, `backup`, `account`, …) need
`sudo` (password, 5-minute ticket).

[Install](#install) · [Keys](#keys) · [Commands](#the-sys-tool) · [Updates](#releases-and-guests) ·
[Recovery](RECOVERY.md).

## Install

Writing an image or installing **erases the target disk**. Hardware requirements:
[README](README.md).

### Disk image

Default size: 30 GiB (32,212,254,720 bytes); some nominal 32-GB sticks are too small. On Linux:

```sh
lsblk -o NAME,SIZE,MODEL,TRAN                        # identify the USB disk
if [ "$(sudo blockdev --getss /dev/sdX)" = 512 ]; then
    zstd -dc <out.img>.zst | sudo dd of=/dev/sdX bs=4M iflag=fullblock oflag=direct conv=fsync status=progress
else
    echo 'Image writing requires 512-byte logical sectors; target refused.' >&2
fi
```

For 4Kn internal disks, boot compatible USB media and use the installer. The image includes the
owner, encrypted state and guests; B is empty. Auto state grows at unlock; fixed/percentage
installations stay bounded.

### Internal disk

As root from UEFI-booted Convergent USB, with a release directory:

```sh
convergent-install /path/to/release
```

The installer verifies the signature with the booted key; CONVERGENT_UNSIGNED=1 bypasses it.
It lists/refuses unsafe targets and needs at least 49 GiB plus 4 MiB without disk swap. Confirm the
disk path or ERASE plus serial, owner name, then password and LUKS passphrase twice. It verifies A,
registers an entry using the release NAME and powers off. Remove USB. Guests are not copied: put
them at `/var/lib/convergent/release-guests/guests`, then run `sys guests setup`.

### First boot

Disable Secure Boot; keep VT-d enabled. Dell firmware/menu keys are F2/F12. Connect the boot disk
directly, without a hub/dock. LUKS uses **US layout** regardless of console_keymap (US by default):
on Slovak keys, @ is Shift+2 and y/z swap.

1. Enter `Passphrase [1/3]:`; three failures power off. Tuigreet then asks for the owner login.
   Ctrl+Alt+F2 through F6 offer text logins.
2. Log in to Sway. The bar reaches `rel <release> good` after health checks.
3. Disk-image setup shows orange SETUP for 10–30 minutes. Red SETUP failed: `sys guests setup`
   resumes; log `/var/log/guests-setup.log`. Finish when SETUP disappears.
4. With trusted devices attached (including built-in camera/Bluetooth/fingerprint reader), replace
   the class policy:
   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```
   Check `sudo devices list`; required devices must not be blocked. Subsequent policy changes:
   [Devices](#devices).
5. Super+m → Wi-Fi → Scan → Connect, or `sys wifi connect`. `sys wifi status` must show an address.
6. Run `sys selftest` and inspect `~/selftest-YYYYmmdd-HHMMSS.txt`: no FAIL; SKIP is acceptable.

Controls: [Keys](#keys), [bar](#the-bar), [alerts](#health-and-alerts). Repairs/menu:
[RECOVERY](RECOVERY.md#recovery-boot-menu); logs: `sys logs`; commands: `sys help`.

### Install options

Use `CONVERGENT_CONFIG` on the builder or `convergent-install --config /path/config.yaml
/path/release` on USB. Keys/defaults: `config.example.yaml`. No secrets, including comments. The
validated copy is saved at `/var/lib/convergent/config.yaml`, unused at runtime. Enter passwords
interactively; build/stick also accepts stdin: owner password, then LUKS passphrase. Both require
12–256 bytes; the LUKS passphrase must use printable ASCII (space through `~`).

```yaml
install:
  disk: auto
  state_size: auto
  swap: none
```

- **disk:** auto needs exactly one internal nonremovable/non-hotplug NVMe/SATA/ATA SSD excluding
  boot; otherwise choose a whole /dev/disk/by-id ID. Mounted/swap/held/boot/read-only disks are
  refused. Erase confirmation remains mandatory
- **state_size:** auto uses/grows remaining space; 1%–100% of space after ESP/slots/alignment or
  32–999999GiB stays fixed
- **swap:** none, zram:1GiB–zram:1024GiB (uncompressed capacity), state:1GiB–state:1024GiB
  (encrypted file outside release snapshots); no hibernation

GPT/LUKS2/Btrfs, 1-GiB ESP and two 8-GiB slots are mandatory. esp_mib, slot_mib and state_max_gib
are rejected inputs. Validation/capacity checks precede partitioning: state needs 32 GiB data plus
state swap; build media needs 12 GiB plus swap. build/stick forces auto state and its loop target;
raise image_size or positional size for disk swap (even 1 GiB exceeds the default 30-GiB image).
OpenRC activates generated swap settings; editing reference YAML has no runtime effect.

## System operations

| Task | Command or behaviour |
|---|---|
| Update | Whole signed release: `sys update install`; no runtime package manager |
| Service status/restart | `rc-status -a`; `sudo rc-service <name> status`, `restart` |
| Enable services | Fixed in the release |
| Read logs | `sys logs`; [log locations](RECOVERY.md#8-where-the-logs-are) |
| Edit /etc | [Writable exceptions](ARCHITECTURE.md#53-what-is-writable); other changes need a release |
| Change password | `sys security password` or `sudo account password [user]`; bind-mounted shadow cannot be replaced by plain passwd |
| Home files | Encrypted state, preserved across updates |
| Manage guests | guests manages infrastructure; Incus UI manages owner work guests |
| Wi-Fi | `sys wifi` controls wan's radio |

Firewall inspection: `sudo ssh -F /etc/convergent/ssh_config fw1`, then `pfctl -sr` or
`ifconfig carp`. Daily use needs no firewall shell. For a manual policy reload, use
`/usr/local/libexec/convergent/fw-pf-reload`; a failed load leaves forwarding off.

## Keys

Stock Sway bindings plus Convergent additions below. Super is the Windows key. Sway, foot, mako and
swaylock use stock styling with a black background/bar; override each in `~/.config/`.

| Key | Does |
|---|---|
| Super+m | `sys`: menu of areas and actions, in a terminal |
| Super+a | one `sys` action by name, in its own terminal |
| Super+d | an app by name: Browser_default, Browser_internal, Browser_temporary, Incus management, Remote, Settings, Screenshot, Files, Notes, Foot |
| Super+b | default browser (`browser def`) |
| Super+Shift+t | temporary browser (`browser tmp`) |
| Super+Escape | lock the screen now |
| Super+Enter | terminal (foot) |
| Super+Shift+q | close the window |
| Super+1 … 9, Super+Shift+1 … 9 | go to a workspace; move the window there |
| Super+f | fullscreen |
| Super+Shift+c | reload the sway configuration |
| Super+Shift+e | exit sway |
| Print | select an area; save to `~/Pictures/screenshots` and copy (Escape cancels) |
| Shift+Print | save and copy the focused screen after 1 s |
| Volume and mute keys | `wpctl` on PipeWire |
| Mic-mute key | toggle the default microphone; while locked, only mute |
| Brightness keys | `sys display bright -5` / `+5` (5 % steps) |

Super+a also runs `usb enrol`, `display save`, `power charge`, `power thermal` and `camera on/off`.

Display preview: type `yes` then Enter within 15 seconds to keep it. Any other answer, Escape then
Enter, or timeout restores the previous layout. Docking/undocking needs no key.

Files (Super+d) opens Midnight Commander in foot, with its internal editor (`mcedit`) and the
`modarin256-defbg` dark skin on the terminal background. Notes opens Vim's directory list in foot at
`~/Documents/notes`, creating it if needed. Keep notes as plain `.md`: `:e name.md` opens one, `:w`
saves.

## The sys tool

`sys AREA [ACTION] [ARGS]`. First action in each row is the default. An unknown second word becomes
an argument to that default (`sys backup /mnt/x proj` works; `sys wifi foo` is a usage error).
Missing arguments are prompted for; partial lists are usage errors. `sys help` lists actions and
aliases. `*` marks actions that ask for `yes` in the terminal (default No).

`sys` (Super+m) uses fzf: menu left; Gentoo dashboard, selected status and commands right, in terminal
colours with blue highlighting. The dashboard refreshes on entry; narrow panes hide the logo.
Enter opens/runs; Esc goes back; typing filters.
Alt+Enter runs what was typed (`area action args`, or `action args` inside an area).

Wi-Fi picker: type to filter, Enter selects the highlighted SSID, Esc cancels, Ctrl+u clears the
filter, Alt+Up/Down scrolls its status. Hidden SSIDs: `sys wifi hidden` and a typed name. Alt+Enter
does not join an unscanned name.

| Area (alias) | Actions, default first |
|---|---|
| `wifi` | `status`, `scan`, `connect [SSID]`, `hidden [SSID]`, `disconnect`, `forget [SSID]` *, `test` |
| `portal` | `status`, `on`, `off` |
| `wired` | `status`, `attach [VENDOR:PRODUCT SERIAL]` *, `remove` * |
| `dns` | `list`, `add [NAME IPv4]` *, `remove [NAME]` *, `allow [DOMAIN]` *, `unallow [DOMAIN]` *, `push` |
| `firewall` (`fw`) | `status`, `rebuild` *, `maintenance` *, `undo` *, `capture INTERFACE-OR-SEGMENT SECONDS` |
| `bluetooth` (`bt`) | `status`, `on`, `off`, `scan`, `pair [MAC]`, `connect [MAC]`, `disconnect [MAC]`, `forget [MAC]` * (device picker without MAC) |
| `usb` | `status`, `allow N\|ID` *, `enrol` *, `review`, `revoke RULE` * |
| `audio` | `status`, `out ID`, `vol N` (0–150), `mute`, `mic on\|off`, `micmute` |
| `camera` | `status`, `on`, `off` |
| `display` (`disp`) | `status`, `bright N\|+N\|-N`, `set OUTPUT mode\|scale\|position\|enable\|disable [VALUE]` (15-second preview), `save`, `reset` *, `watch` (session hook) |
| `keyboard` (`kb`) | `status`, `set LAYOUTS` (e.g. `us,hu`), `next` |
| `touchpad` | `status`, `set OPTION VALUE` (apply and save; options below) |
| `screenshot` (`shot`) | `area`, `screen` (save to `~/Pictures/screenshots` and copy to clipboard) |
| `browser` (`br`) | `status`, `def`, `tmp`, `int`, `incus` |
| `remote` | `open`, `status`, `close` |
| `security` (`sec`) | `status`, `alerts` (`sys alerts`), `events`, `check`, `report`, `password` |
| `update` (`up`) | `status`, `check`, `install` *, `usb [MOUNTPOINT\|DEVICE]` * |
| `guests` | `status`, `setup`, `update` |
| `power` | `status`, `ac`, `battery`, `charge off\|55-100`, `thermal quiet\|balanced\|performance`, `lock`, `logout` *, `reboot` *, `off` * |
| `backup` | `run [MOUNTPOINT PROJECT]` |
| `logs` | `host` (`/var/log/messages`), `debug` (beta only), `services` (`rc-status -a`) |
| `selftest` | `run` |

DNS edits, wired assignment and firewall maintenance ask inside the action, after showing the change
or checking health. Not built into `sys`: owner guest management and printing.

Screen too big: `sys display set eDP-1 scale 1.3`, confirm `yes`, then `sys display save`. Save docked
and undocked layouts. Profiles match connected make/model/serial sets, including disabled panels;
connector names/order may change. They apply at login and set changes. Unknown sets enable screens
at preferred modes: configured `display_scale`, otherwise laptop scale 1.3/external 1. An existing
`~/.config/sway/config.d/outputs` overrides this until the first save. `save` refuses duplicate
identities. `reset` clears only the current set's profile, leaving the live layout. JSON profiles in
`~/.config/convergent/displays/` override `display_scale`; saving retires the old outputs file.

Touchpad: `sys touchpad set` prompts, or takes an option and value (`sys touchpad set pointer_accel
0.3`). Settings are validated, apply live to all touchpads and save to
`~/.config/sway/config.d/touchpad` for every login, independently of keyboard and display settings.
Support depends on hardware; `sys touchpad status` shows libinput settings.

| Option | Values |
|---|---|
| `pointer_accel` | -1 to 1 (pointer speed/sensitivity; default 1, the maximum) |
| `accel_profile` | `adaptive` (default: faster finger movement goes further), `flat` |
| `tap`, `natural_scroll`, `dwt`, `middle_emulation` | `enabled`, `disabled`; `dwt` disables the touchpad while typing |
| `scroll_method` | `none`, `two_finger`, `edge`, `on_button_down` (uses the device's scroll button) |
| `scroll_factor` | 0–10 (scroll speed multiplier; default 3, 0 stops scrolling) |

Screenshots (`sys screenshot`) create the directory if missing and use
`screenshot-YYYYmmdd-HHMMSS.png` names. After saving and copying, `notify-send` displays
**Screenshot saved** and the filename in mako for 3 seconds. Duplicate timestamps are refused.

Leave the microphone enabled in firmware. Each Sway login waits for PipeWire's default source and
mutes it; `sys audio mic on|off` changes that. The bar shows orange `MIC` while unmuted (refreshed
every 10 s), or grey `MIC?` if unknown. That means permission to record, not recording. Config
reloads do not reset mute.

## Browsers

```sh
browser def|tmp|int [url]
browser tmp --portal [url]
```

Run as owner in the Sway session; no password. `sys browser def|tmp|int` (or the menu) opens one
without a URL; `sys browser` lists running ones. Only HTTP/HTTPS URLs are accepted; int accepts only
its Grafana/Incus launch URLs. Each browser is Chromium in its own container, with a restricted
Wayland socket and playback-only audio. Window title starts with `[role]`. Chromium's default
appearance is kept.

Success: a `[def] …` window and `BR:1` in the bar. Super+b or Super+Shift+t failures show the reason
at the top. Full output: `$XDG_RUNTIME_DIR/browser-def.*.log` or
`$XDG_RUNTIME_DIR/browser-tmp.*.log`, one file per launch.

| Role | For | State |
|---|---|---|
| def | everyday browsing | profile and downloads kept in a 4 GiB volume |
| tmp | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| tmp --portal | captive portals; opens `http://<uplink-gateway>/` unless given a URL | container deleted on close; owns portal mode |
| int | Grafana; Incus after a session unlock | profile kept in a 512 MiB volume; UI key lives only in session memory |

A second def or int start raises the open window. Portal mode refuses one; normal tmp runs many at
once. Downloads stay in the container; no action moves a file out. Policies: DNS-over-HTTPS off, no
sync, no password manager, no telemetry. Int and both tmp modes allow no extensions. The int browser
starts Grafana in svc and stops it on close. Log in as `owner`; password: `sudo cat
/var/lib/convergent/guests/tls/admin-password`. A handler that sends links from other programs to
`tmp` is not built.

Network addresses and portal isolation: [ARCHITECTURE 3.5](ARCHITECTURE.md#35-browsers).

### Incus management

With int closed, run `sudo incus-ui setup` once and choose a strong passphrase. Open **Incus
management** from the desktop or `sys browser incus` (`incus-ui open` in a host terminal).
Each session prompts again, then opens `https://100.80.1.10:8443/ui/` in Browser_internal.
This certificate manages everything, including the host's infrastructure. Close the entire int
browser session to lock it; closing only the Incus tab is insufficient. A plain `browser int`
opens Grafana without the administration key. Keep the launcher terminal open for the session.

With int closed, `sudo incus-ui rotate` replaces the 90-day credential and asks for a new
passphrase. `sudo incus-ui revoke` immediately stops an unlocked int session and removes its
trust and stored bundle; setup is then required again. Certificate administration uses normal
sudo authentication; only the fixed session launcher is passwordless.
Failures: [RECOVERY 15](RECOVERY.md#15-incus-ui-session-or-passphrase-failure).

### Remote desktops

Choose **Remote** or run `sys remote open`; `status` reports state and `close` stops the container
and unlocked keyring. Each open needs a nonempty keyring password (twice on first use). Cancellation
or a wrong password closes Remmina. Profiles and encrypted credentials survive updates; there is no
plaintext fallback. Recovery: [recipe 16](RECOVERY.md#16-remmina-session-or-keyring-failure).

Use numeric work addresses: SSH (TCP 22), RDP (TCP/UDP 3389), VNC (TCP 5900–5999) or ping;
firewall nodes and gateways are excluded. Cage confines clipboard transfers to the remote
session; host copy/paste and audio recording are unavailable, playback is allowed.

For RDP file transfer, select `/share` as the shared folder. For direct sharing, use Incus UI
to attach the existing filesystem volume `share` from pool `default` to each stopped VM that
needs it. The VM must support and mount the filesystem share; it is not a shared block disk.
The owner project needs `features.storage.volumes=false` to use default-project volumes;
move existing private volumes before changing that namespace option. Match guest UID/GID 1000
or grant suitable ACLs. Detach when finished. Resize the volume in Incus UI if needed;
4 GiB is the creation default. Stop every attached instance throughout backup or restoration.

## Wi-Fi

`sys wifi` controls wan over SSH; iwd roams between known networks. `sys wifi connect` offers
scanned SSIDs/security/signal, then asks `Passphrase (empty for a known or open network):`. `sys
wifi connect 'SSID with spaces'` skips selection; `sys wifi hidden` asks for an unscanned name.
Saved hidden networks reconnect from the scan cache first, then rescan if needed.
Credentials are stored in wan; replacement also stages root-only copies on encrypted host storage,
which can remain until recovery or cleanup completes.
Scan completion polls for 15 seconds after initiation; initiation/results
have separate timeouts. Failures propagate with guidance; association without IPv4 reports DHCP
failure.

`sudo ssh -F /etc/convergent/ssh_config wan 'wifi auto'` restarts iwd to resume automatic
connection to known networks; it interrupts the current Wi-Fi connection.

Overlapping 100.80.0.0/16 leases raise UpstreamOverlap and are refused. After moving a refused wired
adapter to a safe network, `sudo ssh -F /etc/convergent/ssh_config wan 'check retry'` retries
configured wired DHCP. Only a safe lease clears the latch. `sys wifi test` includes retry advice
when latched and [wan's diagnostic log](RECOVERY.md#8-where-the-logs-are): the last 200 lines, at
most 32 KiB.

## Captive portals

`sys portal on` or `browser tmp --portal [url]` opens a dedicated browser and its firewall/WAN
DNS rules. The default URL is `http://<gateway>/`, using the selected uplink's DHCP gateway;
an explicit HTTP/HTTPS URL is optional. Without a usable gateway, supply an uplink-local URL.
HTTP/HTTPS destinations remain restricted to the selected uplink subnet. Portals requiring
interception of public HTTP requests or publicly hosted login pages are unsupported.
Mode ends on close, `sys portal off`, or after 30 minutes; bar: PORTAL. Wired and Wi-Fi work.
DNS uses only the selected default uplink's first nameserver: IPv4 outside 100.80.0.0/16. An
unusable first resolver refuses activation even if later ones work. New launches require stale-rule
closure on all three guests. Cron retries partial closure/abandoned sessions each minute. `sys
portal status` reports the reason and each guest's state.

```sh
sudo portal on [A.B.C.D/LEN]   # diagnostic; expires after a minute without browser ownership
sudo portal off                # failed closure retries each minute
sudo portal status             # per-node state, aggregate on/off/mixed/unknown and reason
```

## Devices

Disk images initially allow HID/storage/hub classes. `sys usb enrol` replaces that policy with
individual-device rules: review attached devices/hubs, answer yes for each trusted one, then confirm.
Nothing saves before confirmation; declined devices remain blocked. Do not interrupt it after
confirming: an interrupted save can leave the policy half applied; run `sys usb enrol` again.

`sys usb review` shows saved rules (even unplugged) and attached decisions. `sys usb revoke RULE`
takes an allow **rule number**, removes it and denies that device over overlapping allowances. Enrol
first if only broad class rules exist. Both restart USBGuard, potentially disconnecting input or
storage. `sys usb status` shows blocked USB/unauthorized Thunderbolt; `sys usb allow N|ID` takes a
**device number** or Thunderbolt ID.

```sh
sudo devices list
sudo devices allow <number>    # permanent USB; warns for input/storage/network
sudo devices allow tb <id>     # Thunderbolt tunnel until unplugged
```

Both approvals require yes; USB rules persist in `/etc/usbguard/rules.conf`.

Bluetooth starts off. Run `sys bluetooth on`; `sys bluetooth pair` scans ten seconds then lists
MAC/name. `connect`, `disconnect`, `forget` use the current list; `sys bluetooth scan` refreshes it.
Explicit MACs are validated. Picker: terminal fzf, otherwise bemenu; Escape cancels. Forget asks yes
before selection. `sys bluetooth` shows power/known devices.

Serial console: approve through `sys usb allow NUMBER` (from `sys usb status`), then
`tio -b 115200 /dev/ttyUSB0` with the required baud; CDC ACM uses `/dev/ttyACM0`. Exit Ctrl+t, q.
The owner receives dialout membership at install/updated boot.

Wired uplink: approve the dock's Realtek USB device, use `sys wired status` for its serial, then
`sys wired attach 0bda:8153 SERIAL` (or prompts). Confirm vendor/product/serial; empty/ambiguous
serials fail. The persistent wired-uplink device reattaches only that identity to wan as eth1. `sys
wired remove` removes assignment/automatic attachment, retaining USBGuard approval; unplugging alone
retains assignment. Host does no DHCP/addressing. WAN prefers wired and retries replug DHCP within
its minute check.

Camera defaults off. `sys camera on` saves/enables and loads drivers; `sys camera off` saves denial
before non-forced unload. If busy, close the application and retry. `sys camera status` shows choice
and video-core state. CAM means enabled, not recording; CAM! means still loaded despite off.
Choice persists at `/var/lib/convergent/devices/camera`, following slot var snapshots. USB cameras
also require approval. Meeting compartments/screen sharing remain unavailable.

## DNS: blocklist and own records

Owner files: `/var/lib/convergent/dns/allow` (one domain/line, # comments) and
`/var/lib/convergent/dns/records` (Unbound local-data/local-data-ptr). Weekly blocklist
source/limits: `/etc/convergent/dns.conf`. Failed pushes restore both firewalls; interrupted
recovery waits for both.

`sys dns list` shows records/exceptions and last successful UTC push. Edit with `sys dns add
printer.home.arpa 192.168.1.50`, `sys dns remove printer.home.arpa`, `sys dns allow example.org` or
`sys dns unallow example.org`. Exceptions include subdomains. Names lowercase;
duplicate/invalid/built-in conflicts are refused. Non-A records require manual editing, including
removal; records grant no firewall access. Each edit shows a diff and requires yes.

```sh
# Download, validate and push blocklist/records; needed before first local push
sudo dns-push
sudo dns-push local    # current owner files with stored blocklist; also sys dns push
```

## Firewall maintenance

`sys firewall status` / `sys fw` shows registered CARP roles, PF states, Unbound and last DNS push,
including unreachable nodes/pending recovery. `sys fw maintenance` checks coherent roles,
PF/pfsync defer/Unbound/local DNS, asks before demoting MASTER, then verifies full peer takeover.
Failure undoes handover; interruptions retain the journal.

Run `sys fw undo` afterward, before guest updates. Both nodes must be healthy; it verifies normal
fw1 MASTER/fw2 BACKUP. Restore management or rebuild an unreachable node, then retry. Remote work
can outlive SSH; retry after it finishes. Never remove `/var/run/convergent-maintenance.lock`;
its PID does not prove ownership. Reboot nodes using the old symlink lock before these operations.

`sys firewall rebuild fw1|fw2` / `guests rebuild fw1|fw2` recreates a node from installed
images/seed. Finish updates/handoffs first. The peer must be healthy and own all segments before
replacement, or run coherent CARP on every segment if the target still runs; a target Incus cannot
stop is ended by its verified QEMU pid. Maintenance may name the target; undo afterward. Rebuild waits for guest/DNS locks,
checks/seeds replacement, restores normal roles and pushes stored DNS. Browsers may stay open.
Repeat the same command after interruption to resume.

## Backups

```sh
sudo backup [<mountpoint> <owner-project>]
```

`sys backup [MOUNTPOINT PROJECT]` runs it, prompting for `Mounted encrypted external disk:` and
`Owner Incus project:` when arguments are absent. It requires an external LUKS USB disk unlocked
and mounted at a root-owned directory (not the laptop disk), and the owner's Incus project
(`owner`, created by setup; never `default`). It writes
`convergent-backups/backup-<UTC>`: a snapshot of `/home`, the writable `/etc` files, exports of the
owner's containers and profiles, and custom filesystem/ISO volumes of both projects, including
`remmina-state` and `share`, plus Grafana's matching `admin-password` and `secret-key` in
`grafana-secrets/`. Close browsers and Remmina and stop every instance using `share`.
Keep them stopped throughout backup. It verifies readback and retains three generations.
VM instances, custom block volumes, system guest instances and the rest of `/var/lib/convergent` are excluded
(see `EXCLUDED` in the backup). Unmount and close
the disk before unplugging. Restore steps: [RECOVERY 11](RECOVERY.md#11-start-over).

## Health and alerts

Secure Boot off produces SecureBootNotVerified/CheckerFailed; no accepted baseline also produces
CollectorBroken. FirewallRulesetDrift requires an expected hash and reports mismatches. Inspect
alert names, not counts. `sys alerts` / `sys security alerts`, or clicking bar counts, opens
severity, name, summary/description and API active-since time. Invalid/unavailable responses report
errors.

`sys browser int` opens Overview, Network, Guests, Host, Security and Monitoring. Shared navigation,
project/instance selectors and source labels distinguish current tables/history. Dash means no data;
footers state collection limits. CARP annotations are opt-in; Explore · all logs adds routine audit
and full kernel traces. Security shows the latest 50 events in range: login/sudo, USB/AppArmor,
firewall takeovers, guest/host updates and bless/fallback. Connection supplies host identity;
app/message remain sender claims.

`sys security events` works without svc: up to 100 matches per file from its last 5000 lines in
current host messages/audit log, with source/original timestamp. No time merge or rotated logs;
missing files are reported. Minute probes miss brief firewall transitions (use Grafana); audit/PAM
may duplicate logins. Fallback identifies an older boot with exhausted newer UKI.

```sh
sys security check                    # sudo check; report in /var/lib/convergent/check/last
sys security report
sys security events
sudo check accept <release-dir>       # trusted baseline, Secure Boot on and out of Setup Mode
sudo check accept-fw <guest-dir>/fw   # updated firewall hashes, same Secure Boot requirement
```

Baseline input needs manifest and guests/fw/fw{1,2}.{pf,rules}.sha256. Reaccept baselines lacking
tmp's profile. Check fails without a baseline or with Secure Boot off. Acceptance does not verify
manifest signatures: verify the release yourself first.
[Checks/timings](ARCHITECTURE.md#8-observability).

`sys selftest` authenticates sudo once and writes ~/selftest-YYYYmmdd-HHMMSS.txt with bounded
PASS/FAIL/SKIP checks. `sys debug` (Logs → debug, beta only) shows a signed diagnostic's
purpose/expiry and asks before root execution. Expired requests fail. Replay rejection applies to
the current `/var` history; rollback can permit a still-valid diagnostic again, with fresh consent.
Limit: five minutes, 8 MiB output; script failure status is preserved, timeout 124 or forced-kill 137.
The printed
root-only `/var/lib/convergent/debug/<id>.txt` can be read with `sudo less` before a second yes
permits encrypted, laptop-signed upload. `sudo debug key` prints the laptop public key. Builder
commands: [BUILD, Diagnostics](BUILD.md#diagnostics). Crash handling: [RECOVERY
13](RECOVERY.md#13-a-kernel-panic-or-crashrecorded-alert). Cron/anacron mail is disabled; jobs/logs
still run.

### Release and network evidence

Security → Release compares booted/latest signed IDs, inventory versions and advisories/fixes.
`fetch-release check` refreshes it without notifications. Read verification and scan/check ages;
missing/invalid/unavailable is unknown; over two days warns. Versions describe releases, not live
guests after partial updates; pruned installed releases may lack status.

Network shows registry CARP segments, parent traffic, Unbound recursion/SERVFAIL, Wi-Fi signal/
bitrate/observed roams and firewall-to-WAN RTT/loss. These probes do not prove Internet access.
Blocked rankings count sampled logged packets, capped at five/second/firewall.

From the owner login, `sys firewall capture <interface-or-segment> <seconds>` (e.g.
`sys firewall capture vio4 15`) authenticates sudo, selects coherent MASTER and saves private
~/captures pcap. Segments resolve to parent interfaces. Bounds: 1–60 seconds, 1536-byte snapshots,
32000 packets, below 50 MB. Capture does not follow failover. Delete unneeded captures; payloads
may be present. [Missing evidence](RECOVERY.md#17-missing-release-or-network-evidence).

## The bar

Refresh: five seconds; inputs: ten seconds; alerts: thirty seconds. `|` represents bar separators:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx 0.8 rx 12.4 Mb/s
WLAN:home--WAN--[FW1 FW2]--laptop--SVC--BR:2 | rel 0.1.0 good | NL | 0 1 0 | PORTAL
US | UP 3d 03:41 | Tue 04/08 15:33:02 | BAT 87% -
```

| Block | Shows | Look or fix with |
|---|---|---|
| `CPU` | busy percent, lowest-highest core clock, package/hottest temperature (every 5 s); `-` if missing | `sys power status` shows sensors/profile |
| `RAM`, `SWP` | used/total GiB; RAM is memory in use (`MemTotal - MemAvailable`, so reclaimable cache does not count) minus what guests hold (`check status` sums their cgroups without file cache and VM processes every minute) | Grafana, Guests |
| `NET` | transmit/receive Mb/s on the default-route interface (route refreshed every 10 s) | `sys wifi test` |
| Topology | uplink, wan, both firewalls, svc and browsers (below) | `sys guests status`; RECOVERY 5, 6 |
| `rel` | booted semantic version (release ID on older images); grey `good` if the release passed its checks this boot, else red `UNBLESSED` | `sys update` |
| `NL` | click to pause or resume the idle lock (orange while paused); `NL!` (red): swayidle missing | `sys power lock` |
| `MIC` | default microphone unmuted (orange); hidden when muted; `MIC?` (grey) if unknown; every 10 s | `sys audio mic off` / `on` |
| Alerts | firing alerts as three counters: critical (red), warning (orange), info (white); `? ? ?` (grey) if svc cannot be read, including during SETUP until svc is up; every 30 s | click for the firing list in foot, or `sys alerts`; history in Grafana: `sys browser int` |
| `RDP:on/off/?` | Remmina running/stopped/unknown; stale status is unknown | `sys remote status`, `sys remote close` |
| `PORTAL` | portal mode on (orange) | `sys portal off` |
| `CAM`, `CAM!` | camera enabled, or driver still loaded after disabling (orange); not a recording indicator | `sys camera status`, `sys camera off` |
| `SETUP` | guests being created (orange); `SETUP failed` (red) | `sys guests setup` |
| `GUESTS` | downloaded guests being applied (orange); `GUESTS failed` (red) | `sys guests update` |
| layout, `UP`, clock | keyboard layout (every 10 s), uptime, local date and time | `sys keyboard next` |
| `BAT` | capacity; `+` charging, `-` discharging (orange below 30 %, red below 15 %); `AC BAT` on mains but not charging (full or at charge limit); `AC` without a battery | `sys power status` |

Topology starts with the uplink: `WLAN:<network>` (green connected, red with no network, grey when
wan does not answer; names over 16 characters are cut) or `ETH` for a passed-through wired NIC.
`WAN` is green with an uplink, orange without one, red when wan is down. Each firewall is bold
bright green as CARP master, dim green as standby, orange when its CARP interfaces disagree, red
when down. `SVC` is green or red; the host name is green. `BR:n` counts running browser containers
(grey at zero). Cron refreshes it every minute; if it is older than three minutes, it turns grey.
The idle-lock pause is the file `$XDG_RUNTIME_DIR/nolock`; the lid lock still works.

## Releases and guests

Channels/promotion: [BUILD](BUILD.md#status). `sys update status` / `slot status` shows semantic
version and timestamp release ID; timestamp controls ordering. Reports carry both.

### Host updates

`sys update check` reports newest/up-to-date and signed metadata age; over 30 days reports stale.
`sys update install` verifies/downloads the channel host and changed guests, writes the other slot
and offers reboot. Root equivalent: `sudo fetch-release`; check only reports/refreshes evidence.
On online installs, Overview's Security / Updates card degrades two days after the last update check. Installs without online updates show DEGRADED until `sys update check` runs once after each install or USB update.
[Failures](RECOVERY.md#12-an-online-update-fails).

USB: copy latest/latest.sig, manifest/manifest.sig, slot.img, both release .efi files, guests/,
guests.manifest/guests.manifest.sig and any remmina.manifest/remmina.manifest.sig to FAT32/exFAT.
Once guests exist, latest naming guests requires their signed manifest. Approve USB with
`sudo devices list`, `sudo devices allow <number>`, then `sys update usb`. By hand:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo fetch-release usb /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

When upgrading from a client without guest USB delivery, rerun sys update usb after boot with the
same stick. A host-only USB leaves legacy web/admin objects untouched; def/int and tmp --portal need
guest delivery. `slot write` verifies manifest against the embedded key. Unsigned writes need `sudo
env CONVERGENT_UNSIGNED=1 slot write ...`; the menu offers this only without a trusted key. Images
without an embedded release key need USB/unsigned mode for their next update. Host writes require
the booted slot good and a release newer than booted/highest-good. `sudo slot status` shows both.
[Checks/counting](ARCHITECTURE.md#72-update);
[fallback](RECOVERY.md#2-a-new-release-does-not-boot-or-does-not-become-good); [manual
rollback](RECOVERY.md#3-go-back-to-the-previous-release-by-hand).

### Guest updates

```sh
sys update                            # slots; sys update check queries publication
sys guests status                     # guests status: name and state
sys guests update                     # apply pending downloads
sudo guests update fw|wan|svc|browser|def|int|remmina <image-dir>
```

Close browsers/Remmina. After host reboot/bless, apply order is legacy browser migration, svc,
wan, fw, browser, Remmina. Bar: GUESTS / GUESTS failed; retry sys guests update. If the newest host
lacks its guests, sys update install fetches/applies them immediately. Browser updates advance
future tmp/portal images; def/int normally replaces one instance, but migration updates both.

One operation runs at a time. Interrupted browser updates block launches until retried. Replacements
retain state/bookmarks/logins; legacy web/admin names become def/int, without command aliases.
Unused old images prune only after commit and alias release. Staleness starts with update; full
kind updates clear it after recording, def/int leaves browser generation stale. Recording failures
remain pending; next install reuses valid staged data or downloads it.

Manual updates require a good host and closed browsers/Remmina. Keep the release layout:
`$g` is `<release-dir>/guests`, with unpacked images and the signed `guests.manifest`
(or `remmina.manifest`) and its `.sig` in `<release-dir>`. The manifest must match the
booted release; its identity binds the checksums and supplied Incus profiles.
For an unsigned build you trust locally, append `--trusted-local` to bypass authentication.

```sh
sudo guests update fw  $g/fw      # fw2, failover, fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
sudo guests update remmina $g/remmina
```

[Snapshots/rollback](ARCHITECTURE.md#72-update).

### Work VMs

Select owner NIC-only profiles `work-dom-dev-a`, `work-dom-dev-b`, `work-dom-jhn-a`, or
`work-dom-jhn-b` (configured family names); supply disks/resources separately. Owner shares managed
networks, retaining its own profiles. Use DHCP or static .1–.48, /26, gateway/DNS .62 in the
[selected prefix](ARCHITECTURE.md#41-addressing); Incus NIC settings do not configure the guest OS.
Work guests can communicate within their own VLAN; routing to other work VLANs is blocked, including
within the same family. System segments are blocked. Internet works; home-LAN access requires
baked-in canonical RFC1918 prefixes. Topology updates stop both firewalls; failure
restores both old images. Hash mismatch keeps work access closed.

Host shutdown preserves ephemeral work guests. Running work guests with default or `last-state`
autostart return at the next boot.

## Power and locking

Idle locks after idle_lock_minutes (default ten); display-off follows one minute later. Lid/manual
locking still works while NL pauses idle actions. `sys power lock` locks now. Privileged Sway idle
inhibition prevents browsers suppressing the lock.

`sys power ac` / `sys power battery` (`sudo power [ac|battery]`) applies CPU preference/cap now;
boot and AC events also apply it. AC uses balance_performance, battery power, both with cpu_cap_khz
(default none). Manual choice lasts until the next source event. Only changes/failures log.
`sys power status` reports the applied profile and sensors.

`sys power charge 80` sets end 80%, start 75% where supported; range 55–100. `sys power charge off`
(default) restores 100/95. Dell charge_types selects Custom/Standard. Limits do not discharge an
already-fuller battery. `sys power thermal quiet|balanced|performance` selects an offered firmware
profile; firmware controls fans. No override until selected.

Charge/thermal choices in `/var/lib/convergent/power/` persist across boot/AC events and follow
slot var snapshots. Missing controls are skipped; status shows unsupported thresholds
and available choices. [Tuning constraints](ARCHITECTURE.md#112-proposals-not-enabled).
