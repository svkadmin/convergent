#!/bin/bash
# dracut module: Convergent's boot steps (ARCHITECTURE section 5.2, step 4).
# The kernel has already created the dm-verity root from the UKI command line; dracut mounts
# it. This module then opens the state volume and prepares the writable places.

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
	inst_multiple cryptsetup btrfs mount umount mkdir cp cat mv sync modprobe stty tr
	inst_hook pre-pivot 50 "$moddir/convergent-state.sh"
}
