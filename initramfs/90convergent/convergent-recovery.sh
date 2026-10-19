#!/bin/sh
set -eu
export LC_ALL=C
{ set +ax; } 2>/dev/null
umask 077

release=$1
slot=$2
state=$3
exec </dev/console >/dev/console 2>&1
. /lib/convergent-recovery.sh

while :; do
	printf '\nConvergent recovery: release %s, slot %s\nData is mounted read-write at %s\n' "$release" "$slot" "$state"
	printf '1. Root shell (exit returns here)\n2. Reset owner password\n3. Continue booting this release\n4. Reboot\n5. Power off\nRecovery choice: '
	IFS= read -r choice || exit 1
	case $choice in
	1) sh -i || :; stty "$saved" ;;
	2) reset_password || echo 'Password reset failed.' ;;
	3) exit 0 ;;
	4) sync; reboot -f ;;
	5) sync; poweroff -f ;;
	esac
done
