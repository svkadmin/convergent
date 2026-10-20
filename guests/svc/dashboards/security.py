"""Boot evidence, checker, trust, hardware health and security lines."""
from dashlib import (
    AMBER, BAD, GREEN, NEUTRAL, OK, RED, SCREEN_ROWS, SECURITY_EVENTS, Page,
    grid, ov, target, thresholds, vmap)


def generate():
    p = Page()
    p.stat("", [target('max(cv_secure_boot_verified)', "Secure Boot"),
                target('max(cv_lockdown_enabled)', "confidentiality lockdown"),
                target('max(cv_luks_header_matches_release)', "LUKS header")],
           grid(0, 0, 14, 2), "Source: tools/facts boot: EFI SecureBoot=1 and SetupMode=0, kernel confidentiality lockdown, LUKS header against the accepted hash. These are boot-time facts, not continuous verification of the UKI or verity.",
           overrides=[ov("Secure Boot", mappings=vmap([(0, "UNVERIFIED", RED), (1, "VERIFIED", GREEN)])),
                      ov("confidentiality lockdown", mappings=vmap([(0, "OFF", RED), (1, "ENFORCING", GREEN)])),
                      ov("LUKS header", mappings=vmap([(0, "CHANGED", RED), (1, "MATCHES", GREEN)]))])
    p.stat("", [target('max(cv_checker_success)', "checker"),
                target('time() - max(cv_checker_last_run_seconds)', "checker age"),
                target('max(cv_crash_records)', "archived crashes")],
           grid(14, 0, 10, 2), "Source: tools/check last result and timestamp; tools/facts boot archived pstore record count. Checker must first have a trusted baseline accepted.",
           overrides=[ov("checker", mappings=OK), ov("checker age", unit="s", thresholds=thresholds(("text", None), (AMBER, 172800))),
                      ov("archived crashes", thresholds=BAD)])
    p.table("Collectors · now", [target('max by (collector) (cv_collector_success)')],
            grid(0, 2, 8, 6), ["collector"], ["result"],
            "Source: tools/facts boot, daily, NTS and audit collector success. One instant row per collector; a failed daily collector can still publish readable certificate figures. Checker is separate in the band above.", [ov("result", mappings=OK)])
    p.table("Certificates · time remaining", [target('min by (certificate) (cv_certificate_not_after_seconds - time())')],
            grid(8, 2, 8, 6), ["certificate"], ["remaining"],
            "Source: tools/facts daily openssl x509 enddate. Only the Incus server certificate is collected; syslog and client certificates are outside this inventory.",
            [ov("remaining", unit="s", thresholds=thresholds((RED, None), (AMBER, 1209600), ("text", 2592000)))])
    p.stat("Time and audit", [target('max(cv_nts_authenticated_sources)', "NTS agreeing authenticated"),
                              target('max(cv_audit_lost_total)', "audit records lost"),
                              target('max(node_sysctl_kernel_tainted{node="host"})', "kernel taint")],
           grid(16, 2, 8, 6), "Source: tools/facts nts (every minute) chronyc sources/authdata and hourly auditctl lost; host node_exporter configured sysctl collector kernel.tainted. Taint is a bitmask, not a verdict about compromise.",
           overrides=[ov("NTS agreeing authenticated", thresholds=thresholds((RED, None), ("text", 2))),
                      ov("audit records lost", thresholds=BAD),
                      ov("kernel taint", mappings=vmap([(0, "CLEAN", NEUTRAL)]), thresholds=BAD)])
    p.timeseries("Clock · absolute offset", [target('abs(node_timex_offset_seconds{node=~"host|wan"})', "{{node}}")],
                 grid(0, 8, 8, 6), "s", "Source: host and wan node_exporter timex. Absolute kernel clock offset; amber in alert rules above 0.1 seconds. OpenBSD does not expose this collector.")
    p.timeseries("Audit · lost records", [target('cv_audit_lost_total', "lost this boot")],
                 grid(8, 8, 8, 6), "short", "Source: tools/facts hourly auditctl -s lost counter. Any lost record needs attention; this is not a count of audited commands.")
    p.table("NVMe · health", [target('max by (device) (cv_nvme_spare_percent)', optional="No NVMe hardware in QEMU."),
                                   target('max by (device) (cv_nvme_spare_threshold_percent)', optional="No NVMe hardware in QEMU."),
                                   target('max by (device) (cv_nvme_media_errors_total)', optional="No NVMe hardware in QEMU."),
                                   target('max by (device) (cv_nvme_critical_warning)', optional="No NVMe hardware in QEMU.")],
            grid(16, 8, 8, 6), ["device"], ["spare", "threshold", "media errors", "warning bits"],
            "Source: tools/facts daily smartctl NVMe health log. Spare should exceed its device threshold; media errors or critical-warning bits need attention. Absent on QEMU's virtio disk.",
            [ov("spare", unit="percent", min=0, max=100), ov("threshold", unit="percent", min=0, max=100),
             ov("media errors", thresholds=BAD), ov("warning bits", thresholds=BAD)])
    p.table("Textfile freshness · now", [target('max by (node,file) (time() - node_textfile_mtime_seconds)')],
            grid(0, 14, 12, 7), ["node", "file"], ["age"],
            "Source: node_exporter textfile mtimes across host, fw1/fw2 and wan. Boot facts age with this boot; daily facts refresh after 20 hours; audit facts refresh hourly; firewall/wan facts every minute; checker after boot/update and daily. No single age threshold fits them all.", [ov("age", unit="s")])
    p.timeline("Checker · over the range", [target('max(cv_checker_success)', "checker")],
               grid(12, 14, 12, 7), "Source: tools/check result at each scrape. A gap means no result; failure stays visible until the checker passes.", mappings=OK)
    events = p.logs("Security · recent events", SECURITY_EVENTS, grid(0, 21, 24, 10),
                    "Source: host/wan syslog-ng and fw syslogd to VictoriaLogs. Successful/failed logins (including greetd/tuigreet and su), sudo password failures and commands, USBGuard decisions, AppArmor denials and complain-mode events (ALLOWED), CARP takeovers, guest updates/failures, host updates, bless and exhausted-slot fallback. Latest 50 records in the selected range; hostname/app_name identify the source. Routine audit and stack continuations excluded; all logs are in Explore.")
    events["options"]["dedupStrategy"] = "none"
    p.footer(SCREEN_ROWS, "Continuous UKI/ESP hashes, live dm-verity verification, TPM attestation, per-key audit counters, AppArmor/USBGuard policy inventories, file integrity sweeps, guest security state and certificates other than incus-server are not collected. Boot, daily and audit facts retain their last sample until rewritten: read freshness alongside the verdicts.")
    return p.dashboard("cv-security", "Convergent · Security", "Measured boot facts, trust, checker and security logs.", refresh="5m")
