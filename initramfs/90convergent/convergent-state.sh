#!/bin/sh
# ARCHITECTURE 5.2

release=$(getarg convergent.release=)
[ -n "$release" ] || die "state: no convergent.release= on the command line"

. /lib/convergent-unlock.sh

# Disk images are written small: grow state to the end of its disk, while the passphrase is still
# here for the LUKS resize. Each step checks its own size, so an interrupted grow finishes on a
# later boot; Btrfs follows after mounting. A failure only keeps the old size.
grow_state() {
	part=$(readlink -f "$dev") && sys=/sys/class/block/${part##*/} && [ -r "$sys/partition" ] || return 0
	num=$(cat "$sys/partition") && parent=$(readlink -f "$sys/..") && disk=/dev/${parent##*/} || return 0
	start=$(cat "$sys/start") && end=$((start + $(cat "$sys/size"))) || return 1
	limit=$(cat "$parent/size") || return 1
	cap=0
	[ ! -f "$NEWROOT/usr/lib/convergent/state-max-gib" ] || cap=$(cat "$NEWROOT/usr/lib/convergent/state-max-gib")
	case $cap in ''|*[!0-9]*) return 1 ;; esac
	if [ "$cap" -gt 0 ] && [ $((start + cap * 2097152)) -lt "$limit" ]; then limit=$((start + cap * 2097152)); fi
	# Last partition only, and at least 1 GiB (in 512-byte units) to gain.
	last=1
	for p in "$parent"/*/start; do [ "$(cat "$p")" -lt "$end" ] || last=; done
	if [ -n "$last" ] && [ $((limit - end)) -gt 2097152 ]; then
		info=$(LC_ALL=C sgdisk -i "$num" "$disk") || return 1
		first=$(printf '%s\n' "$info" | awk '/^First sector:/ {print $3}')
		guid=$(printf '%s\n' "$info" | awk '/^Partition unique GUID:/ {print $4}')
		[ -n "$first" ] && [ -n "$guid" ] || return 1
		sector=$(blockdev --getss "$disk") || return 1
		sgdisk -e "$disk" >/dev/null || return 1
		table=$(LC_ALL=C sgdisk -p "$disk") || return 1
		usable=$(printf '%s\n' "$table" | awk '/last usable sector is/ {print $NF}')
		case $usable in ''|*[!0-9]*) return 1 ;; esac
		target=$((limit * 512 / sector - 1))
		[ "$target" -le "$usable" ] || target=$usable
		if [ $(((target + 1) * sector / 512)) -gt "$end" ]; then
			sgdisk -d "$num" -n "$num:$first:$target" -t "$num:8309" -c "$num:cv-state" -u "$num:$guid" "$disk" >/dev/null &&
				partx -u --nr "$num" "$disk" || return 1
		fi
	fi
	# The LUKS mapping 1 GiB or more short of its partition (header aside).
	[ $(( $(cat "$sys/size") - $(blockdev --getsz /dev/mapper/cv-state) )) -gt 2097152 ] || return 0
	printf '%s' "$pass" | cryptsetup resize --key-file - cv-state
}
grow_state || warn "state: could not grow the state volume; it keeps its size"
pass=''

# Arm without magic close; a hang must reset the board.
arm_watchdog() {
	if [ -e "$NEWROOT/etc/init.d/convergent-watchdog" ]; then
		# TCO watchdog: LPC or SMBus, depending on chipset.
		modprobe -q lpc_ich
		modprobe -q i2c_i801
		if modprobe iTCO_wdt heartbeat=180 && udevadm settle && [ -c /dev/watchdog ]; then
			printf '.' >/dev/watchdog
		else
			warn "state: no hardware watchdog; a hang needs a manual reset"
		fi
	fi
}
recovery=$(getarg convergent.recovery=) || recovery=
[ "$recovery" = 1 ] || arm_watchdog

mkdir -p "$state"
mount -t btrfs -o subvolid=5,noatime /dev/mapper/cv-state "$state" ||
	die "state: the state volume did not mount"
# A no-op at full size; finishes a grow that stopped after the partition or LUKS step.
btrfs -q filesystem resize max "$state" >/dev/null ||
	warn "state: Btrfs did not grow; run btrfs filesystem resize max /var"

# Replace shadow before binding it, and leave the watchdog idle while the owner works.
if [ "$recovery" = 1 ]; then
	slot=$(getarg dm-mod.waitfor=)
	sh /sbin/convergent-recovery "$release" "${slot#PARTLABEL=cv-slot-}" "$state" ||
		die "state: recovery stopped"
	arm_watchdog
fi

# Prepare this release's /var atomically; cached policy is rebuilt once per release.
if [ ! -d "$state/var-$release" ]; then
	new="$state/var-$release.new"
	[ ! -d "$new" ] || btrfs -q subvolume delete "$new"
	# No file: a fresh install. A file that cannot be read must not look like one.
	good=
	if [ -e "$state/good" ]; then
		good=$(cat "$state/good") || good=
		case $good in "" | *[!0-9]*) die "state: $state/good is unreadable; not starting /var from the image" ;; esac
	fi
	# Only a fresh install starts /var from the image.
	[ -z "$good" ] || [ -d "$state/var-$good" ] ||
		die "state: /var of the good release $good is missing; not starting release $release from the image"
	if [ -n "$good" ]; then
		btrfs -q subvolume snapshot "$state/var-$good" "$new"
	else
		# First install: /var starts from the image's own.
		btrfs -q subvolume create "$new" && cp -a "$NEWROOT/var/." "$new/"
	fi && rm -rf "$new/cache/apparmor" && sync && mv "$new" "$state/var-$release" ||
		die "state: could not prepare /var for release $release"
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
	die "state: could not mount the writable places"

# Add image accounts before the persistent files hide them.
append_account() {
	tmp=$(mktemp "$state/etc/.$1.XXXXXX") || return 1
	cp -p "$state/etc/$1" "$tmp" && printf '%s\n' "$2" >>"$tmp" &&
		sync && mv -f "$tmp" "$state/etc/$1" && sync || { rm -f "$tmp"; return 1; }
}
merge_accounts() {
	while IFS=: read -r name password number rest; do
		case $number in '' | *[!0-9]*) continue ;; esac
		[ "$number" -lt 1000 ] || continue
		awk -F: -v n="$name" '$1 == n {found=1} END {exit !found}' "$state/etc/$1" && continue
		other=$(awk -F: -v id="$number" '$3 == id {print $1}' "$state/etc/$1") || return 1
		if [ -n "$other" ]; then
			warn "state: skipping $1 account $name: ID $number belongs to $other"
			continue
		fi
		if [ "$1" = passwd ]; then
			gid=${rest%%:*}
			group=$(awk -F: -v id="$gid" '$3 == id {print $1}' "$NEWROOT/etc/group") || return 1
			other=$(awk -F: -v id="$gid" -v n="$group" '$3 == id && $1 != n {print $1}' "$state/etc/group") || return 1
			if [ -n "$other" ]; then
				warn "state: skipping passwd account $name: GID $gid belongs to $other"
				continue
			fi
		fi
		if ! awk -F: -v n="$name" '$1 == n {found=1} END {exit !found}' "$state/etc/$2"; then
			line=$(awk -F: -v n="$name" '$1 == n {print; exit}' "$NEWROOT/etc/$2")
			# Gentoo leaves some groups out of gshadow: then a locked entry.
			if [ -z "$line" ]; then
				if [ "$2" = shadow ]; then line="$name:!::0:::::"; else line="$name:!::"; fi
			fi
			# The locked entry lands first, so an interrupted merge can resume.
			append_account "$2" "$line" || return 1
		fi
		append_account "$1" "$name:$password:$number:$rest" || return 1
	done <"$NEWROOT/etc/$1"
}
for entry in passwd group shadow gshadow; do
	[ ! -e "$state/etc/$entry" ] || continue
	tmp=$(mktemp "$state/etc/.$entry.XXXXXX") || die "state: could not seed /etc/$entry"
	cp -p "$NEWROOT/etc/$entry" "$tmp" && sync && mv "$tmp" "$state/etc/$entry" && sync ||
		{ rm -f "$tmp"; die "state: could not seed /etc/$entry"; }
done
merge_accounts group gshadow && merge_accounts passwd shadow ||
	warn "state: could not merge the image's new system accounts; a new service may not start"

# Serial access for the existing owner, before binding the account files.
merge_serial_group() {
	owner=$(awk -F: 'NR == FNR {if ($1 == "wheel") {gid=$3; members="," $4 ","} next}
		$3 >= 1000 && (gid != "" && $4 == gid || index(members, "," $1 ",")) {user=$1; n++}
		END {if (n > 1) exit 1; print user}' "$state/etc/group" "$state/etc/passwd") || return 1
	[ -n "$owner" ] || return 0
	members=$(awk -F: '$1 == "dialout" {print $4; found=1} END {exit !found}' "$state/etc/group") || return 1
	if ! awk -F: '$1 == "dialout" {found=1} END {exit !found}' "$state/etc/gshadow"; then
		append_account gshadow "dialout:!::$members" || return 1
	fi
	for entry in gshadow group; do
		awk -F: -v u="$owner" '$1 == "dialout" && index("," $4 ",", "," u ",") {found=1}
			END {exit !found}' "$state/etc/$entry" && continue
		tmp=$(mktemp "$state/etc/.$entry.XXXXXX") || return 1
		cp -p "$state/etc/$entry" "$tmp" &&
			awk -F: -v OFS=: -v u="$owner" '$1 == "dialout" {$4=$4 ($4 == "" ? "" : ",") u} {print}' \
				"$state/etc/$entry" >"$tmp" && sync && mv -f "$tmp" "$state/etc/$entry" && sync ||
			{ rm -f "$tmp"; return 1; }
	done
}
merge_serial_group || warn "state: could not grant the owner serial access"

# Seed and bind the image's writable /etc list.
while read -r entry; do
	case $entry in '' | '#'*) continue ;; esac
	dst="$state/etc/$entry"
	if [ ! -e "$dst" ]; then
		mkdir -p "${dst%/*}"
		cp -a "$NEWROOT/etc/$entry" "$dst" ||
			die "state: /etc/$entry is missing from the image"
	fi
	mount --bind "$dst" "$NEWROOT/etc/$entry" ||
		die "state: could not bind /etc/$entry"
done <"$NEWROOT/usr/lib/convergent/etc-state"

[ -s "$state/etc/machine-id" ] || tr -d - </proc/sys/kernel/random/uuid >"$state/etc/machine-id"
# root:shadow 0640 for shadow and gshadow, also on installs made before this was right: the lock
# screen checks passwords through unix_chkpwd, which is setgid shadow.
g=$(awk -F: '$1 == "shadow" { print $3 }' "$state/etc/group")
case $g in "" | *[!0-9]*) warn "state: no shadow group; the lock screen cannot check passwords" ;;
*) chown "0:$g" "$state/etc/shadow" "$state/etc/gshadow" && chmod 0640 "$state/etc/shadow" "$state/etc/gshadow" ||
	warn "state: could not set shadow permissions" ;;
esac

umount "$state"
