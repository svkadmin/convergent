# Recovery

Numbered recipes. Each says when it applies, what to do, and how to tell it worked. Commands run
on the laptop as the owner unless the recipe says otherwise.

## Recovery boot menu

At power-on, press an arrow key during the three-second boot menu to stop the timer. Pick the
release and slot with `(Recovery)` at the end, e.g. `Gentoo Linux <release> (slot a) (Recovery)`.
Enter the usual LUKS passphrase (US keyboard layout); three wrong attempts power off. Recovery
requires the same unlock as a normal boot and the same verified release must be able to boot.

The menu shows the release, slot and the data mounted read-write at `/run/cv-state`:

1. Root shell. The verified root is at `/sysroot`; encrypted data and writable `/etc` files are
   under `/run/cv-state`. `exit` returns to the menu.
2. Reset owner password. Enter the new password twice; it changes the account with uid 1000.
   Use 12 to 256 bytes. This uses SHA-512 crypt; a later `account password` in the running system uses yescrypt.
3. Continue booting this release. The normal health checks then mark it good.
4. Reboot.
5. Power off.

Booting recovery on a release not yet marked good uses one of its three tries, shared with
normal boots. Rebooting or powering off from the menu does not mark it good. The watchdog is
armed only after continuing, so time spent in the menu does not reset the laptop. Recovery
starts no network services. If the release cannot reach the passphrase prompt, try the other
slot (recipe 3) or the standalone rescue entry below.

## Standalone rescue entry

Choose `Convergent rescue (<release>)` when neither slot boots. Unlike a release's `(Recovery)`
profile, it has its own initramfs and never mounts a slot root. It needs a working ESP, kernel
and encrypted state. Enter the usual LUKS passphrase with the US layout; three failures power
off. The state is mounted read-write at `/run/cv-state`. There is no network, watchdog, boot
counter, blessing or option to continue into a release.

1. Root shell. The tools are those in the rescue initramfs; `/sysroot` is empty. `exit` returns.
2. Reset owner password. The same uid 1000 reset and password rules as per-release Recovery.
3. Write release from USB. Choose a USB partition and the release directory on it. FAT, exFAT,
   ext4 and Btrfs are supported; the source mounts read-only without journal replay. Bring the
   usual `manifest`, `manifest.sig`, `slot.img` and both release UKIs. Rescue requires the
   signature to verify against its embedded release key, even with `CONVERGENT_UNSIGNED=1`.
   Choose `a` or `b`, or press Enter for the slot opposite the last good release (if uniquely
   identifiable). Confirm the printed release and slot with `yes`. This deliberately permits
   reinstalling an older or identical signed release, preserves existing `/var` subvolumes,
   and leaves `good` and `highest` unchanged. It uses `slot`'s checksum, size and readback checks
   and installs the chosen release UKI with three tries. Use option 4 to boot it next,
   especially if it is older than the other slot. Normal updates still enforce anti-rollback.
4. Choose next slot. Select `a` or `b`; writes `LoaderEntryOneShot` for that entry's normal
   profile. It can select an exhausted entry, without resetting its counter or marking it good.
5. Copy logs to USB. Choose a writable USB partition. A new `convergent-logs-<time>.<suffix>`
   directory holds `logs.tar`: every release's `var-*/log` (including Incus VM console/QEMU logs)
   and reachable container `pool/containers/*/rootfs/var/log`. It does not start guests or open
   their VM disk images; logs inside those images are not copied. The archive contains private
   logs in plaintext; keep the stick private.
6. Reboot.
7. Power off.

The installer installs rescue when the release contains it. On upgrade, the first successful
`slot bless` copies `/usr/lib/convergent/rescue.efi` from the verified slot to the fixed ESP name
`EFI/Linux/convergent-rescue.efi`. It compares first and stages, checks, syncs and renames only
when different. A failed release cannot replace rescue. The ordinary default matches numbered
release entries only; rescue sorts after bootable releases (systemd-boot always puts exhausted
entries last). Select rescue explicitly. An image built without a release key can unlock and
repair state but cannot write releases from this menu. If rescue itself cannot boot, use another
Linux to read state (recipe 9).

`build/test --rescue <release>` boots the shipped rescue UKI with both slots empty, unlocks,
checks the menu, selects power off, and checks that UKI names/content and blessing state did
not change. USB writes, password reset, next-slot selection and log export need separate testing.

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

## 1. Wrong passphrase, the laptop powers off

Three wrong tries power it off; nothing is lost. The passphrase uses the US layout, see
[README, First boot](README.md#first-boot). The screen can stay black while the prompt waits: type
the passphrase blind and press Enter. Keys pressed meanwhile reappear as empty `host login:`
prompts; ignore them. Power on and type it again.

The boot can also stop before the passphrase prompt, with `more than one disk has a cv-state
partition; detach the other`. Power off, unplug the other Convergent disk, and boot again. A
USB disk cannot reinstall over a laptop disk that already holds Convergent (the two cannot be told
apart yet): erase the old one first, from the firmware's disk wipe (Dell: F2, Maintenance, Data Wipe)
or another system.

Right after an update each power-on uses one of the new release's three tries, so three powered-off
sessions bring the previous release back (recipe 2).

## 2. A new release does not boot or does not become good

After `slot write` the new release gets three boot tries. A boot that is not good within about 13
minutes of unlocking is reset by the hardware watchdog, if the laptop has one (otherwise hold the
power button). After the third try the previous slot boots by itself, with the `/var` it had.

Once back, the failed release's log is in its own `/var`, not in the one you are running:

```sh
sudo slot status                                     # booted release, slot, good, highest
sudo mkdir -p /run/st && sudo mount -o ro,subvolid=5 /dev/mapper/cv-state /run/st
sudo grep ' slot:' /run/st/var-<failed release>/log/messages
sudo umount /run/st
```

Send that output with the release number. Nothing else needs undoing: write the next release
when it is fixed.

## 3. Go back to the previous release by hand

At power-on the boot menu shows for three seconds; press an arrow key to stop it. Each slot is
an entry named `Gentoo Linux 0.1.0 (<release>, slot a)` or `slot b` (older releases omit the
semantic version; releases before 2026-10-18 show only `Gentoo Linux`: the top one is the
default). Pick the other one. Works when: `sudo slot status` shows the other slot booted.

That slot uses its own `/var` from before the update, so changes made since are not in it. The
guests are not rolled back: they stay as they are, and nothing stops this after a guest update
yet. The next `slot write` must be newer than the highest release ever marked good.

## 4. `guests init` or `guests update` stopped

On a disk image the first boot runs `guests init` by itself (bar: `SETUP`; log
`/var/log/guests-setup.log`). Both print the step that failed. Run `sys guests setup` (it uses
`/var/lib/convergent/release-guests`) or `sudo guests init <dir>` with the same directory as
before: finished steps are skipped. `guests update` restores the old guest by itself when the
new one fails its checks; run it again once the cause is fixed. Works when: `SETUP` is gone and
fw1, fw2, wan and svc run.

```sh
sudo guests status                          # one line per guest and its state
sudo tail -n 50 /var/log/incus/<guest>/console.log
```

A step that fails twice the same way: photograph the last screen of output and keep the laptop
as it is.

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
list of update servers. Browsers have Internet, so try one (`browser def`) to tell the two apart.

```sh
sys wifi status        # connected, with an address
sys wifi test               # "DNS: ok" or "DNS: failed", then wan diag: addresses, routes, NAT, upstream DNS, DHCP
sys selftest                   # among its checks: fw1 reaches 9.9.9.9:853 (DNS over TLS)
sys guests status              # fw1, fw2, wan, svc running
sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig carp | grep carp:'   # MASTER here, BACKUP on fw2
```

No address or default route in wan diag: check Wi-Fi (`sys wifi status`) and the upstream
network; a captive portal (hotel, train) needs `sys portal on` first. fw1 cannot reach
9.9.9.9:853: fw1, wan or routing is down, or the upstream blocks DNS over TLS. Anything else: send
the output.

## 7. A USB device does not work

USBGuard blocks every device it does not know. The internal keyboard and touchpad are not USB,
so they always work. Works when: the device works and `sudo devices list` no longer shows it.

```sh
sudo devices list            # blocked devices with a number
sudo devices allow <number>  # asks you to type yes; permanent
```

If the disk you boot from was moved to a different port and the system stalls: power off, put it
back in the old port, boot, and regenerate the policy with all trusted devices in place (README,
first boot step 4).

## 8. Where the logs are

| What | Where |
|---|---|
| Warnings and errors of the host | `/var/log/messages`; `sys logs` reads it |
| Release checks, boot tries | `sudo slot status`; `slot:` lines in `/var/log/messages` |
| Self-test of this boot | `sys selftest` writes `~/selftest-YYYYmmdd-HHMMSS.txt` (PASS, FAIL or SKIP per check) |
| Services | `rc-status -a` (all runlevels); `sudo rc-service <name> status`, `restart` |
| Guests | `/var/log/incus/<guest>/console.log` and `qemu.log`; `/var/log/incus/incusd.log` |
| Security audit | `/var/log/audit/audit.log` |
| Health check report | `sys security report`; `/var/lib/convergent/check/last` |
| Searchable in Grafana (int browser, needs svc) | the host's, the firewalls' and wan's syslog, including host audit records; not file-only logs such as `/var/log/guests-setup.log` or `/var/log/incus/` |

All of them need `sudo` to read, except the self-test report in the owner's home.

## 9. Read the encrypted state from another Linux

For example from Rocky, with the Convergent disk attached as `/dev/sdX`. As root:

```sh
cryptsetup open /dev/disk/by-partlabel/cv-state cvstate     # asks the LUKS passphrase
mkdir -p /mnt/cv && mount -o ro,nologreplay,subvolid=5 /dev/mapper/cvstate /mnt/cv
ls /mnt/cv          # home, pool (guests), var-<release> (one per release), etc
umount /mnt/cv && cryptsetup close cvstate
```

If the other Linux has its own Convergent disk attached, `by-partlabel` is ambiguous: use
`/dev/sdX4` instead.

## 10. Second passphrase and header backup

Do this once the laptop is in daily use, and keep the backup on offline encrypted media. Works
when: `luksDump` lists two keyslots.

```sh
sudo cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
sudo rm /var/lib/convergent/luks-header.sha256 && sudo facts boot    # the checker takes the new header
sudo cryptsetup luksDump /dev/disk/by-partlabel/cv-state             # check
```

## 11. Start over

Write the disk image again (README, Install). Everything on the disk is lost, including `/home`.
A `backup` holds `/home`, the writable `/etc` files, the owner's containers and profiles, and
custom filesystem/ISO volumes. VM instances, custom block volumes, the system guest instances
and credentials in `/var/lib/convergent` are excluded; read `EXCLUDED` in the backup.
There is no restore tool. Finish automatic guest setup first, mount the backup disk, then as root
select a generation and verify it before restoring anything:

```sh
set -e
backup=/mnt/backup/convergent-backups/backup-YYYYmmddTHHMMSSZ
(cd "$backup" && sha256sum -c SHA256SUMS)
```

Unpack `home.tar` and restore the needed writable files from `etc.tar`, preserving numeric
ownership, ACLs and xattrs. Recreate the pools/networks referenced by the owner's profiles.
Restore profiles in the recreated owner project before importing containers (older backups
lack `profiles.json` and need their profiles reconstructed manually):

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

Restore custom volumes before importing the owner's containers. Use the same project
and pool as each archive's `projects/<project>/<pool>/` directory. Browser and svc data use
project `default`, pool `default`; they need `incus storage volume import`, not `incus import`
or manual unpacking. Close all browsers, stop svc, and do not run guest setup/updates during
the following steps:

```sh
project=default
pool=default
ic stop svc --timeout 120
ic list                           # def, int and svc must be STOPPED
```

Repeat for each row, setting `volume`, `profile` and `device` from the table. Check the instance's
`ic config show <guest>` first (add `--expanded` to see inherited devices); if its local
`devices` override the profile, update that device too. Older backups may call the browser
archives `browser-web-state.tar.gz` and
`browser-admin-state.tar.gz`; use those archive paths for def and int respectively.

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

The temporary names must be unused. Renaming the old volume also redirects its existing
attachments, so reset every listed consumer's profile/local device to the restored original
name before restarting. Keep `*-before-restore` until the restored data works; its `used_by`
must be empty after reattachment. Repeat for owner volumes with their own project, pool and
consumers; if no volume exists yet, omit the old-volume rename. Start svc with `ic start svc`,
then open def/int normally and verify saved profiles/downloads and Grafana/history. Only then
remove the unused old volumes with `ic storage volume delete "$pool" <volume-before-restore>`.

Finally import the owner's containers, then start them after checking their expanded devices:

```sh
project=owner                       # the original owner project name
for archive in "$backup/projects/$project"/instance-*.tar.gz; do
    [ -f "$archive" ] || continue
    ic import "$archive"
done
```

## 12. An online update fails

First `sys update check`: it names the newest version (or release ID for older manifests)
and how old its signature is. New installs use `beta/`; the temporary `bleeding-edge/` bridge
delivers 0.1.0 to older laptops, which use `beta/` after reboot.
`sys update install` stops with the reason. Running it again resumes the download.

| Message | Do |
|---|---|
| `resolves to no public address` | Wi-Fi first (recipe 5). Otherwise the blocklist holds the server: add the host from `/etc/convergent/update.conf` to `/var/lib/convergent/dns/allow`, run `sudo dns-push local`, try again |
| `could not open the update source` | a firewall is not answering: recipe 6 |
| `signature does not verify`, `latest is not signed`, `does not match the manifest` | never bypass it: what arrived is not what was published. Try again; if it repeats, update from USB with a release you built (README, Update) |
| `this release has no online updates` | the image lacks its release key or update URL: update from USB |
| `not enough free space in /var` | make room in `/var`: what is still missing, plus 1 GiB |

Works when: `sys update` shows the new release with `+3`; then reboot (recipe 2 if it
does not become good).

## 13. A kernel panic or CrashRecorded alert

An oops now panics; a panic reboots after 10 seconds. After unlocking the next boot, `facts boot`
archives EFI pstore records in `/var/lib/convergent/crash/<UTC-timestamp>/`, accessible only to
root. It verifies and syncs each copy before removing the firmware record. Older archives in
`/var/lib/convergent/pstore` move to `crash` on the first run. The Security dashboard shows
archived crash counts beside checker results; `CrashRecorded` reports unacknowledged records.

`kernel.panic_on_oops=1` is KSPP hardening. For a repeatedly oopsing driver, run
`sudo sysctl -w kernel.panic_on_oops=0` to disable that panic trigger until reboot. To keep the
exception, set it to `0` in `rootfs/etc/sysctl.d/90-convergent.conf` and build/install a release;
the running root is read-only. If the reboot loop prevents that, boot the previous slot first
(recipe 3).

```sh
sudo find /var/lib/convergent/crash -type f
sudo cat /var/lib/convergent/crash/<UTC-timestamp>/<record>
```

Keep a copy before acknowledging a crash: remove only its reviewed timestamp directory with
`sudo rm -r /var/lib/convergent/crash/<UTC-timestamp>`, then run `sudo facts boot` to refresh
`cv_crash_records`. The `CrashRecorded` alert clears when no archived files remain.
Firmware must support EFI variable writes during a panic; an empty archive alone does not
prove the previous shutdown was clean. If the release keeps crashing, boot the other slot
(recipe 3).
