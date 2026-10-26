"""Security evidence and update history, with measurement time beside verdicts."""
from dashlib import AMBER, BAD, OK, SECURITY_EVENTS, Page, grid, ov, target, thresholds
from health import CHECKER, fresh, known
from release import panels as release_panels


def generate():
    p = Page()
    boot = fresh('boot', 315360000)
    known(p.stat('Boot evidence', [target('cv_secure_boot_verified and on() (' + boot + ')', 'Secure Boot'),
                 target('cv_lockdown_enabled and on() (' + boot + ')', 'confidentiality lockdown'),
                 target('cv_luks_header_matches_release and on() (' + boot + ')', 'accepted local LUKS baseline'),
                 target('cv_collector_timestamp_seconds{collector="boot"} * 1000', 'measured at')], grid(0, 0, 14, 3),
                 'Boot facts require successful collection in this boot. LUKS is an accepted local baseline, including automatic first-run acceptance; it is not release provenance or continuous verification.',
                 overrides=[ov(n,mappings=OK) for n in ('Secure Boot','confidentiality lockdown','accepted local LUKS baseline')] + [ov('measured at',unit='dateTimeAsIso')] ))
    known(p.stat('Checker evidence', [target('cv_checker_success and on() (' + CHECKER + ')', 'checker'),
                 target('time() - cv_checker_last_run_seconds', 'age'), target('cv_crash_records', 'archived crashes')], grid(14, 0, 10, 3),
                 'Checker expires after 36h. Inspect sys check and /var/lib/convergent/check/last for failure categories. Crash archives remain in /var/lib/convergent/crash until acknowledged.',
                 overrides=[ov('checker',mappings=OK), ov('age',unit='s',thresholds=thresholds(('text',None),(AMBER,129600))), ov('archived crashes',thresholds=BAD)]))
    p.table('Certificates - time remaining', [target('cv_certificate_not_after_seconds - time()')], grid(0, 3, 12, 6),
            ['certificate'], ['remaining'], 'Daily certificate inventory; failure and measurement age are on Monitoring. Incus UI certificate is optional and remains managed by its existing owner flow.', [ov('remaining',unit='s')])
    p.stat('Time / audit evidence', [target('cv_nts_authenticated_sources and on() (' + fresh('nts',180) + ')', 'NTS sources'),
                 target('cv_audit_lost_total and on() (' + fresh('audit',180) + ')', 'audit lost'),
                 target('time() - cv_collector_timestamp_seconds{collector=~"nts|audit"}', '{{collector}} age')], grid(12, 3, 12, 6),
                 'NTS and audit status are read every minute. Any lost audit record needs attention.', overrides=[ov('audit lost',thresholds=BAD)])
    y = release_panels(p, 9)
    events = p.logs('Security · recent events', SECURITY_EVENTS, grid(0, y, 24, 10),
                   'Authentication, denials, identity/USB/guest-key audit events, update/deferred/bless/fallback and Incus lifecycle evidence. Source identity comes from the connection, not sender hostname; last 50 records in the selected range.')
    events['options']['dedupStrategy'] = 'none'
    p.timeline('Checker history', [target('cv_checker_success', 'checker')], grid(0, y+10, 12, 7), 'Historical result; current freshness is above.', mappings=OK)
    p.timeseries('Clock offset', [target('abs(node_timex_offset_seconds{node=~"host|wan"})', '{{node}}')], grid(12, y+10, 12, 7), 's', 'Warns after 5m above 0.1s; independent absolute wall-clock checks remain in rules.')
    p.footer(y+17, 'Continuous UKI/ESP verification, TPM attestation and per-key policy inventories are not collected. Host hardware is on Host; collector plumbing is on Monitoring. The latest checker report and crash archive contain the local recovery evidence.')
    return p.dashboard('cv-security', 'Convergent · Security', 'Boot/checker, signed Release/CVE status and security events.', refresh='1m')
