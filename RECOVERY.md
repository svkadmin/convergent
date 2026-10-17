# Recovery

Numbered recipes. Each says when it applies, what to do, and how to tell it worked. Commands run
on the laptop as the owner unless the recipe says otherwise.

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

## 1. Wrong passphrase, the laptop powers off

Three wrong tries power it off; nothing is lost. The prompt uses the **US layout**: on a Slovak
keyboard `@` is Shift+2, `y` and `z` are swapped, digits are on the top row without Shift. Power
on and type it again.

Right after an update each power-on uses one of the new release's three tries, so three powered-off
sessions bring the previous release back (recipe 2).

## 2. A new release does not boot or does not become good

After `slot write` the new release gets three boot tries. A boot that hangs after unlock is reset
by the hardware watchdog after ten minutes, if the laptop has one (otherwise hold the power
button); a boot whose health checks fail does not mark itself good. After the third try the
previous slot boots by itself, with the `/var` it had.

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
an entry named `Convergent <release> (slot A)` or `(slot B)` (the first release shows `Gentoo
Linux` for both: the top one is the default). Pick the other one.

That slot uses its own `/var` from before the update, so changes made since are not in it. The
next `slot write` must be newer than the highest release ever marked good.

## 4. `guests init` or `guests update` stopped

Both print the step that failed. Run `guests init` again with the same directory: finished steps
are skipped. `guests update` restores the old guest by itself when the new one fails its checks;
run it again once the cause is fixed.

```sh
sudo guests status                          # one line per guest and its state
sudo tail -n 50 /var/log/incus/<guest>/console.log
```

A step that fails twice the same way: photograph the last screen of output and keep the laptop
as it is.

## 5. No Wi-Fi

The radio belongs to the `wan` VM, so `ip link` on the host does not show it.

1. Menu: **Wi-Fi: status**. "not found" or no answer means wan or its radio is not up.
2. Is the card handed to wan?
   ```sh
   lspci -nnk | grep -A3 -i network          # "Kernel driver in use: vfio-pci" is right
   sudo guests status                        # wan must be RUNNING
   ```
3. What wan saw at boot:
   ```sh
   sudo grep -i -E 'iwlwifi|wlan|firmware' /var/log/incus/wan/console.log | tail -n 20
   ```
4. Still nothing: send the output of steps 2 and 3.

## 6. Wi-Fi works, no Internet

The path is wan → fw1 or fw2 → the host. One firewall down is fine; both down is not.

```sh
sudo guests status                                                   # fw1, fw2, wan, svc RUNNING
sudo ssh -F /etc/convergent/ssh_config fw1 'ifconfig carp | grep carp:'   # MASTER here, BACKUP on fw2
sudo check                                                           # report: /var/lib/convergent/check/last
```

A captive portal (hotel, train) needs portal mode first: menu **Portal mode: on**.

## 7. A USB device does not work

USBGuard blocks every device it does not know. The internal keyboard and touchpad are not USB,
so they always work.

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
| Warnings and errors of the host | `/var/log/messages` |
| Release checks, boot tries | `sudo slot status`; `slot:` lines in `/var/log/messages` |
| Services | `rc-status` (all); `sudo rc-service <name> status`, `restart` |
| Guests | `/var/log/incus/<guest>/console.log` and `qemu.log`; `/var/log/incus/incusd.log` |
| Security audit | `/var/log/audit/audit.log` |
| Health check report | `/var/lib/convergent/check/last` |
| Everything, searchable | Grafana in the admin browser (needs svc) |

All of them need `sudo` to read.

## 9. Read the encrypted state from another Linux

For example from Rocky, with the Convergent disk attached as `/dev/sdX`. As root:

```sh
cryptsetup open /dev/disk/by-partlabel/cv-state cvstate     # asks the LUKS passphrase
mkdir -p /mnt/cv && mount -o ro,subvolid=5 /dev/mapper/cvstate /mnt/cv
ls /mnt/cv          # home, pool (guests), var-<release> (one per release), etc
umount /mnt/cv && cryptsetup close cvstate
```

If the other Linux has its own Convergent disk attached, `by-partlabel` is ambiguous: use
`/dev/sdX4` instead.

## 10. Second passphrase and header backup

Do this once the laptop is in daily use, and keep the backup on offline encrypted media:

```sh
sudo cryptsetup luksAddKey /dev/disk/by-partlabel/cv-state
sudo cryptsetup luksHeaderBackup /dev/disk/by-partlabel/cv-state --header-backup-file <file>
sudo rm /var/lib/convergent/luks-header.sha256 && sudo facts boot    # the checker takes the new header
```

## 11. Start over

Write the disk image again (README, Install). Everything on the disk is lost, including `/home`;
restore from `backup` if you made one.
