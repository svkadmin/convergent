# Builder chroot mounts; caller sets BUILDER. Several builds and tests may share them: each
# caller registers its PID with its start time (a reused PID is not a user), and only the last
# one leaving tears the mounts down.
chroot_users=/run/convergent-builder.users
chroot_started() { sed 's/.*) //' "/proc/$1/stat" 2>/dev/null | cut -d' ' -f20; }

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
			for d in run dev sys proc; do
				mountpoint -q "$BUILDER/$d" && { umount -R "$BUILDER/$d" 2>/dev/null || busy=1; }
			done
			[ -z "$busy" ] && exit 0
		done
		echo "chroot: $BUILDER still has busy mounts" >&2
		exit 1
	) 8>/run/convergent-builder.lock
}
