# Preserve the longest reservation from either allocator, including an earlier checkpoint.
/^lease [0-9.]+ \{$/ {address=$2; record=$0 "\n"; expires=""; next}
address != "" {
    record=record $0 "\n"
    if ($1 == "ends") expires=$3 " " $4
    if ($0 ~ /^}/) {
        if (expires == "") {bad=1; exit}
        if (!(address in expiry) || expires >= expiry[address]) {
            expiry[address]=expires; leases[address]=record
        }
        address=""
    }
}
END {
    if (bad || address != "") exit 1
    for (address in leases) printf "%s", leases[address]
}
