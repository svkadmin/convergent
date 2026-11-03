# Builder chroot mounts (caller sets BUILDER), shared by builds and tests.
# Each caller registers its PID and start time, since a reused PID is not a user;
# the last to leave tears the mounts down.
chroot_users=/run/convergent-builder.users
# Portage inputs outlive a rebuilt builder, since upstream prunes them; Portage checks each against its Manifest.
chroot_distfiles=/var/cache/convergent/distfiles
chroot_started() { sed 's/.*) //' "/proc/$1/stat" 2>/dev/null | cut -d' ' -f20; }

qemu_identity() {
	(
		flock 8
		id convergent-qemu >/dev/null 2>&1 ||
			useradd -r -U -M -d /nonexistent -s /sbin/nologin convergent-qemu
	) 8>/run/convergent-qemu.lock
	qemu_uid=$(id -u convergent-qemu)
	qemu_gid=$(stat -c %g /dev/kvm)
	[ "$qemu_uid" != 0 ] && [ "$qemu_gid" != 0 ] || die 'QEMU needs a non-root UID and KVM group'
	qemu_id=$qemu_uid:$qemu_gid
}

chroot_mount() {
	(
		flock 8
		for d in proc sys dev run; do
			mountpoint -q "$BUILDER/$d" && continue
			if [ "$d" = proc ]; then
				mount -t proc proc "$BUILDER/proc"
			else
				mount --rbind "/$d" "$BUILDER/$d"
				mount --make-rslave "$BUILDER/$d"
			fi
		done
		if ! mountpoint -q "$BUILDER/var/cache/distfiles"; then
			if [ ! -d "$chroot_distfiles" ]; then
				# Seeded once by moving the builder's own copy (2.6 GB on the build host); Manifests catch a cut one.
				mkdir -p "$BUILDER/var/cache/distfiles" "${chroot_distfiles%/*}"
				mv -T "$BUILDER/var/cache/distfiles" "$chroot_distfiles"
			fi
			mkdir -p "$BUILDER/var/cache/distfiles"
			mount --bind "$chroot_distfiles" "$BUILDER/var/cache/distfiles"
		fi
		mkdir -p "$chroot_users" && chroot_started $$ >"$chroot_users/$$"
	) 8>/run/convergent-builder.lock
}

chroot_umount() {
	(
		flock 8
		rm -f "$chroot_users/$$"
		for u in "$chroot_users"/*; do
			[ -e "$u" ] || continue
			if [ "$(chroot_started "${u##*/}")" = "$(cat "$u")" ]; then exit 0; fi
			rm -f "$u"
		done
		# Nothing rooted in the builder may outlive it (gpg-agent, keyboxd, dirmngr).
		chroot "$BUILDER" gpgconf --kill all 2>/dev/null || true
		for try in 1 2 3; do
			for p in $(pgrep .); do
				[ "$(readlink "/proc/$p/root" 2>/dev/null)" = "$BUILDER" ] && kill "$p" 2>/dev/null
			done
			sleep 1
			busy=
			for d in var/cache/distfiles run dev sys proc; do
				mountpoint -q "$BUILDER/$d" && { umount -R "$BUILDER/$d" 2>/dev/null || busy=1; }
			done
			[ -z "$busy" ] && exit 0
		done
		echo "chroot: $BUILDER still has busy mounts" >&2
		exit 1
	) 8>/run/convergent-builder.lock
}
