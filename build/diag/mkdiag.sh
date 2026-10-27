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
	echo '('
	cat "$body"
	cat <<'EOF'
) >"$o/raw" 2>&1
status=$?
awk -f "$o/scrub.awk" "$o/raw" >"$o/out" || exit 1
rm -f "$o/raw"
cat "$o/out"
exit "$status"
EOF
} >"$out"
sh -n "$out"
