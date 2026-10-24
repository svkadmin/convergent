# Using Convergent

Tools live in `/usr/local/sbin`. `sys`, `browser` and the bar run as the owner (`sys` calls `sudo`
where needed). The others (`slot`, `fetch-release`, `guests`, `check`, `devices`, `backup`,
`account`, …) need `sudo` (password, 5-minute ticket).

Contents: [Coming from Arch](#coming-from-arch) · [Keys](#keys) · [The sys tool](#the-sys-tool) ·
[Browsers](#browsers) · [Wi-Fi](#wi-fi) · [Captive portals](#captive-portals) ·
[Devices](#devices) · [DNS](#dns-blocklist-and-own-records) · [Backups](#backups) ·
[Health and alerts](#health-and-alerts) · [The bar](#the-bar) ·
[Releases and guests](#releases-and-guests) · [Power and locking](#power-and-locking).
When something breaks: [RECOVERY.md](RECOVERY.md).

## Install

Use `config.example.yaml` as the build/install input, selected with `CONVERGENT_CONFIG` on
the builder or `convergent-install --config /path/config.yaml /path/release` on the UEFI-booted
stick. It contains no secrets, including in comments. The installer saves the validated copy
at `/var/lib/convergent/config.yaml` for reference; nothing reads that YAML at runtime.
Password hashes are no longer accepted: enter the owner password and LUKS passphrase at the
prompts (or on stdin, in that order, for `build/stick`).

```yaml
install:
  disk: auto
  state_size: auto
  swap: none
```

`disk: auto` requires exactly one internal NVMe or SATA/ATA SSD, excluding the boot disk,
removable and hotplug devices. Zero or multiple candidates is an error; select a whole disk
with `/dev/disk/by-id/<id>` instead. The installer shows the selected disk and still requires
the path or serial erase confirmation. Mounted disks, active swap, holders, the boot disk and
read-only targets are refused. `build/stick` uses its own loop image regardless of this key.

`state_size` accepts `auto`, an integer `1%` through `100%` of available space after the release
ESP, slots and alignment, or whole GiB such as `64GiB` (32..999999 GiB). Auto consumes the
remainder and grows when copied to a larger disk; percentage and GiB selections stay at their
installed size. The release fixes the ESP at 1 GiB and each A/B slot at 8 GiB. GPT, LUKS2 and
Btrfs stay mandatory; `esp_mib`, `slot_mib` and `state_max_gib` are no longer accepted.

`swap` accepts `none`, `zram:4GiB` or `state:8GiB`, with whole sizes 1..1024 GiB. Zram's size
is its uncompressed capacity. State swap is a file in a separate Btrfs subvolume inside LUKS2,
outside release snapshots. There is no hibernation. OpenRC activates the generated swap setting;
editing the reference YAML has no effect.

Both stick build and install validate every key and check capacity before partitioning.
State must leave at least 32 GiB for data, plus disk swap; build media needs at least 12 GiB
plus disk swap. With `build/stick`, sizing applies to the image itself: increase `image_size`
or its positional size argument for larger state/swap requests. The default 30 GiB image fits
auto state with no swap or zram; even 1 GiB of state swap needs a larger image.

## Coming from Arch

| On Arch | Here |
|---|---|
| `pacman -Syu` | No package manager on the laptop. An update is a whole new signed release: `sys update install` downloads and writes it (README, Update) |
| `systemctl status`, `restart` | `rc-status -a` lists all runlevels; `sudo rc-service <name> status`, `restart` |
| `systemctl enable` | Services are fixed in the release |
| `journalctl` | `/var/log/messages` (warnings and up; `sys logs`), `/var/log/incus/`, Grafana; see RECOVERY 8 |
| Editing `/etc` | `/etc` is read-only. Only accounts, `machine-id` and `/etc/usbguard/rules.conf` are kept; other changes come with a release |
| `passwd` | `sys security password` (or `sudo account password [user]`); plain `passwd` cannot replace `/etc/shadow`, which is a bind mount |
| Your files | `/home` is on the encrypted state volume and survives updates |
| `incus` | Guests are managed with `guests`; the owner's own Incus project is not set up yet |
| A network manager | Wi-Fi is in `sys wifi`; the radio lives in the `wan` VM |

The firewalls run OpenBSD. You do not log in to them for daily use; for a look,
`sudo ssh -F /etc/convergent/ssh_config fw1` gives a shell (`pfctl -sr` shows the rules,
`ifconfig carp` the failover state).

## Keys

Sway's stock bindings, plus the Convergent ones below. Super is the Windows key.

The look is stock Sway, foot, mako and swaylock on a black background and bar; owners can override each in their `~/.config/` directories.

| Key | Does |
|---|---|
| Super+m | `sys`: the menu of areas and actions, in a terminal |
| Super+a | pick one `sys` action by name and run it in its own terminal |
| Super+d | an app by name: Default browser, Temporary browser, Internal dashboards, Settings, Screenshot, Files, Notes, Foot |
| Super+b | default browser (`browser def`) |
| Super+Shift+t | temporary browser (`browser tmp`) |
| Super+Escape | lock the screen now |
| Super+Enter | terminal (foot) |
| Super+Shift+q | close the window |
| Super+1 … 9, Super+Shift+1 … 9 | go to a workspace, move the window there |
| Super+f | fullscreen |
| Super+Shift+c | reload the sway configuration |
| Super+Shift+e | exit sway |
| Print | select an area, save it to `~/Pictures/screenshots` and copy it (Escape cancels) |
| Shift+Print | save and copy the focused screen after 1 s |
| Volume and mute keys | `wpctl` on PipeWire |
| Mic-mute key | toggle the default microphone; while locked, only mute |
| Brightness keys | `sys display bright -5` / `+5` (5 % steps) |

Use Super+a for `usb enrol`, `display save`, `power charge`, `power thermal` and `camera on/off`.
During a display preview, type `yes` then Enter within 15 seconds to keep it; any other answer,
Escape then Enter, or no answer restores the previous layout. Dock/undock needs no key.

Files (Super+d) opens Midnight Commander in foot, with its internal editor (`mcedit`) and
`modarin256-defbg` dark skin using the terminal background. Notes opens Vim's directory list
in `~/Documents/notes`, creating the folder if needed. Keep notes as plain `.md` files;
`:e name.md` opens a note and `:w` saves it.

## The sys tool

Use `sys AREA [ACTION] [ARGS]`; the first action in each row is the default. An unrecognized
second word becomes an argument to that default: `sys backup /mnt/x proj` works;
`sys wifi foo` is a usage error. Missing arguments are prompted for; partial lists are usage
errors. `sys help` lists actions and aliases; `*` marks actions that ask for `yes` in the terminal (default No).

`sys` (Super+m) looks like the Archer menu: the list left, the highlighted row's status and
commands right, terminal colours with a blue highlight. Enter opens or runs, Esc goes back, typing
filters, Alt+Enter runs what was typed (`area action args`, or `action args` inside an area).
Super+a runs one action by name.
The Wi-Fi network picker uses the same keys: type to filter, Enter selects the highlighted
SSID, Esc cancels, Ctrl+u clears the filter, Alt+Up/Down scrolls its status. Hidden SSIDs use
`sys wifi hidden` and a typed name; Alt+Enter does not join an unscanned name.

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

DNS edits, wired assignment and firewall maintenance ask inside the action, after displaying
the proposed change or checking health. Not built in `sys`: owner guest management and printing.

Screen too big: `sys display set eDP-1 scale 1.3`, confirm with `yes`, then `sys display save`.
Save once docked and once undocked. Profiles use the connected set of monitor make/model/serial
identities, including disabled panels; connector names and connection order can change.
The session applies the matching profile at login and whenever the connected set changes.
Unrecognised sets enable connected screens at their preferred modes (laptop panel scale 1.3,
external scale 1), unless an older `~/.config/sway/config.d/outputs` file still applies; it stays in
charge until the first save. Identical identities cannot be saved unambiguously; `save` refuses them.
`reset` removes only the current set's saved profile; it leaves the live layout alone.
Profiles live in `~/.config/convergent/displays/`; saving retires the old
`~/.config/sway/config.d/outputs` file. The `display_scale` build setting still sets the initial
Sway scale before the profile hook runs.

Touchpad: `sys touchpad set` prompts, or pass an option and value directly, for example
`sys touchpad set pointer_accel 0.3`. Settings apply live to all touchpads and are saved in
`~/.config/sway/config.d/touchpad` for every login, independently of keyboard and display settings.
Support depends on the hardware; `sys touchpad status` shows the current libinput settings.

| Option | Values |
|---|---|
| `pointer_accel` | -1 to 1 (pointer speed/sensitivity; 0 is normal) |
| `accel_profile` | `adaptive`, `flat` |
| `tap`, `natural_scroll`, `dwt`, `middle_emulation` | `enabled`, `disabled`; `dwt` disables the touchpad while typing |
| `scroll_method` | `none`, `two_finger`, `edge`, `on_button_down` (uses the device's scroll button) |
| `scroll_factor` | 0–10 (scroll speed multiplier; 1 is normal, 0 stops scrolling) |

Screenshots create the directory if missing and use `screenshot-YYYYmmdd-HHMMSS.png` names.
After saving and copying, mako shows **Screenshot saved** with the file name for 3 seconds,
using its usual look. A second capture with the same timestamp is refused instead of overwriting.

Leave the microphone enabled in firmware. At each Sway login, the session waits for PipeWire's
default source and mutes it. `sys audio mic on` enables it; `sys audio mic off` mutes it.
The bar shows orange `MIC` while the default source is unmuted (refreshed every 5 s), or grey
`MIC?` if its state is unknown. This indicates permission to record, not active recording.
Config reloads do not reset mute. Browser containers still have playback-only audio.

## Browsers

```sh
browser def|tmp|int [url]
browser tmp --portal [url]
```

Run it as the owner in the Sway session; it needs no password. `sys browser def|tmp|int`
(or the menu) opens one without a URL. `sys browser` lists running browsers.
Only HTTP and HTTPS URLs are accepted. Each browser is
Chromium in its own container with a restricted Wayland socket and playback-only audio; the
window title starts with `[role]`.
Browsers use Chromium's own default appearance.

Works when: a window titled `[def] …` opens and the bar shows `BR:1`. A failed start from
Super+b or Super+Shift+t shows a line at the top with the reason; the full output is in
`$XDG_RUNTIME_DIR/browser.log`.

| Role | For | State |
|---|---|---|
| def | everyday browsing | profile and downloads kept in a 4 GiB volume |
| tmp | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| tmp --portal | captive portals; opens `http://neverssl.com/` unless given a URL | container deleted on close; owns portal mode |
| int | Grafana only (`http://100.80.2.10:3000/`) | profile kept in a 512 MiB volume |

A second start of def or int brings the open window forward; portal mode refuses one; normal tmp can run many
at once. Downloads stay in the container; no action moves a file out. Policies: DNS-over-HTTPS off, no sync, no password
manager, no telemetry; int and tmp in portal mode allow no extensions. The int browser starts Grafana in
svc and stops it on close. Log in as `owner` with the password in
`/var/lib/convergent/guests/tls/admin-password` (`sudo cat`). A handler that sends links from
other programs to `tmp` is not built.

The def and tmp browsers use the `web` network segment; int uses `admin`.
Portal mode uses a single tmp container at 100.80.3.11 without a GPU, with HTTP allowed and
capture, extensions and search disabled. Normal tmp browsers use 100.80.3.20–99 and their usual policies.

## Wi-Fi

The radio belongs to wan; `sys wifi` runs the commands in it over SSH.

`sys wifi connect` offers scanned SSIDs in the sys picker, with security and signal strength,
then asks `Passphrase (empty for a known or open network):`; the passphrase stays in wan.
`sys wifi connect 'SSID with spaces'` skips the picker. Authentication/no-signal failures include
guidance from wan's reply; a successful association without an IPv4 lease reports DHCP failure.

Hidden networks: `sys wifi hidden`. An upstream network that overlaps
100.80.0.0/16 is refused and raises UpstreamOverlap.
After moving a refused wired adapter to a safe network, retry DHCP with
`sudo ssh -F /etc/convergent/ssh_config wan 'check retry'`. This retries only configured wired
uplinks and rechecks the lease; the overlap latch clears only after a safe lease arrives.

## Captive portals

`sys portal on` starts tmp in portal mode, which owns the mode for its lifetime. It opens two pf rules
on both firewalls and wan's DNS pass-through, for the portal browser only; the bar shows `PORTAL`.
It works over Wi-Fi or wired; it ends when the browser closes, with `sys portal off`, or after 30 minutes.
`browser tmp --portal [url]` uses the same lifecycle. A new launch closes stale rules
on all three guests before opening any; it refuses to open if closure fails. Cron also detects an
abandoned browser session and retries incomplete closure every minute. `sys portal status` shows
the reason (active, timeout, browser closed, interrupted, or closure pending) and each guest's state.

```sh
sudo portal on [A.B.C.D/LEN]   # diagnostic opening; without a browser it expires after a minute
sudo portal off                # if a side cannot be closed, retries every minute
sudo portal status             # wan, fw1, fw2; verdict on, off, mixed or unknown
```

## Devices

USBGuard denies devices without an allowance. Attach only trusted devices and run `sys usb enrol`:
review each named device (including hubs), type `yes` for each one you trust, then confirm the
complete replacement. Nothing is saved until that final confirmation. This replaces the existing
policy, including a block-all list or the older installer's input/storage/hub class policy.
Devices you decline remain blocked; there is no blanket approval of attached devices.
`sys usb review` shows saved allow/block rules with names, including unplugged devices, and the
current attached-device decisions. `sys usb revoke RULE` takes an allowed **rule number** from
that review, removes it and adds a device-specific deny against overlapping old allowances.
Enrol first if the only existing allowance is a broad class rule. Enrol and revoke restart
USBGuard to apply the policy now; revoking an input device or storage can disconnect it.
`sys usb status` shows blocked USB and unauthorized Thunderbolt devices;
`sys usb allow N|ID` still takes an attached USB **device number** or Thunderbolt ID.
`sys bluetooth` shows power and known devices. Bluetooth stays off at boot; use
`sys bluetooth on` first. `sys bluetooth pair` scans for 10 seconds, then lists discovered and
known devices by MAC and name. `connect`, `disconnect` and `forget` use the current device list;
run `sys bluetooth scan` to refresh it. Pick with fzf in a terminal or bemenu outside one;
Escape cancels without changing a device. Explicit MAC arguments still work and are validated.
`forget` still asks for `yes` in the terminal before opening the picker. By hand:

```sh
sudo devices list
sudo devices allow <number>    # USB, permanent; warns for keyboards, storage, network
sudo devices allow tb <id>     # Thunderbolt PCIe tunnel, until unplugged
```

Both ask you to type `yes`. USB approvals are written to `/etc/usbguard/rules.conf`.

For a USB serial adapter, approve it once with `sys usb allow NUMBER` (find NUMBER in
`sys usb status`), then run `tio -b 115200 /dev/ttyUSB0`; change the baud rate to match the
console. CDC ACM adapters use `/dev/ttyACM0`. Exit with Ctrl+t then q. The owner gets
Gentoo's `dialout` group at installation and on the first boot of an updated image.

For the Dell dock's Realtek Ethernet, allow its USBGuard device number first, then run
`sys wired status` to read its serial and `sys wired attach 0bda:8153 SERIAL` (or omit arguments
for prompts). Confirm the exact identity shown. The `wired-uplink` Incus USB device persists on
wan and matches that vendor, product and serial on replug; another adapter does not qualify.
An empty or ambiguous serial is refused. `sys wired remove` removes the role, including future
automatic attachment, without revoking the USBGuard approval. Unplugging alone keeps the role.
The host never runs DHCP or assigns addresses to the NIC. Wan uses it as `eth1`, prefers its
wired default route, and retries DHCP on replug at its next check (within a minute).

The camera starts disabled. `sys camera on` saves the choice and loads the camera driver now;
`sys camera off` saves disabled first, then unloads it. If an application holds the driver,
close it and retry `off`; unloading is never forced. `sys camera status` shows both the saved
choice and whether the video core is loaded. `CAM` in the bar means enabled (not necessarily
recording); `CAM!` means a video driver remains loaded despite the disabled choice.
The choice survives reboot in `/var/lib/convergent/devices/camera`, following the release's
state snapshot on update/rollback. USB cameras also need their own USBGuard allowance.
Meeting compartments and screen sharing are not part of this release.

## DNS: blocklist and own records

The firewalls resolve all DNS. Cron downloads the blocklist weekly (URL and limits in
`/etc/convergent/dns.conf`), validates it and pushes it to both firewalls; a failed push is rolled
back on both. The owner's files are on the laptop:

- `/var/lib/convergent/dns/allow`: domains exempt from the blocklist, one per line, `#` comments.
- `/var/lib/convergent/dns/records`: Unbound `local-data` and `local-data-ptr` lines.

Use `sys dns list`, then `sys dns add printer.home.arpa 192.168.1.50` or
`sys dns remove printer.home.arpa`. The editor manages IPv4 A records; other record types can
still be maintained in the owner file. Names are normalized to lowercase; duplicate names,
invalid addresses and built-in name conflicts are refused. Removing a name with non-A records
requires editing the owner file. A local DNS record does not grant firewall access to that address.

`sys dns allow example.org` adds a blocklist exception for that name and its subdomains;
`sys dns unallow example.org` removes it. Each edit shows a diff and needs `yes` before applying
to both firewalls. Failed or interrupted edits restore the previous owner files and firewall data;
if a firewall is unreachable, recovery stays pending until the next push can reach both.
Run `sudo dns-push` once if there is no stored blocklist. `sys dns push` reapplies the current
files with the stored blocklist. `sys dns list` shows the last successful push time in UTC.

```sh
sudo dns-push          # download, validate, push the blocklist and records
sudo dns-push local    # push the stored blocklist with the current files
```

## Firewall maintenance

`sys firewall status` (or `sys fw`) shows fw1 and fw2 CARP roles for transit, host, svc, web,
admin and guests, PF state counts, Unbound status, and the last successful DNS push to both.
Unreachable guests and pending DNS recovery are shown explicitly.

`sys fw maintenance` checks the six-segment MASTER/BACKUP pair, PF, pfsync with defer, Unbound
and a local DNS answer before asking to demote the master. It verifies that the peer owns all
six segments. A failed handover is undone; an interrupted action retains recovery information.
After maintenance, run `sys fw undo`: both firewalls must be healthy, and normal fw1-master /
fw2-backup roles are checked after releasing the demotion. Finish maintenance before guest updates.
If undo cannot reach a firewall, retry it after restoring management access.

`sys firewall rebuild fw1` (or `fw2`; root command: `guests rebuild fw1|fw2`) recreates a broken
firewall from the installed guest release and laptop seed. The peer must be healthy and MASTER
on all six segments; guest updates, handoffs, maintenance and DNS pushes must be finished, and
browsers closed. It checks the replacement, restores fw1 MASTER / fw2 BACKUP and pushes stored
DNS data. Repeat the same command after interruption to resume its replacement journal.

## Backups

```sh
sudo backup [<mountpoint> <owner-project>]
```

`sys backup [MOUNTPOINT PROJECT]` runs it. Without arguments it asks `Mounted encrypted
external disk:` and `Owner Incus project:`. It needs an external USB disk with LUKS, unlocked and
mounted at a root-owned directory, not on the laptop's own disk, and an Incus project for the
owner's guests (not `default`; nothing creates one yet). It writes `convergent-backups/backup-<UTC>`:
a snapshot of `/home`, the writable `/etc` files, exports of the owner's instances and the custom
volumes of both projects, reads it all back, and keeps three. Unmount and close the disk before
unplugging. What it leaves out and how to restore: [RECOVERY 11](RECOVERY.md#11-start-over).

## Health and alerts

`sys alerts` (also `sys security alerts`) lists firing alerts from vmalert: severity, name,
summary or description, and the API's active-since timestamp. The bar counts open the same
list on left-click. An unavailable or invalid response reports an error, not an empty list.

Open **Internal dashboards** (`sys browser int`) for Overview, Network, Guests and Security.
Overview puts the path, alerts, collector freshness, host and guests on the first screen; the
other pages share the same navigation. Guests has project/instance selectors. Current-state
tables show one row per item; graphs show history. CARP role-change annotations are off until
toggled on. Log panels show actionable records; **Explore · all logs** includes routine audit
and full kernel traces. A dash means no data; each panel names its source and each footer lists
what is not collected. Battery is always 0–100%.

Security's recent-events list includes successful/failed logins, sudo commands/password failures,
USBGuard decisions, AppArmor denials, firewall takeovers, guest updates/failures and host
update/bless/fallback records. It shows the latest 50 records in the selected range.
`sys security events` works without svc: up to 100 matches from the last 5000 lines of each
current host log (`/var/log/messages`, then `/var/log/audit/audit.log`), with source and original
timestamp; files are not merged by time and rotated logs are not scanned. Missing logs are
reported. Local firewall events cover maintenance and changes observed by the minute status
probe; brief transitions between probes require the firewall logs in Grafana. Fallback records
identify an older boot with an exhausted newer UKI. Audit and PAM may describe the same login.

There are two checkers. `check` runs on the host and compares it with the accepted release:
verity, the writable `/etc` files, autostart and SUID inventories, the guests' Incus settings, the
radio's VFIO binding, CARP and pf on both firewalls. Cron runs it after boot and updates, and
daily once it passes. svc's alert rules watch metrics and logs from every compartment; the host
checker's result reaches them as CheckerFailed and CheckerStale.

```sh
sys security check                    # run the checker now (sudo check); report in /var/lib/convergent/check/last
sys security report                   # read the last report
sys security events                   # recent local security events, even without svc
sudo check accept <release-dir>       # accept a trusted release as the baseline (once Secure Boot is on)
sudo check accept-fw <guest-dir>/fw   # accept new firewall hashes after a firewall update (once Secure Boot is on)
```

The checker fails until a baseline is accepted (`<release-dir>` holds `manifest` and
`guests/fw/fw{1,2}.{pf,rules}.sha256`) and while Secure Boot is off. Acceptance needs Secure Boot on
and out of Setup Mode. `check` does not verify the manifest's signature, so check the release
yourself before accepting it.

`sys selftest` checks this boot (sudo once, at the start) and writes a report to
`~/selftest-YYYYmmdd-HHMMSS.txt`. Each check prints PASS, FAIL or SKIP with its detail. Every check
has a time limit, so the run cannot hang.

`sys debug` (also Logs → debug) downloads the developer's signed diagnostic, shows its purpose
and expiry, and asks before running it as root. It refuses expired or already-run requests,
limits the run to five minutes and output to 8 MiB, and sends the output encrypted to the
developer. A root-only plaintext copy stays at `/var/lib/convergent/debug/<id>.txt`; its path
is printed so you can read what was sent with `sudo cat`. Only `CHANNEL=beta` builds carry it;
stable builds never do. A failed diagnostic reports its script exit status
even when output reaches the cap; timeout reports 124 (137 if it needs a forced kill).
Returned output is not authenticated: anyone holding the public request can upload a forgery.
Compare it with the laptop's local copy at `/var/lib/convergent/debug/<id>.txt`.

An oops triggers a kernel panic; the host reboots 10 seconds after a panic. At boot, `facts`
copies EFI pstore records to `/var/lib/convergent/crash/<UTC-timestamp>/` (root, mode 0700),
verifies and syncs them, then clears pstore. `cv_crash_records` counts archived files; the
existing `CrashRecorded` alert stays active until acknowledged (RECOVERY, recipe 13).
Crash counts appear beside checker results in the Security dashboard. `kernel.panic_on_oops=1`
is KSPP hardening. If a driver repeatedly oopses, `sudo sysctl -w kernel.panic_on_oops=0`
disables that panic trigger until reboot. For a persistent exception, set it to `0` in
`rootfs/etc/sysctl.d/90-convergent.conf` and build/install a release; the running root is read-only.
If it reboots before you can apply the override, boot the previous slot (RECOVERY, recipe 3).
Host cron and anacron have mail disabled; their jobs and logging still run.

## The bar

Refreshed every second. Blocks are shown here with `|` between them; the bar draws its own
separators:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx 0.8 rx 12.4 Mb/s
WLAN:home--WAN--[FW1 FW2]--laptop--SVC--BR:2 | rel 0.1.0 good | NL | 0 1 0 | PORTAL
US | UP 3d 03:41 | Tue 04/08 15:33:02 | PWR battery | BAT 87% -
```

| Block | Shows | Look or fix with |
|---|---|---|
| `CPU` | busy percent, lowest-highest core clock, package/hottest temperature; `-` if missing | `sys power status` lists every sensor |
| `RAM`, `SWP` | used/total GiB; RAM includes cache (`MemTotal - MemFree`) and subtracts what the guests hold (`check status` sums their cgroups and VM processes every minute) | Grafana, Guests |
| `NET` | transmit/receive Mb/s on the default-route interface (route refreshed every 5 s) | `sys wifi test` |
| Topology | the uplink, wan, both firewalls, svc and browsers (below) | `sys guests status`; RECOVERY 5, 6 |
| `rel` | booted semantic version (release ID on older images); grey `good` when the release passed its checks this boot, else red `UNBLESSED` | `sys update` |
| `NL` | click to pause or resume the idle lock (orange while paused); `NL!` (red): swayidle missing | `sys power lock` |
| `MIC` | default microphone unmuted (orange); hidden when muted, `MIC?` (grey) if unknown; every 5 s | `sys audio mic off` / `on` |
| Alerts | firing alerts as three counters: critical (red), warning (orange), info (white); `? ? ?` (grey) when svc cannot be read (also while SETUP runs, until svc is up); every 30 s | click for the firing list in foot, or `sys alerts`; history in Grafana: `sys browser int` |
| `PORTAL` | portal mode on (orange) | `sys portal off` |
| `CAM`, `CAM!` | camera enabled, or driver still loaded after disabling (orange); not a recording indicator | `sys camera status`, `sys camera off` |
| `PWR` | last successfully applied CPU profile: `ac` or `battery`; `?` if unavailable or failed | `sys power status` |
| `SETUP` | guests being created (orange); `SETUP failed` (red) | `sys guests setup` |
| `GUESTS` | downloaded guests being applied (orange); `GUESTS failed` (red) | `sys guests update` |
| layout, `UP`, clock | keyboard layout (every 5 s), uptime, local date and time | `sys keyboard next` |
| `BAT` | capacity, `+` charging or `-` discharging; orange below 30 %, red below 15 % discharging; `AC` without a battery | `sys power status` |

Topology: the uplink first, `WLAN:<network>` (green connected, red with no network, grey when wan
does not answer; names over 16 characters are cut) or `ETH` for a passed-through wired NIC. `WAN`
green with an uplink, orange without one, red when wan is down.
Each firewall is bold bright green as CARP master, dim green as standby, orange when its CARP
interfaces disagree, red when down. `SVC` green or red; the host name green; `BR:n` counts running
browser containers (grey at zero). Cron refreshes it every minute; older than three minutes, it
turns grey. The idle-lock pause is the file `$XDG_RUNTIME_DIR/nolock`; the lid lock still works.

## Releases and guests

New installs use the `beta` update channel. `dev` is unpublished; `stable` is rebuilt from a
candidate's exact commit with the offline key and tested again. Candidate tags such as `v0.1.0-rc1` are not channels.
`sys update status` and `slot status` show the booted version and timestamp release ID;
the checker and selftest reports include both. The timestamp still controls slot ordering.

```sh
sys update                           # release slots; `sys update check` asks whether a newer one is published
sys guests status                     # one line per instance: name and state (guests status)
sys guests update                     # apply pending downloaded guests now
sudo guests update fw|wan|svc|browser|def|int <image-dir>
```

Online releases carry guests; only changed guests download with `sys update install`. After reboot
and marking the host good, they apply in order: svc, wan, fw, browser. The bar shows GUESTS while
applying and GUESTS failed on failure. Close browsers and run `sys guests update` to retry a pending
browser update. Updating `browser` also moves the image used for future tmp instances, including portal mode;
`def` or `int` normally replaces that instance only; a role migration updates both. One guest operation runs at a time. Writing a release
and manual guest updates: [README, Update](README.md#update).
An interrupted browser update blocks launches until the guest update is retried.
The first full browser update renames existing web/admin instances and state volumes to def/int,
keeping bookmarks and logins. Close all browsers first. An interrupted migration resumes on
the next browser update; the old role names are not command aliases.

If you added a root crontab as a stopgap for the v8/v9 cron bug, remove that stopgap with
`sudo crontab -r` after the first v10 boot; otherwise those jobs run twice.

## Power and locking

- The screen locks after 10 minutes idle by default (`idle_lock_minutes`) and when the lid closes
  (swayidle, swaylock). Display-off follows `idle_lock_minutes + 1` minutes of inactivity.
  `sys power lock` locks now. NL pauses idle locking and display-off only; manual and lid locking still work.
- `power` sets the CPU energy preference and a clock cap for AC or battery (4.2 GHz by default,
  `cpu_cap_khz`). It runs at boot and on AC adapter events; by hand: `sys power ac` or
  `sys power battery` (`sudo power [ac|battery]`).
  Repeated events with no setting changes are silent; changes and failures are logged.
  The bar shows the applied profile, including a manual override until the next plug event.
  AC uses `balance_performance`, battery uses `power`; both keep the configured clock cap.
- `sys power charge 80` stops charging at 80 %, with a start threshold of 75 % where supported.
  Valid limits are 55-100. `sys power charge off` (the default) allows full charging: end 100 %,
  start 95 %. Where Dell exposes `charge_types`, a limit selects Custom mode and off selects
  Standard mode. This does not discharge a battery already above the limit.
- `sys power thermal quiet|balanced|performance` selects a profile offered by the firmware;
  firmware still controls fan speeds. No thermal override is applied until one is selected.
  Charge and thermal choices persist in `/var/lib/convergent/power/`, are restored at boot and
  AC events, and follow the release's state snapshot on update/rollback. Missing sysfs controls
  are optional: actions report unsupported, and other power controls continue to work.
  `sys power status` shows the actual thresholds, thermal profile and available choices.
  The resource review and unimplemented tuning proposals are in ARCHITECTURE section 11.
