#!/bin/bash

check() { return 255; }
depends() { echo convergent; }

installkernel() {
	instmods vfat nls_cp437 nls_iso8859-1 nls_utf8 ext4 exfat
}

install() {
	inst_multiple lsblk findmnt flock logger id rmdir sed grep expr stat sha256sum cut head dd cmp tar date chattr
	inst_simple "$dracutsysrootdir/usr/local/sbin/slot" /sbin/slot
	inst_simple "$moddir/parse-rescue.sh" /etc/convergent/rescue
	[ ! -f "$dracutsysrootdir/etc/convergent/release.pub" ] ||
		inst_simple "$dracutsysrootdir/etc/convergent/release.pub" /etc/convergent/release.pub
	inst_simple "$moddir/menu.sh" /sbin/convergent-rescue
	inst_hook cmdline 95 "$moddir/parse-rescue.sh"
	inst_hook pre-mount 00 "$moddir/rescue.sh"
}
