# Using Convergent

Tools live in `/usr/local/sbin`. `sys`, `browser` and the bar run as the owner; `sys` calls `sudo`
when an action needs root. The other tools (`slot`, `fetch-release`, `guests`, `check`, `devices`,
`backup`, `account`, …) need `sudo`: your password, then a 5-minute ticket.

[Install](#install) · [Keys](#keys) · [The sys tool](#the-sys-tool) ·
[Updates](#releases-and-guests) · [Recovery](RECOVERY.md)

## Install

> [!CAUTION]
> Writing a disk image or installing erases the target disk.

Hardware requirements: [README](README.md).

### Disk image

The default image is 30 GiB (32,212,254,720 bytes); some nominal 32 GB sticks are too small. It
holds the owner account, the state partition and the guests; slot B is empty. Its state grows to
fill the disk at unlock.

1. Identify the USB disk:

   ```sh
   lsblk -o NAME,SIZE,MODEL,TRAN
   ```

2. Write the image, with `/dev/sdX` replaced by that disk. The guard refuses disks without 512-byte
   logical sectors:

   ```sh
   if [ "$(sudo blockdev --getss /dev/sdX)" = 512 ]; then
       zstd -dc <out.img>.zst | sudo dd of=/dev/sdX bs=4M iflag=fullblock oflag=direct conv=fsync status=progress
   else
       echo 'Image writing requires 512-byte logical sectors; target refused.' >&2
   fi
   ```

For a 4Kn internal disk, boot compatible USB media and use the installer
([Internal disk](#internal-disk)).

### Internal disk

1. Boot Convergent from USB in UEFI mode.
2. As root, run the installer on a release directory:

   ```sh
   convergent-install <release-dir>
   ```

3. Choose the target: type its disk path again, or `ERASE` followed by a space and its serial.
4. Enter the owner login name, unless the config file sets it.
5. Enter the owner password and the LUKS passphrase, each twice.
6. Wait for the installer to verify slot A, register a boot entry named after the release `NAME`
   and power off. Remove the USB disk.
7. Guests are not copied. Put them at `/var/lib/convergent/release-guests/guests`, then run
   `sys guests setup`.

The installer verifies the release signature with the booted key; `CONVERGENT_UNSIGNED=1` bypasses
that. It lists the disks and refuses unsafe targets. It needs at least 49 GiB plus 4 MiB without
disk swap.

### Install options

Pass a config file with `convergent-install --config <file> <release-dir>`. Keys and defaults are
in `config.example.yaml`. Put no secrets in it, not even in comments. The installer saves the
validated copy at `/var/lib/convergent/config.yaml`; nothing reads it at runtime.

Passwords are always typed at the prompts. Both need 12–256 bytes; the
LUKS passphrase must use printable ASCII (space through `~`).

```yaml
install:
  disk: auto
  state_size: auto
  swap: none
```

| Key | Values | Note |
|---|---|---|
| `disk` | `auto`, or a whole-disk `/dev/disk/by-id/` ID | `auto`: exactly one internal non-removable SSD besides the boot disk |
| `state_size` | `auto`, `1%`–`100%`, `32GiB`–`999999GiB` | `auto` takes the free space and grows; the others stay fixed |
| `swap` | `none`, `zram:1GiB`–`zram:1024GiB`, `state:1GiB`–`state:1024GiB` | no hibernation |

- `disk: auto` accepts NVMe, SATA or ATA SSDs that are not removable or hotplug.
- Mounted, swap, held, boot and read-only disks are refused, even when named. The erase
  confirmation is always asked.
- A percentage counts the space after the ESP, the slots and alignment.
- `zram` sizes are uncompressed capacity. `state` swap is an encrypted file outside release
  snapshots.

GPT, LUKS2, Btrfs, a 1 GiB ESP and two 8 GiB slots are fixed; `esp_mib`, `slot_mib` and
`state_max_gib` are rejected. Validation and capacity checks run before partitioning: state needs
32 GiB plus any state swap. OpenRC activates the generated swap settings; editing the reference
YAML has no runtime effect. Disk image sizing: [BUILD](BUILD.md).

### First boot

> [!NOTE]
> The LUKS prompt always uses the US layout, whatever `console_keymap` says (US by default). On
> Slovak keys, `@` is Shift+2 and Y and Z swap.

1. In the firmware setup, disable Secure Boot and keep VT-d enabled. On Dell, F2 opens setup and
   F12 the boot menu. Connect the boot disk directly, not through a hub or dock.
2. Enter the LUKS passphrase at `Passphrase [1/3]:`. Three failures power the laptop off.
3. Log in as the owner at the tuigreet prompt. Sway starts; the bar reaches `rel <release> good`
   after the health checks. Ctrl+Alt+F2 to F6 offer text logins.
4. Wait until the orange `SETUP` disappears from the bar (10–30 min after a disk image). On a red
   `SETUP failed`, run `sys guests setup` to resume; the log is `/var/log/guests-setup.log`.
5. Attach every trusted device, including the built-in camera, Bluetooth and fingerprint reader.
   Then replace the USB class policy:

   ```sh
   sudo sh -c 'usbguard generate-policy > /etc/usbguard/rules.conf'
   sudo rc-service usbguard restart
   ```

   Success: `sudo devices list` shows no required device blocked. Later changes:
   [Devices](#devices).
6. Connect to Wi-Fi: Super+m → Wi-Fi → Scan → Connect, or `sys wifi connect`.
   Success: `sys wifi status` shows an address.
7. Run `sys selftest`. Success: `~/selftest-YYYYmmdd-HHMMSS.txt` has no FAIL; SKIP is acceptable.

Next: [Keys](#keys), [The bar](#the-bar), [Health and alerts](#health-and-alerts). Logs: `sys logs`;
commands: `sys help`. Repairs: [RECOVERY](RECOVERY.md#recovery-boot-menu).

## System operations

Updates come only as whole signed releases; there is no runtime package manager
([Releases and guests](#releases-and-guests)).

| Task | Command or behaviour |
|---|---|
| Services | `rc-status -a`; `sudo rc-service <name> status` or `restart`; the release fixes which run |
| Logs | `sys logs`; [log locations](RECOVERY.md#8-where-the-logs-are) |
| Edit `/etc` | only the [writable exceptions](ARCHITECTURE.md#53-what-is-writable); other changes need a release |
| Password | `sys security password` (`sudo account password [user]`) |
| Home files | on the state partition, kept across updates |
| Shutdown | `sys power off`; the guests stop first, in order |

Plain `passwd` cannot replace the bind-mounted shadow file. At shutdown, work VMs stop first, then
the browsers and Remmina, `svc`, `wan` and both firewalls. Each guest gets 20 s to stop cleanly
before Incus forces it off.

## Keys

Stock Sway bindings plus the Convergent additions below. Super is the Windows key.

| Key | Does |
|---|---|
| Super+m | `sys`: menu of areas and actions, in a terminal |
| Super+a | one `sys` action by name, in its own terminal |
| Super+d | an app by name: Browser_default, Browser_internal, Browser_temporary, Incus management, Remote, Settings (the `sys` menu), Screenshot, Files, Notes, Foot |
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

## Desktop

Sway, foot, mako and swaylock keep their stock styling, with a black background and bar (foot uses
an 11-point font). Override each in `~/.config/`.

### Displays

To change a screen's scale:

1. Run `sys display set eDP-1 scale 1.3`.
2. Type `yes`, then Enter, within 15 s to keep it. Any other answer, Escape then Enter, or the
   timeout restores the previous layout.
3. Run `sys display save`.

Save the docked and the undocked layout separately. Docking and undocking need no key.

- A profile matches the set of connected screens by make, model and serial, including disabled
  panels. Connector names and order may change.
- Profiles apply at login and whenever the set changes.
- An unknown set enables its screens at preferred modes: `display_scale` if configured, otherwise
  scale 1.3 for the laptop panel and 1 for external screens.
- `save` refuses duplicate identities. `reset` clears only the current set's profile and leaves the
  live layout.

Profiles live in `~/.config/convergent/displays/` and override `display_scale`. An existing
`~/.config/sway/config.d/outputs` overrides them until the first save, which retires it.

### Touchpad

`sys touchpad set` prompts, or takes an option and a value: `sys touchpad set pointer_accel 0.3`.
Settings are validated, apply live to all touchpads and are saved to
`~/.config/sway/config.d/touchpad` for every login. Support depends on the hardware; `sys touchpad
status` shows the libinput settings.

| Option | Values |
|---|---|
| `pointer_accel` | -1 to 1 (pointer speed; default 1, the maximum) |
| `accel_profile` | `adaptive` (default: faster movement goes further), `flat` |
| `tap`, `natural_scroll`, `dwt`, `middle_emulation` | `enabled`, `disabled`; `dwt` disables the touchpad while typing |
| `scroll_method` | `none`, `two_finger`, `edge`, `on_button_down` (the device's scroll button) |
| `scroll_factor` | 0–10 (scroll speed multiplier; default 3, 0 stops scrolling) |

### Screenshots

Print selects an area; Shift+Print takes the focused screen after 1 s (`sys screenshot area` or
`screen`). Each shot is saved as `~/Pictures/screenshots/screenshot-YYYYmmdd-HHMMSS.png` and copied
to the clipboard. Mako shows **Screenshot saved** and the file name for 3 s. A second shot within
the same second is refused.

### Audio and microphone

Leave the microphone enabled in the firmware. Each Sway login waits for PipeWire's default source
and mutes it; `sys audio mic on` or `off` changes that. Config reloads do not reset the mute.

The bar shows an orange `MIC` while the microphone is unmuted, refreshed every 10 s, or a grey
`MIC?` if the state is unknown. `MIC` means permission to record, not recording.

### Files and notes

Files (Super+d) opens Midnight Commander in foot, with its internal editor (`mcedit`) and the
`modarin256-defbg` dark skin. Notes opens Vim's directory list in foot at `~/Documents/notes`,
creating it if needed. Keep notes as plain `.md`: `:e name.md` opens one, `:w` saves.

## The sys tool

The form is `sys AREA [ACTION] [ARGS]`. The first action in each row of the table is the default.
An unknown second word becomes an argument to that default: `sys backup /mnt/x proj` works, but
`sys wifi foo` is a usage error. Missing arguments are prompted for; partial lists are usage
errors. `sys help` lists actions and aliases. `*` marks actions that ask for `yes` (default No);
a prompt left unanswered for a minute counts as No.

`sys` without arguments (Super+m) opens an fzf menu: areas on the left; a dashboard, the selected
status and commands on the right. The dashboard refreshes on entry; narrow panes hide the logo.

| Menu key | Does |
|---|---|
| Enter | open or run the selection |
| Esc | go back; quit from the area list |
| typing | filter |
| Alt+Enter | run what was typed (`area action args`, or `action args` inside an area) |

| Area (alias) | Actions, default first |
|---|---|
| `wifi` | `status`, `scan`, `connect [SSID]`, `hidden [SSID]`, `disconnect`, `forget [SSID]` *, `test` |
| `portal` | `status`, `on`, `off` |
| `wired` | `status`, `attach [0bda:8153 SERIAL]` *, `remove` * |
| `dns` | `list`, `add [NAME IPv4]` *, `remove [NAME]` *, `allow [DOMAIN]` *, `unallow [DOMAIN]` *, `push` |
| `firewall` (`fw`) | `status`, `rebuild` *, `maintenance` *, `undo` *, `capture INTERFACE-OR-SEGMENT SECONDS` |
| `bluetooth` (`bt`) | `status`, `on`, `off`, `scan`, `pair [MAC]`, `connect [MAC]`, `disconnect [MAC]`, `forget [MAC]` * (device picker without MAC) |
| `usb` | `status`, `allow N\|ID` *, `enrol` *, `review`, `revoke RULE` * |
| `audio` | `status`, `out ID`, `vol N` (0–150), `mute`, `mic on\|off`, `micmute` |
| `camera` | `status`, `on`, `off` |
| `display` (`disp`) | `status`, `bright N\|+N\|-N`, `set OUTPUT mode\|scale\|position\|enable\|disable [VALUE]` (15 s preview), `save`, `reset` *, `watch` (session hook) |
| `keyboard` (`kb`) | `status`, `set LAYOUTS` (e.g. `us,sk(qwerty),ru`), `next` |
| `touchpad` | `status`, `set OPTION VALUE` (apply and save) |
| `screenshot` (`shot`) | `area`, `screen` (save to `~/Pictures/screenshots` and copy to the clipboard) |
| `browser` (`br`) | `status`, `def`, `tmp`, `int`, `incus` |
| `remote` | `open`, `status`, `close` |
| `security` (`sec`) | `status`, `alerts` (`sys alerts`), `events`, `check`, `report`, `password` |
| `update` (`up`) | `status`, `check`, `install` *, `usb [MOUNTPOINT\|DEVICE]` * |
| `guests` | `status`, `setup`, `update` |
| `power` | `status`, `ac`, `battery`, `charge off\|55-100`, `thermal quiet\|balanced\|performance`, `lock`, `logout` *, `reboot` *, `off` * |
| `backup` | `run [MOUNTPOINT PROJECT]` |
| `logs` | `host` (`/var/log/messages`), `debug` (beta only), `services` (`rc-status -a`) |
| `selftest` | `run` |

DNS edits, wired assignment and firewall maintenance ask inside the action, after showing the
change or checking health.

## The bar

The bar refreshes every 5 s, its inputs every 10 s and its alerts every 30 s. `|` separates
blocks:

```
CPU 7% 1.2-4.5GHz 61/74C | RAM 3.2/15G SWP 0.0/8G | NET tx 0.8 rx 12.4 Mb/s
WLAN:home--WAN--[FW1 FW2]--laptop--SVC--BR:2 RM:off | rel 0.1.0 good | NL | 0 1 0 | PORTAL
US | UP 3d 03:41 | Tue 04/08 15:33:02 | BAT 87% -
```

| Block | Shows | Look or fix with |
|---|---|---|
| `CPU` | busy percent, lowest-highest core clock (every 5 s), package/hottest temperature (every 20 s); `-` if missing | `sys power status` shows sensors and profile |
| `RAM`, `SWP` | used/total GiB; RAM excludes reclaimable cache and what guests hold (below) | Grafana, Guests |
| `NET` | transmit/receive Mb/s on the default-route interface (route refreshed every 10 s) | `sys wifi test` |
| Topology | uplink, `wan`, both firewalls, `svc` and browsers (below) | `sys guests status`; RECOVERY 5, 6 |
| `rel` | booted version (release ID on older images); grey `good` if the release passed its checks this boot, else red `UNBLESSED` | `sys update` |
| `NL` | click to pause or resume the idle lock (orange while paused); `NL!` (red): swayidle missing | `sys power lock` |
| `MIC` | default microphone unmuted (orange); hidden when muted; `MIC?` (grey) if unknown; every 10 s | `sys audio mic off` / `on` |
| Alerts | firing alerts: critical (red), warning (orange), info (white); every 30 s | click for the list, or `sys alerts` |
| `RM:on/off/?` | Remmina running, stopped or unknown; stale status is unknown | `sys remote status`, `sys remote close` |
| `PORTAL` | portal mode on (orange) | `sys portal off` |
| `CAM`, `CAM!` | camera enabled, or driver still loaded after disabling (orange); not a recording indicator | `sys camera status`, `sys camera off` |
| `SETUP` | guests being created (orange); `SETUP failed` (red) | `sys guests setup` |
| `GUESTS` | downloaded guests being applied (orange); `GUESTS failed` (red) | `sys guests update` |
| layout, `UP`, clock | keyboard layout (every 10 s), uptime, local date and time | `sys keyboard next` |
| `BAT` | capacity; `+` charging, `-` discharging (orange below 30 %, red below 15 %); `AC BAT` on mains but not charging; `AC` without a battery | `sys power status` |

RAM is memory in use (`MemTotal - MemAvailable`) minus what the guests hold. `check status` sums
the guests' cgroups, without file cache and VM processes, every minute. RAM shows `?` while that
sum is missing or over three minutes old.

The alert counters show grey `? ? ?` when `svc` cannot be read, including during SETUP until `svc`
is up. When `/var` is lost or read-only, a red `state disk lost or read-only: reboot` replaces
them. Alert history is in Grafana: `sys browser int`. `AC BAT` means the battery is full or at its
charge limit.

Topology starts with the uplink: `WLAN:<network>` (green connected, red with no network, grey when
`wan` does not answer; names over 16 characters are cut) or `ETH` for a passed-through wired NIC.
`WAN` is green with an uplink, orange without one, red when `wan` is down. Each firewall is bold
bright green as CARP `MASTER`, dim green as standby, orange when its CARP interfaces disagree, red
when down. `SVC` is green or red; the host name is green. `BR:n` counts running browser containers
(grey at zero). Cron refreshes the topology every minute; older than three minutes, it turns grey.

The idle-lock pause is the file `$XDG_RUNTIME_DIR/nolock`; the lid lock still works.

## Browsers

```sh
browser def|tmp|int [url]
browser tmp --portal [url]
```

Run `browser` as the owner in the Sway session; it needs no password. `sys browser def|tmp|int`
(or the menu) opens one without a URL; `sys browser` lists the running ones. Each browser is
Chromium in its own container, with a restricted Wayland socket and playback-only audio. Its
window title starts with `[role]`.

| Role | For | State |
|---|---|---|
| `def` | everyday browsing | profile and downloads kept in a 4 GiB volume |
| `tmp` | anything untrusted; several at once | container deleted on close; history, cookies and cache cleared |
| `tmp --portal` | captive portals; opens `http://<uplink-gateway>/` unless given a URL | container deleted on close; owns portal mode |
| `int` | Grafana; Incus after a session unlock | Grafana profile kept in a 512 MiB volume |

The Incus session in `int` uses its own profile in tmpfs, gone when `int` stops; the UI key lives
only in session memory. A plain `int` browser starts Grafana in `svc` and stops it on close; the
Incus session does not. Log in to Grafana as `owner`; the password is in
`/var/lib/convergent/guests/tls/admin-password` (`sudo cat` it).

Success: a `[def] …` window and `BR:1` in the bar. The browser refuses:

- URLs other than HTTP and HTTPS; `int` accepts only its Grafana and Incus launch URLs.
- a second `def` or `int` with a URL (without one, the open window is raised).
- a second portal browser; normal `tmp` runs many at once.

Downloads stay in the container; no action moves a file out. Policies: DNS-over-HTTPS off, no
sync, no password manager, no telemetry. `int` and both `tmp` modes allow no extensions.
Chromium's default appearance is kept.

Super+b and Super+Shift+t show the reason for a failure at the top of the screen. Full output:
`$XDG_RUNTIME_DIR/browser-def.*.log` or `$XDG_RUNTIME_DIR/browser-tmp.*.log`, one file per launch.
`sys browser` launches log to `$XDG_RUNTIME_DIR/sys-browser-<role>.*`, replacing that role's older
logs. A launch that fails within 3 s prints the reason and removes its log.

Not built: printing, and a handler that sends links from other programs to `tmp`. Network
addresses and portal isolation: [ARCHITECTURE 3.5](ARCHITECTURE.md#35-browsers).

### Incus management

The Incus UI administers everything, including the host's infrastructure. Its certificate is
locked behind a passphrase.

1. Close `int`.
2. Run `sudo incus-ui setup` once and choose a passphrase of at least 12 bytes.
3. Open **Incus management** (Super+d), or run `sys browser incus` (`incus-ui open` in a host
   terminal).
4. Enter the passphrase. `int` opens `https://100.80.1.10:8443/ui/`. Keep the launcher terminal
   open for the session. Each session first resets `int` to its installed image (state and
   bookmarks stay), so it starts a little slower than Grafana.
5. To lock it again, close the entire `int` browser; closing only the Incus tab is not enough.

A plain `browser int` opens Grafana without the administration key. Certificate administration
uses normal sudo authentication; only the fixed session launcher is passwordless.

| Command (with `int` closed) | Does |
|---|---|
| `sudo incus-ui rotate` | replaces the 90-day credential and asks for a new passphrase |
| `sudo incus-ui revoke` | stops an unlocked `int` session, removes its trust and stored bundle; setup is needed again |

Failures: [RECOVERY 15](RECOVERY.md#15-incus-ui-session-or-passphrase-failure).

## Remote desktops

Choose **Remote** (Super+d) or run `sys remote open`. Each open asks for a non-empty keyring
password (twice on first use). Cancelling or a wrong password closes Remmina. `sys remote status`
reports the state; `sys remote close` stops the container and locks the keyring. Profiles and
encrypted credentials survive updates; there is no plaintext fallback.

Use numeric work addresses: SSH (TCP 22), RDP (TCP/UDP 3389), VNC (TCP 5900–5999) or ping. The
firewalls and the gateways are excluded. Cage confines clipboard transfers to the remote session;
host copy and paste and audio recording are unavailable, playback is allowed.

For RDP file transfer, select `/share` as the shared folder. To share directly with a VM:

1. Stop the VM.
2. In the Incus UI, attach the existing filesystem volume `share` from pool `default` to it. The VM
   must support and mount a filesystem share; it is not a shared block disk.
3. Match guest UID/GID 1000, or grant suitable ACLs.
4. Detach the volume when finished.

The owner project needs `features.storage.volumes=false` to use default-project volumes; move
existing private volumes before changing that option. The volume is created at 4 GiB; resize it in
the Incus UI if needed. Stop every attached instance throughout a backup or restore.

Repairs: [RECOVERY 16](RECOVERY.md#16-remmina-session-or-keyring-failure).

## Wi-Fi

`sys wifi` controls `wan`, which owns the radio, over SSH; iwd roams between known networks.

### Connect

1. Run `sys wifi connect`. It lists the scanned networks with security and signal.
2. Pick one: type to filter, Enter selects, Esc cancels, Ctrl+u clears the filter, Alt+Up/Down
   scrolls its status.
3. Enter the passphrase (8–63 bytes); leave it empty for a known or open network.

Success: `sys wifi status` shows an address. Association without an IPv4 address reports a DHCP
failure.

`sys wifi connect 'SSID with spaces'` skips the list. A scan waits up to 15 s for results.
`sys wifi test` checks host DNS and prints [wan's diagnostic log](RECOVERY.md#8-where-the-logs-are):
the last 200 lines, at most 32 KiB.

To resume automatic connection to known networks, restart iwd. This interrupts the current Wi-Fi
connection:

```sh
sudo ssh -F /etc/convergent/ssh_config wan 'wifi auto'
```

An upstream lease that overlaps 100.80.0.0/16 is refused and raises `UpstreamOverlap`. For a wired
uplink, see [Wired uplink](#wired-uplink).

### Hidden networks and changed passphrases

- `sys wifi hidden` asks for a name that is not in the scan. Alt+Enter in the list does not join an
  unscanned name.
- Saved hidden networks reconnect from the scan cache first, then rescan if needed.
- After a network's passphrase changes, run `sys wifi forget` on it first. Otherwise the first
  connect fails on the old passphrase and a retry succeeds.

### What survives a wan replacement

Credentials are stored in `wan`. A replacement also
stages root-only copies on encrypted host storage, which can remain until recovery or cleanup
completes. A saved profile carries over only if it is a WPA-PSK, SAE or open network in the form
iwd writes for a joined one (at most 4 KiB; no EAP). Others are logged and must be joined again.

## Captive portals

1. Join the network (Wi-Fi or wired).
2. Run `sys portal on`, or `browser tmp --portal [url]`. The portal browser opens
   `http://<gateway>/`, the selected uplink's DHCP gateway, and the bar shows `PORTAL`.
3. Log in on the portal page.
4. Close the browser, or run `sys portal off`.

Portal mode also ends after 30 minutes. Without a usable gateway, give an uplink-local HTTP or HTTPS
URL. `sys portal status` reports the reason and each guest's state.

Limits:

- Destinations are ports 80 and 443 in the selected uplink subnet only (/8 to /30; a /31 or /32
  lease is refused).
- DNS uses only the uplink's first nameserver, an IPv4 address outside 100.80.0.0/16. An unusable
  first resolver refuses activation, even if later ones work.
- Portals that intercept public HTTP requests or host their login page publicly are unsupported.
- A new launch needs stale rules closed on all three guests. Cron retries a partial closure or an
  abandoned session each minute.

Root commands, for diagnosis:

```sh
sudo portal on [A.B.C.D/LEN]   # expires after a minute without browser ownership
sudo portal off                # a failed closure retries each minute
sudo portal status             # per-node state, aggregate on/off/mixed/unknown and reason
```

## Devices

### USB

A fresh disk image allows whole USB classes (HID, storage, hubs). `sys usb enrol` replaces that
with one rule per trusted device:

1. Attach the devices and hubs you trust.
2. Run `sys usb enrol` and review the attached devices.
3. Answer `yes` for each trusted device.
4. Confirm the new policy.

Nothing is saved before the confirmation; declined devices stay blocked.

> [!WARNING]
> Do not interrupt `sys usb enrol` after confirming: an interrupted save can leave the policy half
> applied. Run `sys usb enrol` again.

| Command | Does |
|---|---|
| `sys usb status` | lists blocked USB and unauthorized Thunderbolt devices |
| `sys usb allow N\|ID` | allows a **device number** or a Thunderbolt ID; asks `yes` |
| `sys usb review` | shows saved rules, even unplugged, and attached decisions |
| `sys usb revoke RULE` | removes an allow **rule number** and denies that device |

`revoke` overrides overlapping allowances; enrol first if only broad class rules exist. `enrol` and
`revoke` restart USBGuard, which can disconnect input or storage. USB rules persist in
`/etc/usbguard/rules.conf`. The root tool:

```sh
sudo devices list
sudo devices allow <number>    # permanent USB; warns for input, storage and network
sudo devices allow tb <id>     # Thunderbolt tunnel until unplugged
```

### Wired uplink

1. Approve the dock's Realtek USB device: `sys usb allow <number>`.
2. Run `sys wired status` and note its serial.
3. Run `sys wired attach 0bda:8153 <serial>` (or answer the prompts), and confirm the vendor,
   product and serial. Empty or ambiguous serials fail.

Only that identity passes to `wan`, as `eth1`. `wan` prefers the wired uplink and retries DHCP on a
replug within its minute check. A replug returns within about two minutes: the checker re-adds the
role once `wan` has not held the NIC for two runs. It does so three times an hour, then alerts and
retries once the hour has passed.

- `sys wired remove` removes the assignment and automatic attachment; the USBGuard approval stays.
- Unplugging alone keeps the assignment.
- `sys usb revoke` or `enrol` removes the role once no rule allows the NIC.

The host has no USB network drivers and does no DHCP or addressing. After moving an adapter refused
for an [overlapping lease](#connect) to a safe network, retry its DHCP. Only a safe lease clears
the refusal; `sys wifi test` shows retry advice while it holds.

```sh
sudo ssh -F /etc/convergent/ssh_config wan 'check retry'
```

### Bluetooth

Bluetooth starts off.

1. Run `sys bluetooth on`.
2. Run `sys bluetooth pair` in a terminal. It scans for 10 s and lists MAC and name.
3. Pick a device. bluetoothctl opens.
4. Type `pair <MAC>`, answer any PIN prompt, then type `quit`.

A paired device is also trusted. `connect`, `disconnect` and `forget` pick from the current list;
`sys bluetooth scan` refreshes it. Explicit MACs are validated. The picker is fzf in a terminal,
otherwise bemenu; Escape cancels. `forget` asks `yes` before the selection. `sys bluetooth` shows
power and known devices.

### Serial console

1. Find the adapter's number with `sys usb status`.
2. Approve it with `sys usb allow <number>`.
3. Open it with the required baud rate:

   ```sh
   tio -b 115200 /dev/ttyUSB0
   ```

CDC ACM adapters use `/dev/ttyACM0`. Exit with Ctrl+t, then q. The owner is in group `dialout`
from the install or the first updated boot.

### Camera

The camera starts off. `sys camera on` saves the choice and loads the drivers; `sys camera off`
saves the denial, then unloads them without force. If the camera is busy, close the application
and retry. `sys camera status` shows the choice and the video-core state.

`CAM` in the bar means enabled, not recording; `CAM!` means still loaded although off. The choice
persists in `/var/lib/convergent/devices/camera` and follows slot `/var` snapshots. USB cameras
also need USB approval. Not built: meeting compartments and screen sharing.

## DNS: blocklist and own records

| File | Holds |
|---|---|
| `/var/lib/convergent/dns/allow` | blocklist exceptions, one domain per line, `#` comments |
| `/var/lib/convergent/dns/records` | own records, as Unbound `local-data` and `local-data-ptr` |
| `/etc/convergent/dns.conf` | weekly blocklist source and limits |

| Command | Does |
|---|---|
| `sys dns list` | shows records, exceptions and the last successful push (UTC) |
| `sys dns add printer.home.arpa 192.168.1.50` | adds an A record |
| `sys dns remove printer.home.arpa` | removes a record |
| `sys dns allow example.org` | exempts a domain and its subdomains from the blocklist |
| `sys dns unallow example.org` | removes the exception |

Each edit shows a diff and asks `yes`; no answer within a minute is No. Names are lowercase; duplicate, invalid and built-in
conflicting names are refused. Non-A records, including their removal, need manual editing.
Records grant no firewall access.

```sh
sudo dns-push          # download, validate and push; needed before the first local push
sudo dns-push local    # push the current owner files with the stored blocklist; also sys dns push
```

A failed push restores both firewalls; an interrupted recovery waits for both.

## Firewall maintenance

### Status

`sys firewall status` (`sys fw`) shows the registered CARP roles, PF states, Unbound and the last
DNS push, including unreachable firewalls and pending recovery.

Daily use needs no firewall shell. To inspect one, open it with
`sudo ssh -F /etc/convergent/ssh_config fw1`, then run `pfctl -sr` or `ifconfig carp`. A manual
policy reload is `/usr/local/libexec/convergent/fw-pf-reload`; a failed load leaves forwarding off.

### Maintenance and undo

1. Run `sys fw maintenance`. It checks coherent roles, PF, pfsync defer, Unbound and local DNS,
   asks before demoting the `MASTER`, then verifies that the peer took over fully.
2. Do the maintenance.
3. Run `sys fw undo`. Both firewalls must be healthy. Success: `fw1` is `MASTER` and `fw2` is
   `BACKUP` on every registered segment.

A failure or interruption after the demotion undoes it. One while the demotion is uncertain keeps
the journal: run `sys fw undo`. If the peer then loses its WAN probes, it demotes equally, and
`MASTER` can return to the firewall in maintenance until the WAN recovers.

End maintenance before guest updates. If a firewall is unreachable, restore its management or
rebuild it, then retry. Remote work can outlive SSH; retry once it finishes.

> [!WARNING]
> Never remove `/var/run/convergent-maintenance.lock`; its PID does not prove ownership. Reboot
> firewalls that still use the old symlink lock before these operations.

### Rebuild a firewall

`sys firewall rebuild fw1|fw2` (`sudo guests rebuild fw1|fw2`) recreates one firewall from the
installed images and seed. Before you run it:

- Finish updates and handoffs.
- The peer must be healthy and own every segment. If the target still runs, coherent CARP on
  every segment also suffices.
- Maintenance may name the target; run `sys firewall undo` afterwards.

The rebuild waits for the guest and DNS locks, checks and seeds the replacement, restores normal
roles and pushes the stored DNS. It first starts a `wan` or `svc` that Incus left stopped or
paused. A target that Incus cannot stop is ended by its verified QEMU pid. Browsers may stay open.
After an interruption, repeat the same command to resume. How the pair is replaced:
[ARCHITECTURE 7.2](ARCHITECTURE.md#72-update).

## Releases and guests

Channels and promotion: [BUILD, Channels](BUILD.md#channels). `sys update status` (`slot status`)
shows each slot's version and release ID; the release ID orders releases, and reports carry both.

| Phase | What runs | The bar shows | What you do |
|---|---|---|---|
| 1. Download | `sys update install` verifies and downloads host and changed guests | | answer the prompts |
| 2. Slot write | `slot write` fills the other slot | | accept the reboot offer |
| 3. Boot | health checks, then the release is marked good | `rel … UNBLESSED`, then `good` | wait |
| 4. Guests | `guests apply` after the bless | orange `GUESTS` | close browsers; on `GUESTS failed`, `sys guests update` |
| 5. Baseline | the checker compares with the accepted baseline | `CheckerFailed` until accepted | [accept the new baseline](#accept-the-new-baseline) |

The guest step waits up to 30 min for the release to become good. Only one guests operation runs
at a time; another waits up to 10 min, then prints `another guests operation is running`. A release
that never becomes good falls back to the previous one
([RECOVERY 2](RECOVERY.md#2-a-new-release-does-not-boot-or-does-not-become-good)).

### Host updates

1. Run `sys update check`. It reports the newest release or "up to date", and the age of the signed
   metadata; over 30 days is stale.
2. Run `sys update install`. It verifies and downloads the host and changed guests, writes the
   other slot and offers a reboot.
3. Type `yes` to reboot.
4. Wait for `good`, then for `GUESTS` to clear.
5. [Accept the new baseline](#accept-the-new-baseline).

The root equivalent is `sudo fetch-release`; `fetch-release check` only reports and refreshes the
evidence. When the booted release is the newest and only guests differ, `sys update install`
fetches and applies them at once.

Host writes need the booted slot good and a release newer than both the booted and the highest
good release; `sudo slot status` shows both. On online installs, Overview's Security / Updates card
degrades two days after the last update check. Installs without online updates show DEGRADED until
`sys update check` runs once after each install or USB update.

Failures: [RECOVERY 12](RECOVERY.md#12-an-online-update-fails). Mechanism and counting:
[ARCHITECTURE 7.2](ARCHITECTURE.md#72-update). Going back by hand:
[RECOVERY 3](RECOVERY.md#3-go-back-to-the-previous-release-by-hand).

### USB updates

Copy the release directory to a FAT32 or exFAT USB filesystem (`sys update usb` also takes ext4 and
Btrfs, and refuses any other filesystem). It holds:

- `latest`, `latest.sig`, `manifest`, `manifest.sig` and `slot.img`
- both release `.efi` files
- `guests/`, `guests.manifest` and `guests.manifest.sig`
- `remmina.manifest` and `remmina.manifest.sig`, if present

Once guests exist, a `latest` that names guests requires their signed manifest.

1. Plug in the USB disk and find its number with `sudo devices list`.
2. Approve it with `sudo devices allow <number>`.
3. Run `sys update usb` and pick the release by number.
4. Accept the reboot offer, then continue as for [host updates](#host-updates) from step 4.

By hand:

```sh
sudo mkdir -p /run/usb && sudo mount -o ro /dev/sdX1 /run/usb
sudo fetch-release usb /run/usb/<release>
sudo umount /run/usb && sudo reboot
```

When upgrading from a release without guest USB delivery, run `sys update usb` again after the boot
with the same disk. A host-only USB leaves legacy `web`/`admin` objects untouched; `def`, `int` and
`tmp --portal` need guest delivery.

`slot write` verifies the manifest against the embedded key. An unsigned write needs
`sudo env CONVERGENT_UNSIGNED=1 slot write <dir>`. The menu offers this only for a release without
`manifest.sig` on an image without a trusted key. On such an image, write a signed release with that
command by hand.

### Guest updates

```sh
sys guests status    # name and state of each guest
sys guests update    # apply pending downloads
```

Close the browsers and Remmina first. After the host reboot and bless, guests apply in the order
`svc`, `wan`, `fw`, `browser`, `remmina`. While legacy `web`/`admin` objects exist, `browser` goes
first and migrates them to `def`/`int`, without command aliases. Replacements keep state,
bookmarks and logins.

- With a browser open, the update is deferred and the tool prints
  `a browser is open; close it, then sys guests update`.
- An interrupted browser update blocks browser launches until retried; an interrupted Remmina
  update blocks only Remmina.
- A browser update advances future `tmp` and portal images. `def`/`int` normally replaces one
  instance; a migration updates both.
- Unused old images are pruned only after the commit and the alias release.
- Staleness starts with the update. A full kind update clears it after recording; a `def`/`int`
  update leaves the browser generation stale.
- A recording failure stays pending; the next install reuses valid staged data or downloads it.

With no update pending, `sys guests update` also starts a `wan` or `svc` that Incus left stopped
(after ten crashes in a minute) or paused (on a full disk), with a forced restart. If three tries
fail, it names the manual rebuild.

Manual updates need a good host and closed browsers and Remmina. Keep the release layout: `$g` is
`<release-dir>/guests`, with the unpacked images, and the signed `guests.manifest` (or
`remmina.manifest`) and its `.sig` sit in `<release-dir>`. The manifest must match the booted
release; its identity binds the checksums and the supplied Incus profiles.

```sh
sudo guests update fw  $g/fw      # fw2, failover, fw1
sudo guests update wan $g/wan
sudo guests update svc $g/svc
sudo guests update remmina $g/remmina
```

The command also takes `browser`, `def` and `int`. For an unsigned build you trust locally, append
`--trusted-local` to bypass authentication. Snapshots and rollback:
[ARCHITECTURE 7.2](ARCHITECTURE.md#72-update).

### Accept the new baseline

After a host update, `CheckerFailed` is expected: the manifest release, kernel and verity hash
differ from the accepted baseline. After the slot write, `fetch-release` keeps the verified manifest
in `/var/lib/convergent/release-guests`, beside the installed firewall hashes.

1. Wait until `GUESTS` clears from the bar.
2. Run:

   ```sh
   sudo check accept /var/lib/convergent/release-guests
   ```

Only the latest written release is kept: accept each release before writing the next. Updates
written by 0.1.5 or older keep no manifest; accept with the release directory from the build host
or the USB disk. Acceptance requirements:
[Security check and baseline](#security-check-and-baseline).

### Work VMs

Create work VMs in the Incus UI, in project `owner`; `sys` does not manage them. Select one of the
owner's NIC-only profiles `work-dom-dev-a`, `work-dom-dev-b`, `work-dom-jhn-a` or `work-dom-jhn-b`
(the configured family names), and supply disks and resources separately. The owner project shares
the managed networks and keeps its own profiles.

Inside the guest, use DHCP, or static .1–.48 with /26 and gateway and DNS .62, in the
[selected prefix](ARCHITECTURE.md#41-addressing). Incus NIC settings do not configure the guest OS.

- Work VMs reach each other within their own VLAN. Routing to other work VLANs is blocked, even
  within the same family. System segments are blocked.
- Internet works; home-LAN access needs canonical RFC1918 prefixes baked into the release.
- Topology updates stop both firewalls; a failure restores both old images. A hash mismatch keeps
  work access closed.
- Shutdown preserves ephemeral work VMs. Running work VMs with default or `last-state` autostart
  return at the next boot.

`work-` profile names are reserved. After a domain rename, a NIC-only `work-` profile left behind
is renamed to its VLAN's new profile, or removed when unused. One still used by an instance, with no
new domain profile on its VLAN, stops the update until that instance detaches it; the message names
the command.

Work profiles turn the Incus guest API off and deny Btrfs subvolume ioctls to work containers.
`incus exec`, `incus file` and the console still reach a work VM through its agent; only
`/dev/incus` inside the guest (`user.*` keys, ready state) stops answering. Set
`security.guestapi=true` on an instance that needs it.

## Health and alerts

### Alerts that need you

`sys alerts` (`sys security alerts`), or a click on the bar counters, lists the firing alerts with
severity, name, summary and active-since time. Read alert names, not counts.

| Alert | Cause | What to do |
|---|---|---|
| `SecureBootNotVerified` | Secure Boot is off or unverifiable | expected while Secure Boot is off ([BUILD, Status](BUILD.md#status)) |
| `CheckerFailed` | the checker reported a failure, for example after an update | `sys security report`; [accept the new baseline](#accept-the-new-baseline) |
| `PfRuleStatesFull` | a forwarding rule hit its state cap; its new flows drop unlogged | Grafana, Network |
| `WanConntrackHigh` | `wan`'s NAT table is over 80 %; new NAT flows drop when it fills | Grafana, Network |
| `CrashRecorded` | an unacknowledged kernel crash record | [RECOVERY 13](RECOVERY.md#13-a-kernel-panic-or-crashrecorded-alert) |

Secure Boot off also raises `CheckerFailed`. No accepted baseline also produces `CollectorBroken`.
`FirewallRulesetDrift` needs an expected hash and reports mismatches. Invalid or unavailable
responses report errors. All alerts: [ARCHITECTURE 8](ARCHITECTURE.md#8-observability).

### Dashboards

`sys browser int` opens Grafana: Overview, Network, Guests, Host, Security and Monitoring. Shared
navigation, project and instance selectors and source labels tell current tables from history. A
dash means no data; footers state collection limits.

- CARP annotations are opt-in. Explore · all logs adds routine audit and full kernel traces.
- Security shows the latest 50 events in range: login and sudo, USB and AppArmor, firewall
  takeovers, guest and host updates, bless and fallback.
- The connection supplies the host identity; app and message remain sender claims.

### Security check and baseline

```sh
sys security check                    # sudo check; report in /var/lib/convergent/check/last
sys security report
sudo check accept <release-dir>       # trusted baseline, Secure Boot on and out of Setup Mode
sudo check accept-fw <guest-dir>/fw   # updated firewall hashes, same Secure Boot requirement
```

- Baseline input needs `manifest` and `guests/fw/fw{1,2}.{pf,rules}.sha256`.
- Acceptance needs `def`, `int` and Remmina to exist: open and close each once first.
- Accept again if the baseline lacks the profile of `tmp` or Remmina.
- The check fails without a baseline or with Secure Boot off.
- Acceptance does not verify manifest signatures: verify the release yourself first.

Check and accept wait up to 120 s for a minute run's locks. The autostart scan gives up after
120 s and reads at most 64 MiB of each owner file; a larger file fails the check, and the report
names it. Checks and timings: [ARCHITECTURE 8](ARCHITECTURE.md#8-observability).

### Self-test and events

`sys selftest` authenticates sudo once and writes `~/selftest-YYYYmmdd-HHMMSS.txt` with bounded
PASS, FAIL and SKIP checks.

`sys security events` works without `svc`. It shows up to 100 matches per file from the last
5000 lines of the current host messages and audit log, with source and original timestamp.

- It neither merges by time nor reads rotated logs; missing files are reported.
- Minute probes miss brief firewall transitions; use Grafana for those.
- Audit and PAM may report a login twice.
- A fallback shows as an older boot with an exhausted newer UKI.

Cron and anacron mail is disabled; the jobs and their logs still run.

### Release and network evidence

Security → Release compares the booted and latest signed release IDs, inventory versions, and
advisories and fixes. `fetch-release check` refreshes it without notifications. Read the
verification and the scan and check ages: missing, invalid or unavailable is unknown, and over two
days warns. Versions describe releases, not live guests after partial updates; pruned installed
releases may lack status.

Network shows registry CARP segments, parent traffic, pf and WAN conntrack use, Unbound recursion
and SERVFAIL, Wi-Fi signal, bitrate and observed roams, and firewall-to-WAN RTT and loss. These
probes do not prove Internet access. Blocked rankings count sampled logged packets, capped at five
per second per firewall.

To capture packets, run from the owner login:

```sh
sys firewall capture vio4 15    # interface or segment, then seconds
```

It authenticates sudo, selects the coherent `MASTER` and saves a private pcap in `~/captures`.
Segments resolve to their parent interfaces. Bounds: 1–60 s, 1536-byte snapshots, 32000 packets,
below 50 MB. A capture does not follow failover. Delete captures you do not need; they may hold
payloads.

Missing evidence: [RECOVERY 17](RECOVERY.md#17-missing-release-or-network-evidence).

### Diagnostics, beta only

`sys debug` (Logs → debug) shows a signed diagnostic's purpose and expiry and asks before running
it as root. Expired requests fail. Replay rejection applies to
the current `/var` history; rollback can permit a still-valid diagnostic again, with fresh consent.
Limits: five minutes and 8 MiB of output. The script's failure status is kept; a timeout returns
124 and a forced kill 137.

Read the printed root-only `/var/lib/convergent/debug/<id>.txt` with `sudo less`. A second `yes`
permits the encrypted, laptop-signed upload. `sudo debug key` prints the laptop public key. Builder
side: [BUILD, Diagnostics](BUILD.md#diagnostics).

## Backups

Needs:

- an unlocked LUKS USB disk mounted on a root-owned directory whose parents are all root-owned and
  not writable by others (sticky ones such as `/tmp` excepted), not the laptop disk;
- the owner project (`owner`, created by setup; never `default`).

A backup writes one generation, `convergent-backups/backup-<UTC>`:

| Item | Holds |
|---|---|
| `home.tar` | a snapshot of `/home` |
| `etc.tar` | the writable `/etc` files |
| `projects/<owner>/instance-<name>.tar.gz` | each owner container |
| `projects/<owner>/profiles.json` | the owner's profiles |
| `projects/<project>/<pool>/` | custom filesystem and ISO volumes of both projects, including `remmina-state` and `share`; `default` ones without their update snapshots |
| `grafana-secrets/` | Grafana's matching `admin-password` and `secret-key` |
| `machine-id`, `EXCLUDED`, `SHA256SUMS` | the laptop's identity, what was left out, checksums |

VM instances, custom block volumes, system guest instances and the rest of `/var/lib/convergent`
are excluded; `EXCLUDED` lists them.

1. Close the browsers and Remmina.
2. Stop every instance that uses `share`, and keep it stopped until the backup ends.
3. Unlock and mount the USB disk.
4. Run `sys backup <mountpoint> owner`. Without arguments it asks for `Mounted encrypted external
   disk:` and `Owner Incus project:`. The root tool is `sudo backup [<mountpoint> <owner-project>]`.
5. Wait for `readback verified`.
6. Unmount and close the disk before unplugging it.

The backup waits up to 120 s for a running guest operation, then refuses. It verifies the readback
and keeps three generations. One disk serves one laptop: each generation records `machine-id`, and
a disk holding another laptop's backups is refused. After Start over, restore `etc/machine-id` from
`etc.tar` to keep using the disk.

Restore: [RECOVERY 19](RECOVERY.md#19-restore-a-backup).

## Power and locking

The screen locks after `idle_lock_minutes` idle (default 10) and turns off one minute later. `NL`
in the bar pauses these idle actions; the lid and manual locking still work. Closing the lid also
turns the internal panel off until it opens; an external monitor stays on. `sys power lock`
locks now. Privileged Sway idle inhibition stops browsers from suppressing the lock.

The lock screen takes the owner's login password. A forgotten password is reset from the Recovery
menu ([RECOVERY](RECOVERY.md#recovery-boot-menu)).

| Command | Does |
|---|---|
| `sys power ac`, `sys power battery` | applies a CPU preference and cap now (`sudo power ac\|battery`) |
| `sys power charge 80` | charge ends at 80 %, starts at 75 %, where supported; range 55–100 |
| `sys power charge off` | default; restores 100/95 |
| `sys power thermal quiet\|balanced\|performance` | selects a firmware profile; firmware controls the fans |
| `sys power status` | the applied profile, sensors, unsupported thresholds and available choices |

Boot and AC events also apply the power profile. AC uses `balance_performance`, battery uses
`power`; both apply `cpu_cap_khz` (default none). A manual choice lasts until the next power-source
event. Only changes and failures are logged.

Dell's `charge_types` selects Custom or Standard. A limit does not discharge a battery that is
already fuller. There is no thermal override until you select one. Charge and thermal choices in
`/var/lib/convergent/power/` persist across boots and AC events and follow slot `/var` snapshots.
Missing controls are skipped. Tuning constraints:
[ARCHITECTURE 11.2](ARCHITECTURE.md#112-proposals-not-enabled).
