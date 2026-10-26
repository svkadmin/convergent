NR == 1 {for (i=1;i<=NF;i++) {if ($i == "Ibytes") rx=i; if ($i == "Obytes") tx=i}; next}
{
    name=$1; sub(/\*$/, "", name)
    if (rx && tx && name ~ /^(vio|vlan)[0-9]+$/ && !seen[name]++ &&
        $rx ~ /^[0-9]+$/ && $tx ~ /^[0-9]+$/) {
        printf "convergent_interface_receive_bytes_total{carpdev=\"%s\"} %s\n", name, $rx
        printf "convergent_interface_transmit_bytes_total{carpdev=\"%s\"} %s\n", name, $tx
    }
}
