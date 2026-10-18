# Using Convergent

The tools are in `/usr/local/sbin`. Most need root and run with `sudo` (wheel only, password
asked, ticket valid for 5 minutes). If `sudo` does not find a tool, give its full path. `sys` is
the exception: run it as the owner, and it asks for `sudo` itself where an action needs root.

Contents: [Coming from Arch](#coming-from-arch) · [Keys](#keys) · [The sys tool](#the-sys-tool) ·
[Browsers](#browsers) · [Wi-Fi](#wi-fi) · [Captive portals](#captive-portals) ·
[Devices](#devices) · [DNS](#dns-blocklist-and-own-records) · [Backups](#backups) ·
[Health and alerts](#health-and-alerts) · [Releases and guests](#releases-and-guests) ·
[Power and locking](#power-and-locking). When something breaks: [RECOVERY.md](RECOVERY.md).

## Coming from Arch

| On Arch | Here |
|---|---|
| `pacman -Syu` | No package manager on the laptop. An update is a whole new release: `sudo slot write` (README) |
| `systemctl status`, `restart` | `rc-status` lists every service; `sudo rc-service <name> status`, `restart` |
| `systemctl enable` | Services are fixed in the release |
| `journalctl` | `/var/log/messages` (warnings and up; `sys system logs`), `/var/log/incus/`, Grafana; see RECOVERY 8 |
| Editing `/etc` | `/etc` is read-only. Only accounts, `machine-id` and `/etc/usbguard/rules.conf` are kept; other changes come with a release |
| Your files | `/home` is on the encrypted state volume and survives updates |
| `incus` | Guests are managed with `guests`; the owner's own Incus project is not set up yet |
| A network manager | Wi-Fi is in `sys network`; the radio lives in the `wan` VM |

The firewalls run OpenBSD. You do not log in to them for daily use; for a look,
`sudo ssh -F /etc/convergent/ssh_config fw1` gives a shell (`pfctl -sr` shows the rules,
`ifconfig carp` the failover state).

## Keys

Sway's stock bindings, plus the Convergent ones below. Super is the Windows key.

| Key | Does |
|---|---|
| Super+m | `sys`: the menu of areas and actions, in a terminal |
| Super+a | pick one `sys` action by name and run it in its own terminal |
| Super+d | run a program by name |
| Super+b | web browser (`browser web`) |
| Super+Shift+t | temporary browser (`browser tmp`) |
| Super+Escape | lock the screen now |
| Super+Enter | terminal (foot) |
| Super+Shift+q | close the window |
| Super+1 … 9, Super+Shift+1 … 9 | go to a workspace, move the window there |
| Super+f | fullscreen |
| Super+Shift+c | reload the sway configuration |
| Super+Shift+e | exit sway |
| Print | select an area and copy it to the clipboard (Escape cancels) |
| Shift+Print | copy the focused screen to the clipboard |
| Volume, mute and mic-mute keys | `wpctl` on PipeWire |

## The sys tool

`sys` is the one menu for the laptop. Super+m runs it in a terminal: pick an area, then an
action. `sys AREA ACTION [ARGS]` runs one action without the menu; a missing argument is asked
for. `sys help` lists every action with its label, and Super+a picks one action by name. Each
command is printed before it runs. Actions marked `*` ask you to type `yes` first.

```sh
sys                                  # the menu (needs a terminal)
sys network wifi-scan                # one action
sys help                             # all actions
```

| Area | Actions |
|---|---|
| `network` | `wifi-status`, `wifi-scan`, `wifi-connect [SSID]`, `wifi-connect-hidden [SSID]`, `wifi-disconnect`, `wifi-forget [SSID]` \*, `portal-on`, `portal-off`, `portal-status`, `test` |
| `devices` | `usb-list`, `usb-allow N`, `thunderbolt-allow ID`, `bluetooth-power on\|off`, `bluetooth-scan`, `bluetooth-pair MAC`, `bluetooth-connect MAC`, `bluetooth-disconnect MAC`, `bluetooth-remove MAC` \*, `bluetooth-list` |
| `audio` | `list`, `output ID`, `volume PERCENT` (0-150), `mute`, `mic-mute` |
| `display` | `list`, `set OUTPUT mode\|scale\|position\|enable\|disable [VALUE]`, `save`, `reset` \* |
| `keyboard` | `layouts`, `set LAYOUTS` (for example `us,hu`), `next` |
| `screenshot` | `area`, `screen` (saves to `~/Pictures`) |
| `browser` | `web`, `tmp`, `admin`, `portal` |
| `security` | `status`, `check`, `report` |
| `system` | `release`, `update [MOUNTPOINT\|DEVICE]` \*, `guests`, `backup [MOUNTPOINT PROJECT]`, `logs`, `services` |
| `power` | `profile ac\|battery`, `lock`, `logout` \*, `reboot` \*, `poweroff` \* |
| `selftest` | `run` |

Not built in `sys`: owner guest management (`system guests` shows status only), firewall
failover and printing.

## Browsers

```sh
browser web|tmp|portal|admin [url]
```

Run it as the owner in the Sway session; it needs no password. `sys browser` opens the same
roles without a URL. Only HTTP and HTTPS URLs are accepted. Each browser is Chromium in its own
container with a restricted Wayland socket and playback-only audio; the window title starts with
`[role]`.

| Role | For | State |
|---|---|---|
| web | everyday browsing | profile and downloads kept in a 4 GiB volume |
| tmp | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| portal | captive portals; opens `http://neverssl.com/` unless given a URL | container deleted on close; starts only while portal mode is on |
| admin | Grafana only (`http://100.80.2.10:3000/`) | profile kept in a 512 MiB volume |

web, admin and portal refuse a second start while open; tmp can run many at once. Downloads stay
in the container; no action moves a file out. Policies: DNS-over-HTTPS off, no sync, no password
manager, no telemetry; admin and portal allow no extensions. The admin browser starts Grafana in
svc and stops it on close. Log in as `owner` with the password in
`/var/lib/convergent/guests/tls/admin-password` (`sudo cat`). A handler that sends links from
other programs to `tmp` is not built.

## Wi-Fi

The radio belongs to wan; `sys network` runs the commands in it over SSH.

- `sys network wifi-status`: the connection and address. `sys network wifi-scan`: networks in
  range, after a few seconds.
- `sys network wifi-connect`: lists the networks in range, then asks `SSID:` and `Passphrase
  (empty for a known or open network):` (8 to 63 characters; it goes to wan on standard input
  and stays there). An empty passphrase connects to a known network.
- `sys network wifi-forget`: lists known networks, asks `SSID to forget:`.
- `sys network wifi-disconnect`: drops the current connection.

Hidden networks: `sys network wifi-connect-hidden`. An upstream network that overlaps
100.80.0.0/16 is refused and raises UpstreamOverlap.

## Captive portals

`sys network portal-on` runs `sudo portal on` and then the portal browser. It opens two pf rules
on both firewalls and wan's DNS pass-through, for the portal browser only; the bar shows `PORTAL`.
It ends when the browser closes, with `sys network portal-off`, or after 30 minutes.

```sh
sudo portal on [A.B.C.D/LEN]   # upstream network, taken from wan's address if omitted
sudo portal off                # if a side cannot be closed, retries every minute
sudo portal status             # wan, fw1, fw2; verdict on, off, mixed or unknown
```

## Devices

USBGuard blocks every device not in the allow-list. `sys devices usb-list` shows the blocked USB
and unauthorized Thunderbolt devices; `sys devices usb-allow N` and `sys devices thunderbolt-allow
ID` allow them. The `bluetooth-*` actions in the same area drive Bluetooth. By hand:

```sh
sudo devices list
sudo devices allow <number>    # USB, permanent; warns for keyboards, storage, network
sudo devices allow tb <id>     # Thunderbolt PCIe tunnel, until unplugged
```

Both ask you to type `yes`. USB approvals are written to `/etc/usbguard/rules.conf`.

## DNS: blocklist and own records

The firewalls resolve all DNS. Cron downloads the blocklist weekly (URL and limits in
`/etc/convergent/dns.conf`), validates it and pushes it to both firewalls; a failed push is rolled
back on both. The owner's files are on the laptop:

- `/var/lib/convergent/dns/allow`: domains exempt from the blocklist, one per line, `#` comments.
- `/var/lib/convergent/dns/records`: Unbound `local-data` and `local-data-ptr` lines.

```sh
sudo dns-push          # download, validate, push the blocklist and records
sudo dns-push local    # push the stored blocklist with the current files
```

## Backups

```sh
sudo backup [<mountpoint> <owner-project>]
```

`sys system backup [MOUNTPOINT PROJECT]` runs it. Without arguments it asks `Mounted encrypted
external disk:` and `Owner Incus project:`. It needs an external USB disk with LUKS, unlocked and
mounted at a root-owned directory, not on the laptop's own disk, and an Incus project for the
owner's guests (not `default`; nothing creates one yet). It writes `convergent-backups/backup-<UTC>`:
a snapshot of `/home`, the writable `/etc` files, exports of the owner's instances and the custom
volumes of both projects, reads it all back, and keeps three. Unmount and close the disk before
unplugging. There is no restore tool.

## Health and alerts

```sh
sys security check          # run the checker now (sudo check); report in /var/lib/convergent/check/last
sys security report         # read the last report
sudo check accept <dir>     # accept a trusted release as the baseline
sudo check accept-fw <dir>  # accept new firewall hashes after a firewall update
```

With Secure Boot off the checker always fails, so `accept` and `accept-fw` cannot complete until
release signing exists.

The checker compares the running system with the release: verity, the writable `/etc` files,
autostart and SUID inventories, the guests' Incus settings, the radio's VFIO binding, CARP and pf
on both firewalls. Cron runs it after boot and updates, and daily once it passes. It fails until
a baseline is accepted (`<dir>` holds `manifest` and `guests/fw/fw{1,2}.{pf,rules}.sha256`), and
with Secure Boot off.

`sys selftest run` checks this boot (sudo once, at the start) and writes a report to
`~/selftest-YYYYmmdd-HHMM.txt`. Each check prints PASS, FAIL or SKIP with its detail. Every check
has a time limit, so the run cannot hang.

The status bar, refreshed every second. Blocks are shown here with `|` between them; the bar
draws its own separators:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx0.8 rx12.4 Mb/s
WAN--[FW1 FW2]--laptop--SVC--BR:2 | NL | wifi home | alerts 0 | PORTAL
rel 202610170000 good | US | UP 3d 03:41 | Tue 04/08 15:33:02 | BAT 87% -
```

- `CPU`: busy percent, lowest-highest core clock, package/hottest sensor temperature; `-` if missing.
- `RAM`, `SWP`: used/total GiB. `NET`: transmit/receive Mb/s on the default-route interface;
  the route is refreshed every five seconds.
- Topology: `WAN` green when Wi-Fi is connected, orange without a network, red when wan is down.
  Each firewall is bold bright green when it is CARP master, dim green as standby, orange when
  its CARP interfaces do not all agree (degraded), red when down. `SVC` green or red. The host name is
  green. `BR:n` counts running browser containers (grey at zero). The topology is refreshed by cron
  once a minute; if it is missing or older than three minutes, the whole topology is grey.
- `NL`: click to pause or resume the owner's idle lock (orange while paused). `NL!` (red) means
  swayidle is missing. The pause is the file `$XDG_RUNTIME_DIR/nolock`. The lid lock still works.
- `wifi`: network name, `-` if none, `?` if wan does not answer; refreshed once a minute.
- `alerts`: `0` (green), counts such as `1c 2w` (critical, warning), or `?` (grey) when the alert
  service or its rules cannot be read. Red when there is any critical alert, yellow for warnings
  only. Polled every 30 seconds; details are in Grafana (admin browser).
- `PORTAL` orange while portal mode is on, `portal ?` grey when unclear; absent when off.
- `rel`: the booted release; grey `good` once marked good, otherwise red `UNBLESSED`.
- Keyboard layout (`US` or two letters, every five seconds), `UP` (days, hours and minutes), and
  the local date and time.
- `BAT`: capacity, `+` charging or `-` discharging; orange below 30%, red below 15% while
  discharging. `AC` without a battery.

## Releases and guests

```sh
sys system release                    # booted release and slot, both slots, good, highest (slot status)
sys system guests                     # one line per instance: name and state (guests status)
sudo guests update fw|wan|svc|web|admin <image-dir>
```

`sys system update` mounts a USB stick read-only, lists the release directories on it, writes the
one you pick and offers a reboot. The README steps do the same by hand.

Writing a release, updating guests and rolling back are in the README. Close every browser
first: an open browser makes guest operations wait, then fail after ten minutes. One guest
operation runs at a time; browsers, `check` and `backup` refuse to start while one runs.

## Power and locking

- The screen locks after 10 minutes idle and when the lid closes (swayidle, swaylock).
  `sys power lock` locks now. Pause or resume the idle lock with the `NL` block in the bar.
- `power` sets the CPU energy preference and a 4.2 GHz clock cap for AC or battery. It runs at
  boot and on AC adapter events; by hand: `sys power profile ac` or `sys power profile battery`
  (`sudo power [ac|battery]`).

## What needs sudo

`browser`, `sys`, the bar, lock and log out run as the owner. `browser` asks sudo for its own
validated entry point, with no password. `sys` asks sudo for the actions that call root tools.
Everything else asks for the owner's password: `slot`, `guests`, `check`, `facts`, `portal`,
`dns-push`, `devices`, `backup`, `power`, and the root `sys` actions (Wi-Fi, portal, devices,
system, security, selftest, reboot and power off).
