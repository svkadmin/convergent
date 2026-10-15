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
	# Stop Portage's gpg-agent before unmounting /dev.
	chroot "$BUILDER" gpgconf --kill all 2>/dev/null || true
	# Kill only agents rooted in this builder.
	for p in $(pgrep -x gpg-agent); do
		[ "$(readlink "/proc/$p/root")" = "$BUILDER" ] && kill "$p"
	done
	for d in run dev sys proc; do
		mountpoint -q "$BUILDER/$d" && umount -R "$BUILDER/$d"
	done
	return 0
}
