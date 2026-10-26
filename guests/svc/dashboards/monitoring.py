"""Evidence freshness, collection failures and the stack's own cost."""
from dashlib import BAD, ERRORS, LOGS, OK, Page, grid, ov, target
from health import RULES, known


def generate():
    p = Page()
    known(p.stat('Evaluation / ingestion', [target('cv_rules_healthy', 'rule health'),
                  target('time() - cv_rules_last_evaluation_seconds', 'oldest evaluation age'),
                  target('vm_storage_is_read_only', 'metrics read only'), target('vl_storage_is_read_only', 'logs read only')], grid(0, 0, 24, 3),
          'Rule API includes every rule and group, with age bounded by twice its interval plus 90s. This stack cannot page while svc itself is unavailable; the bar shows unknown.',
          overrides=[ov('rule health', mappings=OK), ov('oldest evaluation age', unit='s'), ov('metrics read only', thresholds=BAD), ov('logs read only', thresholds=BAD)]))
    p.table('Collectors - measurement age and result', [target('max by (collector) (cv_collector_success)'),
             target('max by (collector) (time() - cv_collector_timestamp_seconds)')], grid(0, 3, 12, 9),
            ['collector'], ['success', 'age'], 'Minute: NTS, audit, rules, Internet and cgroups. Hourly: storage and failed daily retry. Daily: hardware/certificates (20h overdue threshold). Boot: valid only within this boot. Failure reasons are in facts syslog.',
            [ov('success', mappings=OK), ov('age', unit='s')])
    p.table('Scrapes - cost and availability', [target('up'), target('scrape_duration_seconds'), target('scrape_samples_post_metric_relabeling')],
            grid(12, 3, 12, 9), ['job', 'node', 'instance', 'service'], ['up', 'duration', 'samples'],
            'Incus runs at 60s; all other scrapes 30s with a 5s timeout. Payload allowlists limit stored families.',
            [ov('up', mappings=OK), ov('duration', unit='s')])
    p.table('Firewall collection sections', [target('convergent_fw_section_success')], grid(0, 12, 12, 8),
            ['node', 'section'], ['success'], 'A failed command is explicit. Parser/required-field failures also clear the aggregate firewall collection verdict.', [ov('success', mappings=OK)])
    p.table('Textfiles - source age', [target('time() - node_textfile_mtime_seconds')], grid(12, 12, 12, 8),
            ['node', 'file'], ['age'], 'Raw age includes files whose producers have stopped. Boot age alone is not a failure.', [ov('age', unit='s')])
    heartbeats = p.add('table', 'Log sender heartbeats - last 5m', grid(0, 20, 12, 7),
                      'One minute heartbeat per host/firewall/WAN. Four rows expected; absent rows mean missing delivery, not quiet logs. Sender identity is the connection address.',
                      [target('_time:5m app_name:="cv-heartbeat" remote_ip:in("100.80.1.10","100.80.2.2","100.80.2.3","100.80.0.10") | stats by (remote_ip) count() as heartbeats', ds=LOGS, queryType='instant')])
    heartbeats['datasource'] = LOGS
    p.timeseries('Evaluation / remote-write errors', [target('sum by (__name__) (increase({__name__=~"vmalert_(alerting_rules_errors_total|recording_rules_errors_total|remotewrite_errors_total|remotewrite_dropped_rows_total)"}[5m]))', '{{__name__}}')],
                 grid(12, 20, 12, 7), 'short', 'Counter changes over 5m; errors must remain zero. Monitoring alerts remain fallible if their own evaluator is failing.')
    p.timeseries('svc cgroup - actual memory constraint', [target('cv_guest_memory_current_bytes{name="svc"}', 'current'),
                 target('cv_guest_memory_max_bytes{name="svc"}', 'hard limit')], grid(0, 27, 12, 7), 'bytes',
                 'Host cgroup memory.current includes cache; compare idle against 350 MiB and admin-browser sessions against 768 MiB. Go/cache budgets are not RSS limits.')
    p.timeseries('svc processes - RSS / Go heap', [target('process_resident_memory_bytes{node="svc"}', 'RSS {{job}} {{service}}'),
                 target('go_memstats_heap_alloc_bytes{node="svc"}', 'heap {{job}} {{service}}')], grid(12, 27, 12, 7), 'bytes', 'Native process metrics, bounded to monitoring processes. Grafana RSS is included only in cgroup totals.')
    p.timeseries('Guest OOM / throttling', [target('increase(cv_guest_memory_events_total{event=~"oom|oom_kill"}[5m])', '{{name}} {{event}}'),
                 target('rate(cv_guest_cpu_throttled_seconds_total[4m])', '{{name}} throttled seconds/s')], grid(0, 34, 12, 7), 'short', 'Fixed container cgroups: svc and browser compartments. Counters reset when a cgroup is recreated.')
    p.timeseries('Guest pressure', [target('rate(cv_guest_pressure_seconds_total[4m])', '{{name}} {{resource}} {{scope}}')],
                 grid(12, 34, 12, 7), 'percentunit', 'Cgroup PSI total stall seconds per second; some/full scope remains distinct.')
    p.logs('Monitoring errors', '(remote_ip:="127.0.0.1" AND severity:in("0","1","2","3","4")) OR (' + ERRORS + ' AND app_name:in("facts","observe","syslog-ng"))',
           grid(0, 41, 24, 8), 'svc local syslog is forwarded over loopback UDP to VictoriaLogs and retained for 7d / 4 GiB threshold. RAM ring remains the fallback while VL is down; UDP is not durable.')
    p.stat('Retained log window / storage headroom', [target('time() - vl_storage_log_min_timestamp_seconds', 'oldest log age', optional='No logs have been stored yet.'),
                 target('vm_free_disk_space_bytes', 'metrics filesystem free'), target('vl_free_disk_space_bytes', 'logs filesystem free')], grid(0,49,24,3),
                 'Effective oldest retained record, not a retention guarantee. Filesystem free space does not replace qgroup headroom on Host.',
                 overrides=[ov('oldest log age',unit='s'),ov('metrics filesystem free',unit='bytes'),ov('logs filesystem free',unit='bytes')])
    p.timeseries('Ingestion / query failures', [target('sum by(__name__,service) (increase({__name__=~"vm_rows_ignored_total|vl_rows_dropped_total|vm_http_request_errors_total|vm_request_errors_total|vmauth_http_request_errors_total"}[5m]))', '{{__name__}} {{service}}', optional='Some failure counters are created only after the first error; required read-only and process metrics remain checked.')], grid(0,52,24,7), 'short', 'Rejected samples, logs and query/proxy errors; do not interpret missing lazily-created counters as proof of health.')
    p.footer(59, 'Metrics: 14d, no dedup. Logs: 7d / 4 GiB threshold, 6 GiB quota. Quota usage is on Host. No remote paging or durable svc log queue; sender heartbeats detect loss of delivery, not queue depth. Measure idle/admin-browser memory and GC on the rig before changing budgets.')
    p.table('Native collectors - result and cost', [target('node_scrape_collector_success'), target('node_scrape_collector_duration_seconds')],
            grid(0,0,24,7), ['node','collector'], ['success','duration'], 'Exporter collector failures alert even when HTTP scraping succeeds.', [ov('success',mappings=OK),ov('duration',unit='s')])
    p.timeseries('Go GC pause cost', [target('rate(go_gc_duration_seconds_sum{node="svc"}[5m]) / rate(go_gc_duration_seconds_count{node="svc"}[5m])', '{{job}} {{service}}', optional='No GC cycles yet produces an undefined mean.')],
                 grid(0,0,24,7), 's', 'Mean GC pause duration; compare with process RSS and the actual cgroup limit before changing memory budgets.')
    p.collapse('Collector and runtime diagnostics', ['Native collectors - result and cost','Go GC pause cost'])
    p.reflow()
    return p.dashboard('cv-monitoring', 'Convergent · Monitoring', 'Collection, evaluation, storage, log delivery and resource cost.')
