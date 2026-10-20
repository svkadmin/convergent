#!/bin/sh
# Shared by the installer and stick preflight.
# Fixed by the release.
esp_mib=1024 slot_mib=8192

install_size() {
	# Whole MiB, with space for GPT and alignment on 512-byte and 4K disks.
	available_mib=$(($1 / 1048576 - esp_mib - slot_mib * 2 - 4))
	case $state_size in
		auto) state_mib=$available_mib; state_end=0 ;;
		*%) state_mib=$((available_mib * ${state_size%\%} / 100)); state_end=+${state_mib}M ;;
		*GiB) state_mib=$((${state_size%GiB} * 1024)); state_end=+${state_mib}M ;;
	esac
	swap_mib=0
	case $swap in state:*) swap_gib=${swap#state:}; swap_mib=$((${swap_gib%GiB} * 1024)) ;; esac
	[ "$state_mib" -ge $(($2 + swap_mib)) ] ||
		die "install.state_size provides $state_mib MiB; need at least $2 MiB for state plus $swap_mib MiB for swap"
	[ "$state_mib" -le "$available_mib" ] ||
		die "install.state_size needs $state_mib MiB; only $available_mib MiB fits after the release ESP and slots"
}

install_target() {
	devices=$(lsblk -dnrpo NAME,TYPE,TRAN,ROTA,RM,HOTPLUG) || die "cannot enumerate target disks"
	candidates=$(printf '%s\n' "$devices" | awk '
		NF == 6 && $2 == "disk" && ($3 == "nvme" || $3 == "sata" || $3 == "ata") &&
			$4 == 0 && $5 == 0 && $6 == 0 {print $1}')
	target= count=0
	for candidate in $candidates; do
		live=
		for bootdisk in $bootdisks; do [ "$candidate" != "$bootdisk" ] || live=1; done
		[ -z "$live" ] || continue
		target=$candidate; count=$((count + 1))
	done
	[ "$count" = 1 ] ||
		die "install.disk auto found $count internal NVMe/SSD disks; set one explicit /dev/disk/by-id path"
	printf '%s\n' "$target"
}
