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
	instmods lpc_ich i2c_i801 iTCO_wdt
}

install() {
	inst_multiple cryptsetup btrfs mount umount mkdir cp cat mv sync modprobe stty tr readlink awk sgdisk partx blockdev blkid wc sleep
	inst_hook pre-pivot 50 "$moddir/convergent-state.sh"
}
