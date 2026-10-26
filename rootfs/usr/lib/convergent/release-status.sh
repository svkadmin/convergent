# Sourced by fetch-release while its download lock and update-source access are held.
release_metrics() (
	set -eu
	out=/var/lib/node_exporter
	cache=/var/lib/convergent/release-status
	mkdir -p "$out"
	chmod 755 "$out"
	private "$cache"
	tmp=$(mktemp "$out/.release.XXXXXX")
	trap 'rm -f "$tmp"' 0
	trap 'exit 1' HUP INT TERM
	now=$(date +%s)
	printf 'cv_release_check_timestamp_seconds %s\ncv_release_check_success %s\n' "$now" "$1" >"$tmp"
	printf 'cv_release_info{role="installed",release="%s"} 1\n' "$booted" >>"$tmp"
	if [ "$1" = 1 ]; then
		printf 'cv_release_info{role="latest",release="%s"} 1\n' "$latest" >>"$tmp"
		for role in installed latest; do
			if [ "$role" = installed ]; then release=$booted; else release=$latest; fi
			f=$pointer/advisories.json
			previous=0
			if [ -f "$cache/$release.json" ]; then previous=$(jq -r '.generated' "$cache/$release.json"); fi
			if get --max-time 30 --max-filesize 1048576 -o "$f" "$url/$release/advisories.json" 2>/dev/null &&
				get --max-time 30 --max-filesize 1024 -o "$f.sig" "$url/$release/advisories.json.sig" 2>/dev/null &&
				verify "$f" &&
				jq -ser --arg release "$release" --arg role "$role" --argjson now "$now" --argjson previous "$previous" \
					-f /usr/lib/convergent/release-status.jq "$f" >"$pointer/status.prom" 2>/dev/null; then
				cat "$pointer/status.prom" >>"$tmp"
				cp "$f" "$cache/$release.json.new"
				mv "$cache/$release.json.new" "$cache/$release.json"
			else
				printf 'cv_release_status_verified{role="%s",release="%s"} 0\n' "$role" "$release" >>"$tmp"
			fi
		done
		for f in "$cache"/*.json; do
			case ${f##*/} in "$booted.json"|"$latest.json") ;; *) rm -f "$f" ;; esac
		done
	fi
	chmod 644 "$tmp"
	mv "$tmp" "$out/release.prom"
)
