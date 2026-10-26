# Recovery

Each recipe says when it applies, what to do, and how to tell it worked. Run commands on the laptop
as the owner unless stated.

## Recovery boot menu

Press an arrow key during the three-second boot menu to stop the timer. Pick the release and slot
ending in `(Recovery)`, e.g. `Gentoo Linux <release> (slot a) (Recovery)`. Enter the LUKS passphrase
(US layout); three wrong attempts power off. Recovery needs the same unlock as a normal boot, and
the same verified release must be able to boot.

The menu shows the release, slot and read-write data at `/run/cv-state`:

1. Root shell. Verified root is `/sysroot`; encrypted data and writable `/etc` files are under
   `/run/cv-state`. `exit` returns to the menu.
2. Reset owner password. Enter it twice. It changes the uid 1000 account. Use 12 to 256 bytes. Uses
   SHA-512 crypt; a later `account password` in the running system uses yescrypt.
3. Continue booting. Normal health checks then mark this release good.
4. Reboot.
5. Power off.

Booting recovery on an unblessed release uses one of its three tries, shared with normal boots.
Rebooting or powering off from the menu does not mark it good. The watchdog arms only after you
continue, so time in the menu does not reset the laptop. Recovery starts no network services. If the
release cannot reach the passphrase prompt, try the other slot (recipe 3) or the rescue entry below.

## Standalone rescue entry

Choose `Convergent rescue (<release>)` when neither slot boots. Unlike a release's `(Recovery)`
profile, it has its own initramfs and never mounts a slot root. It needs a working ESP, kernel and
encrypted state. Enter the LUKS passphrase (US layout); three failures power off. State mounts
read-write at `/run/cv-state`. No network, watchdog, boot counter, blessing or option to continue
into a release.

1. Root shell. Tools are those in the rescue initramfs; `/sysroot` is empty. `exit` returns.
2. Reset owner password. Same reset and password rules as per-release Recovery, uid 1000.
3. Write release from USB. Choose a USB partition and its release directory (FAT, exFAT, ext4 or
   Btrfs; mounted read-only, without journal replay). Bring `manifest`, `manifest.sig`, `slot.img`
   and both release UKIs. The signature must verify against the embedded release key, even with
   `CONVERGENT_UNSIGNED=1`. Choose `a` or `b`, or press Enter for the slot opposite the last good
   release (if uniquely identifiable). Confirm the printed release and slot with `yes`. This
   deliberately allows reinstalling an older or identical signed release. It keeps `/var` subvolumes
   and leaves `good` and `highest` unchanged. It uses `slot`'s checksum, size and readback checks,
   and installs the chosen release UKI with three tries. Use option 4 to boot it next, especially if
   it is older than the other slot. Normal updates still enforce anti-rollback.
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
| 13 | [Incus state torn by a power loss](#13-incus-state-torn-by-a-power-loss) |

## 1. Wrong passphrase, the laptop powers off

Three wrong tries power it off; nothing is lost. The passphrase uses the US layout; see
[README, First boot](README.md#first-boot). The screen may stay black while the prompt waits. Type
it blind and press Enter. Keys pressed meanwhile show as empty `host login:` prompts; ignore them.
Power on and type it again.

The boot can also stop before the prompt, with
`more than one disk has a cv-state partition; detach the other`. Power off, unplug the other
Convergent disk, and boot again. A USB disk cannot reinstall over a laptop disk that holds
Convergent, since the two cannot yet be told apart. Erase the old one first, with the firmware's
disk wipe (Dell: F2, Maintenance, Data Wipe) or another system.

Right after an update, each power-on uses one of the new release's three tries; three powered-off
sessions bring the previous release back (recipe 2).

## 2. A new release does not boot or does not become good

After `slot write`, the new release gets three boot tries. A boot not good within about 13 minutes
of unlocking is reset by the hardware watchdog if the laptop has one (otherwise hold the power
button). After the third try, the previous slot boots by itself, with its own `/var`.

Once back, the failed release's log is in its own `/var`, not in the running one:

```sh
sudo slot status                                     # booted release, slot, good, highest
sudo mkdir -p /run/st && sudo mount -o ro,subvolid=5 /dev/mapper/cv-state /run/st
sudo grep ' slot:' /run/st/var-<failed release>/log/messages
sudo umount /run/st
```

Send that output with the release number. Nothing else needs undoing. Write the next release once it
is fixed.

## 3. Go back to the previous release by hand

At power-on, press an arrow key within the three-second menu to stop it. Each slot is an entry named
`Gentoo Linux 0.1.0 (<release>, slot a)` or `slot b`. Older releases omit the semantic version.
Releases before 2026-10-18 show only `Gentoo Linux`; the top one is the default. Pick the other
slot. Works when: `sudo slot status` shows the other slot booted.

That slot's `/var` predates the update, so changes made since are not in it. Guests are not rolled
back and stay as they are. Nothing stops this after a guest update yet. The next `slot write` must
be newer than the highest release ever marked good.

## 4. `guests init` or `guests update` stopped

On a disk image, the first boot runs `guests init` automatically (bar: `SETUP`; log
`/var/log/guests-setup.log`). Both print the failed step. Run `sys guests setup` (it uses
`/var/lib/convergent/release-guests`), or `sudo guests init <dir>` with the same directory as
before. Finished steps are skipped. `guests update` restores the old guest automatically if the new
one fails its checks; run it again once the cause is fixed. Works when: `SETUP` is gone and fw1,
fw2, wan and svc run.

```sh
sudo guests status                          # one line per guest and its state
sudo tail -n 50 /var/log/incus/<guest>/console.log
```

If a step fails twice the same way, photograph the last screen of output and leave the laptop as it
is.

## 5. No Wi-Fi

The radio belongs to the `wan` VM, so `ip link` on the host does not show it. Works when:
`sys wifi status` shows the network and an address.

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

The path is wan → fw1 or fw2 → the host. One firewall down is fine; both down is not. The host
itself cannot browse, by design: pf lets it resolve names through the firewalls and reach a short
list of update servers. Browsers have Internet, so try one (`browser def`) to tell them apart.

```sh
sys wifi status        # connected, with an address
sys wifi test               # "DNS: ok" or "DNS: failed", then wan diag: addresses, routes, NAT, upstream DNS, DHCP
sys selftest                   # among its checks: fw1 reaches 9.9.9.9:853 (DNS over TLS)
sys guests status              # fw1, fw2, wan, svc running
sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig carp | grep carp:'   # MASTER here, BACKUP on fw2
```

No address or default route in wan diag: check Wi-Fi (`sys wifi status`) and the upstream network. A
captive portal (hotel, train) needs `sys portal on` first. Portal DNS uses the selected default-route
uplink's first nameserver; it must be IPv4 outside 100.80.0.0/16. Later usable nameservers are not
tried, so `no usable upstream resolver` does not prove the lease has no usable resolver. fw1 cannot
reach 9.9.9.9:853: fw1, wan or routing is down, or the upstream blocks DNS over TLS. Anything else:
send the output.

## 7. A USB device does not work

USBGuard blocks every device it does not know. The internal keyboard and touchpad are not USB, so
they always work. Works when the device works and `sudo devices list` no longer shows it.

```sh
sudo devices list            # blocked devices with a number
sudo devices allow <number>  # asks you to type yes; permanent
```

If the boot disk was moved to another port and the system stalls: power off, put it back in the old
port, boot, and regenerate the policy with all trusted devices in place (README, first boot step 4).

## 8. Where the logs are

| What | Where |
|---|---|
| Host warnings and errors | `/var/log/messages`; `sys logs` reads it |
| Release checks, boot tries | `sudo slot status`; `slot:` lines in `/var/log/messages` |
| Self-test of this boot | `sys selftest` writes `~/selftest-YYYYmmdd-HHMMSS.txt` (PASS, FAIL or SKIP per check) |
| Services | `rc-status -a` (all runlevels); `sudo rc-service <name> status`, `restart` |
| Guests | `/var/log/incus/<guest>/console.log` and `qemu.log`; `/var/log/incus/incusd.log` |
| Security audit | `/var/log/audit/audit.log` |
| Health check report | `sys security report`; `/var/lib/convergent/check/last` |
| Searchable in Grafana (int browser, needs svc) | Host, firewall and wan syslog, incl. host audit records. Not file-only logs such as `/var/log/guests-setup.log` or `/var/log/incus/` |

All need `sudo` to read, except the self-test report in the owner's home.

## 9. Read the encrypted state from another Linux

For example, from Rocky with the Convergent disk attached as `/dev/sdX`. As root:

```sh
cryptsetup open /dev/disk/by-partlabel/cv-state cvstate     # asks the LUKS passphrase
mkdir -p /mnt/cv && mount -o ro,nologreplay,subvolid=5 /dev/mapper/cvstate /mnt/cv
ls /mnt/cv          # home, pool (guests), var-<release> (one per release), etc
umount /mnt/cv && cryptsetup close cvstate
```

If the other Linux has a Convergent disk attached too, `by-partlabel` is ambiguous: use `/dev/sdX4`
instead.

## 10. Second passphrase and header backup

Do this once the laptop is in daily use. Keep the backup on offline encrypted media. Works when:
`luksDump` lists two keyslots.

```sh
sudo cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
sudo rm /var/lib/convergent/luks-header.sha256 && sudo facts boot    # the checker takes the new header
sudo cryptsetup luksDump /dev/disk/by-partlabel/cv-state             # check
```

## 11. Start over

Write the disk image again (README, Install). Everything on the disk is lost, `/home` included.
Backup contents and exclusions: [USAGE, Backups](USAGE.md#backups). There is no restore tool. Finish
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
jq -r '.[].name' "$backup/projects/$project/profiles.json" > /run/restore-profiles
while IFS= read -r name; do
    ic profile show "$name" >/dev/null 2>&1 || ic profile create "$name"
    jq --arg n "$name" '.[] | select(.name == $n) | {config,description,devices}' \
        "$backup/projects/$project/profiles.json" | ic profile edit "$name"
done < /run/restore-profiles
rm /run/restore-profiles
```

Restore custom volumes before importing the owner's containers. Use the project and pool of each
archive's `projects/<project>/<pool>/` directory. Browser and svc data use project `default` and
pool `default`. They need `incus storage volume import`, not `incus import` or manual unpacking.
Close all browsers, stop svc, and run no guest setup or updates during the steps below:

```sh
project=default
pool=default
ic stop svc --timeout 120
ic list                           # def, int and svc must be STOPPED
```

Repeat for each row, setting `volume`, `profile` and `device` from the table. Check the instance
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
each listed consumer's profile or local device to the restored original name before restarting. Keep
`*-before-restore` until the restored data works; its `used_by` must be empty after reattachment.
Repeat for owner volumes with their own project, pool and consumers. If no volume exists yet, skip
the old-volume rename. Start svc with `ic start svc`. Open def/int normally and verify saved
profiles, downloads and Grafana/history. Only then remove the unused old volumes with
`ic storage volume delete "$pool" <volume-before-restore>`.

Finally, import the owner's containers. Then start them after checking their expanded devices:

```sh
project=owner                       # the original owner project name
for archive in "$backup/projects/$project"/instance-*.tar.gz; do
    [ -f "$archive" ] || continue
    ic import "$archive"
done
```

## 12. An online update fails

Start with `sys update check`: it names the newest version (or release ID for older manifests) and
how old its signature is. Channel migration: [BUILD, Sign and publish](BUILD.md#sign-and-publish).
`sys update install` stops with the reason; running it again resumes the download.

| Message | Do |
|---|---|
| `resolves to no public address` | Wi-Fi first (recipe 5). Else the blocklist holds the server: add the host from `/etc/convergent/update.conf` to `/var/lib/convergent/dns/allow`, run `sudo dns-push local`, retry |
| `could not open the update source` | A firewall is not answering: recipe 6 |
| `signature does not verify`, `latest is not signed`, `does not match the manifest` | Never bypass it: what arrived is not what was published. Retry; if it repeats, update from USB with a release you built (README, Update) |
| `this release has no online updates` | The image lacks its release key or update URL: update from USB |
| `not enough free space in /var` | Free what is still missing in `/var`, plus 1 GiB |
| `latest is signed more than 5 minutes in the future; check the clock` | Set the clock (`date`), then run it again |

Works when `sys update` shows the new release with `+3`. Then reboot (recipe 2 if it does not become
good).

## 13. A kernel panic or CrashRecorded alert

An oops now panics; a panic reboots after 10 seconds. After unlocking the next boot, `facts boot`
archives built-in EFI pstore records to `/var/lib/convergent/crash/<UTC-timestamp>/`, accessible
only to root (mode 0700). It verifies and syncs each copy before removing the firmware record. Older
archives in `/var/lib/convergent/pstore` move to `crash` on the first run. The Security dashboard
shows archived crash counts beside checker results; `CrashRecorded` reports unacknowledged records.

`kernel.panic_on_oops=1` is KSPP hardening. For a repeatedly oopsing driver, run
`sudo sysctl -w kernel.panic_on_oops=0` to disable that panic trigger until reboot. To keep the
exception, set `0` in `rootfs/etc/sysctl.d/90-convergent.conf` and build/install a release; the
running root is read-only. If the reboot loop prevents that, boot the previous slot first (recipe
3).

```sh
sudo find /var/lib/convergent/crash -type f
sudo cat /var/lib/convergent/crash/<UTC-timestamp>/<record>
```

Keep a copy before acknowledging a crash. Remove only its reviewed timestamp directory
(`sudo rm -r /var/lib/convergent/crash/<UTC-timestamp>`), then run `sudo facts boot` to refresh
`cv_crash_records` (the archived file count). `CrashRecorded` clears when no archived files remain. Firmware must support EFI
variable writes during a panic. An empty archive alone does not prove the last shutdown was clean.
If the release keeps crashing, boot the other slot (recipe 3).

## 13. Incus state torn by a power loss

Incus does two of the guest tool's steps in halves that a power loss can separate. `guests` then
refuses every command (the bar shows the failed update; `/var/log/guests-update.log` has the
message with the exact commands) rather than fail later with the guest down. Two cases:

- A guest without a storage record: the loss hit a rebuild between dropping and recreating the
  record (a few milliseconds). Run the printed `incus admin sql global "INSERT ..."`, then the
  printed `incus rebuild <image> <guest>` (the image is the one in
  `/var/lib/convergent/guests/pending`), then `sys guests update`, which re-seeds the guest.
- A state volume with a `.incustmp` copy beside it or instead of it: the loss hit a snapshot
  restore (well under a second). Volume missing: `sudo mv` the copy back. Volume present: the
  restore completed, `sudo btrfs subvolume delete` the copy. Then `sys guests update`.

### Interrupted work-topology migration

Finish old-release handoff/maintenance journals before upgrading the host.
A topology change uses `/var/lib/convergent/guests/fw.topology`, which retains
both old image fingerprints and instance configurations. Both firewalls have
autostart/restart held while their roots are being replaced; a partially
rebuilt pair must never be started manually. Rerun `sudo guests apply` (or the
original `guests update fw <image-dir>`) to replay recovery. Uncommitted work
restores both old images before either starts; committed work finishes startup.
If rollback itself fails, the journal and holds remain for the next retry.

Do not delete this journal, prune its old images or clear its boot holds.
Inspect `guests status`, the update log and both consoles. Work access stays
closed until the topology hashes in the host, fw1, fw2 and wan agree; ordinary
`check auto` reopens it after convergence. DHCP clients may need to renew after
a pair rebuild because lease files are intentionally not restored.

## 14. Incus UI session or passphrase failure

Close int, then run `sudo incus-ui cleanup` to retry orphan cleanup; `check auto` also retries
each minute and boot cleanup runs before the greeter. Cleanup stops int before discarding its
session journal; trust is revoked even if stopping fails, and the journal remains for retry.
If a launcher still holds the session lock, close its terminal or use `sudo incus-ui revoke`
to stop an unlocked session and invalidate its credential. Existing WebSockets require stopping
int, not just removing the certificate. Never import the private key into persistent NSS state.

Forgotten passphrase or expired certificate: with int closed, `sudo incus-ui rotate` creates a
new encrypted bundle. After restoring state from backup, revoke and set up a fresh credential
before opening int. Boot cleanup removes stale named UI trust even without a runtime journal;
interrupted rotation restores the previous complete directory if the new one was not installed.
Check `/var/log/messages` for `incus-ui` events and the `incus-ui` certificate-expiry metric.
The trusted local Unix-socket CLI remains available if the web interface is unusable.
