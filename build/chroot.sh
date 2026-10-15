# chroot.sh: mount and unmount what the builder chroot needs. Sourced by the build scripts,
# which set BUILDER (build.conf).

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
	# gpg-agent, started by Portage's key helper, would keep /dev busy.
	chroot "$BUILDER" gpgconf --kill all 2>/dev/null || true
	# Any agent left running inside the builder (its root is the builder), and no other.
	for p in $(pgrep -x gpg-agent); do
		[ "$(readlink "/proc/$p/root")" = "$BUILDER" ] && kill "$p"
	done
	for d in run dev sys proc; do
		mountpoint -q "$BUILDER/$d" && umount -R "$BUILDER/$d"
	done
	return 0
}
