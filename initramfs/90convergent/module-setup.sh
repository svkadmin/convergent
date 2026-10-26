#!/bin/bash
# ARCHITECTURE 5.2

check() {
	return 255 # only when asked for by name
}

depends() {
	echo crypt btrfs dm
}

installkernel() {
	# The hardware watchdog, armed once the passphrase is in.
	if ! dracut_module_included convergent-rescue; then instmods lpc_ich i2c_i801 iTCO_wdt; fi
}

install() {
	inst_multiple cryptsetup btrfs mount umount mkdir cp cat mv sync modprobe stty tr readlink awk sgdisk partx blockdev blkid wc sleep chown chmod openssl mktemp rm reboot poweroff
	inst_simple "$moddir/convergent-recovery.sh" /sbin/convergent-recovery
	inst_simple "$moddir/recovery-lib.sh" /lib/convergent-recovery.sh
	inst_simple "$moddir/unlock-state.sh" /lib/convergent-unlock.sh
	if ! dracut_module_included convergent-rescue; then inst_hook pre-pivot 50 "$moddir/convergent-state.sh"; fi
}
