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

# The installer's answers: each check says why it refuses, and the installer asks again.
owner_valid() {   # name, the accounts' etc
	case $1 in '' | [!a-z_]* | *[!a-z0-9_-]*) echo 'Use a lowercase login name: a-z or _, then a-z, 0-9, _ or -.'; return 1 ;; esac
	[ "${#1}" -le 32 ] || { echo 'Use at most 32 characters.'; return 1; }
	for f in passwd shadow group gshadow subuid subgid; do
		rc=0; grep -q "^$1:" "$2/$f" || rc=$?
		case $rc in
		0) echo "$1 is an account of the system; choose another name."; return 1 ;;
		1) ;;
		*) echo "cannot read the image's $f"; return 1 ;;
		esac
	done
}
secret_valid() {
	case $1 in *"$(printf '\r')"*) echo 'It has a carriage return (a Windows line ending).'; return 1 ;; esac
	[ "${#1}" -ge 12 ] || { echo 'Use at least 12 bytes.'; return 1; }
	[ "${#1}" -le 256 ] || { echo 'Use at most 256 bytes.'; return 1; }
}
luks_valid() {   # passphrase, the password's file
	secret_valid "$1" || return 1
	case $1 in *[!\ -~]*) echo 'Use only printable ASCII for the LUKS passphrase (space through ~).'; return 1 ;; esac
	rc=0; printf '%s' "$1" | cmp -s - "$2" || rc=$?
	case $rc in
	0) echo 'Use a LUKS passphrase that is not the password.'; return 1 ;;
	1) ;;
	*) echo 'cannot compare with the password'; return 1 ;;
	esac
}
# Sway keeps us on an unknown layout or variant; check as sys keyboard does (build/image has the same).
xkb_known() {
	for pair in $(printf '%s' "$1" | tr , ' '); do
		layout=${pair%%(*} variant=
		case $pair in *'('*) variant=${pair#*(}; variant=${variant%)} ;; esac
		awk -v code="$layout" -v variant="$variant" '
			$1 == "!" {section=$2}
			section == "layout" && $1 == code {layout=1}
			section == "variant" && $1 == variant && $2 == code ":" {found=1}
			END {exit !(layout && (variant == "" || found))}
		' "$2" || return
	done
}
layouts_valid() {   # layouts, evdev.lst
	printf '%s\n' "$1" | awk -F, 'NR != 1 {exit 1} {
		for (i=1;i<=NF;i++) if ($i !~ /^[a-z]{2,5}(\([A-Za-z0-9_-]+\))?$/) exit 1
		if (!NF) exit 1
	}' && xkb_known "$1" "$2" || { echo "Not a list of installed layouts, such as us,sk(qwerty),ru: $1"; return 1; }
}
# The same rule as tools/timezone: a zone name under zoneinfo, never posix/ or right/, and a TZif file.
zone_valid() {
	printf '%s\n' "$1" | LC_ALL=C awk '{n++} n == 1 && /^[A-Za-z0-9_+-]+(\/[A-Za-z0-9_+-]+)*$/ && !/^(posix|right)\// && !/^(localtime|posixrules|Factory)$/ {ok = 1}
		END {exit !(ok && n == 1)}' &&
		[ ! -L "$2/$1" ] && [ -f "$2/$1" ] && LC_ALL=C awk '{ok = substr($0, 1, 4) == "TZif"; exit} END {exit !ok}' "$2/$1"
}
# wan-wifi's rules; what wan's carry-over check (tools/guests wan_profile_valid) reads back.
ssid_valid() {
	[ -n "$1" ] || { echo 'Enter the network name.'; return 1; }
	case $1 in -*) echo 'The name must not start with -.'; return 1 ;; esac
	[ "${#1}" -le 32 ] || { echo 'Use at most 32 bytes.'; return 1; }
	case $1 in *[[:cntrl:]]*) echo 'The name has control characters.'; return 1 ;; esac
}
wifi_pass_valid() {   # empty: an open network; 2: valid for wan-wifi, but not storable here
	[ -n "$1" ] || return 0
	[ "${#1}" -ge 8 ] && [ "${#1}" -le 63 ] || { echo 'Use 8 to 63 characters, or none for an open network.'; return 1; }
	case $1 in *[!\ -~]*) echo 'Use printable ASCII (space through ~).'; return 1 ;; esac
	case $1 in *\\* | ' '* | *' ')
		echo 'A backslash or a space at either end cannot be stored here; join this network with sys wifi after installing.'
		return 2 ;;
	esac
}
iwd_name() {   # ssid, type: the SSID itself when iwd keeps it as the file name, else = and its hex
	case $1 in
	*[!A-Za-z0-9_\ -]*) printf '=%s.%s\n' "$(printf '%s' "$1" | od -An -tx1 -v | tr -d ' \n')" "$2" ;;
	*) printf '%s.%s\n' "$1" "$2" ;;
	esac
}
iwd_profile() {   # hidden (y or n), passphrase
	if [ -n "$2" ]; then printf '[Security]\nPassphrase=%s\n' "$2"; fi
	if [ "$1" = y ]; then printf '[Settings]\nHidden=true\n'; fi
}
# The erase confirmation: the disk as typed, or ERASE and a serial no other disk has.
erase_ok() {   # answer, typed path, serial, disks with that serial
	[ "$1" = "$2" ] && return 0
	[ -n "$3" ] && [ "$4" = 1 ] && [ "$1" = "ERASE $3" ]
}
