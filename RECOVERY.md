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
an entry named `Gentoo Linux <release> (slot a)` or `(slot b)` (releases before 2026-10-18 show
only `Gentoo Linux`: the top one is the default). Pick the other one. Works when: `sudo slot
status` shows the other slot booted.

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
list of update servers. Browsers have Internet, so try one (`browser web`) to tell the two apart.

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
| Searchable in Grafana (admin browser, needs svc) | the host's, the firewalls' and wan's syslog, including host audit records; not file-only logs such as `/var/log/guests-setup.log` or `/var/log/incus/` |

All of them need `sudo` to read, except the self-test report in the owner's home.

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
A `backup` holds `/home`, the writable `/etc` files, the owner's instances and the custom volumes;
not the firewalls, wan (with its saved Wi-Fi networks), svc, or the credentials in
`/var/lib/convergent`. There is no restore tool: unpack the archives and bring instances back
with `incus import`.

## 12. An online update fails

First `sys update check`: it names the newest release and how old its signature is.
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
