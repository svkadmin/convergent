# Recovery

Run commands on the laptop as the owner unless a step says otherwise; `sudo` marks the ones that
need root. Find your symptom in the index, follow the numbered steps in order and stop at the
success check. Each recipe says what to do when a step fails. A `sys` `[yes/No]` prompt left
unanswered for 60 s counts as No.

## Symptom index

| Area | # | Symptom |
|---|---|---|
| Boot and releases | 1 | [Wrong passphrase, the laptop powers off](#1-wrong-passphrase-the-laptop-powers-off) |
| Boot and releases | 2 | [A new release does not boot or does not become good](#2-a-new-release-does-not-boot-or-does-not-become-good) |
| Boot and releases | 3 | [Go back to the previous release by hand](#3-go-back-to-the-previous-release-by-hand) |
| Boot and releases | 12 | [An online update fails](#12-an-online-update-fails) |
| Boot and releases | 13 | [A kernel panic or CrashRecorded alert](#13-a-kernel-panic-or-crashrecorded-alert) |
| Network | 5 | [No Wi-Fi](#5-no-wi-fi) |
| Network | 6 | [Wi-Fi works, no Internet](#6-wi-fi-works-no-internet) |
| Guests | 4 | [`guests init` or `guests update` stopped](#4-guests-init-or-guests-update-stopped) |
| Guests | 14 | [Incus state torn by a power loss](#14-incus-state-torn-by-a-power-loss) |
| Guests | 18 | [Damaged CA or management key](#18-damaged-ca-or-management-key) |
| Devices | 7 | [A USB device does not work](#7-a-usb-device-does-not-work) |
| Sessions | 15 | [Incus UI session or passphrase failure](#15-incus-ui-session-or-passphrase-failure) |
| Sessions | 16 | [Remmina session or keyring failure](#16-remmina-session-or-keyring-failure) |
| Sessions | 21 | [A browser does not close](#21-a-browser-does-not-close) |
| Data and keys | 9 | [Read the encrypted state from another Linux](#9-read-the-encrypted-state-from-another-linux) |
| Data and keys | 10 | [Second passphrase and header backup](#10-second-passphrase-and-header-backup) |
| Data and keys | 11 | [Start over](#11-start-over) |
| Data and keys | 19 | [Copy your data by hand](#19-copy-your-data-by-hand) |
| Data and keys | 20 | [The state disk is lost or read-only](#20-the-state-disk-is-lost-or-read-only) |
| Evidence | 8 | [Where the logs are](#8-where-the-logs-are) |
| Evidence | 17 | [Missing release or network evidence](#17-missing-release-or-network-evidence) |
| Login | – | Forgotten login password: [Recovery boot menu](#recovery-boot-menu), option 2 |

When to call it a loss: a lost LUKS passphrase with no second passphrase (recipe 10) means the data
is gone; a lost management key (recipe 18) means [Start over](#11-start-over).

## Messages

What a tool prints, and the recipe that answers it.

| Message | Recipe |
|---|---|
| `more than one disk has a cv-state partition; detach the other` | [1](#1-wrong-passphrase-the-laptop-powers-off) |
| `booted host slot is not marked good` | [2](#2-a-new-release-does-not-boot-or-does-not-become-good) |
| `release <release> failed its checks` (on the console at boot) | [2](#2-a-new-release-does-not-boot-or-does-not-become-good) |
| `another guests operation is running` | [4](#4-guests-init-or-guests-update-stopped) |
| `interrupted firewall rebuild; run sys firewall rebuild <node>` | run it, then [4](#4-guests-init-or-guests-update-stopped) |
| `<guest>'s QEMU no longer answers Incus` | [4, A frozen guest QEMU](#a-frozen-guest-qemu) |
| `pair commit pending`, `pair rollback pending; both firewalls held` | [4, Interrupted work-topology migration](#interrupted-work-topology-migration) |
| `latest is signed more than 5 minutes in the future; check the clock` | [6, Recover an incorrect clock](#recover-an-incorrect-clock) |
| `certificates: cannot issue under this clock` | [6, Recover an incorrect clock](#recover-an-incorrect-clock) |
| `blocklist serial regressed` | [6](#6-wi-fi-works-no-internet) |
| `this release has no online updates; run sys update usb` | [12](#12-an-online-update-fails) |
| `<guest> has no storage record (a rebuild cut by a power loss)` | [14](#14-incus-state-torn-by-a-power-loss) |
| `<volume> was moved aside by a snapshot restore cut by a power loss` | [14](#14-incus-state-torn-by-a-power-loss) |
| `<volume> still has its pre-restore copy` | [14](#14-incus-state-torn-by-a-power-loss) |
| `invalid CA pair`, `invalid CA key`, `invalid CA certificate` | [18](#18-damaged-ca-or-management-key) |
| `slot: cannot read the highest blessed release` | [2](#2-a-new-release-does-not-boot-or-does-not-become-good) |
| `invalid management private key`, `missing management private key` | [18](#18-damaged-ca-or-management-key) |
| `state disk lost or read-only: reboot` (also on the bar) | [20](#20-the-state-disk-is-lost-or-read-only) |
| `a browser is open; close it, then sys guests update` | [USAGE, Guest updates](USAGE.md#guest-updates) |
| `close browsers before updating guests` | [USAGE, Guest updates](USAGE.md#guest-updates) |
| `firewall maintenance is active; end it with sys firewall undo first` | [USAGE, Firewall maintenance](USAGE.md#firewall-maintenance) |

## Boot menu entries

The boot menu shows for 3 s; an arrow key stops the timer. `<name>` is the base system's name
from the image, `<version>` the Convergent version and `<kernel>` the kernel version.

| Entry | What it boots | When to pick it | What it costs |
|---|---|---|---|
| `SLOT A \| <name> <version> - <kernel>`, `SLOT B …` | that slot's release, straight into services | to go back by hand (recipe 3); the newest release with tries left is the default | one try while the release is not yet good |
| the same entry ending in `(Recovery)` | the same release, with the Recovery menu before any service | a root shell or a password reset | one try while the release is not yet good; only Continue leads to the bless |
| `RESCUE \| <name> <version> - <kernel>` | the standalone rescue initramfs; no slot root | neither slot boots; a release from USB; logs to USB | nothing: it never counts a try or marks a release good |

## Recovery boot menu

Pick the entry of the release and slot you want, ending in `(Recovery)`. Enter the LUKS passphrase
(US layout); three wrong tries power off. Recovery needs a release that boots and the normal state
unlock: if it cannot reach the passphrase prompt, try the other slot (recipe 3) or Rescue.

The menu names the release and slot; the state partition is mounted read-write at `/run/cv-state`.

1. Root shell. The verified root is `/sysroot`; the encrypted data and the writable `/etc` files
   are under `/run/cv-state`. `exit` returns to the menu.
2. Reset owner password. Type 12–256 bytes twice; it sets the password of uid 1000.
3. Continue booting this release. The health checks then mark it good as usual.
4. Reboot.
5. Power off.

Recovery starts no network service, and the watchdog arms only on Continue, so time in the menu
cannot reset the laptop. On a release that is not yet good, a Recovery boot uses one of its three
tries; Reboot and Power off do not mark it good.

## Standalone rescue entry

Pick `RESCUE | <name> <version> - <kernel>` when neither slot boots. It carries its own initramfs,
needs a working ESP, kernel and state partition, and never mounts a slot root. Enter the LUKS
passphrase (US layout); three failures power off. The state partition is mounted read-write at
`/run/cv-state`. There is no network, watchdog, boot counter, blessing or way to continue into a
release.

1. Root shell. Only the tools of the rescue initramfs; `/sysroot` is empty. `exit` returns.
2. Reset owner password. As in the Recovery menu: 12–256 bytes, uid 1000.
3. Write a release from USB. Steps below.
4. Choose next slot. Type `a` or `b`: the next boot takes that slot's normal entry once, even an
   exhausted one, without resetting its counter or marking it good.
5. Copy logs to USB. Choose a writable USB partition. A new `convergent-logs-<time>.<suffix>`
   directory receives `logs.tar`: every release's `var-*/log` (Incus console and QEMU logs
   included) and the reachable `pool/containers/*/rootfs/var/log`. Guests are not started and VM
   disks not opened, so logs inside VMs are missing. The archive is plaintext: keep the disk
   private.
6. Reboot.
7. Power off.

Write a release from USB (option 3). Bring, in one directory on the USB disk: `manifest`,
`manifest.sig`, `slot.img`, `convergent-<release>-a.efi` and `convergent-<release>-b.efi`. The
filesystem is FAT, exFAT, ext4 or Btrfs; it is mounted read-only, without journal replay.

1. Choose the USB partition from the list, then the release directory (a relative path; `.` for the
   root).
2. Choose the slot: `a`, `b`, or Enter for the slot opposite the last good release.
3. Confirm the printed release and slot with `yes`. The signature must verify against the
   embedded release key; a Rescue entry from a release built without one cannot write releases.
4. Pick option 4 to boot the written slot next; otherwise the newest release boots.

Rescue accepts an older or identical signed release and keeps the `/var` subvolumes, `good` and
`highest`. The write uses the checksum, size and readback checks of `slot` and installs the UKI
with three tries. Later boots return to the newer slot (recipe 3); a normal update refuses a
release that is not newer than `highest`. If Rescue cannot boot, read the state from another
Linux (recipe 9).

## 1. Wrong passphrase, the laptop powers off

Symptom: the passphrase prompt refused three tries and the laptop powered off, or the screen stays
black at boot.

1. Power on and type the passphrase in US layout ([USAGE, First boot](USAGE.md#first-boot)), then
   press Enter, even on a black screen. Ignore an empty `host login:` prompt left by earlier keys.
2. Boot stops with `more than one disk has a cv-state partition; detach the other`: power off,
   unplug the other Convergent disk and boot again.

Success: the passphrase opens the state partition and the login prompt appears.

If it fails: three wrong tries cost no data. Right after an update every power-on uses one of the
new release's three tries; after the third, the previous release comes back (recipe 2). A USB disk
cannot install over an existing Convergent disk, because the two are ambiguous: erase the old disk
first, in the firmware (Dell: F2, Maintenance, Data Wipe) or from another system.

## 2. A new release does not boot or does not become good

Symptom: after an update the bar stays at `rel <release> UNBLESSED`, the laptop resets by itself,
or the previous release is back.

After `slot write` the new release has three boot tries. A boot that is not good within about
13 minutes of unlocking is reset by the hardware watchdog if the laptop has one (otherwise hold
the power button). After the third try the previous slot boots by itself, with its own `/var`.

The release booted, but the bar says `UNBLESSED` because setup failed early:

1. Close the browsers.
2. Start setup and the health checks again, then read the result:
   ```sh
   sudo rc-service convergent-setup start
   sudo rc-service convergent-bless start
   sudo slot status
   ```

Success: `sudo slot status` shows `good` equal to the booted release and the booted slot as `good`;
the bar shows `rel <release> good`.

If it fails: `convergent-bless` prints what the health checks found (a crashed or stopped service
of the default runlevel, a protection not running, Incus not answering). Fix that, then run the
three commands again, within the watchdog window. `slot: cannot read the highest blessed release`
means the state file `highest` is damaged: in the Recovery root shell, write the release ID the
menu names into it (`echo <release> >/run/cv-state/highest`), then Continue.

The release does not boot, or the previous one came back by itself:

1. On the previous release, read the failed release's log from its own `/var`:
   ```sh
   sudo slot status                                     # booted release, slot, good, highest
   sudo mkdir -p /run/st && sudo mount -o ro,nologreplay,subvolid=5 /dev/mapper/cv-state /run/st
   sudo grep ' slot:' /run/st/var-<failed release>/log/messages
   sudo umount /run/st
   ```
2. Keep the output and the release ID; write the fixed release when it is available.

Success: `sudo slot status` shows the previous release booted and `good`.

If it fails: neither slot boots, so use [Rescue](#standalone-rescue-entry).

## 3. Go back to the previous release by hand

Symptom: the release in the other slot is wanted, for example because the newer one misbehaves
after it became good.

1. Stop the boot menu with an arrow key and pick the other `SLOT A | <name> <version> - <kernel>`
   or `SLOT B` entry. Older entries may show only the base system's name.
2. Check the result:
   ```sh
   sudo slot status          # booted: the slot you picked
   ```
3. To stay on the older release, press `d` on its entry in the menu for a persistent default (the
   next `slot write` clears it), or write it over the newer slot too (Rescue option 3).
   Otherwise the newer slot stays the default.

Success: `sudo slot status` shows the chosen release as booted.

If going back cut a firewall update, work DHCP can be off on both firewalls (the newer `/var` held
the leases). Resume it:

```sh
sudo mkdir -p /var/lib/convergent/guests/leases
sudo touch /var/lib/convergent/guests/leases/held
sys guests update
```

> [!NOTE]
> The older release's `/var` predates the update; guest pool data stays current and may conflict
> with old metadata. There is no guest-update rollback guard. The next `slot write` must exceed
> `highest`.

## 4. `guests init` or `guests update` stopped

Symptom: the bar shows `SETUP failed` or `GUESTS failed`, or `sys guests update` stops with an
error.

1. Read the state and the reason:
   ```sh
   sys guests status                            # one line per guest and its state
   sudo tail -n 50 /var/log/guests-setup.log    # first boot (SETUP)
   sudo tail -n 50 /var/log/guests-update.log   # updates (GUESTS)
   sudo tail -n 50 /var/log/incus/<guest>/console.log
   ```
2. Retry. First-boot setup: `sys guests setup` (completed steps are skipped). An update: fix the
   printed cause, then `sys guests update`; a failed update has already restored the old guest.
3. If fw1 stays silent after a handoff, run `sys firewall rebuild fw1`, then `sys guests update` to
   apply the rest and clear `GUESTS failed`.
   After a commit, rebuild the silent firewall the same way; for wan or svc run the printed
   `guests update` command, then `sys guests update`.

Success: `SETUP` and `GUESTS` leave the bar; `sys guests status` shows fw1, fw2, wan and svc
`running`.

If a step fails twice the same way, photograph the last screen and leave the laptop unchanged.
`another guests operation is running` means another run held the lock for 10 minutes: wait for it
(`GUESTS` on the bar) and retry.

### A frozen guest QEMU

Symptom: `guests` stops with `<guest>'s QEMU no longer answers Incus`; the VM answers no Incus
read or change.

The checker kills and restarts a frozen firewall by itself unless a guest journal, maintenance or
shutdown inhibits it, and starts both firewalls when both are stopped or paused for 180 s
([ARCHITECTURE, Self-heal](ARCHITECTURE.md#self-heal)). For wan, or a firewall while the heal is
inhibited, end the QEMU yourself:

```sh
sudo timeout 30 incus --force-local query '/1.0/instances/<guest>/state?project=default'; echo $?  # 124: frozen
pid=$(sudo cat /run/incus/<guest>/qemu.pid)
ps -o args= -p "$pid"                       # must show qemu-system and -name <guest>
sudo kill -KILL "$pid"
```

Then rerun the guests command that failed. Success: `sys guests status` shows the guest `running`.

A wan or svc paused on a full disk (`sys guests status` shows `error` or `frozen`; no uplink):
free space, then `sys guests update` restarts it with `restart --force`; if three tries fail, run
the printed `guests update … --trusted-local` command.

### Interrupted work-topology migration

Symptom: a host upgrade changed the work topology while a handoff or maintenance was active;
`/var/lib/convergent/guests/fw.topology` exists and both firewalls are held stopped.

1. Rerun `sys guests update` (or the original `sudo guests update fw <image-dir>`). Uncommitted
   work restores both old roots before either firewall starts; committed work finishes the start,
   and a firewall that never answers is rebuilt from the journal.
2. If recovery fails, the journal and the holds stay for the next try: inspect `sys guests status`,
   `/var/log/guests-update.log` and both consoles, then rerun.

Success: `sys guests update` ends without error and the checker reopens work access once the
topology validates. Replacement keeps the DHCP leases.

> [!WARNING]
> Never start a partial pair by hand, delete the journal, prune its images or clear its holds.

A committed migration (`fw.topology/committed` exists) whose firewalls answer but never form fw1
`MASTER` and fw2 `BACKUP` fails the pair check on every run. Both already run the new image:

1. Find the demoted firewall (then the same for fw2):
   ```sh
   sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig -g carp; ifconfig carp | grep carp:'
   ```
2. Restore a lost uplink first (recipe 6).
3. Restart that firewall, then rerun `sys guests update`:
   ```sh
   sudo incus --force-local --project default restart fw1 --force   # or fw2
   ```

## 5. No Wi-Fi

Symptom: `sys wifi status` shows no network or no address, or prints "not found".

1. Run `sys wifi status`. "not found" or no answer means wan or its radio is not up.
2. Check that the card is handed to wan and that wan runs:
   ```sh
   lspci -nnk | grep -A3 -i network          # "Kernel driver in use: vfio-pci" is right
   sys guests status                         # wan must be running
   ```
3. wan or svc stopped (Incus gives up after ten crashes in a minute): `sys guests update` starts
   it when no update is pending. If it does not stay up, rebuild it from the installed release
   (svc likewise):
   ```sh
   sudo guests update wan /var/lib/convergent/release-guests/guests/wan --trusted-local
   ```
4. Read what wan saw at boot:
   ```sh
   sudo grep -i -E 'iwlwifi|wlan|firmware' /var/log/incus/wan/console.log | tail -n 20
   ```

Success: `sys wifi status` shows the network and an address.

If it fails: keep the output of steps 2 and 4 for the report.

## 6. Wi-Fi works, no Internet

Symptom: `sys wifi status` shows an address, but names do not resolve or pages do not load in
`def`.

The path is wan, then either firewall, then the host and the browsers; one firewall suffices. The
host reaches the web only for updates: test the Internet in `def`.

1. Collect the facts:
   ```sh
   sys wifi status                # connected, with an address
   sys wifi test                  # "DNS: ok" or "DNS: failed", then wan's own view of its uplink
   sys selftest                   # among its checks: fw1 reaches 9.9.9.9:853 (DNS over TLS)
   sys guests status              # fw1, fw2, wan, svc running
   sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig carp | grep carp:'   # MASTER; BACKUP on fw2
   ```
2. No address or default route: check `sys wifi status` and the upstream router.
3. A captive portal: `sys portal on` ([USAGE, Captive portals](USAGE.md#captive-portals)).
   Resolver selection uses only the first upstream server, so an unusable first resolver does not
   rule out usable later ones.
4. `9.9.9.9:853` fails: a firewall, wan or routing is broken, or the upstream blocks DNS over TLS.
5. `dns-push: blocklist serial regressed` on every run after the provider reset its serial: take
   the lower serial once (local pushes keep the stored list meanwhile):
   ```sh
   echo reset | sudo tee /var/lib/convergent/dns/list.source >/dev/null; sudo dns-push
   ```

Success: `sys wifi test` prints `DNS: ok` and a page loads in `def`.

If it fails: send the output of step 1.

### Recover an incorrect clock

Symptom: `latest is signed more than 5 minutes in the future; check the clock`,
`certificates: cannot issue under this clock`, or DNS and time never come up together.

A clock years off breaks the firewalls' DNS-over-TLS checks and the host's NTS exchange, so DNS and
time cannot bootstrap each other. Correct the host and both firewalls: ntpd only slews, and the host
steps each firewall once per boot. Never disable certificate checks or add unauthenticated servers.

1. Get the current UTC from an independently trusted clock (a correctly set offline device, for
   example) and compare it with `date -u` on the host.
2. Wait for any guest update to finish. Both firewalls must run and answer over SSH; no DNS or
   Internet is needed.
3. Put the verified UTC in place of `YYYY-MM-DD HH:MM:SS`, right before running this on the
   normally booted laptop:

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

4. Check the three clocks against the trusted one: `date -u` on the host, then
   `sudo ssh -F /etc/convergent/ssh_config fw1 date -u`, and the same for fw2.
5. With Wi-Fi back, run `sys wifi test`, then `sudo chronyc online` and `chronyc sources -v`.
6. Run `sys guests update`, so the certificates are checked again.

Success: DNS works, at least two sources are selected or combined (`*` or `+`), and
`chronyc authdata` shows NTS cookies for them. Retry the failed update only after that.

If a command fails: stop and fix that error, then repeat with fresh verified UTC; time services
may still be stopped. Stopping ntpd before the step discards its old samples, and OpenBSD `date`
cancels a pending slew. wan takes its time from the host and follows a step by itself; to step it
at once, run `sudo timeout -k 5 60 incus --force-local --project default exec wan -- rc-service
chronyd restart`.

A laptop that has not finished setup (`cannot issue under this clock`) runs no firewalls yet: set
only the host clock with `sudo date -u -s 'YYYY-MM-DD HH:MM:SS'`, then reboot; setup runs again at
boot.

## 7. A USB device does not work

Symptom: a USB device is ignored, or the wired uplink is gone after a replug.

A fresh disk image allows whole USB classes (HID, storage, hubs); after
[enrolment](USAGE.md#devices) only listed devices work. An empty blocked list alone does not prove
enrolment. Keyboards and touchpads that are not USB are outside USBGuard.

1. List the blocked devices and allow the one you trust:
   ```sh
   sys usb status                # blocked devices with a number (sudo devices list)
   sys usb allow <number>        # asks you to type yes; permanent (sudo devices allow <number>)
   ```

Success: the device works and `sys usb status` no longer lists it as blocked.

If the boot disk was moved to another port and the boot stalls: power off, put it back in its old
port, boot and regenerate the policy with the trusted devices attached
([USAGE, First boot](USAGE.md#first-boot)).

Wired uplink gone after a replug, or `sys security report` says the allowed NIC is not passed
through: the checker re-adds the role by itself about two minutes after the replug, three times
an hour at most ([ARCHITECTURE, Self-heal](ARCHITECTURE.md#self-heal)). Otherwise:

```sh
sys wired remove
sys wired attach
```

If Incus refuses the NIC, reboot.

## 8. Where the logs are

| What | Where |
|---|---|
| Host warnings and errors | `/var/log/messages`; `sys logs` reads it. Failures of `check`, `facts` and `power` are logged at error severity |
| wan warnings, kernel, Wi-Fi, DHCP and time messages | `/var/log/wan/diag.log` in wan (root only, 256 KiB, one rotation); `sys wifi test` shows its last 200 lines |
| Release checks, boot tries | `sudo slot status`; `slot:` lines in `/var/log/messages` |
| Self-test of this boot | `sys selftest` writes `~/selftest-YYYYmmdd-HHMMSS.txt` (PASS, FAIL or SKIP per check) |
| Services | `rc-status -a` (all runlevels); `sudo rc-service <name> status`, `restart`; `convergent-setup` takes `start` only |
| Guests | `/var/log/incus/<guest>/console.log` and `qemu.log`; `/var/log/incus/incusd.log` |
| Guest setup and updates | `/var/log/guests-setup.log`, `/var/log/guests-update.log` |
| Security audit | `/var/log/audit/audit.log` |
| Health check report | `sys security report`; `/var/lib/convergent/check/last` |
| Searchable in Grafana (int browser, needs svc) | Host, firewall and wan syslog, incl. host audit records. Not file-only logs such as `/var/log/guests-setup.log` or `/var/log/incus/` |

Local protected logs need `sudo`; the owner can read the self-test report, run `rc-status -a` and
use Grafana without it. When the laptop does not boot, Rescue copies the logs to USB
([option 5](#standalone-rescue-entry)).

## 9. Read the encrypted state from another Linux

Symptom: the laptop does not boot, or data must be read without it.

On another Linux with the disk attached, as root:

1. Open and mount the state partition read-only:
   ```sh
   cryptsetup open /dev/disk/by-partlabel/cv-state cvstate     # asks the LUKS passphrase
   mkdir -p /mnt/cv && mount -o ro,nologreplay,subvolid=5 /dev/mapper/cvstate /mnt/cv
   ls /mnt/cv          # home, pool (guests), var-<release> (one per release), etc
   ```
2. Copy what you need, then close:
   ```sh
   umount /mnt/cv && cryptsetup close cvstate
   ```

Success: `ls /mnt/cv` lists `home`, `pool`, `etc` and one `var-<release>` per release.

If `by-partlabel` is ambiguous because that Linux has a Convergent disk too, use the partition
itself, `/dev/sdX4`.

## 10. Second passphrase and header backup

Symptom: none; do this once the laptop is in daily use.

> [!CAUTION]
> A lost passphrase with no second one, or a damaged LUKS header without a backup, means the data
> is gone. Keep the header backup on offline encrypted media.

1. Add the passphrase and save the header. The boot prompt types only the US layout: first run
   `sys keyboard next` until the bar shows `US`, and use printable ASCII only.
   ```sh
   sudo cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
   sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
   ```
2. Let the checker take the new header, then check:
   ```sh
   sudo rm /var/lib/convergent/luks-header.sha256 && sudo facts boot
   sudo cryptsetup luksDump /dev/disk/by-partlabel/cv-state
   ```
3. Reboot once and unlock with the new passphrase.

Success: `luksDump` lists two keyslots, and the new passphrase unlocks at boot.

## 11. Start over

Symptom: the laptop must be reinstalled from the disk image, or a lost management key (recipe 18)
leaves no other way.

> [!CAUTION]
> Writing the disk image erases everything on the laptop disk, including `/home`.

1. If the laptop still runs, copy your data ([recipe 19](#19-copy-your-data-by-hand)).
2. [Write the disk image](USAGE.md#install) and complete first boot, including the automatic guest
   setup.
3. Copy your data back (recipe 19).

Success: first boot ends with `rel <release> good` and no `SETUP` on the bar.

## 12. An online update fails

Symptom: `sys update install` stops with a reason.

1. Run `sys update check`: it names the newest version and how old its signature is.
2. Run `sys update install` again; it resumes the download and keeps that release's staged guests
   until their replacement is ready.
3. Follow the table for the printed reason.

| Message | Do |
|---|---|
| `resolves to no public address` | Wi-Fi first (recipe 5). Else the blocklist holds the server: `sys dns allow <host>` with the host from `/etc/convergent/update.conf`, then retry |
| `could not open the update source` | A firewall is not answering: recipe 6 |
| `signature does not verify`, `latest is not signed`, `does not match the manifest` | Never bypass it: what arrived is not what was published. Retry; if it repeats, update from USB with a release you built ([USAGE, USB updates](USAGE.md#usb-updates)); after a release-key rotation, [BUILD, Sign and publish](BUILD.md#sign-and-publish) |
| `this release has no online updates` | The release has no release key or update URL: update from USB |
| `not enough free space in /var` | Free what is still missing in `/var`, plus 1 GiB |
| `latest is signed more than 5 minutes in the future; check the clock` | [Recover an incorrect clock](#recover-an-incorrect-clock), then run it again |

Success: `sudo slot status` shows the new release in the other slot with `+3`. Then reboot
(recipe 2 if it does not become good).

## 13. A kernel panic or CrashRecorded alert

Symptom: the laptop rebooted by itself, or the Security dashboard shows `CrashRecorded`.

A kernel oops reboots the laptop after 10 s. The next boot saves the crash records under
`/var/lib/convergent/crash/`: EFI pstore records in a `<UTC-timestamp>/` directory, and the ACPI
BERT record, when there is one, as `bert-<sha256>`. The Security dashboard shows the counts;
`CrashRecorded` flags unacknowledged records.

1. Review the records:
   ```sh
   sudo find /var/lib/convergent/crash -type f
   sudo cat /var/lib/convergent/crash/<UTC-timestamp>/<record>
   ```
2. Keep a copy, then acknowledge a pstore record by removing its reviewed directory:
   ```sh
   sudo rm -r /var/lib/convergent/crash/<UTC-timestamp>
   ```
3. Acknowledge a BERT record by its hash. The marker suppresses that hash for good, byte-identical
   future records included. It takes the collector's lock; if the 30 s wait expires, retry later:

```sh
sudo flock -w 30 /run/convergent/facts.lock sh -c '
install -d -m 0700 /var/lib/convergent/crash-ack &&
touch /var/lib/convergent/crash-ack/bert-<sha256> &&
sync &&
rm /var/lib/convergent/crash/bert-<sha256>
'
```

4. Refresh the count with `sudo facts boot`.

Success: `CrashRecorded` clears once no archived file remains.

If the release keeps crashing, boot the other slot (recipe 3). For a driver that oopses
repeatedly, `sudo sysctl -w kernel.panic_on_oops=0` stops the panics until reboot. An empty archive
does not prove a clean shutdown: not every firmware writes pstore during a panic.

## 14. Incus state torn by a power loss

Symptom: after a power loss `guests` refuses to run and prints the repair; the bar shows
`GUESTS failed`.

Read the repair in `/var/log/guests-update.log`, or run `sys guests update` to see it. Two cases:

1. A guest without a storage record (the loss hit a rebuild between dropping and recreating the
   record). Run the printed `incus admin sql global "INSERT ..."`, then the printed
   `incus --force-local --project default rebuild <image> <guest>`, then `sys guests update`,
   which re-seeds the guest.
2. A custom volume with a `.incustmp` copy beside it or instead of it (the loss hit a snapshot
   restore). Volume missing: run the printed `sudo mv` to put the copy back. Volume present: the
   restore completed, so run the printed `sudo btrfs subvolume delete` on the copy. Then
   `sys guests update`.

Success: `sys guests update` runs through and `GUESTS failed` leaves the bar.

If it fails with another repair, follow that one the same way; the messages name every step.

## 15. Incus UI session or passphrase failure

Symptom: `int` does not open the Incus UI, a session lock is held, or the passphrase or certificate
is refused.

1. Close `int`, then retry the orphan cleanup:
   ```sh
   sudo incus-ui cleanup
   ```
   The checker retries it every minute, and boot cleanup runs before the greeter. While a guest or
   browser update holds its lock the retries stay quiet; after 6 hours syslog shows `Incus UI orphan
   cleanup busy for over 6 hours`: an update is stuck.
2. A launcher still holds the session lock: close its terminal, or stop the unlocked session,
   delete its credential and set up a new one with a new passphrase:
   ```sh
   sudo incus-ui revoke
   sudo incus-ui setup
   ```
3. Forgotten passphrase or expired certificate: with `int` closed, create a new encrypted bundle:
   ```sh
   sudo incus-ui rotate
   ```

Success: `sys browser incus` unlocks the session and `int` opens the UI. The passphrase prompt
waits 120 s; `passphrase cancelled or timed out` means run `sys browser incus` again.

If it fails: `cleanup` stops `int`, removes the trust and keeps the journal if the stop fails; it
also stops an orphaned Grafana and restores svc's 350 MiB limit. Open WebSockets need `int`
stopped, not just the certificate removed. Never import the private key into persistent NSS state.
`/var/log/messages` holds the `incus-ui` events; `incus` on the Unix socket keeps working.

## 16. Remmina session or keyring failure

Symptom: Remmina does not open or close, or its keyring password is lost.

1. Close it; the checker also stops orphans, and the next open removes stale sockets:
   ```sh
   sys remote close
   ```
2. Resume an interrupted update with `sys guests update`.
3. A lost keyring password cannot be recovered. Keep an offline copy, run `sys remote close`, then
   move the keyrings aside:
   ```sh
   v=/var/lib/incus/storage-pools/default/custom/default_remmina-state
   sudo mv "$v/.local/share/keyrings" "$v/.local/share/keyrings.lost"
   ```
   The next open creates a new encrypted keyring; enter the remote credentials again.

Success: `sys remote open` opens Remmina.

If it fails: a manual rollback uses a retained `guests-*` snapshot of `remmina-state` while
Remmina is stopped; leave `share` alone, because it may hold newer work. Stop every instance that
uses `share` before copying or replacing it.

## 17. Missing release or network evidence

Symptom: the Security dashboard lacks advisory status, blocked-packet samples or radio metrics.

1. Run `sys update check` and inspect Security › Release › Advisory evidence. A missing or
   tampered status means unknown, not zero advisories. Check the clocks before chasing future or
   replayed metadata.
2. Absent blocked-packet samples: on each firewall check `rcctl check pflog_stream`, the TLS
   syslog path to svc, and whether the relevant PF rule logs. `rcctl restart pflog_stream`
   restarts sampling; suppression summaries mean the sample cap was reached.
3. Missing radio metrics can mean disconnected or unsupported hardware. WAN RTT and loss are
   measured from the firewall to the uplink only.
4. For a bounded capture, run `sys firewall capture <interface-or-segment> <seconds>` (1–60 s);
   the pcap lands in `~/captures`. It refuses an incoherent `MASTER`/`BACKUP` pair.

Success: the dashboard shows the evidence again.

If it fails: a failed upstream feed leaves the previous status on the channel, and a pruned
release has no status; republishing is the builder's job ([BUILD, Daily advisory
status](BUILD.md#daily-advisory-status)). After a firewall crash, remove abandoned
`/var/run/fw-capture.*` directories there; they are never durable archives.

## 18. Damaged CA or management key

Symptom: `guests` stops with `invalid CA pair`, `invalid CA key` or `invalid CA certificate`.

1. Close the browsers.
2. Replace the local CA:

```sh
sudo -i
cd /var/lib/convergent/guests/tls
rm -f ca.key ca.crt server.crt incus-server.crt incus-client.crt   # the leaf keys stay
exit
```

3. Run `sys guests update`: it issues a new CA and certificates and installs them in Incus, svc,
   the firewalls and wan.
4. If the Incus UI is set up, run `sudo incus-ui rotate`: the old CA signed its credential.

Success: `sys guests update` finishes without an error.

A damaged or lost management key (`invalid management private key`,
`missing management private key`) cannot be replaced: the firewalls and wan accept only the old
one. [Start over](#11-start-over).

## 19. Copy your data by hand

Symptom: `/home`, a work VM or the `share` volume must be kept off the laptop, before Start over
(recipe 11) or as a routine copy.

There is no backup tool. Copy to a LUKS-encrypted USB disk with `cryptsetup`, `rsync` and `incus`
from the image; the disk must be allowed in USBGuard ([USAGE, USB](USAGE.md#usb)). Each copy goes
into a new dated folder, so an earlier copy stays until you delete it. Browsers, Grafana history,
Remmina's keyring and the system guests are not copied: setup creates them again.

1. Once per disk, find it with `lsblk -o NAME,SIZE,MODEL,TRAN`, then erase and format it. The
   first line refuses anything that is not a USB disk:
   ```sh
   [ "$(lsblk -dno TRAN /dev/sdX)" = usb ] || echo 'STOP: not a USB disk'
   sudo cryptsetup luksFormat /dev/sdX
   sudo cryptsetup open /dev/sdX cv-copy
   sudo mkfs.btrfs /dev/mapper/cv-copy
   sudo cryptsetup close cv-copy
   ```
2. Open and mount it, then check the mount. Stop if the last line does not print
   `/dev/mapper/cv-copy`: a copy would land on the laptop instead.
   ```sh
   sudo cryptsetup open /dev/sdX cv-copy
   sudo mkdir -p /run/copy
   sudo mount -o nodev,nosuid,noexec /dev/mapper/cv-copy /run/copy && sudo chmod 700 /run/copy
   findmnt -no SOURCE /run/copy
   ```
3. Copy into a new folder. Stop each work VM first; an export needs free state space for its VM.
   Close Remmina and stop every VM using `share` before exporting it.
   ```sh
   d=/run/copy/$(date -u +%Y%m%d-%H%M)
   sudo mkdir "$d"
   sudo rsync -aHAX /home/<owner>/ "$d/home/"
   sudo incus --force-local --project owner stop <vm>
   sudo incus --force-local --project owner export <vm> "$d/<vm>.tar.gz"
   sudo incus --force-local --project default storage volume export default share "$d/share.tar.gz"
   ```
4. Check the home copy: this prints nothing when it matches.
   ```sh
   sudo rsync -aHAXcn --itemize-changes /home/<owner>/ "$d/home/"
   ```
5. Unmount and close it before unplugging:
   ```sh
   sync
   sudo umount /run/copy
   sudo cryptsetup close cv-copy
   ```

Restore: open and mount the disk (step 2), copy back from the folder you choose, then close it
(step 5). A VM import needs a name no instance uses; the `share` copy comes back beside the live
volume, to copy files from:

```sh
sudo rsync -aHAX "$d/home/" /home/<owner>/
sudo chown -R <owner>: /home/<owner>
sudo incus --force-local --project owner import "$d/<vm>.tar.gz" <vm>-restored
sudo incus --force-local --project default storage volume import default "$d/share.tar.gz" share-restored
```

Copies made by `sys backup` in 0.1.6 and older hold `home.tar`, `etc.tar` and Incus archives:
extract home with `sudo tar --acls --xattrs --numeric-owner -C / -xpf home.tar`, and import the
archives with the same `incus` commands.

Success: steps 3 and 4 end without an error or output, and `sudo cryptsetup status cv-copy`
reports the device inactive before you unplug the disk.

## 20. The state disk is lost or read-only

Symptom: the bar shows `state disk lost or read-only: reboot`; `check` and `guests` refuse with the
same words; the alerts `StateReadOnly` or `BtrfsDeviceErrors` fire.

`/var` lives on the state partition. The bar shows the message when `/var` is mounted read-only or
not mounted at all, which is what Btrfs does after a disk error; nothing can be repaired in place.

1. Note the error counts while the terminal still works:
   ```sh
   sudo btrfs device stats /var
   ```
2. Reboot:
   ```sh
   sys power reboot
   ```
3. After the reboot, check the alerts and the counts again:
   ```sh
   sys security alerts
   sudo btrfs device stats /var
   ```

Success: the bar shows the alert counts instead of the message, and `StateReadOnly` is not firing.
`BtrfsDeviceErrors` counts errors since the counters were last reset: counts that keep rising
mean a failing disk.

If it repeats: boot [Rescue](#standalone-rescue-entry) and copy the logs to USB (option 5), save
what you can from another Linux (recipe 9), then start over on a sound disk (recipe 11) and copy
your data back (recipe 19).

## 21. A browser does not close

Symptom: a browser window is frozen and closing it from the desktop does nothing.

1. Find its name; running browsers are `def`, `int`, `tmp-portal` or `tmp-<n>`:
   ```sh
   sys browser status
   ```
2. Stop it (`tmp` stops every temporary browser but `tmp-portal`, which is `portal`):
   ```sh
   sys browser close <role>    # def, tmp, int or portal
   ```
3. Open it again as usual.

Success: `sys browser status` no longer lists it, and the browser opens again. A temporary browser
disappears with its stop.

If it fails: Incus not answering at all points to a frozen VM ([recipe 4](#a-frozen-guest-qemu)).
An Incus UI session that stays behind after `int` is recipe 15; Remmina is `sys remote close`
(recipe 16).
