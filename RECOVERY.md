# Recovery

Run commands on the laptop as owner unless stated. Each recipe includes a success check.

## Recovery boot menu

Press an arrow key during the three-second boot menu to stop the timer. Pick the release and slot
ending in `(Recovery)`, e.g. `SLOT A | Gentoo <version> - <kernel> (Recovery)`. Enter the LUKS
passphrase (US layout); three wrong attempts power off. Recovery requires a bootable verified release
and normal state unlock.

The menu shows the release, slot and read-write data at `/run/cv-state`:

1. Root shell. Verified root is `/sysroot`; encrypted data and writable `/etc` files are under
   `/run/cv-state`. `exit` returns to the menu.
2. Reset owner password. Enter 12–256 bytes twice for uid 1000. Uses SHA-512 crypt;
   `account password` in the running system uses yescrypt.
3. Continue booting. Normal health checks then mark this release good.
4. Reboot.
5. Power off.

Recovery on an unblessed release consumes one of three tries shared with normal boots.
Reboot/power-off does not bless it. The watchdog arms only on Continue; time in the menu cannot reset
the laptop. Recovery starts no network services. If the release cannot reach the passphrase prompt,
try the other slot (recipe 3) or the rescue entry below.

## Standalone rescue entry

Choose `RESCUE | Gentoo <version> - <kernel>` when neither slot boots. It has its own initramfs,
needs working ESP/kernel/encrypted state, and never mounts a slot root. Enter the LUKS passphrase
(US layout); three failures power off. State mounts read-write at `/run/cv-state`. No network,
watchdog, boot counter, blessing or option to continue into a release.

1. Root shell. Tools are those in the rescue initramfs; `/sysroot` is empty. `exit` returns.
2. Reset owner password. Same reset and password rules as per-release Recovery, uid 1000.
3. Write release from USB. Choose a USB partition and its release directory (FAT, exFAT, ext4 or
   Btrfs; mounted read-only, without journal replay). Bring `manifest`, `manifest.sig`, `slot.img`
   and both release UKIs. The signature must verify against the embedded release key, even with
   `CONVERGENT_UNSIGNED=1`. Choose `a` or `b`, or press Enter for the slot opposite the last good
   release (if uniquely identifiable). Confirm the printed release and slot with `yes`. This
   allows older or identical signed releases, preserving `/var` subvolumes, `good` and `highest`.
   It uses `slot`'s checksum, size and readback checks and installs the UKI with three tries.
   Use option 4 to boot it next, especially if older than the other slot; later boots return to the
   newer slot (recipe 3). Normal updates enforce anti-rollback.
4. Choose next slot. Select `a` or `b`; this writes `LoaderEntryOneShot` for its normal profile. It
   can pick an exhausted entry without resetting its counter or marking it good.
5. Copy logs to USB. Choose a writable USB partition. A new `convergent-logs-<time>.<suffix>`
   directory holds `logs.tar`: each release's `var-*/log` (including Incus VM console and QEMU logs)
   and reachable `pool/containers/*/rootfs/var/log`. It does not start guests or open VM disk
   images; logs inside them are not copied. The archive holds private logs in plaintext. Keep the
   stick private.
6. Reboot.
7. Power off.

Rescue installation and replacement: [ARCHITECTURE 5.2](ARCHITECTURE.md#52-boot). Select rescue
explicitly. An image built without a release key can unlock and repair state but cannot write
releases here. If rescue cannot boot, read the state from another Linux (recipe 9).

Rescue test coverage: [BUILD, Test in QEMU](BUILD.md#test-in-qemu).

| # | Symptom |
|---|---|
| 1 | [Wrong passphrase, the laptop powers off](#1-wrong-passphrase-the-laptop-powers-off) |
| 2 | [A new release does not boot or does not become good](#2-a-new-release-does-not-boot-or-does-not-become-good) |
| 3 | [Go back to the previous release by hand](#3-go-back-to-the-previous-release-by-hand) |
| 4 | [`guests init` or `guests update` stopped](#4-guests-init-or-guests-update-stopped) |
| 5 | [No Wi-Fi](#5-no-wi-fi) |
| 6 | [Wi-Fi works, no Internet](#6-wi-fi-works-no-internet) |
| 7 | [A USB device does not work](#7-a-usb-device-does-not-work) |
| 8 | [Where the logs are](#8-where-the-logs-are) |
| 9 | [Read the encrypted state from another Linux](#9-read-the-encrypted-state-from-another-linux) |
| 10 | [Second passphrase and header backup](#10-second-passphrase-and-header-backup) |
| 11 | [Start over](#11-start-over) |
| 12 | [An online update fails](#12-an-online-update-fails) |
| 13 | [A kernel panic or CrashRecorded alert](#13-a-kernel-panic-or-crashrecorded-alert) |
| 14 | [Incus state torn by a power loss](#14-incus-state-torn-by-a-power-loss) |
| 15 | [Incus UI session or passphrase failure](#15-incus-ui-session-or-passphrase-failure) |
| 16 | [Remmina session or keyring failure](#16-remmina-session-or-keyring-failure) |
| 17 | [Missing release or network evidence](#17-missing-release-or-network-evidence) |

## 1. Wrong passphrase, the laptop powers off

Three wrong tries power off without data loss. [US layout](USAGE.md#first-boot) applies. If the screen
is black, type the passphrase and press Enter. Ignore empty `host login:` prompts from intervening
keystrokes. After power-off, power on and retry.

Boot can stop before the prompt with `more than one disk has a cv-state partition; detach
the other`. Power off, unplug the other Convergent disk, and reboot. A USB disk cannot reinstall
over an existing Convergent disk: the two are ambiguous. Erase the old disk first with firmware
(Dell: F2, Maintenance, Data Wipe) or another system.

Right after an update, each power-on uses one of the new release's three tries; three powered-off
sessions bring the previous release back (recipe 2).

## 2. A new release does not boot or does not become good

After `slot write`, the new release gets three boot tries. A boot not good within about 13 minutes
of unlocking is reset by the hardware watchdog if the laptop has one (otherwise hold the power
button). After the third try, the previous slot boots by itself, with its own `/var`.

Once back, the failed release's log is in its own `/var`, not in the running one:

```sh
sudo slot status                                     # booted release, slot, good, highest
sudo mkdir -p /run/st && sudo mount -o ro,nologreplay,subvolid=5 /dev/mapper/cv-state /run/st
sudo grep ' slot:' /run/st/var-<failed release>/log/messages
sudo umount /run/st
```

Send the output/release ID; install the fixed release when available.

## 3. Go back to the previous release by hand

Stop the three-second menu with an arrow key. Pick the other `SLOT A | Gentoo <version> - <kernel>`
or SLOT B entry. Older entries may show only Gentoo Linux; the top bootable release is default.
Verify the other slot booted with `sudo slot status`. The newer slot stays the default after a
downgrade or this rollback: to stay on the older release, write it into both slots (rescue option 3,
once per slot), or press `d` on its entry in the menu for a persistent default (the next `slot write`
clears it).

Its `/var` predates the update; guest pool data stays current and may conflict with old metadata.
There is no guest-update rollback guard. The next `slot write` must exceed highest-good.

## 4. `guests init` or `guests update` stopped

Disk-image first boot runs `guests init` (bar SETUP, log `/var/log/guests-setup.log`). Retry the
printed failure with `sys guests setup` (uses `/var/lib/convergent/release-guests`) or
`sudo guests init <dir>` using the original directory; completed steps skip. Update failure restores
the old guest: fix the cause and retry. If fw1 stays silent after a handoff, run `sys firewall rebuild fw1`,
then `sys guests update`; after a commit, rebuild the silent firewall (wan/svc: run the printed `guests update`),
then `sys guests update`. Finish when SETUP disappears and fw1/fw2/wan/svc run.

```sh
sudo guests status                          # one line per guest and its state
sudo tail -n 50 /var/log/incus/<guest>/console.log
```

If a step fails twice identically, photograph the last output screen and leave the laptop unchanged.

### Interrupted work-topology migration

Finish handoff/maintenance before upgrading the host. `/var/lib/convergent/guests/fw.topology`
retains both old images/configurations and holds both firewalls stopped during replacement.
Never start a partial pair manually, delete the journal, prune its images or clear its holds.
Rerun `sudo guests apply` or the original `sudo guests update fw <image-dir>`: uncommitted work
restores both old roots before either starts; committed work finishes startup. Failed recovery
retains the journal and holds for retry. Inspect `guests status`, the update log and both consoles.
`check auto` reopens work access once topology validation passes. Replacement preserves DHCP leases.

## 5. No Wi-Fi

The `wan` VM owns the radio; host `ip link` cannot show it. Success: `sys wifi status` shows the
network and an address.

1. `sys wifi status`. "not found" or no answer means wan or its radio is not up.
2. Is the card handed to wan?
   ```sh
   lspci -nnk | grep -A3 -i network          # "Kernel driver in use: vfio-pci" is right
   sudo guests status                        # wan must be running
   ```
3. What wan saw at boot:
   ```sh
   sudo grep -i -E 'iwlwifi|wlan|firmware' /var/log/incus/wan/console.log | tail -n 20
   ```
4. Still nothing: send the output of steps 2 and 3.

## 6. Wi-Fi works, no Internet

Path: wan → either firewall → host/browser. One firewall suffices. Host web access is restricted to
updates; test Internet in `browser def`.

```sh
sys wifi status        # connected, with an address
sys wifi test               # "DNS: ok" or "DNS: failed", then wan diag: addresses, routes, NAT, upstream DNS, DHCP
sys selftest                   # among its checks: fw1 reaches 9.9.9.9:853 (DNS over TLS)
sys guests status              # fw1, fw2, wan, svc running
sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig carp | grep carp:'   # MASTER here, BACKUP on fw2
```

No address/default route: check `sys wifi status` and upstream. Captive portal: `sys portal on`.
[Resolver selection](USAGE.md#captive-portals) uses only the first server, so no usable upstream
resolver does not rule out usable later servers. Failed 9.9.9.9:853 means firewall/WAN/routing
failure or upstream DoT blocking. Otherwise send the output.

### Recover an incorrect clock

A clock years off can prevent both firewall DoT certificate validation and the host's NTS
key exchange. With no usable saved NTS cookies, DNS and authenticated time cannot bootstrap
each other. Correct the host **and both firewalls**; correcting only the host leaves firewall
ntpd slewing a large offset. Do not disable certificate checks or add unauthenticated servers.

Obtain current UTC from an independently trusted clock (for example, a correctly set offline
device). Compare it with `date -u` on the host. Replace `YYYY-MM-DD HH:MM:SS` below with that
verified UTC immediately before running this on the normally booted laptop. This needs no
working DNS or Internet; both firewalls must be running and reachable over their pinned SSH
connections. It also works when the host was already corrected: use its independently verified
current UTC. Wait for any guest update to finish first.

```sh
sudo sh <<'CLOCK'
set -eu
rc-service chronyd stop
date -u -s 'YYYY-MM-DD HH:MM:SS'
for fw in fw2 fw1; do
    timeout -k 5 60 ssh -F /etc/convergent/ssh_config -o ControlMaster=no -o ControlPath=none \
        "$fw" 'rcctl stop ntpd'
    stamp=$(date -u +%Y%m%d%H%M.%S)
    timeout -k 5 60 ssh -F /etc/convergent/ssh_config -o ControlMaster=no -o ControlPath=none \
        "$fw" "date -u $stamp && rcctl start ntpd && rcctl check ntpd"
done
rc-service chronyd start
CLOCK
```

Stopping ntpd before the step discards its old samples; OpenBSD `date` also cancels the pending
slew ([adjtime(2)](https://man.openbsd.org/OpenBSD-7.9/adjtime.2)). Each SSH call is bounded. If a
command fails, stop and fix that error, then repeat with fresh verified UTC; time services may
remain stopped. No validation policy changes are needed.

Check `date -u` on the host and with `sudo ssh -F /etc/convergent/ssh_config fw1 date -u`
(repeat for fw2). All three should agree with the trusted clock. With Wi-Fi restored, retry
`sys wifi test`, then `sudo chronyc online` and `chronyc sources -v`. Success: DNS works and at
least two sources are selected/combined (`*`/`+`); `chronyc authdata` shows NTS cookies for them.
Retry the failed update only after these checks pass.

## 7. A USB device does not work

Disk images initially allow broad HID/storage/hub classes. Individual-device restrictions apply
after replacing that policy during [first-boot enrollment](USAGE.md#first-boot). An empty blocked
list alone does not prove enrollment. Non-USB keyboards/touchpads are unaffected by USBGuard.
Success: the device works and `sudo devices list` no longer lists it as blocked.

```sh
sudo devices list            # blocked devices with a number
sudo devices allow <number>  # asks you to type yes; permanent
```

If moving the boot disk causes a stall, power off, restore its old port, boot and regenerate policy
with trusted devices attached ([first boot, step 4](USAGE.md#first-boot)).

## 8. Where the logs are

| What | Where |
|---|---|
| Host warnings and errors | `/var/log/messages`; `sys logs` reads it. Failures of `check`, `facts` and `power` are logged at error severity |
| wan warnings, kernel, Wi-Fi, DHCP and time messages | `/var/log/wan/diag.log` in wan (root only, 256 KiB, one rotation); `sys wifi test` shows its last 200 lines |
| Release checks, boot tries | `sudo slot status`; `slot:` lines in `/var/log/messages` |
| Self-test of this boot | `sys selftest` writes `~/selftest-YYYYmmdd-HHMMSS.txt` (PASS, FAIL or SKIP per check) |
| Services | `rc-status -a` (all runlevels); `sudo rc-service <name> status`, `restart` |
| Guests | `/var/log/incus/<guest>/console.log` and `qemu.log`; `/var/log/incus/incusd.log` |
| Security audit | `/var/log/audit/audit.log` |
| Health check report | `sys security report`; `/var/lib/convergent/check/last` |
| Searchable in Grafana (int browser, needs svc) | Host, firewall and wan syslog, incl. host audit records. Not file-only logs such as `/var/log/guests-setup.log` or `/var/log/incus/` |

Local protected logs need `sudo`; the owner can read the self-test report, run `rc-status -a` and
use Grafana without it.

## 9. Read the encrypted state from another Linux

On another Linux with the disk attached as `/dev/sdX`, as root:

```sh
cryptsetup open /dev/disk/by-partlabel/cv-state cvstate     # asks the LUKS passphrase
mkdir -p /mnt/cv && mount -o ro,nologreplay,subvolid=5 /dev/mapper/cvstate /mnt/cv
ls /mnt/cv          # home, pool (guests), var-<release> (one per release), etc
umount /mnt/cv && cryptsetup close cvstate
```

If the other Linux has a Convergent disk attached too, `by-partlabel` is ambiguous: use `/dev/sdX4`
instead.

## 10. Second passphrase and header backup

Once in daily use, add a second passphrase and keep the header backup on offline encrypted media.
Success: `luksDump` lists two keyslots.

```sh
sudo cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
sudo rm /var/lib/convergent/luks-header.sha256 && sudo facts boot    # the checker takes the new header
sudo cryptsetup luksDump /dev/disk/by-partlabel/cv-state             # check
```

## 11. Start over

[Rewrite the disk image](USAGE.md#install); this erases everything, including `/home`. Backup
contents and exclusions: [USAGE, Backups](USAGE.md#backups). There is no restore tool. Finish
automatic guest setup first. Mount the backup disk. Then, as root, select a generation and verify it
before restoring anything:

```sh
set -e
backup=/mnt/backup/convergent-backups/backup-YYYYmmddTHHMMSSZ
(cd "$backup" && sha256sum -c SHA256SUMS)
```

Unpack `home.tar` and restore needed writable files from `etc.tar`, preserving numeric ownership,
ACLs and xattrs for both. Recreate the pools and networks the owner's profiles reference. Restore
profiles in the recreated owner project before importing containers (older backups lack
`profiles.json`; reconstruct their profiles manually):

```sh
project=owner                       # the original owner project name
ic() { incus --force-local --project "$project" "$@"; }
ic project create "$project"        # skip if it already exists
# If the backed-up project used default-project volumes, set this before restoring profiles:
# ic project set "$project" features.storage.volumes=false
jq -r '.[].name' "$backup/projects/$project/profiles.json" > /run/restore-profiles
while IFS= read -r name; do
    ic profile show "$name" >/dev/null 2>&1 || ic profile create "$name"
    jq --arg n "$name" '.[] | select(.name == $n) | {config,description,devices}' \
        "$backup/projects/$project/profiles.json" | ic profile edit "$name"
done < /run/restore-profiles
rm /run/restore-profiles
```

Restore custom volumes before importing the owner's containers. Use the project and pool of each
archive's `projects/<project>/<pool>/` directory. Browser, svc, `remmina-state` and `share` use
project `default`, pool `default`; restore them with `incus storage volume import`.
Close browsers and Remmina (`sys remote close`), stop svc and every instance attached to `share`
in any project, and run no guest setup, updates or launches during restoration:

```sh
project=default
pool=default
ic stop svc --timeout 120
incus --force-local list --all-projects  # all volume consumers must be STOPPED
```

For these filesystem volumes, set `volume`, `profile` and `device` from the table. Check the instance
with `ic config show <guest>` (`--expanded` shows inherited devices). If its local `devices`
override the profile, update that device too. Older backups may name the browser archives
`browser-web-state.tar.gz` and `browser-admin-state.tar.gz`: use those for def and int,
respectively.

| volume | profile | device | guest |
|---|---|---|---|
| browser-def-state | browser-def | state | def |
| browser-int-state | browser-int | state | int |
| svc-metrics | svc | metrics | svc |
| svc-logs | svc | logs | svc |
| svc-grafana | svc | grafana | svc |
| remmina-state | remmina | state | remmina (if created) |
| share | remmina | share | remmina; also reset every owner attachment separately |

```sh
volume=svc-metrics; profile=svc; device=metrics
ic storage volume import "$pool" "$backup/projects/$project/$pool/$volume.tar.gz" "$volume-restored"
ic storage volume rename "$pool" "$volume" "$volume-before-restore"
ic storage volume rename "$pool" "$volume-restored" "$volume"
ic profile device set "$profile" "$device" source="$volume"
# Only when the instance has a local override of this device:
# ic config device set <guest> "$device" source="$volume"
ic storage volume show "$pool" "$volume"
ic storage volume show "$pool" "$volume-before-restore"
```

The temporary names must be unused. Renaming the old volume also redirects its attachments, so reset
every consumer's profile or local device to the restored name before restarting. For `share`, use
`--project owner` for owner devices/profiles, retaining its default volume namespace
(`features.storage.volumes=false`; [share setup](USAGE.md#remote-desktops)). The old volume's
`used_by` identifies attachments and must be empty after reattachment. Keep it until data is
verified. Repeat for owner volumes with their own project, pool and consumers. Filesystem exports
use `.tar.gz`; ISO exports use `.iso` and require this import command instead:

```sh
ic storage volume import "$pool" "$backup/projects/$project/$pool/$volume.iso" "$volume-restored" --type=iso
```

Use the same rename/reattachment steps for either type; if no volume exists, skip the old-volume
rename. Before starting Grafana against restored `svc-grafana`, restore its matching secrets.
For backups containing `grafana-secrets/`, run the following after volume restoration. An attached
seed means setup has not finished; stop and finish setup before retrying. The unused cached seed
is discarded so the next guest rebuild uses the restored host secrets.

```sh
# Restore Grafana secrets.
project=default
state=/var/lib/convergent/guests
devices=$(ic config device show svc)
if printf '%s\n' "$devices" | grep -q '^seed:'; then
    echo 'finish guest setup before restoring Grafana secrets' >&2
    exit 1
fi
if [ -f "$state/seeds/svc.img" ]; then
    loops=$(losetup -j "$state/seeds/svc.img")
    [ -z "$loops" ]
fi
for secret in admin-password secret-key; do
    [ -s "$backup/grafana-secrets/$secret" ]
done
rm -f "$state/seeds/svc.img" "$state/seeds/svc.sha256"
ic start svc
# Grafana is absent from boot runlevels; keep it stopped until both files are installed.
ic exec svc -- rc-service grafana stop
for secret in admin-password secret-key; do
    install -m 600 "$backup/grafana-secrets/$secret" "$state/tls/$secret"
    ic exec svc -- sh -eu -c '
        umask 077
        cat >"$1.new"
        chown root:grafana "$1.new"
        chmod 640 "$1.new"
        mv "$1.new" "$1"
    ' sh "/etc/grafana/$secret" <"$state/tls/$secret"
done
sync
# Grafana secrets restored.
```

Older backups lack these secrets. Start svc with `project=default; ic start svc`, keep Grafana
stopped, and [reset the restored admin password](https://grafana.com/docs/grafana/latest/administration/cli/#reset-admin-password)
to the newly generated host password:

```sh
ic exec svc -- rc-service grafana stop
ic exec svc -- grafana-cli --homepath /usr/share/grafana --config /etc/grafana.ini \
    admin reset-admin-password --password-from-stdin </var/lib/convergent/guests/tls/admin-password
```

If you had saved encrypted credentials or settings, re-enter them after login: the new
`secret-key` cannot decrypt values saved with the lost key. Shipped data sources have no credentials.
For either backup format, a password changed in Grafana remains the database password unless reset.
Open def/int normally and verify
saved profiles, downloads and Grafana/history. Open Remmina to check its keyring and `/share`, then
verify owner share attachments before restarting those instances. Then remove unused old volumes
with `ic storage volume delete "$pool" <volume-before-restore>`.

Import the owner's containers, check their expanded devices, then start them:

```sh
project=owner                       # the original owner project name
for archive in "$backup/projects/$project"/instance-*.tar.gz; do
    [ -f "$archive" ] || continue
    ic import "$archive"
done
```

## 12. An online update fails

Start with `sys update check`: it names the newest version (or release ID for older manifests) and
how old its signature is. `sys update install` stops with the reason; running it again resumes the
download. A retry keeps that release's staged guests until their replacement is ready.

| Message | Do |
|---|---|
| `resolves to no public address` | Wi-Fi first (recipe 5). Else the blocklist holds the server: add the host from `/etc/convergent/update.conf` to `/var/lib/convergent/dns/allow`, run `sudo dns-push local`, retry |
| `could not open the update source` | A firewall is not answering: recipe 6 |
| `signature does not verify`, `latest is not signed`, `does not match the manifest` | Never bypass it: what arrived is not what was published. Retry; if it repeats, update from USB with a release you built ([USB updates](USAGE.md#host-updates)) |
| `this release has no online updates` | The image lacks its release key or update URL: update from USB |
| `not enough free space in /var` | Free what is still missing in `/var`, plus 1 GiB |
| `latest is signed more than 5 minutes in the future; check the clock` | Follow [clock recovery](#recover-an-incorrect-clock), then run it again |

Works when `sys update` shows the new release with `+3`. Then reboot (recipe 2 if it does not become
good).

## 13. A kernel panic or CrashRecorded alert

An oops panics; a panic reboots after 10 seconds. After unlocking the next boot, `facts boot`
archives built-in EFI pstore records to `/var/lib/convergent/crash/<UTC-timestamp>/`, and the ACPI
BERT record, when available, to `/var/lib/convergent/crash/bert-<sha256>` (deduplicated by hash).
Archive directories are root-only 0700; BERT files are 0600. Pstore copies are compared/synced
before firmware deletion; the collector does not delete BERT. Old `/var/lib/convergent/pstore`
archives move to crash. Security shows counts; CrashRecorded flags unacknowledged records.

`kernel.panic_on_oops=1` is KSPP hardening. For a repeatedly oopsing driver, run `sudo sysctl -w
kernel.panic_on_oops=0` to disable that panic trigger until reboot. To keep the exception, set `0`
in `rootfs/etc/sysctl.d/90-convergent.conf` and build/install a release; the running root is
read-only. If the reboot loop prevents that, boot the previous slot first (recipe 3).

```sh
sudo find /var/lib/convergent/crash -type f
sudo cat /var/lib/convergent/crash/<UTC-timestamp>/<record>
```

Keep a copy before acknowledging a crash. Remove only its reviewed timestamp directory
(`sudo rm -r /var/lib/convergent/crash/<UTC-timestamp>`). For BERT, persist an acknowledgment
outside the archive before deleting the reviewed file (replace `<sha256>` with its hash).
Take the collector's lock; if the 30-second wait expires, retry later:

```sh
sudo flock -w 30 /run/convergent/facts.lock sh -c '
install -d -m 0700 /var/lib/convergent/crash-ack &&
touch /var/lib/convergent/crash-ack/bert-<sha256> &&
sync &&
rm /var/lib/convergent/crash/bert-<sha256>
'
```

The marker permanently suppresses that hash, including future byte-identical BERT records.
Then run `sudo facts boot` to refresh `cv_crash_records` (the archived file count). `CrashRecorded`
clears when no archived files remain. Firmware must support EFI variable writes during a panic. An empty archive
alone does not prove the last shutdown was clean. If the release keeps crashing, boot the other slot
(recipe 3).

## 14. Incus state torn by a power loss

Power loss can split Incus operations. `guests` refuses commands; the bar shows failure and
`/var/log/guests-update.log` prints exact repairs. Two cases:

- A guest without a storage record: the loss hit a rebuild between dropping and recreating the
  record (a few milliseconds). Run the printed `incus admin sql global "INSERT ..."`, then the
  printed `incus rebuild <image> <guest>` (the image is the one in
  `/var/lib/convergent/guests/pending`), then `sys guests update`, which re-seeds the guest.
- A state volume with a `.incustmp` copy beside it or instead of it: the loss hit a snapshot
  restore (well under a second). Volume missing: `sudo mv` the copy back. Volume present: the
  restore completed, `sudo btrfs subvolume delete` the copy. Then `sys guests update`.

## 15. Incus UI session or passphrase failure

Close int, then run `sudo incus-ui cleanup` to retry orphan cleanup; `check auto` also retries
each minute and boot cleanup runs before the greeter. Cleanup stops int before discarding its
session journal; trust is revoked even if stopping fails, and the journal remains for retry.
Cleanup also stops orphaned Grafana and restores svc's 350 MiB idle limit if its 768 MiB session
limit was left behind.
If a launcher still holds the session lock, close its terminal or use `sudo incus-ui revoke`
to stop an unlocked session and invalidate its credential. Existing WebSockets require stopping
int, not just removing the certificate. Never import the private key into persistent NSS state.

Forgotten passphrase or expired certificate: with int closed, `sudo incus-ui rotate` creates a
new encrypted bundle. After restoring state from backup, revoke and set up a fresh credential
before opening int. Boot cleanup removes stale named UI trust even without a runtime journal;
interrupted rotation restores the previous complete directory if the new one was not installed.
Check `/var/log/messages` for `incus-ui` events and the `incus-ui` certificate-expiry metric.
The trusted local Unix-socket CLI remains available if the web interface is unusable.

## 16. Remmina session or keyring failure

Run `sys remote close`; the minute checker also stops orphans. The next open removes stale sockets.
Resume an interrupted update with `sys guests update`. Manual rollback uses a retained `guests-*`
snapshot of `remmina-state` while Remmina is stopped; leave `share` alone because it may hold newer
work.

A lost keyring password cannot be recovered. Keep an offline copy, then move the stopped volume's
`.local/share/keyrings` directory aside. Next open creates a new encrypted keyring; re-enter remote
credentials. Stop every instance using `share` before restoring or backing it up (recipe 11).

## 17. Missing release or network evidence

Run `sudo fetch-release check` and inspect Security → Release → Advisory evidence. A
missing/tampered status is unknown, not zero advisories; payload updates remain independent.
On the builder, restore the retained release inventories and rerun `build/advisories-publish`
with the channel signing key. Failed upstream feeds leave the previous status in R2; a pruned
installed release has no status. Check clocks before investigating future/replayed metadata.

For absent blocked-packet samples, check `rcctl check pflog_stream` on each firewall, the existing
TLS syslog path to svc, and whether the relevant PF rule logs. `rcctl restart pflog_stream`
restarts sampling; suppression summaries mean the sample cap was reached. Missing radio metrics
can mean disconnected or unsupported hardware. WAN RTT/loss is firewall-to-WAN only.

Use `sys firewall capture <interface-or-segment> <seconds>` from the owner login for a bounded
pcap in `~/captures`; it refuses an incoherent MASTER/BACKUP pair. Interrupted remote captures
stop within 60 seconds and temporary files are removed on normal exit. After a firewall crash,
remove abandoned `/var/run/fw-capture.*` directories there; they are never durable archives.
