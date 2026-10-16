# Caller sets here; bootstrap sets mini, with the image at $mini/target.
. "$here/../alpine.conf"
alpine_mounts=
export PATH=/usr/sbin:/usr/bin:/sbin:/bin   # for commands run in the chroots

alpine_bootstrap() {
	mini=$1
	alpine_tar=$2/$MINIROOTFS
	mkdir -p "$mini" "$2"
	if [ ! -f "$alpine_tar" ]; then
		curl -fsSL --proto '=https' --proto-redir '=https' -o "$alpine_tar.part" \
			"$ALPINE_MIRROR/$ALPINE_BRANCH/releases/x86_64/$MINIROOTFS"
		mv "$alpine_tar.part" "$alpine_tar"
	fi
	printf '%s  %s\n' "$MINIROOTFS_SHA256" "$alpine_tar" | sha256sum -c - >/dev/null ||
		die "$MINIROOTFS does not match its pin"
	tar -xzf "$alpine_tar" -C "$mini"
	alpine_repositories "$mini"
}

alpine_repositories() {
	printf '%s\n' "$ALPINE_MIRROR/$ALPINE_BRANCH/main" "$ALPINE_MIRROR/$ALPINE_BRANCH/community" \
		>"$1/etc/apk/repositories"
}

alpine_mount() {
	mount "$@" || return
	for alpine_last; do :; done
	alpine_mounts="$alpine_last
$alpine_mounts"
}

alpine_prepare() {
	mkdir -p "$mini/target/etc/apk/keys"
	cp "$mini"/etc/apk/keys/* "$mini/target/etc/apk/keys/"
	alpine_repositories "$mini/target"
	: >"$mini/etc/resolv.conf"
	alpine_mount --bind /etc/resolv.conf "$mini/etc/resolv.conf"
	for alpine_path in "$mini" "$mini/target"; do
		mkdir -p "$alpine_path/proc" "$alpine_path/dev" "$alpine_path/sys"
		alpine_mount -t proc proc "$alpine_path/proc"
		alpine_mount --bind /dev "$alpine_path/dev"
	done
	alpine_mount --bind /sys "$mini/target/sys"
}

alpine_apk() { chroot "$mini" /sbin/apk --root /target --no-cache "$@"; }

alpine_cleanup() {
	alpine_failed=
	while IFS= read -r alpine_path; do
		[ -n "$alpine_path" ] || continue
		if ! umount "$alpine_path"; then
			alpine_failed="$alpine_failed$alpine_path
"
		fi
	done <<EOF
$alpine_mounts
EOF
	alpine_mounts=$alpine_failed
	[ -z "$alpine_mounts" ] || { echo "build: mounts remain; work tree left in place" >&2; return 1; }
}
