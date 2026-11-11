#!/bin/sh
# ARCHITECTURE 5.2: the install image (convergent.install=1, build/stick). No state, no unlock and no
# watchdog: tmpfs /var, /home and /tmp, the install data read-only at /run/convergent-install, and an
# inittab that starts only the installer. dracut moves /run, these mounts included, into the system.

[ "$(getarg convergent.install=)" = 1 ] || return 0

# The installer's terminal: tty1, or convergent.install.console= (a screen or a built-in serial port).
console=$(getarg convergent.install.console=) || console=
[ -n "$console" ] || console=tty1
case $console in
tty[1-9] | tty[1-9][0-9]) line="$console linux" ;;
ttyS[0-9] | ttyS[1-9][0-9]) line="-L 115200 $console vt100" ;;
*) die "install: convergent.install.console=$console is not a screen or serial terminal" ;;
esac
[ -c "/dev/$console" ] || die "install: no terminal /dev/$console"

# rd.emergency=poweroff acts at once: leave the reason on the screen first.
die_shown() { printf '\n%s\nPowering off in 30 seconds.\n' "$1" 2>/dev/null >/dev/console; sleep 30; die "$1"; }
udevadm settle
# One install stick, its data beside its root: a second one would make the labels ambiguous.
for label in cv-inst-root cv-inst-data; do
	[ "$(blkid -o device -t "PARTLABEL=$label" | wc -l)" = 1 ] ||
		die_shown "install: not exactly one partition labelled $label; detach other install media"
done
root_part=$(blkid -o device -t PARTLABEL=cv-inst-root) && data_part=$(blkid -o device -t PARTLABEL=cv-inst-data) &&
	root_disk=$(readlink -f "/sys/class/block/${root_part##*/}/..") &&
	data_disk=$(readlink -f "/sys/class/block/${data_part##*/}/..") || die "install: cannot locate the install partitions"
[ -n "$root_disk" ] && [ "$root_disk" = "$data_disk" ] || die_shown "install: the install data is not on the install stick"
mkdir -p /run/convergent-install &&
	mount -t erofs -o ro,nodev,nosuid,noexec "$data_part" /run/convergent-install ||
	die "install: the install data did not mount"

# /var starts from the image's own, as a first install's does.
mkdir -p /run/cv-image-var &&
	mount --bind "$NEWROOT/var" /run/cv-image-var &&
	mount -t tmpfs -o mode=0755,nodev,nosuid tmpfs "$NEWROOT/var" &&
	cp -a /run/cv-image-var/. "$NEWROOT/var/" &&
	umount /run/cv-image-var && rmdir /run/cv-image-var &&
	mount -t tmpfs -o mode=0755,nodev,nosuid,noexec tmpfs "$NEWROOT/home" &&
	mount -t tmpfs -o mode=1777,nodev,nosuid,noexec,size=8G tmpfs "$NEWROOT/tmp" ||
	die "install: could not mount the writable places"

# Runlevel install only: OpenRC adds boot's services to any runlevel, so boot is emptied (no usbguard
# daemon, auditd, network, Incus, bless or setup). No getty: the installer's terminal is the only login.
boot=/run/convergent-install-boot
mkdir -p "$boot/empty" &&
	{
		printf '# The install image (initramfs): the installer on %s and nothing else.\n' "$console"
		printf '%s\n' 'id:3:initdefault:' 'si::sysinit:/sbin/openrc sysinit' 'rc::bootwait:/sbin/openrc install' \
			'l0u:0:wait:/sbin/telinit u' 'l0:0:wait:/sbin/openrc shutdown' 'l0s:0:wait:/sbin/halt.sh' \
			'l6u:6:wait:/sbin/telinit u' 'l6:6:wait:/sbin/openrc reboot' 'l6r:6:wait:/sbin/reboot -dkn' \
			'ca:12345:ctrlaltdel:/sbin/shutdown -r now'
		printf 'i1:3:respawn:/sbin/agetty -n -l /usr/lib/convergent/installer %s\n' "$line"
	} >"$boot/inittab" && chmod 0644 "$boot/inittab" &&
	[ -d "$NEWROOT/etc/runlevels/install" ] &&
	mount --bind "$boot/inittab" "$NEWROOT/etc/inittab" &&
	mount --bind "$boot/empty" "$NEWROOT/etc/runlevels/boot" ||
	die "install: could not prepare the install runlevel"
