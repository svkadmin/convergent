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
	ext4) [ "$1" != ro ] || options=$options,noload ;;
	btrfs) [ "$1" != ro ] || options=$options,nologreplay ;;
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
	tar --one-file-system --numeric-owner -cf "$dest/logs.tar" "$@" || exit 1
	sync
	echo "Logs copied to ${dest#"$usb"}/logs.tar (includes Incus VM console logs)."
)

while :; do
	printf '\nConvergent rescue: state at %s\n' "$state"
	printf '1. Root shell (exit returns here)\n2. Reset owner password\n3. Write release from USB\n4. Choose next slot\n5. Copy logs to USB\n6. Reboot\n7. Power off\nRescue choice: '
	IFS= read -r choice || exit 1
	case $choice in
	1) sh -i || :; stty "$saved" ;;
	2) reset_password || echo 'Password reset failed.' ;;
	3) write_release || echo 'Release write failed.' ;;
	4) printf 'Next slot (a or b): '; IFS= read -r target || exit 1
		slot rescue-next "$target" || echo 'Slot selection failed.' ;;
	5) copy_logs || echo 'Log copy failed.' ;;
	6) sync; reboot -f ;;
	7) sync; poweroff -f ;;
	esac
done
