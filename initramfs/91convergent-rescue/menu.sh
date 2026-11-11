#!/bin/sh
set -eu
export LC_ALL=C
{ set +ax; } 2>/dev/null
umask 077
state=$1
exec </dev/console >/dev/console 2>&1
. /lib/convergent-recovery.sh

usb_mount() {
	lsblk -p -o NAME,SIZE,FSTYPE,TRAN,MOUNTPOINTS
	printf 'USB partition path: '
	IFS= read -r device || return 1
	case $device in /dev/*) ;; *) return 1 ;; esac
	device=$(readlink -f "$device") || return 1
	[ -b "$device" ] || return 1
	lsblk -snro TRAN "$device" | grep -qx usb || { echo 'Choose a USB device.'; return 1; }
	mounts=$(lsblk -nro MOUNTPOINTS "$device") || return 1
	[ -z "$mounts" ] || { echo 'Device is in use.'; return 1; }
	# Refuse the system disk, including its unmounted slots and ESP.
	system=$(lsblk -snrpo NAME /dev/disk/by-partlabel/cv-state) || return 1
	ancestors=$(lsblk -snrpo NAME "$device") || return 1
	for ancestor in $ancestors; do
		printf '%s\n' "$system" | grep -qxF "$ancestor" && return 1
	done
	fs=$(blkid -s TYPE -o value "$device") || return 1
	options=$1,nodev,nosuid,noexec
	case $fs in
	# Links on the stick are not followed, as in sys update usb.
	ext4) [ "$1" != ro ] || options=$options,noload; options=$options,nosymfollow ;;
	btrfs) [ "$1" != ro ] || options=$options,nologreplay; options=$options,nosymfollow ;;
	vfat | exfat) ;;
	*) echo 'Use a FAT, exFAT, ext4 or Btrfs USB filesystem.'; return 1 ;;
	esac
	mount -t "$fs" -o "$options" "$device" "$usb"
}

write_release() (
	usb=$(mktemp -d /run/rescue-usb.XXXXXX) || exit 1
	trap 'umount "$usb" 2>/dev/null || :; rmdir "$usb"' 0
	usb_mount ro || exit 1
	printf 'Release directory on USB (relative path, . for its root): '
	IFS= read -r path || exit 1
	dir=$(readlink -f "$usb/$path") || exit 1
	case $dir in "$usb" | "$usb"/*) ;; *) exit 1 ;; esac
	printf 'Slot to overwrite (a or b; Enter chooses opposite the last good slot): '
	IFS= read -r target || exit 1
	case $target in '' | a | b) ;; *) exit 1 ;; esac
	slot rescue-write "$dir" "${target:-inactive}"
)

copy_logs() (
	usb=$(mktemp -d /run/rescue-usb.XXXXXX) || exit 1
	trap 'umount "$usb" 2>/dev/null || :; rmdir "$usb"' 0
	usb_mount rw || exit 1
	dest=$(mktemp -d "$usb/convergent-logs-$(date -u +%Y%m%dT%H%M%S).XXXXXX") || exit 1
	cd "$state"
	set --
	for logs in var-*/log pool/containers/*/rootfs/var/log; do
		[ ! -d "$logs" ] || set -- "$@" "$logs"
	done
	[ $# -gt 0 ] || { echo 'No logs found.'; exit 1; }
	# Archive numeric guest owners; do not follow links out of their filesystems.
	# A failing disk has unreadable files: tar skips them and exits 2, and the rest is still worth keeping.
	rc=0; tar --one-file-system --numeric-owner -cf "$dest/logs.tar" "$@" || rc=$?
	case $rc in 0) ;; 2) [ -s "$dest/logs.tar" ] || exit 1 ;; *) exit 1 ;; esac
	sync
	[ "$rc" = 0 ] || echo 'Some files could not be read: the archive is incomplete.'
	echo "Logs copied to ${dest#"$usb"}/logs.tar (includes Incus VM console logs)."
)

eof=0
while :; do
	printf '\nConvergent rescue: state at %s\n' "$state"
	printf '1. Root shell (exit returns here)\n2. Reset owner password\n3. Write release from USB\n4. Choose next slot\n5. Copy logs to USB\n6. Reboot\n7. Power off\nRescue choice: '
	# Ctrl-D (one too many after the shell) shows the menu again; a console that keeps closing stops it.
	IFS= read -r choice || { eof=$((eof + 1)); [ "$eof" -lt 3 ] || exit 1; echo; continue; }
	eof=0
	# Read-only state: the password and release writes would stop half-way.
	case ${CV_STATE_RO:-}:$choice in
	1:2 | 1:3) echo 'The state volume is read-only: copy the logs (5), or read it from another Linux (RECOVERY 9).'; continue ;;
	esac
	case $choice in
	1) sh -i || :; stty "$saved" ;;
	2) reset_password || echo 'Password reset failed.' ;;
	3) write_release || echo 'Release write failed.' ;;
	4) printf 'Next slot (a or b): '; IFS= read -r target || { echo; continue; }
		slot rescue-next "$target" || echo 'Slot selection failed.' ;;
	5) copy_logs || echo 'Log copy failed.' ;;
	6) sync; reboot -f ;;
	7) sync; poweroff -f ;;
	esac
done
