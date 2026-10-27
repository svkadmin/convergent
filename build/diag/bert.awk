# Generic Error Status Block headers only; CPER payloads may contain serials or memory addresses.
function u32(p) {return b[p]+256*b[p+1]+65536*b[p+2]+16777216*b[p+3]}
{for (i=1;i<=NF;i++) b[n++]=$i}
END {
	printf "BERT bytes=%d\n", n
	p=0; records=0
	while (p+20<=n) {
		status=u32(p); offset=u32(p+4); raw=u32(p+8); data=u32(p+12); severity=u32(p+16)
		size=20+data; if (raw && offset+raw>size) size=offset+raw
		if (!status && !raw && !data) break
		if (size>n-p || (raw && offset<20+data) || severity>3) {print "BERT invalid/truncated header"; exit 1}
		records++
		printf "BERT record=%d severity=%s data_bytes=%d raw_bytes=%d\n", records, (severity==0?"recoverable":severity==1?"fatal":severity==2?"corrected":"none"), data, raw
		p+=size
	}
	if (n<20) {print "BERT truncated header"; exit 1}
	printf "BERT records=%d\n", records
}
