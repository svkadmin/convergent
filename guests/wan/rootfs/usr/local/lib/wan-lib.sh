# Convergent wan: helpers shared by wan-check and wan-portal. Sourced, not run.

# ip2int A.B.C.D: the address as a number.
ip2int() {
	(
		IFS=.
		set -- $1
		echo $(( ($1 << 24) + ($2 << 16) + ($3 << 8) + $4 ))
	)
}

# is_ipv4 STRING: four decimal fields, each 0 to 255.
is_ipv4() {
	case $1 in
	*[!0-9.]* | .* | *. | *..*) return 1 ;;
	esac
	(
		IFS=.
		set -- $1
		[ $# -eq 4 ] || exit 1
		for o in "$@"; do
			case $o in
			0?*) exit 1 ;;
			esac
			[ "${#o}" -le 3 ] && [ "$o" -le 255 ] || exit 1
		done
	)
}

# overlaps_internal ADDR PREFIXLEN: does ADDR/PREFIXLEN share any address with INTERNAL_NET?
overlaps_internal() {
	_a=$(ip2int "$1")
	_b=$(ip2int "${INTERNAL_NET%/*}")
	_l=$2
	[ "$_l" -le "${INTERNAL_NET#*/}" ] || _l=${INTERNAL_NET#*/}
	_m=$(( (0xFFFFFFFF << (32 - _l)) & 0xFFFFFFFF ))
	[ $(( _a & _m )) -eq $(( _b & _m )) ]
}
