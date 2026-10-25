dev=/dev/disk/by-partlabel/cv-state
state=/run/cv-state
udevadm settle
# The passphrase prompt only after the display driver took the screen (i915 on the laptop; none in QEMU).
i=0
while [ ! -e /dev/dri/card0 ] && [ $i -lt 20 ]; do sleep 0.25; i=$((i + 1)); done
[ -b "$dev" ] || die "state: no partition labelled cv-state"
# A second Convergent disk would make every label ambiguous.
[ "$(blkid -o device -t PARTLABEL=cv-state | wc -l)" = 1 ] ||
	die "state: more than one disk has a cv-state partition; detach the other"

# Three passphrase attempts; failure powers off.
# rd.debug traces every command; no trace may hold the passphrase.
{ set +x; } 2>/dev/null
tries=0
while :; do
	[ "$tries" -lt 3 ] || die "state: the state volume did not open"
	tries=$((tries + 1))
	stty -echo </dev/console 2>/dev/null
	printf 'Passphrase [%s/3]: ' "$tries" >/dev/console
	IFS= read -r pass </dev/console || pass=''
	stty echo </dev/console 2>/dev/null
	echo >/dev/console
	printf '%s' "$pass" | cryptsetup open --type luks2 --key-file - "$dev" cv-state && break
done

