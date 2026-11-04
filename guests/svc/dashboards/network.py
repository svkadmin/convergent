"""Label-derived CARP segments, firewall evidence, DNS and physical interfaces."""
from dashlib import (
    AMBER, BAD, CARP, CYAN, GRAY, FIREWALLS, FW_CHANGES, LOGS, OK, UP, Page, grid, ov, query_var, target, thresholds, vmap)

from health import CHECKER, FW, WAN, fresh, known


def generate():
    p = Page()
    known(p.stat('Internet - DNS and on-demand web', [target('cv_internet_probe_success and on() (' + fresh('internet', 180) + ')', '{{probe}} {{target}}', optional='HTTPS is measured only while def is running; DNS remains minute evidence.'),
                 target('time() - cv_collector_timestamp_seconds{collector="internet"}', 'measurement age'), target('cv_https_probe_available', 'web probe available')], grid(0, 0, 24, 3),
                 'Minute DNS via the host resolver; verified HTTPS to example.com uses only an already-running def network namespace and the resolved IPv4 address. No browser startup or policy openings. Closed def means HTTPS unavailable, not failed; a single endpoint is not the whole Internet.',
                 overrides=[ov('dns example.com', mappings=OK), ov('https example.com', mappings=OK), ov('measurement age', unit='s'), ov('web probe available', mappings=vmap([(0,'N/A - def closed',GRAY),(1,'AVAILABLE',CYAN)]))]))
    p.table('Firewall readiness - pair', [target('convergent_wan_watch_up and on(node) (' + FW + ') and on(node) (convergent_wan_watch_probe_timestamp_seconds > time() - 180) and on(node) (convergent_wan_watch_probe_timestamp_seconds <= time() + 60)'),
             target('convergent_pfsync_up and on(node) (' + FW + ')'), target('convergent_pfsync_defer and on(node) (' + FW + ')'),
             target('convergent_carp_preempt and on(node) (' + FW + ')'),
             target('max by(node) (convergent_carp_demotion)'),
             target('(max by(node) (convergent_pf_ruleset_info and on(node,loaded) label_replace(cv_firewall_ruleset_expected_info,"node","$1","firewall","(fw1|fw2)")) or on(node) (convergent_fw_facts_success * 0)) and on(node) (' + FW + ') and on() (' + CHECKER + ')'),
             target('time() - convergent_fw_facts_timestamp_seconds')], grid(0, 0, 24, 6), ['node'],
            ['watcher','pfsync','defer','preempt','demotion','rules agree','age'],
            'Readiness is local evidence, not proof of synchronized peer state contents. Missing/stale/failed collection blanks health columns. Demotion groups are below; rules compare against checker baseline.',
            [ov(n,mappings=OK) for n in ('watcher','pfsync','defer','preempt','rules agree')] + [ov('age',unit='s')])
    p.table('CARP readiness - segment by firewall', [target('max by(node,segment,interface) (convergent_carp_state and on(node) (' + FW + '))')],
            grid(0, 0, 24, 7), ['segment','interface','node'], ['role'], 'Every registered segment on both nodes. Mixed roles and missing/split masters alert; colors describe roles.', [ov('role',mappings=CARP)])
    p.table('CARP advertisement skew', [target('convergent_carp_advskew')], grid(0,0,12,6), ['node','segment','interface'], ['advskew'], 'Configured election preference; descriptive, not a failure verdict.')
    p.timeseries('DNS - NXDOMAIN', [target('rate(convergent_unbound_nxdomain_total[4m])', '{{node}}')], grid(0,0,12,6), 'reqps', 'Negative answers can be normal; correlate with SERVFAIL and recursion latency.')
    p.table('DNS deployed files', [target('convergent_dns_file_mtime_seconds * 1000')], grid(0,0,12,6), ['node','file'], ['modified'], 'Compare deployment times between peers. An unchanged local-owner.conf has no age alarm.', [ov('modified',unit='dateTimeAsIso')])
    p.table('CARP demotion groups', [target('convergent_carp_demotion')], grid(0, 0, 12, 6), ['node','group'], ['demotion'],
            'wanwatch, maintenance, upgrade and handoff demotions explain role changes. A nonzero administrative demotion is not automatically a fault.')
    p.timeseries('pf state utilization', [target('100 * convergent_pf_states / convergent_pf_state_limit', '{{node}}')], grid(12, 0, 12, 6), 'percent', 'Alert at 80% for 5m; absolute counts remain in diagnostics.', max_=100)
    p.timeseries('WAN conntrack utilization', [target('100 * node_nf_conntrack_entries{node="wan"} / node_nf_conntrack_entries_limit{node="wan"}', 'wan')], grid(12, 0, 12, 6), 'percent',
                 'Source: wan node_exporter conntrack. Alert at 80% for 5m; a full table drops new NAT flows.', max_=100)
    p.stat("", [target('max by (node) (convergent_pf_enabled and on(node) (' + FW + '))', "pf · {{node}}"),
                target('max by (node) (convergent_pfsync_up and on(node) (' + FW + '))', "pfsync · {{node}}"),
                target('max by (node) (convergent_unbound_up and on(node) (' + FW + '))', "resolver · {{node}}")],
           grid(0, 0, 16, 2), "Source: fw-facts pfctl, ifconfig pfsync0 and unbound-control status.", mappings=UP)
    p.stat("", [target('max(convergent_wan_upstream_up{node="wan"} and on(node) (' + WAN + '))', "WAN lease"),
                target('max(convergent_wan_upstream_overlap{node="wan"})', "overlap refused"),
                target('max(convergent_wan_portal_mode{node="wan"})', "portal mode")],
           grid(16, 0, 8, 2), "Source: wan-check. Lease present is not an Internet probe; overlap is latched until a safe lease; portal lasts at most 30 minutes.",
           overrides=[ov("WAN lease", mappings=UP), ov("overlap refused", thresholds=BAD), ov("portal mode", thresholds=BAD)])
    p.timeline("CARP · all segments", [target('max by (node,segment,interface) (convergent_carp_state and on(node) (' + FW + '))', "{{segment}} · {{interface}} · {{node}}")],
               grid(0, 2, 24, 10),
               "Source: fw-facts CARP labels; every observed segment/interface on both firewalls, with no fixed segment count. INIT 0, BACKUP 1, MASTER 2; gaps mean missing data. The expected-registry alert detects missing segments.")
    p.timeseries("pf · states against limit", [target('max by (node) (convergent_pf_states)', "states · {{node}}"),
                                               target('max by (node) (convergent_pf_state_limit)', "limit · {{node}}")],
                 grid(0, 12, 8, 6), "short", "Source: fw-facts pfctl -si and -sm; current state entries and configured ceiling.")
    p.timeseries("pf · diagnostic counters", [target('sum by (node,name) (rate(convergent_pf_counter_total[4m]))', "{{node}} · {{name}}")],
                 grid(8, 12, 8, 6), "pps", "Source: fw-facts pfctl -si Counters. Rates of diagnostic events, not policy pass/block verdicts; rule-label traffic is not collected.")
    p.timeseries("DNS · queries and cache hits", [target('rate(convergent_unbound_queries_total[4m])', "queries · {{node}}"),
                                                   target('rate(convergent_unbound_cachehits_total[4m])', "cache hits · {{node}}")],
                 grid(16, 12, 8, 6), "reqps", "Source: fw-facts unbound-control stats_noreset, total.num.queries and total.num.cachehits.")
    p.table("Default route · presence and next hop", [target('max by (node,gateway) (convergent_default_route_info)')],
            grid(0, 18, 8, 5), ["node", "gateway"], ["route"],
            "Source: fw-facts route -n show -inet; one current row per firewall/next hop. This confirms presence, not a policy comparison.", [ov("route", mappings=UP)])
    p.stat("Resolver input ages", [target('max by (node) (time() - convergent_dns_source_refreshed_seconds)', "RPZ · {{node}}"),
                                    target('max by (node) (time() - convergent_fw_facts_timestamp_seconds)', "facts · {{node}}"),
                                    target('max by (node) (convergent_default_route_present and on(node) (' + FW + '))', "default · {{node}}")],
           grid(8, 18, 8, 5), "Source: fw-facts RPZ source refresh, collection timestamp and route presence. A missing route is DOWN; RPZ warns at ten days, facts at three minutes.", unit="s",
           overrides=[ov("RPZ · " + n, thresholds=thresholds(("text", None), (AMBER, 864000))) for n in ("fw1", "fw2")] +
                     [ov("facts · " + n, thresholds=thresholds(("text", None), (AMBER, 180))) for n in ("fw1", "fw2")] +
                     [ov("default · " + n, unit="none", mappings=UP) for n in ("fw1", "fw2")])
    p.timeseries("WAN · traffic by interface", [target('8 * rate(node_network_receive_bytes_total{node="wan",device!="lo"}[4m])', "in · {{device}}"),
                                                 target('8 * rate(node_network_transmit_bytes_total{node="wan",device!="lo"}[4m])', "out · {{device}}")],
                 grid(16, 18, 8, 5), "bps", "Source: wan node_exporter netdev. Includes internal and physical interfaces; radio evidence is below.")
    p.timeseries("Interfaces · errors and queue drops", [target('rate(node_network_receive_errs_total{node=~"${node:regex}",device=~"${device:regex}"}[4m])', "RX error · {{node}} {{device}}"),
                                                          target('rate(node_network_transmit_errs_total{node=~"${node:regex}",device=~"${device:regex}"}[4m])', "TX error · {{node}} {{device}}"),
                                                          target('rate(node_network_receive_drop_total{node=~"${node:regex}",device=~"${device:regex}"}[4m])', "RX drop · {{node}} {{device}}"),
                                                          target('rate(node_network_transmit_drop_total{node=~"${node:regex}",device=~"${device:regex}"}[4m])', "TX drop · {{node}} {{device}}")],
                 grid(0, 23, 12, 8), "pps", "Source: node_exporter netdev on scraped nodes. Interface errors/drops are queue or link failures, not pf policy drops; platforms may expose only some counters.")
    p.logs("Firewall and CARP changes", '(' + FW_CHANGES + ') OR (remote_ip:="100.80.1.10" app_name:="sys-firewall")', grid(12, 23, 12, 8),
           "Source: fw syslogd via TLS to VictoriaLogs; CARP role transitions, wan-watch and pfctl. The same role-transition filter is the disabled-by-default annotation.")
    for direction, metric in (("in", "receive"), ("out", "transmit")):
        p.timeseries("Segments · " + direction, [target('8 * rate(convergent_interface_%s_bytes_total[4m]) * on(node,carpdev) group_left(segment,interface) (convergent_carp_state >= bool 0)' % metric,
                                                      "{{segment}} · {{interface}} · {{node}}")],
                     grid(0 if direction == "in" else 12, 31, 12, 7), "bps",
                     "Source: OpenBSD netstat interface byte counters joined to CARP parent/segment labels. Physical/VLAN parent traffic includes CARP and broadcasts; this is interface traffic, not routed-only traffic. Both nodes remain visible across failover.")
    p.timeseries("DNS · mean recursion latency", [target('convergent_unbound_recursion_seconds', "{{node}}")],
                 grid(0, 38, 12, 6), "s", "Source: Unbound total.recursion.time.avg via stats_noreset. Cumulative mean for recursive/cache-miss work since reset, not per-client or cached-answer latency.")
    p.timeseries("DNS · SERVFAIL rate", [target('rate(convergent_unbound_servfail_total[4m])', "{{node}}")],
                 grid(12, 38, 12, 6), "reqps", "Source: Unbound num.answer.rcode.SERVFAIL counter; rate across the selected interval.")
    p.timeseries("Wi-Fi · signal", [target('convergent_wifi_signal_dbm', "signal", optional="No associated Wi-Fi radio in QEMU or while disconnected.")],
                 grid(0, 44, 8, 6), "dBm", "Source: iw link at wan-check cadence. Missing while disconnected or unsupported; no SSID/BSSID is exported.", min_=-100, max_=0)
    p.timeseries("Wi-Fi · link bitrate", [target('convergent_wifi_bitrate_bits_per_second', "{{direction}}", optional="Radio/driver may not report bitrate; absent in QEMU.")],
                 grid(8, 44, 8, 6), "bps", "Source: iw link's reported TX/RX PHY bitrate when available; not payload throughput.")
    p.timeseries("Wi-Fi · observed roams", [target('increase(convergent_wifi_roams_total[4m])', "association changes")],
                 grid(16, 44, 8, 6), "short", "BSSID changes between successive associated wan-check samples. Disconnect/reconnect and changes between samples are not counted; resets on WAN reboot.")
    p.timeseries("WAN watch · RTT", [target('convergent_wan_watch_rtt_seconds and on(node) (convergent_wan_watch_probe_timestamp_seconds > time() - 180)', "{{node}} -> WAN transit")],
                 grid(0, 50, 12, 6), "s", "Source: existing three-ping firewall-to-WAN probe round, sampled once per minute. No extra probe. Missing when all packets are lost or resolver health skips probing; not Internet RTT.")
    p.timeseries("WAN watch · packet loss", [target('convergent_wan_watch_loss_ratio and on(node) (convergent_wan_watch_probe_timestamp_seconds > time() - 180)', "{{node}}")],
                 grid(12, 50, 12, 6), "percentunit", "Source: existing probe round, three packets; sampled loss is 0, 1/3, 2/3 or 1. Missing when resolver health skips the round.", max_=1)
    blocked = (FIREWALLS + ' AND app_name:="pflog" AND _msg:~" block "'
               ' | extract_regexp "(?P<src>(?:[0-9]{1,3}[.]){3}[0-9]{1,3}|[0-9a-f]*:[0-9a-f:]+)(?:[.][0-9]+)? > (?P<dst>(?:[0-9]{1,3}[.]){3}[0-9]{1,3}|[0-9a-f]*:[0-9a-f:]+)(?:[.](?P<port>[0-9]+))?: "')
    for i, (label, field) in enumerate((("sources", "src"), ("destinations", "dst"), ("destination ports", "port"))):
        panel = p.add("table", "Blocked · top " + label, grid(i * 8, 56, 8, 8),
                      "Source: sampled pflog headers in VictoriaLogs over the selected time range. At most five packets/second/firewall; these are sampled counts, not total blocks. Only logged rules appear; ports are numeric TCP/UDP endpoints when present.",
                      [target(blocked + ' | filter ' + field + ':* | top 10 by (' + field + ')', ds=LOGS, queryType="instant")],
                      options={"showHeader": True, "cellHeight": "sm"})
        panel["datasource"] = LOGS
    p.footer(64, "Complete pf verdict counts by rule, RPZ hit counts and per-client DNS queries, host/WAN default next hops, Wi-Fi SSID/security/PMF, BFD and flow accounting are not collected. DNS probes use the host; HTTPS uses an already-running def namespace to example.com. pflog is sampled; resolver up means unbound-control responds.")
    # Put user-visible failures before histories; keep generated geometry deterministic.
    def priority(panel):
        title = panel['title']
        for i, prefix in enumerate(('Internet', 'DNS', 'Wi-Fi', 'WAN watch', 'Firewall readiness', 'CARP readiness', 'CARP ', 'Firewall and', 'Segments', 'Blocked', 'pf state utilization', 'WAN conntrack')):
            if title.startswith(prefix):
                return i
        return 99 if panel['type'] == 'text' else 90
    p.panels.sort(key=priority)
    diagnostic = [panel['title'] for panel in p.panels if priority(panel) == 90]
    diagnostic += ['CARP demotion groups', 'CARP advertisement skew', 'DNS deployed files', 'DNS - NXDOMAIN']
    p.collapse('Troubleshooting - routes, pf and interfaces', diagnostic)
    p.reflow()
    return p.dashboard("cv-network-path", "Convergent · Network", "All CARP segments, pf, DNS, radio, uplink and interface health.",
                       [query_var('node','label_values(up{job="node"}, node)','wan'),
                        query_var('device','label_values(node_network_receive_bytes_total{node=~"${node:regex}"}, device)','eth0')])
