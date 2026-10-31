#!/bin/sh
# Shared signed downloads and temporary firewall access; caller traps close_src.
ssh_conf=/etc/convergent/ssh_config
key=/etc/convergent/release.pub
fws="fw2 fw1"
src_open=

# Shared SSH connections must not inherit locks.
rsh() { _h=$1; shift; timeout 120 ssh -F "$ssh_conf" -n "$_h" "$@" 9>&- 8>&- 7>&-; }
lock_src() {
	mkdir -p /run/convergent
	exec 9>/run/convergent/fetch-release.lock
	flock -n 9 || die "another download is running"
}
close_src() {
	_r=0
	for _f in $fws; do
		rsh "$_f" 'rc=0; pfctl -t update_src -T flush || rc=1; pfctl -k label -k update || rc=1; exit "$rc"' >/dev/null || _r=1
	done
	[ "$_r" = 1 ] || src_open=
	return "$_r"
}
# As in dns-push: an address pf.conf does not count as nonpublic.
public_v4() {
	case $1 in
	'' | *[!0-9.]* | *..* | .* | *.) return 1 ;;
	0.* | 10.* | 127.* | 169.254.* | 192.168.* | 198.18.* | 198.19.* | 192.0.0.* | 192.0.2.* | \
	198.51.100.* | 203.0.113.* | 22[4-9].* | 2[3-5][0-9].* | 172.1[6-9].* | 172.2[0-9].* | 172.3[01].* | \
	100.6[4-9].* | 100.[7-9][0-9].* | 100.1[01][0-9].* | 100.12[0-7].*) return 1 ;;
	esac
	case $(printf '%s\n' "$1" | tr -cd . | wc -c) in 3) ;; *) return 1 ;; esac
}
update_url() {
	url=${UPDATE_URL:-}
	case $url in https://[A-Za-z0-9]*) ;; *) die "UPDATE_URL must start with https://" ;; esac
	case $url in *[!A-Za-z0-9._~:/-]*) die "UPDATE_URL has characters that are not allowed" ;; esac
	host=${url#https://}
	host=${host%%/*}
	case $host in '' | *[!A-Za-z0-9.-]*) die "UPDATE_URL must name a host, without port or user" ;; esac
}
open_src() {
	host=$1
	ips=
	for _a in $(getent ahostsv4 "$host" | awk '$2 == "STREAM" { print $1 }' | sort -u | head -n 8); do
		if public_v4 "$_a"; then ips="$ips $_a"; fi
	done
	[ -n "$ips" ] || die "$host resolves to no public address (no Wi-Fi, or the blocklist: run sys dns allow $host)"
	src_open=1
	for _f in $fws; do
		rsh "$_f" "pfctl -q -t update_src -T replace$ips" >/dev/null || die "could not open the update source on $_f"
	done
	res=$(echo $ips | tr ' ' ',')
}
get() {
	curl -q --silent --show-error --fail --noproxy '*' --proto =https --proto-redir =https --tlsv1.2 \
		--connect-timeout 15 --resolve "$host:443:$res" "$@"
}
verify() { openssl pkeyutl -verify -pubin -inkey "$key" -rawin -in "$1" -sigfile "$1.sig" >/dev/null 2>&1; }
private() {
	[ ! -L "$1" ] || die "$1 is a symlink"
	[ -d "$1" ] || mkdir -m 0700 "$1"
	[ "$(stat -c '%u %a %F' "$1")" = "0 700 directory" ] || die "$1 is not root's private directory"
}
