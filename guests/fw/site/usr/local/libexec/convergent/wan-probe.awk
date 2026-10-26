/packets transmitted/ {
    for (i=1;i<=NF;i++) if ($i ~ /^[0-9.]+%$/ && $(i+1) == "packet") {
        loss=$i; sub(/%$/, "", loss)
        printf "convergent_wan_watch_loss_ratio %.6f\n", loss/100
    }
}
/^(round-trip|rtt)/ {
    split($0, sides, "="); split(sides[2], times, "/")
    if (times[2] ~ /^[0-9.]+$/) printf "convergent_wan_watch_rtt_seconds %.6f\n", times[2]/1000
}
