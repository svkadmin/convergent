# Using Convergent

Tools live in `/usr/local/sbin`. `sys`, `browser` and the bar run as owner; `sys` uses `sudo` as
needed. Others (`slot`, `fetch-release`, `guests`, `check`, `devices`, `backup`, `account`, …) need
`sudo` (password, 5-minute ticket).

Contents: [Coming from Arch](#coming-from-arch) · [Keys](#keys) · [The sys tool](#the-sys-tool) ·
[Browsers](#browsers) · [Wi-Fi](#wi-fi) · [Captive portals](#captive-portals) · [Devices](#devices)
· [DNS](#dns-blocklist-and-own-records) · [Backups](#backups) ·
[Health and alerts](#health-and-alerts) · [The bar](#the-bar) ·
[Releases and guests](#releases-and-guests) · [Power and locking](#power-and-locking). When
something breaks: [RECOVERY.md](RECOVERY.md).

## Install

Input: `config.example.yaml`, selected by `CONVERGENT_CONFIG` on the builder or
`convergent-install --config /path/config.yaml /path/release` on the UEFI-booted stick. No secrets,
comments included. The installer saves the validated copy at `/var/lib/convergent/config.yaml`;
nothing reads it at runtime. Password hashes are no longer accepted: enter owner password and LUKS
passphrase at the prompts (or on stdin, in that order, for `build/stick`).

```yaml
install:
  disk: auto
  state_size: auto
  swap: none
```

`disk: auto` needs exactly one internal NVMe or SATA/ATA SSD, excluding boot, removable and hotplug
disks. Zero or several candidates is an error; pick a whole disk with `/dev/disk/by-id/<id>`. The
installer shows the disk and still requires the path or serial erase confirmation. Refused: mounted
disks, active swap, holders, boot disk, read-only targets. `build/stick` uses its own loop image
regardless of this key.

`state_size`: `auto`; an integer percentage from `1%` to `100%` of space left after release ESP,
slots and alignment; or whole GiB, such as `64GiB` (32..999999). Auto takes the rest and grows when
copied to a larger disk. Percent and GiB sizes keep their installed size. Release fixes ESP at 1
GiB, each A/B slot at 8 GiB. GPT, LUKS2 and Btrfs mandatory. `esp_mib`, `slot_mib` and
`state_max_gib` no longer accepted.

`swap`: `none`, `zram:4GiB` or `state:8GiB`; whole sizes 1..1024 GiB. Zram size is its uncompressed
capacity. State swap is a file in a separate Btrfs subvolume inside LUKS2, outside release
snapshots. No hibernation. OpenRC activates the generated swap setting; editing the reference YAML
does nothing.

Stick build and install validate every key and check capacity before partitioning. State leaves at
least 32 GiB for data plus disk swap; build media needs 12 GiB plus disk swap. With `build/stick`,
sizing applies to the image itself; raise `image_size` or its positional size argument for larger
state or swap. The default 30 GiB image fits auto state with no swap or zram. Even 1 GiB of state
swap needs a larger image.

## Coming from Arch

| On Arch | Here |
|---|---|
| `pacman -Syu` | No package manager on the laptop. An update is a whole signed release: `sys update install` downloads and writes it (README, Update) |
| `systemctl status`, `restart` | `rc-status -a` lists all runlevels; `sudo rc-service <name> status`, `restart` |
| `systemctl enable` | Services are fixed in the release |
| `journalctl` | `/var/log/messages` (warnings and up; `sys logs`), `/var/log/incus/`, Grafana; see RECOVERY 8 |
| Editing `/etc` | Read-only. Only accounts, `machine-id` and `/etc/usbguard/rules.conf` are kept; other changes come with a release |
| `passwd` | `sys security password` (or `sudo account password [user]`). Plain `passwd` cannot replace `/etc/shadow`, a bind mount |
| Your files | `/home` is on the encrypted state volume and survives updates |
| `incus` | Guests use `guests`; owner's own Incus project not set up yet |
| A network manager | Wi-Fi is in `sys wifi`; the radio lives in the `wan` VM |

Firewalls run OpenBSD. Daily use needs no firewall login. To look:
`sudo ssh -F /etc/convergent/ssh_config fw1` gives a shell (`pfctl -sr` shows rules; `ifconfig carp`
shows failover state).

## Keys

Sway's stock bindings, plus the Convergent ones below. Super is the Windows key.

Stock Sway, foot, mako and swaylock on a black background and bar. Owners can override each in
`~/.config/`.

| Key | Does |
|---|---|
| Super+m | `sys`: menu of areas and actions, in a terminal |
| Super+a | one `sys` action by name, in its own terminal |
| Super+d | an app by name: Browser_default, Browser_internal, Browser_temporary, Settings, Screenshot, Files, Notes, Foot |
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
Enter, or no answer restores the previous layout. Dock and undock need no key.

Files (Super+d) opens Midnight Commander in foot, with its internal editor (`mcedit`) and the
`modarin256-defbg` dark skin on the terminal background. Notes opens Vim's directory list in foot at
`~/Documents/notes`, creating it if needed. Keep notes as plain `.md`: `:e name.md` opens one, `:w`
saves.

## The sys tool

`sys AREA [ACTION] [ARGS]`. First action in each row is the default. An unknown second word becomes
an argument to that default (`sys backup /mnt/x proj` works; `sys wifi foo` is a usage error).
Missing arguments are prompted for; partial lists are usage errors. `sys help` lists actions and
aliases. `*` marks actions that ask for `yes` in the terminal (default No).

`sys` (Super+m) uses fzf: the menu left; right, a Gentoo system dashboard above the highlighted row's
status and commands, in terminal colours with a blue highlight. The dashboard refreshes on menu entry;
narrow panes hide the logo. Enter opens or runs; Esc goes back; typing filters. Alt+Enter runs what
was typed (`area action args`, or `action args` inside an area).

Wi-Fi picker: type to filter, Enter selects the highlighted SSID, Esc cancels, Ctrl+u clears the
filter, Alt+Up/Down scrolls its status. Hidden SSIDs: `sys wifi hidden` and a typed name. Alt+Enter
does not join an unscanned name.

| Area (alias) | Actions, default first |
|---|---|
| `wifi` | `status`, `scan`, `connect [SSID]`, `hidden [SSID]`, `disconnect`, `forget [SSID]` *, `test` |
| `portal` | `status`, `on`, `off` |
| `wired` | `status`, `attach [VENDOR:PRODUCT SERIAL]` *, `remove` * |
| `dns` | `list`, `add [NAME IPv4]` *, `remove [NAME]` *, `allow [DOMAIN]` *, `unallow [DOMAIN]` *, `push` |
| `firewall` (`fw`) | `status`, `rebuild` *, `maintenance` *, `undo` * |
| `bluetooth` (`bt`) | `status`, `on`, `off`, `scan`, `pair [MAC]`, `connect [MAC]`, `disconnect [MAC]`, `forget [MAC]` * (device picker without MAC) |
| `usb` | `status`, `allow N\|ID` *, `enrol` *, `review`, `revoke RULE` * |
| `audio` | `status`, `out ID`, `vol N` (0–150), `mute`, `mic on\|off`, `micmute` |
| `camera` | `status`, `on`, `off` |
| `display` (`disp`) | `status`, `bright N\|+N\|-N`, `set OUTPUT mode\|scale\|position\|enable\|disable [VALUE]` (15-second preview), `save`, `reset` *, `watch` (session hook) |
| `keyboard` (`kb`) | `status`, `set LAYOUTS` (e.g. `us,hu`), `next` |
| `touchpad` | `status`, `set OPTION VALUE` (apply and save; options below) |
| `screenshot` (`shot`) | `area`, `screen` (save to `~/Pictures/screenshots` and copy to clipboard) |
| `browser` (`br`) | `status`, `def`, `tmp`, `int` |
| `security` (`sec`) | `status`, `alerts` (`sys alerts`), `events`, `check`, `report`, `password` |
| `update` (`up`) | `status`, `check`, `install` *, `usb [MOUNTPOINT\|DEVICE]` * |
| `guests` | `status`, `setup`, `update` |
| `power` | `status`, `ac`, `battery`, `charge off\|55-100`, `thermal quiet\|balanced\|performance`, `lock`, `logout` *, `reboot` *, `off` * |
| `backup` | `run [MOUNTPOINT PROJECT]` |
| `logs` | `host` (`/var/log/messages`), `services` (`rc-status -a`) |
| `selftest` | `run` |

DNS edits, wired assignment and firewall maintenance ask inside the action, after showing the change
or checking health. Not built into `sys`: owner guest management and printing.

Screen too big: `sys display set eDP-1 scale 1.3`, confirm with `yes`, then `sys display save`. Save
once docked and once undocked. Profiles key on the connected make/model/serial set, including
disabled panels; connector names and order can change. Profiles apply at login and on any set
change. Unrecognised sets enable connected screens at preferred modes (`display_scale` if configured,
otherwise laptop panel scale 1.3, external scale 1),
unless an older `~/.config/sway/config.d/outputs` file applies, which stays in charge until the
first save. Identical identities cannot be saved, so `save` refuses them. `reset` clears only the
current set's profile, not the live layout. Profiles live as JSON in `~/.config/convergent/displays/`;
saving retires the old outputs file. Saved profiles take precedence over `display_scale`.

Touchpad: `sys touchpad set` prompts, or takes an option and value
(`sys touchpad set pointer_accel 0.3`). Settings are validated, apply live to all touchpads and save to
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
`screenshot-YYYYmmdd-HHMMSS.png` names. After saving and copying, mako shows **Screenshot saved**
and the file name for 3 seconds, in its usual look. A repeated timestamp is refused, not
overwritten.

Leave the microphone enabled in firmware. Each Sway login waits for PipeWire's default source and
mutes it; `sys audio mic on|off` changes that. The bar shows orange `MIC` while unmuted (refreshed
every 5 s), or grey `MIC?` if unknown. That means permission to record, not recording. Config
reloads do not reset mute.

## Browsers

```sh
browser def|tmp|int [url]
browser tmp --portal [url]
```

Run as owner in the Sway session; no password. `sys browser def|tmp|int` (or the menu) opens one
without a URL; `sys browser` lists running ones. Only HTTP and HTTPS URLs are accepted. Each browser
is Chromium in its own container, with a restricted Wayland socket and playback-only audio. Window
title starts with `[role]`. Chromium's default appearance is kept.

Works when a window titled `[def] …` opens and the bar shows `BR:1`. If Super+b or Super+Shift+t
fails, a line at the top gives the reason. Full output: `$XDG_RUNTIME_DIR/browser-def.*.log` or
`$XDG_RUNTIME_DIR/browser-tmp.*.log`, one file per launch.

| Role | For | State |
|---|---|---|
| def | everyday browsing | profile and downloads kept in a 4 GiB volume |
| tmp | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| tmp --portal | captive portals; opens `http://neverssl.com/` unless given a URL | container deleted on close; owns portal mode |
| int | Grafana; Incus after a session unlock | profile kept in a 512 MiB volume; UI key lives only in session memory |

A second def or int start raises the open window. Portal mode refuses one; normal tmp runs many at
once. Downloads stay in the container; no action moves a file out. Policies: DNS-over-HTTPS off, no
sync, no password manager, no telemetry. Int and both tmp modes allow no extensions. The int
browser starts Grafana in svc and stops it on close. Log in as `owner`; password:
`sudo cat /var/lib/convergent/guests/tls/admin-password`. A handler that sends links from other
programs to `tmp` is not built.

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

## Wi-Fi

The radio belongs to wan; `sys wifi` runs its commands there over SSH. wan roams between known
networks.

`sys wifi connect` offers scanned SSIDs in the picker, with security and signal, then asks
`Passphrase (empty for a known or open network):`. The passphrase stays in wan.
`sys wifi connect 'SSID with spaces'` skips the picker. Authentication and no-signal failures
include guidance from wan's reply. A successful association with no IPv4 lease reports DHCP failure.
After scan initiation succeeds, completion is polled for up to 15 seconds; initiation/result
retrieval have separate timeouts, and command failures propagate.

Hidden networks: `sys wifi hidden`. An upstream network overlapping 100.80.0.0/16 is refused and
raises UpstreamOverlap. After moving a refused wired adapter to a safe network, retry DHCP with
`sudo ssh -F /etc/convergent/ssh_config wan 'check retry'`. That retries only configured wired
uplinks and rechecks the lease. The overlap latch clears only after a safe lease arrives.

## Captive portals

`sys portal on` starts tmp in portal mode, which owns the mode until the browser closes,
`sys portal off`, or 30 minutes. It opens two pf rules on both firewalls and wan's DNS pass-through,
for the portal browser only. Portal DNS uses the selected default-route uplink's first nameserver;
it must be IPv4 outside 100.80.0.0/16. Later usable nameservers are not tried. If that nameserver is
unusable, `sys portal on` refuses and closes everything again. The bar shows `PORTAL`. Works over
Wi-Fi or wired.
`browser tmp --portal [url]` is the same. A new launch first closes stale rules on all three guests
and refuses to open if closure fails. Every minute, cron detects abandoned browser sessions and
retries incomplete closure. `sys portal status` gives the reason (active, timeout, browser closed,
interrupted, or closure pending) and each guest's state.

```sh
sudo portal on [A.B.C.D/LEN]   # diagnostic opening; without a browser it expires after a minute
sudo portal off                # if a side cannot be closed, retries every minute
sudo portal status             # wan, fw1, fw2; verdict on, off, mixed or unknown
```

## Devices

USBGuard denies devices without an allowance. Attach only trusted devices, then run `sys usb enrol`.
Review each named device (hubs included). Type `yes` for each one you trust, then confirm the full
replacement; nothing is saved before that. Enrol replaces the existing policy, including any
block-all list or the older installer's input/storage/hub class policy. Declined devices stay
blocked. No blanket approval of attached devices.

`sys usb review` lists saved allow and block rules by name, including unplugged devices, and
decisions for attached ones. `sys usb revoke RULE` takes an allowed **rule number** from that
review, removes it, and adds a device-specific deny over overlapping old allowances. Enrol first if
the only existing allowance is a broad class rule. Enrol and revoke restart USBGuard now; revoking
an input device or storage can disconnect it. `sys usb status` shows blocked USB and unauthorized
Thunderbolt devices. `sys usb allow N|ID` still takes an attached USB **device number** or
Thunderbolt ID.

`sys bluetooth` shows power and known devices. Bluetooth stays off at boot; run `sys bluetooth on`
first. `sys bluetooth pair` scans for 10 seconds, then lists discovered and known devices by MAC and
name. `connect`, `disconnect` and `forget` use the current list; `sys bluetooth scan` refreshes it.
The picker is fzf in a terminal, or bemenu outside one. Escape cancels without changing a device.
Explicit MAC arguments work and are validated. `forget` asks for `yes` in the terminal before the
picker opens. By hand:

```sh
sudo devices list
sudo devices allow <number>    # USB, permanent; warns for keyboards, storage, network
sudo devices allow tb <id>     # Thunderbolt PCIe tunnel, until unplugged
```

Both ask for a typed `yes`. USB approvals go to `/etc/usbguard/rules.conf`.

USB serial adapter: approve once with `sys usb allow NUMBER` (from `sys usb status`), then run
`tio -b 115200 /dev/ttyUSB0`, with the baud rate set to match the console. CDC ACM adapters use
`/dev/ttyACM0`. Exit with Ctrl+t then q. The owner gets Gentoo's `dialout` group at installation and
on the first boot of an updated image.

Dell dock Realtek Ethernet: allow its USBGuard device number first. Run `sys wired status` for its
serial, then `sys wired attach 0bda:8153 SERIAL` (or omit the arguments for prompts). Confirm the
exact identity shown. The `wired-uplink` Incus USB device persists on wan and matches that vendor,
product and serial on replug; another adapter does not qualify. An empty or ambiguous serial is
refused. `sys wired remove` drops the role, including automatic attachment, but keeps the USBGuard
approval. Unplugging alone keeps the role. The host never runs DHCP or assigns addresses to the NIC.
Wan uses it as `eth1`, prefers its wired default route, and retries DHCP on replug at its next check
(within a minute).

Camera starts disabled. `sys camera on` saves the choice and loads the driver now. `sys camera off`
saves disabled first, then unloads it. If an application holds the driver, close it and retry `off`;
unloading is never forced. `sys camera status` shows the saved choice and whether the video core is
loaded. `CAM` in the bar means enabled, not necessarily recording; `CAM!` means a driver stays
loaded despite the disabled choice. The choice survives reboot in
`/var/lib/convergent/devices/camera` and follows the release's state snapshot on update or rollback.
USB cameras need their own USBGuard allowance too. Meeting compartments and screen sharing are not
in this release.

## DNS: blocklist and own records

The firewalls resolve all DNS. Cron downloads the blocklist weekly (URL and limits in
`/etc/convergent/dns.conf`), validates it and pushes it to both firewalls; a failed push rolls back
on both. Owner files on the laptop:

- `/var/lib/convergent/dns/allow`: domains exempt from the blocklist, one per line, `#` comments.
- `/var/lib/convergent/dns/records`: Unbound `local-data` and `local-data-ptr` lines.

Use `sys dns list`, then `sys dns add printer.home.arpa 192.168.1.50` or
`sys dns remove printer.home.arpa`. The editor manages IPv4 A records; other types stay in the owner
file. Names are lowercased. Duplicate names, invalid addresses and built-in name conflicts are
refused. Removing a name with non-A records needs an edit to the owner file. A local DNS record does
not grant firewall access to that address.

`sys dns allow example.org` adds a blocklist exception for that name and its subdomains;
`sys dns unallow example.org` removes it. Each edit shows a diff and needs `yes` before it applies
to both firewalls. Failed or interrupted edits restore the previous owner files and firewall data.
If a firewall is unreachable, recovery stays pending until a push reaches both. Run `sudo dns-push`
once if there is no stored blocklist. `sys dns push` reapplies the current files with the stored
blocklist. `sys dns list` shows the last successful push time in UTC.

```sh
sudo dns-push          # download, validate, push the blocklist and records
sudo dns-push local    # push the stored blocklist with the current files
```

## Firewall maintenance

`sys firewall status` (or `sys fw`) shows fw1 and fw2 CARP roles for transit, host, svc, web, admin
and guests, PF state counts, Unbound status, and the last successful DNS push to both. Unreachable
guests and pending DNS recovery are shown explicitly.

`sys fw maintenance` checks the six-segment MASTER/BACKUP pair, PF, pfsync with defer, Unbound and a
local DNS answer before it asks to demote the master. It verifies that the peer owns all six
segments. A failed handover is undone; an interrupted action keeps its recovery information.

After maintenance, run `sys fw undo`. Both firewalls must be healthy; normal fw1-master / fw2-backup
roles are checked after the demotion is released. Finish maintenance before guest updates. If undo
cannot reach a firewall, restore management access or rebuild that node, then retry undo. Remote
work may outlive an SSH timeout; retry undo after it finishes. Do not remove
`/var/run/convergent-maintenance.lock`: it is a persistent advisory lock file, and its recorded PID
alone does not show whether the lock is held. A firewall reboot clears `/var/run`; the next mutation
recreates the file. Reboot firewalls still using the old symlink lock before using this version.

`sys firewall rebuild fw1|fw2` (root command: `guests rebuild fw1|fw2`) recreates a broken firewall
from the installed guest release and laptop seed. The peer must be healthy. Rebuild stops the target
if needed, then waits for the peer to be MASTER on all six segments. Finish guest updates and
handoffs first. Maintenance may name the target; run `sys fw undo` after rebuilding it. Rebuild
waits for guest checks and DNS pushes; browsers may stay open. It checks the replacement, restores
fw1 MASTER / fw2 BACKUP, and pushes stored DNS data. After an interruption, repeat the same command
to resume its replacement journal.

## Backups

```sh
sudo backup [<mountpoint> <owner-project>]
```

`sys backup [MOUNTPOINT PROJECT]` runs it. Without arguments it asks
`Mounted encrypted external disk:` and `Owner Incus project:`. It needs an external USB disk with
LUKS, unlocked and mounted at a root-owned directory (not the laptop's own disk), and an Incus
project for the owner's guests (not `default`; none is created yet). It writes
`convergent-backups/backup-<UTC>`: a snapshot of `/home`, the writable `/etc` files, exports of the
owner's containers and profiles, and custom filesystem/ISO volumes of both projects. It reads the
backup back and keeps three. VM instances, custom block volumes, system guest instances and
`/var/lib/convergent` are excluded (see `EXCLUDED` in the backup). Unmount and close
the disk before unplugging. Restore steps: [RECOVERY 11](RECOVERY.md#11-start-over).

## Health and alerts

With Secure Boot off, expect SecureBootNotVerified and CheckerFailed; without an accepted baseline,
also CollectorBroken. FirewallRulesetDrift needs an expected hash and reports only a mismatch.
Inspect the named alerts rather than inferring faults from the counts. Timing:
[ARCHITECTURE 8](ARCHITECTURE.md#8-observability).

`sys alerts` (also `sys security alerts`) lists firing vmalert alerts: severity, name, summary or
description, and the API's active-since time. Left-clicking the bar's alert counts opens the same
list. An unavailable or invalid response reports an error, not an empty list.

Open **Browser_internal** (`sys browser int`) for Overview, Network, Guests and Security. Overview
shows the path, alerts, collector freshness, host and guests on the first screen. Other pages share
its navigation. Guests has project and instance selectors. Current-state tables show one row per
item; graphs show history. CARP role-change annotations stay off until toggled on. Log panels show
actionable records; **Explore · all logs** adds routine audit and full kernel traces. A dash means
no data. Each panel names its source; each footer lists what is not collected. Battery is always
0–100%.

Security's recent-events list covers successful and failed logins, sudo commands and password
failures, USBGuard decisions, AppArmor denials, firewall takeovers, guest updates and failures, and
host update, bless and fallback records. It shows the latest 50 records in the selected range. Each
record's host comes from the connection that delivered it; app name and message are the sender's
claims.

`sys security events` works without svc. It shows up to 100 matches from the last 5000 lines of each
current host log (`/var/log/messages`, then `/var/log/audit/audit.log`), with source and original
timestamp. Files are not merged by time; rotated logs are not scanned. Missing logs are reported.
Local firewall events cover maintenance and changes the minute status probe sees; brief transitions
between probes need the firewall logs in Grafana. Fallback records identify an older boot with an
exhausted newer UKI. Audit and PAM may describe the same login.

Host checks and svc alert evaluation: [ARCHITECTURE 8](ARCHITECTURE.md#8-observability).

```sh
sys security check                    # run the checker now (sudo check); report in /var/lib/convergent/check/last
sys security report                   # read the last report
sys security events                   # recent local security events, even without svc
sudo check accept <release-dir>       # accept a trusted release as the baseline (once Secure Boot is on)
sudo check accept-fw <guest-dir>/fw   # accept new firewall hashes after a firewall update (once Secure Boot is on)
```

The checker fails until a baseline is accepted (`<release-dir>` holds `manifest` and
`guests/fw/fw{1,2}.{pf,rules}.sha256`), and while Secure Boot is off. A baseline from an earlier
release lacks the temporary browser's profile record: accept again. Acceptance needs Secure Boot on
and out of Setup Mode. `check` does not verify the manifest's signature, so check the release
yourself before accepting it.

`sys selftest` checks this boot (sudo once, at the start) and writes a report to
`~/selftest-YYYYmmdd-HHMMSS.txt`. Each check prints PASS, FAIL or SKIP with its detail. Every check
has a time limit, so the run cannot hang.

`sys debug` (also Logs → debug) downloads the developer's signed diagnostic, shows its purpose and
expiry, and asks before running it as root. It refuses expired or already-run requests. Runs stop
after five minutes; output is capped at 8 MiB, signed with the laptop's own key and sent encrypted to
the developer after a second yes. A root-only plaintext copy stays at `/var/lib/convergent/debug/<id>.txt`;
the path is printed first, so `sudo less` shows it before anything is sent. Only `CHANNEL=beta` builds carry it; stable builds never
do. A failed diagnostic reports its script exit status, even at the cap. Timeout reports 124 (137 if
it needs a forced kill). `sudo debug key` prints the laptop's public key; pin it once on the builder
as `/etc/convergent/keys/debug-laptop.pub`. Beta-only `build/debug send <script-file> <purpose>`
embeds a 24-hour upload link for one random output key; `build/debug fetch [id]` verifies the
laptop's signature and the request binding, then decrypts, and refuses forged, replayed or corrupt
results.

Crash records and panic recovery:
[RECOVERY 13](RECOVERY.md#13-a-kernel-panic-or-crashrecorded-alert).

Host cron and anacron have mail disabled; their jobs and logging still run.

## The bar

Refreshed every second. Blocks are shown here separated by `|`; the bar draws its own separators:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx 0.8 rx 12.4 Mb/s
WLAN:home--WAN--[FW1 FW2]--laptop--SVC--BR:2 | rel 0.1.0 good | NL | 0 1 0 | PORTAL
US | UP 3d 03:41 | Tue 04/08 15:33:02 | BAT 87% -
```

| Block | Shows | Look or fix with |
|---|---|---|
| `CPU` | busy percent, lowest-highest core clock, package/hottest temperature (every 5 s); `-` if missing | `sys power status` lists every sensor |
| `RAM`, `SWP` | used/total GiB; RAM is memory in use (`MemTotal - MemAvailable`, so reclaimable cache does not count) minus what guests hold (`check status` sums their cgroups without file cache and VM processes every minute) | Grafana, Guests |
| `NET` | transmit/receive Mb/s on the default-route interface (route refreshed every 5 s) | `sys wifi test` |
| Topology | uplink, wan, both firewalls, svc and browsers (below) | `sys guests status`; RECOVERY 5, 6 |
| `rel` | booted semantic version (release ID on older images); grey `good` if the release passed its checks this boot, else red `UNBLESSED` | `sys update` |
| `NL` | click to pause or resume the idle lock (orange while paused); `NL!` (red): swayidle missing | `sys power lock` |
| `MIC` | default microphone unmuted (orange); hidden when muted; `MIC?` (grey) if unknown; every 5 s | `sys audio mic off` / `on` |
| Alerts | firing alerts as three counters: critical (red), warning (orange), info (white); `? ? ?` (grey) if svc cannot be read, including during SETUP until svc is up; every 30 s | click for the firing list in foot, or `sys alerts`; history in Grafana: `sys browser int` |
| `PORTAL` | portal mode on (orange) | `sys portal off` |
| `CAM`, `CAM!` | camera enabled, or driver still loaded after disabling (orange); not a recording indicator | `sys camera status`, `sys camera off` |
| `SETUP` | guests being created (orange); `SETUP failed` (red) | `sys guests setup` |
| `GUESTS` | downloaded guests being applied (orange); `GUESTS failed` (red) | `sys guests update` |
| layout, `UP`, clock | keyboard layout (every 5 s), uptime, local date and time | `sys keyboard next` |
| `BAT` | capacity; `+` charging, `-` discharging (orange below 30 %, red below 15 %); `AC BAT` on mains but not charging (full or at charge limit); `AC` without a battery | `sys power status` |

Topology starts with the uplink: `WLAN:<network>` (green connected, red with no network, grey when
wan does not answer; names over 16 characters are cut) or `ETH` for a passed-through wired NIC.
`WAN` is green with an uplink, orange without one, red when wan is down. Each firewall is bold
bright green as CARP master, dim green as standby, orange when its CARP interfaces disagree, red
when down. `SVC` is green or red; the host name is green. `BR:n` counts running browser containers
(grey at zero). Cron refreshes it every minute; if it is older than three minutes, it turns grey.
The idle-lock pause is the file `$XDG_RUNTIME_DIR/nolock`; the lid lock still works.

## Releases and guests

Channels and promotion: [BUILD, Status](BUILD.md#status).

`sys update status` and `slot status` show the booted version and timestamp release ID; checker and
selftest reports include both. The timestamp still controls slot ordering.

```sh
sys update                           # release slots; `sys update check` asks whether a newer one is published
sys guests status                     # one line per instance: name and state (guests status)
sys guests update                     # apply pending downloaded guests now
sudo guests update fw|wan|svc|browser|def|int <image-dir>
```

Online releases carry guests; only changed guests download with `sys update install`. After reboot
and marking the host good, they apply in order: svc, wan, fw, browser. Nothing applies while a
browser is open. The bar shows GUESTS while applying and GUESTS failed on failure. To retry a
pending browser update, close browsers and run `sys guests update`. Updating `browser` also moves
the image for future tmp instances, including portal mode. If the booted release is already newest
but its guests were not installed (host-only update), `sys update install` downloads and applies
them at once. `def` or `int` normally replaces only that instance; a role migration updates both.
One guest operation runs at a time. Host updates: [README, Update](README.md#update). An interrupted
browser update blocks launches until the guest update is retried. Superseded guest images are
deleted once an update commits and no alias uses them. A guest is marked stale from the start of its
update. Full guest-kind updates clear staleness after recording; def/int updates leave the browser
generation stale until a full browser update. Recording failure leaves the guest needing update;
the next `sys update install` reuses valid staged payloads or downloads them.

The first full browser update renames existing web/admin instances and state volumes to def/int,
keeping bookmarks and logins. Close all browsers first. An interrupted migration resumes on the next
browser update. The old role names are not command aliases.

Guests can also update manually, on a slot already marked good, with every browser closed. Copy the
new guest images to the laptop; `$g` is that directory. Backup and rollback design:
[ARCHITECTURE 7.2](ARCHITECTURE.md#72-update).

```sh
sudo guests update fw  $g/fw      # fw2 first, then failover, then fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
```

If you added a root crontab as a stopgap for the v8/v9 cron bug, remove it with `sudo crontab -r`
after the first v10 boot. Otherwise those jobs run twice.

## Power and locking

- The screen locks after 10 minutes idle by default (`idle_lock_minutes`) and when the lid closes
  (swayidle, swaylock). Display-off follows `idle_lock_minutes + 1` minutes of inactivity.
  `sys power lock` locks now. NL pauses only idle locking and display-off; manual and lid locking
  still work.
- `power` sets the CPU energy preference and an optional clock cap for AC or battery (none by
  default; `cpu_cap_khz`). It runs at boot and on AC adapter events. By hand: `sys power ac` or
  `sys power battery` (`sudo power [ac|battery]`). Repeated events with no setting change are
  silent; changes and failures are logged. The bar shows the applied profile, including a manual
  override until the next plug event. AC uses `balance_performance`, battery uses `power`; both keep
  the configured clock cap.
- `sys power charge 80` stops charging at 80 %, with a start threshold of 75 % where supported.
  Valid limits are 55-100. `sys power charge off` (the default) allows full charging: end 100 %,
  start 95 %. Where Dell exposes `charge_types`, a limit selects Custom mode and off selects
  Standard mode. The limit does not discharge a battery already above it.
- `sys power thermal quiet|balanced|performance` selects a profile the firmware offers; firmware
  still controls fan speeds. No thermal override applies until one is selected. Charge and thermal
  choices persist in `/var/lib/convergent/power/`, are restored at boot and AC events, and follow
  the release's state snapshot on update or rollback. Missing sysfs controls are optional: actions
  report unsupported, and other power controls keep working. `sys power status` shows the actual
  thresholds, thermal profile and available choices. The resource review and unimplemented tuning
  proposals are in ARCHITECTURE section 11.
