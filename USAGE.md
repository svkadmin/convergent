# Using Convergent

The tools are in `/usr/local/sbin`. Most need root and run with `sudo` (wheel only, password
asked, ticket valid for 5 minutes). If `sudo` does not find a tool, give its full path.

## The menu

Super+m opens the menu: one action per file in `/usr/lib/convergent/menu`. An action runs in a
terminal window that shows its command first; browsers, lock and log out run without one.

| Entry | Does |
|---|---|
| Browser: web, disposable, admin, portal | `browser web`, `tmp`, `admin`, `portal` |
| Wi-Fi: status, scan, connect, forget | see Wi-Fi |
| Portal mode: on, off, status | see Captive portals |
| Devices: approve USB or Thunderbolt | see Devices |
| Blocklist: download and push; push own records only | see DNS |
| Backup; Release: slot status | `sudo backup`; `sudo slot status` |
| Lock, Log out, Reboot, Power off | `swaylock -f`, `swaymsg exit`; reboot and power off ask `yes` |

Not built: menu actions for owner guests, firewall failover, displays, printing, Bluetooth,
keyboard, audio, power profile, logs and dashboards.

## Browsers

```sh
browser web|tmp|portal|admin [url]
```

Run it as the owner in the Sway session; it needs no password. Only HTTP and HTTPS URLs are
accepted. Each browser is Chromium in its own container with a restricted Wayland socket and
playback-only audio; the window title starts with `[role]`.

| Role | For | State |
|---|---|---|
| web | everyday browsing | profile and downloads kept in a 4 GiB volume |
| tmp | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| portal | captive portals; opens `http://neverssl.com/` unless given a URL | container deleted on close; starts only while portal mode is on |
| admin | Grafana only (`http://100.80.2.10:3000/`) | profile kept in a 512 MiB volume |

A role already open refuses a second start. Downloads stay in the container; no action moves a
file out. Policies: DNS-over-HTTPS off, no sync, no password manager, no telemetry; admin and
portal allow no extensions. The admin browser starts Grafana in svc and stops it on close. Log in
as `owner` with the password in `/var/lib/convergent/guests/tls/admin-password` (`sudo cat`).
A handler that sends links from other programs to `tmp` is not built.

## Wi-Fi

The radio belongs to wan; the menu runs commands in it over SSH.

- **status**: the connection and address. **scan**: networks in range, after a few seconds.
- **connect**: lists known networks, asks `SSID:` and `Passphrase (empty for a known or open
  network):` (8 to 63 characters; it goes to wan on standard input and stays there).
- **forget**: lists known networks, asks `SSID to forget:`.

Hidden networks are supported by wan but not offered by the menu. An upstream network that
overlaps 100.80.0.0/16 is refused and raises UpstreamOverlap.

## Captive portals

"Portal mode: on" runs `sudo portal on` and then the portal browser. It opens two pf rules on
both firewalls and wan's DNS pass-through, for the portal browser only; the bar shows `PORTAL`.
It ends when the browser closes, with "Portal mode: off", or after 30 minutes.

```sh
sudo portal on [A.B.C.D/LEN]   # upstream network, taken from wan's address if omitted
sudo portal off                # if a side cannot be closed, retries every minute
sudo portal status             # wan, fw1, fw2; verdict on, off, mixed or unknown
```

## Devices

USBGuard blocks every device not in the allow-list. The menu entry lists blocked USB and
unauthorized Thunderbolt devices and asks for a USB device number, or `tb` and the id. By hand:

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
sudo dns-push          # download, validate, push the blocklist and records (menu: download and push)
sudo dns-push local    # push the stored blocklist with the current files (menu: own records only)
```

## Backups

```sh
sudo backup [<mountpoint> <owner-project>]
```

Without arguments it asks `Mounted encrypted external disk:` and `Owner Incus project:`. It needs
an external USB disk with LUKS, unlocked and mounted at a root-owned directory, not on the
laptop's own disk, and an Incus project for the owner's guests (not `default`; nothing creates
one yet). It writes `convergent-backups/backup-<UTC>`: a snapshot of `/home`, the writable `/etc`
files, exports of the owner's instances and the custom volumes of both projects, reads it all
back, and keeps three. Unmount and close the disk before unplugging. There is no restore tool.

## Health and alerts

```sh
sudo check                  # run the checker now; report in /var/lib/convergent/check/last
sudo check accept <dir>     # accept a trusted release as the baseline
sudo check accept-fw <dir>  # accept new firewall hashes after a firewall update
```

The checker compares the running system with the release: verity, the writable `/etc` files,
autostart and SUID inventories, the guests' Incus settings, the radio's VFIO binding, CARP and pf
on both firewalls. Cron runs it after boot and updates, and daily once it passes. It fails until
a baseline is accepted (`<dir>` holds `manifest` and `guests/fw/fw{1,2}.{pf,rules}.sha256`), and
with Secure Boot off.

The status bar, refreshed every five seconds:

```
bat 87%- | cpu 4% | mem 1310M | wifi home | alerts 0 | rel 202610170000 good | 14:05
```

- `bat`: capacity, `+` charging or `-` discharging; absent without a battery.
- `wifi`: network name, `-` if none, `?` if wan does not answer; refreshed once a minute.
- `alerts`: `0`, counts such as `1c 2w` (critical, warning), or `?` when svc or its rules cannot
  be read; polled every 30 seconds. Details are in Grafana (admin browser).
- `PORTAL` while portal mode is on, `portal ?` when its state is unclear.
- `rel`: the booted release; `good` once marked good, otherwise `UNBLESSED`.

## Releases and guests

```sh
sudo slot status                      # booted release and slot, both slots, good, highest
sudo guests status                    # one line per instance: name and state
sudo guests update fw|wan|svc|web|admin <image-dir>
```

Writing a release, updating guests and rolling back are in the README. `guests update web` and
`admin` need that browser closed. One guest operation runs at a time; browsers, `check` and
`backup` refuse to start while one runs.

## Power and locking

- The screen locks after 10 minutes idle and when the lid closes (swayidle, swaylock).
- `power` sets the CPU energy preference and a 4.2 GHz clock cap for AC or battery. It runs at
  boot and on AC adapter events; by hand: `sudo power [ac|battery]`.
- Pausing the idle lock from the bar is not built.

## What needs sudo

`browser`, `menu`, the bar, lock and log out run as the owner. `browser` asks sudo for its own
validated entry point, with no password. Everything else asks for the owner's password: `slot`,
`guests`, `check`, `facts`, `portal`, `dns-push`, `devices`, `backup`, `power`, the Wi-Fi
entries (through `menu`), reboot and power off.
