# First input is the trusted registry; remaining input is ifconfig, never the expectation.
FNR == NR {
	if ($0 ~ /^#/ || NF == 0) next
	if (NF != 7 || $1 !~ /^carp[0-9]+$/ || $2 !~ /^[1-9][0-9]*$/ || $2 > 255 || $3 !~ /^(vio|vlan)[0-9]+$/ || $4 !~ /^[a-z][a-z0-9-]*$/ || $5 !~ /^[0-9.]+\/[0-9]+$/ || $6 !~ /^[0-9.]+$/ || $7 !~ /^(system|dev|jhn)$/ || ($1 in vhid) || ids[$2]++ || parents[$3]++ || labels[$4]++) {bad=1; next}
	order[++expected]=$1; vhid[$1]=$2; parent[$1]=$3; label[$1]=$4
	net[$1]=$5; gateway[$1]=$6; family[$1]=$7
	next
}
/^[a-z][a-z0-9]*:/ {
	iface=$1; sub(/:$/, "", iface)
	if (iface ~ /^carp[0-9]+$/ && (!(iface in vhid) || seen[iface]++)) bad=1
}
/^[ \t]+carp: / {
	if (!(iface in vhid) || states[iface]++) bad=1
	v=p=""
	for (i=3;i<NF;i++) {if ($i == "vhid") v=$(i+1); if ($i == "carpdev") p=$(i+1); if ($i == "advskew") skew[iface]=$(i+1)}
	if (v != vhid[iface] || p != parent[iface]) bad=1
	role[iface]=$2
	if ($2 != "MASTER" && $2 != "BACKUP" && !(mode == "metrics" && $2 == "INIT")) bad=1
	if (want != "" && $2 != want) bad=1
	if (first == "") first=$2
	if ($2 != first && mode != "metrics" && mode != "status") bad=1
}
/^Status: Enabled/ {pf=1}
/^pfsync0:.*RUNNING/ {sync=1}
/defer: on/ {defer=1}
END {
	if (!expected) bad=1
	if (mode != "registry" && mode != "interfaces" && mode != "count") {
		for (iface in vhid) if (seen[iface] != 1 || states[iface] != 1) bad=1
		if (health && (!pf || !sync || !defer)) bad=1
	}
	if (bad) exit 1
	if (mode == "count") print expected
	else if (mode == "interfaces") for (j=1;j<=expected;j++) print order[j]
	else if (mode == "status" || mode == "metrics") {
		for (j=1;j<=expected;j++) {
			iface=order[j]
			if (mode == "status") print "  " label[iface] ": " role[iface]
			else {
				printf "convergent_carp_state{interface=\"%s\",carpdev=\"%s\",vhid=\"%s\",segment=\"%s\"} %d\n", iface,parent[iface],vhid[iface],label[iface],(role[iface] == "MASTER" ? 2 : (role[iface] == "BACKUP" ? 1 : 0))
				printf "convergent_carp_advskew{interface=\"%s\",segment=\"%s\"} %d\n",iface,label[iface],skew[iface]
			}
		}
	} else if (mode != "registry") print tolower(first)
}
