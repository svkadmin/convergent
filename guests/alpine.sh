# Caller sets here; bootstrap sets mini, with the image at $mini/target.
. "$here/../alpine.conf"
alpine_mounts=
export PATH=/usr/sbin:/usr/bin:/sbin:/bin   # for commands run in the chroots
# Network failures only: curl retries DNS, refused connections, timeouts and HTTP 408/429/500/502/503/504; callers verify pins.
alpine_curl() { curl --retry 2 --retry-delay 5 --retry-connrefused "$@"; }
# Three tries while apk names a network cause (apk 3 messages); any signature or integrity error stops at once.
alpine_net='^(WARNING|ERROR): .*: (DNS: |DNS lookup error|network error|could not connect to server|temporary error|network connection aborted|Connection (refused|reset by peer|aborted)|Operation timed out|(Network|Host) is (down|unreachable)|Network unreachable|HTTP 5[0-9][0-9]|unexpected end of file)'
alpine_retry() {
	alpine_try=1
	while :; do
		alpine_rc=0
		"$@" 2>"$mini/apk.err" || alpine_rc=$?
		cat "$mini/apk.err" >&2
		[ "$alpine_rc" != 0 ] && [ "$alpine_try" -lt 3 ] && grep -Eq "$alpine_net" "$mini/apk.err" &&
			! grep -Eiq 'signature|integrity|checksum|format|crypto|untrusted' "$mini/apk.err" || return "$alpine_rc"
		echo "alpine: network failure; try $((alpine_try + 1)) of 3 in $((alpine_try * 5)) s" >&2
		sleep $((alpine_try * 5))
		alpine_try=$((alpine_try + 1))
	done
}

alpine_bootstrap() {
	mini=$1
	alpine_tar=$2/$MINIROOTFS
	mkdir -p "$mini" "$2"
	if [ -f "$alpine_tar" ]; then
		if ! printf '%s  %s\n' "$MINIROOTFS_SHA256" "$alpine_tar" | sha256sum -c - >/dev/null; then
			rm -f "$alpine_tar"
			die "$MINIROOTFS does not match its pin"
		fi
	else
		alpine_part=$(mktemp "$alpine_tar.part.XXXXXX")
		if ! alpine_curl -fsSL --proto '=https' --proto-redir '=https' -o "$alpine_part" \
			"$ALPINE_MIRROR/$ALPINE_BRANCH/releases/x86_64/$MINIROOTFS"; then
			rm -f "$alpine_part"
			die "$MINIROOTFS download failed"
		fi
		if ! printf '%s  %s\n' "$MINIROOTFS_SHA256" "$alpine_part" | sha256sum -c - >/dev/null; then
			rm -f "$alpine_part"
			die "$MINIROOTFS does not match its pin"
		fi
		mv "$alpine_part" "$alpine_tar"
	fi
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

alpine_apk() { alpine_retry chroot "$mini" /sbin/apk --root /target --no-cache "$@"; }

# Pinned edge build $1 (repository $2, version $3, sha256 $4) into $mini/apks; apk checks its signature
# on install. Edge keeps only its newest build, so a verified copy stays in cache $5.
alpine_edge() {
	alpine_apk_file=$mini/apks/$1-$3.apk
	alpine_cached=$5/$1-$3.apk
	if [ -f "$alpine_cached" ]; then
		cp "$alpine_cached" "$alpine_apk_file"
		[ "$(sha256sum <"$alpine_apk_file" | cut -d' ' -f1)" != "$4" ] || return 0
		rm -f "$alpine_cached" "$alpine_apk_file"
		echo "alpine: cached $1 $3 does not match its pin; removed" >&2
	fi
	# Fetch by name; a version constraint makes apk resolve dependencies edge alone lacks.
	alpine_retry chroot "$mini" /sbin/apk --repositories-file /dev/null --repository "$ALPINE_MIRROR/edge/$2" \
		--no-cache fetch --output /apks "$1" || die "cannot fetch $1 from edge"
	[ -f "$alpine_apk_file" ] || die "$1 $3 is no longer on edge; update its pin"
	[ "$(sha256sum <"$alpine_apk_file" | cut -d' ' -f1)" = "$4" ] || die "$1 $3 does not match its pinned sha256"
	mkdir -p "$5"
	alpine_part=$(mktemp "$alpine_cached.part.XXXXXX")
	cp "$alpine_apk_file" "$alpine_part" || { rm -f "$alpine_part"; die "cannot cache $1 $3"; }
	mv "$alpine_part" "$alpine_cached"
}

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
