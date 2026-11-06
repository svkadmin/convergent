# Each file is collapsed to its current declaration per address first (the last one wins, dhcpd.leases(5)).
# Across files a current binding (bound, unexpired at now, "YYYY/MM/DD HH:MM:SS" UTC) beats the rest: a node
# that pinged the client its peer had just bound abandons the address, and every later sync of it is refused.
# Otherwise the latest assignment wins (a released address may have moved on), among equal starts the longest.
# One MAC keeps one address per VLAN subnet (its first three octets): its current binding, else its newest.
BEGIN {if (now == "") {bad=1; exit}}
function merge(   a, live) {
    for (a in cur) {
        live=(cbound[a] && cexpiry[a] > now) ? 1 : 0
        if (!(a in leases) || live > held[a] || (live == held[a] && (cstarts[a] > began[a] || (cstarts[a] == began[a] && cexpiry[a] >= expiry[a])))) {
            began[a]=cstarts[a]; expiry[a]=cexpiry[a]; leases[a]=cur[a]; held[a]=live
            owner[a]=(cbound[a] ? cmac[a] : "")
        }
    }
    split("", cur); split("", cstarts); split("", cexpiry); split("", cbound); split("", cmac)
}
# A record still open at a file's end or at the next declaration is a torn checkpoint, never dropped silently.
FNR == 1 {if (address != "") {bad=1; exit}; merge()}
/^lease [0-9.]+ \{$/ {if (address != "") {bad=1; exit}; address=$2; record=$0 "\n"; starts=""; expires=""; mac=""; bound=1; next}
address != "" {
    record=record $0 "\n"
    # A lease record is a few hundred bytes; never accumulate an unterminated one.
    if (length(record) > 4096) {bad=1; exit}
    if ($1 == "starts") starts=$3 " " $4
    if ($1 == "ends") expires=$3 " " $4
    if ($1 == "hardware" && $2 == "ethernet") {mac=$3; sub(/;$/, "", mac)}
    if ($1 == "abandoned;") bound=0
    if ($0 ~ /^}/) {
        if (expires == "") {bad=1; exit}
        if (mac == "") bound=0
        cur[address]=record; cstarts[address]=starts; cexpiry[address]=expires; cbound[address]=bound; cmac[address]=mac
        address=""
    }
}
END {
    if (bad || address != "") exit 1
    merge()
    for (address in leases) {
        if (owner[address] == "") continue
        key=address; sub(/\.[0-9]+$/, "", key); key=owner[address] " " key
        # Its current binding first: an expired later address must not erase a live reservation.
        if (!(key in newest) || held[address] > held[newest[key]] || (held[address] == held[newest[key]] && (began[address] > began[newest[key]] || (began[address] == began[newest[key]] && (expiry[address] > expiry[newest[key]] || (expiry[address] == expiry[newest[key]] && address > newest[key])))))) newest[key]=address
    }
    for (address in leases) {
        if (owner[address] != "") {key=address; sub(/\.[0-9]+$/, "", key); key=owner[address] " " key}
        if (owner[address] == "" || newest[key] == address) printf "%s", leases[address]
    }
}
