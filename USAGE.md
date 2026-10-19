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
| Super+d | an app by name: Web browser, Temporary browser, Admin dashboards, Settings, Screenshot, Foot |
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
| Brightness keys | `sys display bright -5` / `+5` (5 % steps) |

## The sys tool

Use `sys AREA [ACTION] [ARGS]`; the first action in each row is the default. An unrecognized
second word becomes an argument to that default: `sys backup /mnt/x proj` works;
`sys wifi foo` is a usage error. Missing arguments are prompted for; partial lists are usage
errors. `sys help` lists actions and aliases; `*` asks for `yes` in the terminal (default No).

`sys` (Super+m) looks like the Archer menu: the list left, the highlighted row's status and
commands right, terminal colours with a blue highlight. Enter opens or runs, Esc goes back, typing
filters, Alt+Enter runs what was typed (`area action args`, or `action args` inside an area).
Super+a runs one action by name.

| Area (alias) | Actions, default first |
|---|---|
| `wifi` | `status`, `scan`, `connect [SSID]`, `hidden [SSID]`, `disconnect`, `forget [SSID]` *, `test` |
| `portal` | `status`, `on`, `off` |
| `bluetooth` (`bt`) | `status`, `on`, `off`, `scan`, `pair MAC`, `connect MAC`, `disconnect MAC`, `forget MAC` * |
| `usb` | `status`, `allow N\|ID` |
| `audio` | `status`, `out ID`, `vol N` (0–150), `mute`, `micmute` |
| `display` (`disp`) | `status`, `bright N\|+N\|-N`, `set OUTPUT mode\|scale\|position\|enable\|disable [VALUE]`, `save`, `reset` * |
| `keyboard` (`kb`) | `status`, `set LAYOUTS` (e.g. `us,hu`), `next` |
| `screenshot` (`shot`) | `area`, `screen` (save to `~/Pictures`) |
| `browser` (`br`) | `status`, `web`, `tmp`, `admin`, `portal` |
| `security` (`sec`) | `status`, `check`, `report`, `password` |
| `update` (`up`) | `status`, `check`, `install` *, `usb [MOUNTPOINT\|DEVICE]` * |
| `guests` | `status`, `setup`, `update` |
| `power` | `status`, `ac`, `battery`, `lock`, `logout` *, `reboot` *, `off` * |
| `backup` | `run [MOUNTPOINT PROJECT]` |
| `logs` | `host` (`/var/log/messages`), `services` (`rc-status -a`) |
| `selftest` | `run` |

Not built in `sys`: owner guest management, firewall failover and printing.

Screen too big: `sys display set eDP-1 scale 1.2`, then `sys display save` (every login). Release
default: `display_scale` in config.yaml ([README, Build](README.md#build-a-release)).

## Browsers

```sh
browser web|tmp|portal|admin [url]
```

Run it as the owner in the Sway session; it needs no password. `sys browser web|tmp|admin|portal`
(or the menu) opens one without a URL. `sys browser` lists running browsers.
Only HTTP and HTTPS URLs are accepted. Each browser is
Chromium in its own container with a restricted Wayland socket and playback-only audio; the
window title starts with `[role]`.
Browsers prefer dark pages; sites without a dark style stay light.

Works when: a window titled `[web] …` opens and the bar shows `BR:1`. A failed start from
Super+b or Super+Shift+t shows a line at the top with the reason; the full output is in
`$XDG_RUNTIME_DIR/browser.log`.

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

The radio belongs to wan; `sys wifi` runs the commands in it over SSH.

`sys wifi connect` lists networks, asks `SSID:` and
`Passphrase (empty for a known or open network):`; the passphrase stays in wan.

Hidden networks: `sys wifi hidden`. An upstream network that overlaps
100.80.0.0/16 is refused and raises UpstreamOverlap.

## Captive portals

`sys portal on` runs `sudo portal on` and then the portal browser. It opens two pf rules
on both firewalls and wan's DNS pass-through, for the portal browser only; the bar shows `PORTAL`.
It ends when the browser closes, with `sys portal off`, or after 30 minutes.

```sh
sudo portal on [A.B.C.D/LEN]   # upstream network, taken from wan's address if omitted
sudo portal off                # if a side cannot be closed, retries every minute
sudo portal status             # wan, fw1, fw2; verdict on, off, mixed or unknown
```

## Devices

USBGuard blocks every device not in the allow-list. A disk image starts with a policy by class
(input, storage, hubs); replace it with a per-device one after the first boot (README, First boot
step 4; there is no `sys` action for it). `sys usb status` shows the blocked USB and
unauthorized Thunderbolt devices; `sys usb allow N|ID` allows a USB number or Thunderbolt ID.
`sys bluetooth` shows power and known devices. By hand:

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

`sys backup [MOUNTPOINT PROJECT]` runs it. Without arguments it asks `Mounted encrypted
external disk:` and `Owner Incus project:`. It needs an external USB disk with LUKS, unlocked and
mounted at a root-owned directory, not on the laptop's own disk, and an Incus project for the
owner's guests (not `default`; nothing creates one yet). It writes `convergent-backups/backup-<UTC>`:
a snapshot of `/home`, the writable `/etc` files, exports of the owner's instances and the custom
volumes of both projects, reads it all back, and keeps three. Unmount and close the disk before
unplugging. What it leaves out and how to restore: [RECOVERY 11](RECOVERY.md#11-start-over).

## Health and alerts

Open **Admin dashboards** (`sys browser admin`) for Overview, Network, Guests and Security.
Overview puts the path, alerts, collector freshness, host and guests on the first screen; the
other pages share the same navigation. Guests has project/instance selectors. Current-state
tables show one row per item; graphs show history. CARP role-change annotations are off until
toggled on. Log panels show actionable records; **Explore · all logs** includes routine audit
and full kernel traces. A dash means no data; each panel names its source and each footer lists
what is not collected. Battery is always 0–100%.

There are two checkers. `check` runs on the host and compares it with the accepted release:
verity, the writable `/etc` files, autostart and SUID inventories, the guests' Incus settings, the
radio's VFIO binding, CARP and pf on both firewalls. Cron runs it after boot and updates, and
daily once it passes. svc's alert rules watch metrics and logs from every compartment; the host
checker's result reaches them as CheckerFailed and CheckerStale.

```sh
sys security check                    # run the checker now (sudo check); report in /var/lib/convergent/check/last
sys security report                   # read the last report
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

## The bar

Refreshed every second. Blocks are shown here with `|` between them; the bar draws its own
separators:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx0.8 rx12.4 Mb/s
WLAN:home--WAN--[FW1 FW2]--laptop--SVC--BR:2 | rel 202610170000 good | NL | 0 1 0 | PORTAL
US | UP 3d 03:41 | Tue 04/08 15:33:02 | BAT 87% -
```

| Block | Shows | Look or fix with |
|---|---|---|
| `CPU` | busy percent, lowest-highest core clock, package/hottest temperature; `-` if missing | `sys power status` lists every sensor |
| `RAM`, `SWP` | used/total GiB; RAM counts the host and its programs, not what the guests hold (`check status` sums their cgroups and VM processes every minute) | Grafana, Guests |
| `NET` | transmit/receive Mb/s on the default-route interface (route refreshed every 5 s) | `sys wifi test` |
| Topology | the uplink, wan, both firewalls, svc and browsers (below) | `sys guests status`; RECOVERY 5, 6 |
| `rel` | booted release; grey `good` when the release passed its checks this boot, else red `UNBLESSED` | `sys update` |
| `NL` | click to pause or resume the idle lock (orange while paused); `NL!` (red): swayidle missing | `sys power lock` |
| Alerts | firing alerts as three counters: critical (red), warning (orange), info (white); `? ? ?` (grey) when svc cannot be read (also while SETUP runs, until svc is up); every 30 s | details in Grafana: `sys browser admin` |
| `PORTAL` | portal mode on (orange) | `sys portal off` |
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

```sh
sys update                           # release slots; `sys update check` asks whether a newer one is published
sys guests status                     # one line per instance: name and state (guests status)
sys guests update                     # apply pending downloaded guests now
sudo guests update fw|wan|svc|browser|web|admin <image-dir>
```

Online releases carry guests; only changed guests download with `sys update install`. After reboot
and marking the host good, they apply in order: svc, wan, fw, browser. The bar shows GUESTS while
applying and GUESTS failed on failure. Close browsers and run `sys guests update` to retry a pending
browser update. Updating `browser` also moves the image used for future tmp and portal instances;
`web` or `admin` replaces that instance only. One guest operation runs at a time. Writing a release
and manual guest updates: [README, Update](README.md#update).

## Power and locking

- The screen locks after 10 minutes idle by default (`idle_lock_minutes`) and when the lid closes
  (swayidle, swaylock).
  `sys power lock` locks now. Pause or resume the idle lock with the `NL` block in the bar.
- `power` sets the CPU energy preference and a clock cap for AC or battery (4.2 GHz by default,
  `cpu_cap_khz`). It runs at boot and on AC adapter events; by hand: `sys power ac` or
  `sys power battery` (`sudo power [ac|battery]`).
