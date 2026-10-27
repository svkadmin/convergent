# Read-only system probes; mkdiag.sh scrubs output before debug stores or sends it.
c=/etc/convergent/ssh_config
s=/var/lib/convergent/guests
x() {
	echo; printf '### %s\n' "$*"
	# Drain excess output so truncation cannot turn the probe's status into SIGPIPE.
	(timeout -k 2 25 "$@"; printf '%s\n' "$?" >"$o/status") 2>&1 |
		{ head -c 400000; cat >/dev/null; }
	printf '\n(rc=%s)\n' "$(cat "$o/status")"
}
r() { x ssh -F "$c" -o ControlMaster=no -o ControlPath=none -o BatchMode=yes "$@"; }
echo '## system'
x date -u
x uptime
x uname -r
x rc-status
x cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io
x free -m
echo '## hardware (IDs and drivers only)'
x lspci -nnk
x lsusb -t
echo '## USB authorization'
for d in /sys/bus/usb/devices/*; do
	[ -r "$d/authorized" ] || continue
	for f in idVendor idProduct authorized authorized_default bConfigurationValue; do
		[ ! -r "$d/$f" ] || x cat "$d/$f"
	done
done
x rc-service usbguard status
echo '## power policy'
x cat /usr/lib/convergent/cpu-cap-khz
x cat /run/convergent-power.profile
for p in /sys/devices/system/cpu/cpufreq/policy*; do
	[ -d "$p" ] || continue
	for f in affected_cpus scaling_governor energy_performance_preference cpuinfo_max_freq scaling_max_freq; do
		[ ! -r "$p/$f" ] || x cat "$p/$f"
	done
done
for p in /sys/class/power_supply/*; do
	[ -d "$p" ] || continue
	for f in type online status capacity charge_control_start_threshold charge_control_end_threshold charge_types; do
		[ ! -r "$p/$f" ] || x cat "$p/$f"
	done
done
x cat /sys/firmware/acpi/platform_profile
x cat /sys/firmware/acpi/platform_profile_choices
for p in /sys/bus/pci/devices/*; do
	for f in power/control power/runtime_status power/runtime_active_time power/runtime_suspended_time; do
		[ ! -r "$p/$f" ] || x cat "$p/$f"
	done
done
for t in /sys/class/thermal/thermal_zone*; do
	x cat "$t/type"
	x cat "$t/temp"
done
echo '## storage'
x df -h / /var
x btrfs device stats /var
x btrfs filesystem usage -T /var
for d in /sys/class/nvme/nvme[0-9]* /sys/block/sd*; do
	[ -e "$d" ] || continue
	x sh -c 'smartctl -H -A "$1" >"$2/smart" 2>/dev/null; rc=$?
		awk -f "$2/smart.awk" "$2/smart"; exit "$rc"' sh "/dev/${d##*/}" "$o"
done
x cat /var/lib/node_exporter/daily.prom
x dmsetup status
echo '## BERT (private archive; header summary only)'
for f in /var/lib/convergent/crash/bert-*; do
	[ -f "$f" ] || continue
	x sh -c 'od -An -v -tu1 "$1" >"$2/bert" || exit; awk -f "$2/bert.awk" "$2/bert"' sh "$f" "$o"
done
echo '## kernel log (hardware errors and passthrough)'
x sh -c 'dmesg >"$1/kernel" 2>&1; rc=$?; if [ "$rc" != 0 ]; then cat "$1/kernel"; else grep -aiE "bert:|hardware error|vfio|iommu|dmar|btrfs|usb .*(disconnect|reset)|xhci|thunderbolt|watchdog|acpi.*(error|bug)" "$1/kernel" | tail -n 300; fi; exit "$rc"' sh "$o"
echo '## incus'
x incus version
x incus list -c ns -f csv
x incus storage info default
for g in wan fw1 fw2; do x incus console "$g" --show-log; done
echo '## guest updates'
for f in pending preparing committed fw.handoff; do [ ! -e "$s/$f" ] || x cat "$s/$f"; done
x tail -n 80 "$s/updates"
x sh -c 'tail -n 4000 /var/log/messages >"$1/messages" || exit; grep -aE " (guests|check|facts|power|usbguard(-daemon)?)(\[[0-9]+\])?:" "$1/messages"' sh "$o"
echo '## network'
x ip -br link
x ip -br addr
x ip route
x cat /etc/resolv.conf
x getent ahostsv4 codeberg.org
for f in fw1 fw2; do
	for cmd in 'host codeberg.org 127.0.0.1' 'ifconfig carp' 'ifconfig -g carp' 'rcctl check unbound' 'rcctl check wan_watch' 'unbound-control status' 'pfctl -si' 'uptime'; do
		r "$f" "$cmd"
	done
done
r wan check
r wan diag
r wan seed-status
echo '## svc'
x incus exec svc -- df -h /var/lib
x incus exec svc -- wget -qO- http://127.0.0.1:8428/health
x incus exec svc -- wget -qO- http://127.0.0.1:9428/health
