$1 == "signal:" && $2 ~ /^-?[0-9]+([.][0-9]+)?$/ {print "convergent_wifi_signal_dbm " $2}
($1 == "tx" || $1 == "rx") && $2 == "bitrate:" && $3 ~ /^[0-9]+([.][0-9]+)?$/ && $4 == "MBit/s" {
    printf "convergent_wifi_bitrate_bits_per_second{direction=\"%s\"} %.0f\n", $1, $3*1000000
}
