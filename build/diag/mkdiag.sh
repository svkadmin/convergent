#!/bin/sh
# Wrap the collector so only scrubbed system evidence reaches debug's output file.
set -eu
[ $# = 2 ] || { echo 'usage: mkdiag.sh BODY OUT' >&2; exit 2; }
body=$1 out=$2
d=$(dirname "$0")
{
	cat <<'EOF'
#!/bin/sh
PATH=/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
export LC_ALL=C
umask 077
o=$(mktemp -d /var/lib/convergent/debug/.d.XXXXXX) || exit 1
trap 'rm -rf "$o"' 0
trap 'exit 1' HUP INT TERM
EOF
	for parser in scrub smart bert; do
		printf "cat >\"\$o/%s.awk\" <<'AWK'\n" "$parser"
		cat "$d/$parser.awk"
		echo AWK
	done
	# Shell termination diagnostics can quote the unsanitized collector command.
	echo '{ { ('
	cat "$body"
	cat <<'EOF'
)
printf '%s\n' "$?" >"$o/collector-status"
} 2>&1 | awk -f "$o/scrub.awk" || exit 1
} 2>/dev/null
status=$(cat "$o/collector-status") || exit 1
exit "$status"
EOF
} >"$out"
sh -n "$out"
