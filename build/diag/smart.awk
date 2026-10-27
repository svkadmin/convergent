# Select health values only; never print SMART identity or error-log payloads.
/^SMART overall-health self-assessment test result: (PASSED|FAILED!)/ {print; next}
/^SMART Health Status: (OK|BAD)/ {print; next}
/^(Critical Warning|Temperature|Available Spare|Available Spare Threshold|Percentage Used|Data Units Read|Data Units Written|Host Read Commands|Host Write Commands|Controller Busy Time|Power Cycles|Power On Hours|Unsafe Shutdowns|Media and Data Integrity Errors|Error Information Log Entries|Warning  *Comp\. Temperature Time|Critical Comp\. Temperature Time|Temperature Sensor [0-9]+):/ {
	value=$0; sub(/^[^:]*:[ \t]*/, "", value)
	if (value ~ /^(0x[0-9a-fA-F]+|[0-9][0-9,]*)(%| Celsius| minutes| hours)?( \[.*\])?$/) {
		sub(/ \[.*\]$/, "", $0); print
	}
}
$1 ~ /^[0-9]+$/ && $2 ~ /^(Reallocated_Sector_Ct|Reported_Uncorrect|Current_Pending_Sector|Offline_Uncorrectable|UDMA_CRC_Error_Count|Temperature_Celsius|Power_On_Hours)$/ && $10 ~ /^[0-9]+$/ {
	print $2 ": " $10
}
