# The latest assignment wins (a released address may have moved on); among equal starts, the longest reservation.
/^lease [0-9.]+ \{$/ {address=$2; record=$0 "\n"; starts=""; expires=""; next}
address != "" {
    record=record $0 "\n"
    # A lease record is a few hundred bytes; never accumulate an unterminated one.
    if (length(record) > 4096) {bad=1; exit}
    if ($1 == "starts") starts=$3 " " $4
    if ($1 == "ends") expires=$3 " " $4
    if ($0 ~ /^}/) {
        if (expires == "") {bad=1; exit}
        if (!(address in expiry) || starts > began[address] || (starts == began[address] && expires >= expiry[address])) {
            began[address]=starts; expiry[address]=expires; leases[address]=record
        }
        address=""
    }
}
END {
    if (bad || address != "") exit 1
    for (address in leases) printf "%s", leases[address]
}
