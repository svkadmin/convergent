# The latest assignment wins (a released address may have moved on); among equal starts, the longest reservation.
# A bound record beats an abandoned one: a node that pinged the client its peer had just bound abandons the
# address, and every later sync of it is refused. One MAC keeps one address, its newest bound record.
/^lease [0-9.]+ \{$/ {address=$2; record=$0 "\n"; starts=""; expires=""; mac=""; bound=1; next}
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
        if (!(address in expiry) || bound > held[address] || (bound == held[address] && (starts > began[address] || (starts == began[address] && expires >= expiry[address])))) {
            began[address]=starts; expiry[address]=expires; leases[address]=record; held[address]=bound
            owner[address]=(bound ? mac : "")
        }
        address=""
    }
}
END {
    if (bad || address != "") exit 1
    for (address in leases) {
        mac=owner[address]
        if (mac == "") continue
        if (!(mac in newest) || began[address] > began[newest[mac]] || (began[address] == began[newest[mac]] && (expiry[address] > expiry[newest[mac]] || (expiry[address] == expiry[newest[mac]] && address > newest[mac])))) newest[mac]=address
    }
    for (address in leases) if (owner[address] == "" || newest[owner[address]] == address) printf "%s", leases[address]
}
