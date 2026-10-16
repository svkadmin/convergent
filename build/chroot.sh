# Builder chroot mounts; caller sets BUILDER.

chroot_mount() {
	for d in proc sys dev run; do
		mountpoint -q "$BUILDER/$d" && continue
		if [ "$d" = proc ]; then
			mount -t proc proc "$BUILDER/proc"
		else
			mount --rbind "/$d" "$BUILDER/$d"
			mount --make-rslave "$BUILDER/$d"
		fi
	done
}

chroot_umount() {
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
		[ -z "$busy" ] && return 0
	done
	echo "chroot: $BUILDER still has busy mounts" >&2
	return 1
}
