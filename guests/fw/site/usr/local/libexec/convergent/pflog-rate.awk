# OpenBSD -ttt includes a wall-clock timestamp; limit each second to five headers.
{
    second = ""
    for (i = 1; i <= NF; i++)
        if ($i ~ /^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\./) {second = substr($i, 1, 8); break}
    if (second == "") next
    if (second != previous) {
        if (dropped) print "suppressed=" dropped
        previous = second; count = dropped = 0
    }
    if (++count <= 5) print substr($0, 1, 1024)
    else dropped++
    fflush()
}
END {if (dropped) print "suppressed=" dropped}
