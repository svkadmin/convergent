#!/bin/sh
# ARCHITECTURE 5.2

release=$(getarg convergent.release=)
[ -n "$release" ] || die "convergent: no convergent.release= on the command line"

dev=/dev/disk/by-partlabel/cv-state
state=/run/cv-state
udevadm settle
[ -b "$dev" ] || die "convergent: no partition labelled cv-state"

# Three passphrase attempts; failure powers off.
tries=0
while :; do
	[ "$tries" -lt 3 ] || die "convergent: the state volume did not open"
	tries=$((tries + 1))
	stty -echo </dev/console 2>/dev/null
	printf 'Convergent passphrase [%s/3]: ' "$tries" >/dev/console
	IFS= read -r pass </dev/console || pass=''
	stty echo </dev/console 2>/dev/null
	echo >/dev/console
	printf '%s' "$pass" | cryptsetup open --type luks2 --key-file - "$dev" cv-state && break
done
pass=''

# Arm without magic close; a hang must reset the board.
if [ -e "$NEWROOT/etc/init.d/convergent-watchdog" ]; then
	# TCO watchdog: LPC or SMBus, depending on chipset.
	modprobe -q lpc_ich
	modprobe -q i2c_i801
	if modprobe iTCO_wdt heartbeat=180 && udevadm settle && [ -c /dev/watchdog ]; then
		printf '.' >/dev/watchdog
	else
		warn "convergent: no hardware watchdog; a hang needs a manual reset"
	fi
fi

mkdir -p "$state"
mount -t btrfs -o subvolid=5,noatime /dev/mapper/cv-state "$state" ||
	die "convergent: the state volume did not mount"

# Prepare this release's /var atomically from the good release.
if [ ! -d "$state/var-$release" ]; then
	new="$state/var-$release.new"
	[ ! -d "$new" ] || btrfs -q subvolume delete "$new"
	good=$(cat "$state/good" 2>/dev/null)
	# Only a fresh install starts /var from the image.
	[ -z "$good" ] || [ -d "$state/var-$good" ] ||
		die "convergent: /var of the good release $good is missing; not starting release $release from the image"
	if [ -n "$good" ]; then
		btrfs -q subvolume snapshot "$state/var-$good" "$new"
	else
		# First install: /var starts from the image's own.
		btrfs -q subvolume create "$new" && cp -a "$NEWROOT/var/." "$new/"
	fi && sync && mv "$new" "$state/var-$release" ||
		die "convergent: could not prepare /var for release $release"
fi
[ -d "$state/home" ] || btrfs -q subvolume create "$state/home"
[ -d "$state/pool" ] || btrfs -q subvolume create "$state/pool"
mkdir -p "$state/etc"

opts=noatime,nodev,nosuid
mount -t btrfs -o "subvol=var-$release,$opts" /dev/mapper/cv-state "$NEWROOT/var" &&
	mount -t btrfs -o "subvol=home,$opts" /dev/mapper/cv-state "$NEWROOT/home" &&
	mkdir -p "$NEWROOT/var/lib/incus-pool" &&
	mount -t btrfs -o "subvol=pool,noatime,nodev" /dev/mapper/cv-state "$NEWROOT/var/lib/incus-pool" &&
	mount -t tmpfs -o mode=1777,nodev,nosuid,noexec tmpfs "$NEWROOT/tmp" ||
	die "convergent: could not mount the writable places"

# Seed and bind the image's writable /etc list.
while read -r entry; do
	case $entry in '' | '#'*) continue ;; esac
	dst="$state/etc/$entry"
	if [ ! -e "$dst" ]; then
		mkdir -p "${dst%/*}"
		cp -a "$NEWROOT/etc/$entry" "$dst" ||
			die "convergent: /etc/$entry is missing from the image"
	fi
	mount --bind "$dst" "$NEWROOT/etc/$entry" ||
		die "convergent: could not bind /etc/$entry"
done <"$NEWROOT/usr/lib/convergent/etc-state"

[ -s "$state/etc/machine-id" ] || tr -d - </proc/sys/kernel/random/uuid >"$state/etc/machine-id"

umount "$state"
