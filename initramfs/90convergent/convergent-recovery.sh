#!/bin/sh
set -eu
export LC_ALL=C
{ set +ax; } 2>/dev/null
umask 077

release=$1
slot=$2
state=$3
exec </dev/console >/dev/console 2>&1
saved=$(stty -g)
tmp=
cleanup() {
	stty "$saved"
	[ -z "$tmp" ] || rm -f "$tmp"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

reset_password() (
	trap cleanup 0
	owner=$(awk -F: '$3 == 1000 {u=$1; n++} END {if (n != 1) exit 1; print u}' "$state/etc/passwd") || return 1
	g=$(awk -F: '$1 == "shadow" {g=$3; n++} END {if (n != 1) exit 1; print g}' "$state/etc/group") || return 1
	case $g in '' | *[!0-9]*) return 1 ;; esac
	stty -echo || return 1
	printf 'New password for %s: ' "$owner"
	IFS= read -r pass || return 1
	printf '\nRepeat new password: '
	IFS= read -r again || return 1
	printf '\n'
	stty "$saved" || return 1
	[ "$pass" = "$again" ] || { echo 'The passwords differ.'; return 1; }
	# As the installer asks.
	[ "${#pass}" -ge 12 ] || { echo 'Use at least 12 bytes.'; return 1; }
	[ "${#pass}" -le 256 ] || { echo 'Use at most 256 bytes.'; return 1; }
	hash=$(printf '%s\n' "$pass" | openssl passwd -6 -stdin) || return 1
	unset pass again
	case $hash in '$6$'*) ;; *) return 1 ;; esac
	tmp=$(mktemp "$state/etc/.shadow.XXXXXX") || return 1
	awk -F: -v OFS=: -v u="$owner" -v h="$hash" '
		$1 == u {$2=h; n++} {print} END {exit n != 1}' "$state/etc/shadow" >"$tmp" &&
		chown "0:$g" "$tmp" && chmod 0640 "$tmp" &&
		sync && mv -f "$tmp" "$state/etc/shadow" && sync || return 1
	echo "Password changed for $owner."
)

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
