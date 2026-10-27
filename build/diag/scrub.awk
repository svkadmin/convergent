# Keep system facts; suppress personal log fields before output is stored or sent.
function mask(s,    out, m, parts, count, i, valid) {
	if (s ~ /\/(home|root|media|mnt)\// || tolower(s) ~ /ssid|network name|connect(ed|ing) to|command=|user(name)?=/) return "<personal line>"
	gsub(/(name|serial|hash|parent-hash) "[^"]*"/, "<identity>", s)
	gsub(/[Ss]erial([ _]?[Nn]umber)?[ :=]+[^ ,;]+/, "SerialNumber: <serial>", s)
	out = ""
	while (match(s, /[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]/)) {
		out = out substr(s, 1, RSTART - 1) "<mac>"
		s = substr(s, RSTART + RLENGTH)
	}
	s = out s; out = ""
	while (match(s, /[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/)) {
		m = substr(s, RSTART, RLENGTH)
		out = out substr(s, 1, RSTART - 1) (keep4(m) ? m : "<ip>")
		s = substr(s, RSTART + RLENGTH)
	}
	s = out s; out = ""
	# A PCI vendor:device pair has one colon, a BDF two; neither is IPv6.
	while (match(s, /[0-9a-fA-F:]*:[0-9a-fA-F:]+/)) {
		m = substr(s, RSTART, RLENGTH)
		count = split(m, parts, ":"); valid = (index(m, "::") || count == 8)
		for (i=1; i<=count; i++) if (length(parts[i]) > 4) valid=0
		out = out substr(s, 1, RSTART - 1) (valid && m != "::1" ? "<ip6>" : m)
		s = substr(s, RSTART + RLENGTH)
	}
	return out s
}
function keep4(a) {return a ~ /^100\.80\./ || a ~ /^127\./ || a == "0.0.0.0" || a ~ /^255\./}
{print mask($0)}
