"""The six CARP segments, firewall evidence, DNS and physical interfaces."""
from dashlib import (
    AMBER, BAD, FW_CHANGES, SCREEN_ROWS, UP, Page, grid, ov, target, thresholds)


def generate():
    p = Page()
    p.stat("", [target('max by (node) (convergent_pf_enabled)', "pf · {{node}}"),
                target('max by (node) (convergent_pfsync_up)', "pfsync · {{node}}"),
                target('max by (node) (convergent_unbound_up)', "resolver · {{node}}")],
           grid(0, 0, 16, 2), "Source: fw-facts pfctl, ifconfig pfsync0 and unbound-control status.", mappings=UP)
    p.stat("", [target('max(convergent_wan_upstream_up{node="wan"})', "WAN lease"),
                target('max(convergent_wan_upstream_overlap{node="wan"})', "overlap refused"),
                target('max(convergent_wan_portal_mode{node="wan"})', "portal mode")],
           grid(16, 0, 8, 2), "Source: wan-check. Lease present is not an Internet probe; overlap is latched until a safe lease; portal lasts at most 30 minutes.",
           overrides=[ov("WAN lease", mappings=UP), ov("overlap refused", thresholds=BAD), ov("portal mode", thresholds=BAD)])
    for i, segment in enumerate(("transit", "host", "svc", "web", "admin", "guests")):
        p.timeline("CARP · " + segment, [target('max by (node) (convergent_carp_state{interface="carp%d"})' % i, "{{node}}")],
                   grid(i % 3 * 8, 2 + i // 3 * 5, 8, 5),
                   "Source: fw-facts ifconfig CARP interface carp%d / VHID %d. Raw roles: INIT 0, BACKUP 1, MASTER 2; two rows, one per firewall. Gaps mean missing data." % (i, i + 1))
    p.timeseries("pf · states against limit", [target('max by (node) (convergent_pf_states)', "states · {{node}}"),
                                               target('max by (node) (convergent_pf_state_limit)', "limit · {{node}}")],
                 grid(0, 12, 8, 6), "short", "Source: fw-facts pfctl -si and -sm; current state entries and configured ceiling.")
    p.timeseries("pf · diagnostic counters", [target('sum by (node,name) (rate(convergent_pf_counter_total[$__rate_interval]))', "{{node}} · {{name}}")],
                 grid(8, 12, 8, 6), "pps", "Source: fw-facts pfctl -si Counters. Rates of diagnostic events, not policy pass/block verdicts; rule-label traffic is not collected.")
    p.timeseries("DNS · queries and cache hits", [target('rate(convergent_unbound_queries_total[$__rate_interval])', "queries · {{node}}"),
                                                   target('rate(convergent_unbound_cachehits_total[$__rate_interval])', "cache hits · {{node}}")],
                 grid(16, 12, 8, 6), "reqps", "Source: fw-facts unbound-control stats_noreset, total.num.queries and total.num.cachehits.")
    p.table("Default route · presence and next hop", [target('max by (node,gateway) (convergent_default_route_info)')],
            grid(0, 18, 8, 5), ["node", "gateway"], ["route"],
            "Source: fw-facts route -n show -inet; one current row per firewall/next hop. This confirms presence, not a policy comparison.", [ov("route", mappings=UP)])
    p.stat("Resolver input ages", [target('max by (node) (time() - convergent_dns_file_mtime_seconds{file="blocklist.rpz"})', "RPZ · {{node}}"),
                                    target('max by (node) (time() - convergent_fw_facts_timestamp_seconds)', "facts · {{node}}"),
                                    target('max by (node) (convergent_default_route_present)', "default · {{node}}")],
           grid(8, 18, 8, 5), "Source: fw-facts RPZ file mtime, collection timestamp and route presence. A missing route is DOWN; RPZ warns at ten days, facts at three minutes.", unit="s",
           overrides=[ov("RPZ · " + n, thresholds=thresholds(("text", None), (AMBER, 864000))) for n in ("fw1", "fw2")] +
                     [ov("facts · " + n, thresholds=thresholds(("text", None), (AMBER, 180))) for n in ("fw1", "fw2")] +
                     [ov("default · " + n, unit="none", mappings=UP) for n in ("fw1", "fw2")])
    p.timeseries("WAN · traffic by interface", [target('8 * rate(node_network_receive_bytes_total{node="wan",device!="lo"}[$__rate_interval])', "in · {{device}}"),
                                                 target('8 * rate(node_network_transmit_bytes_total{node="wan",device!="lo"}[$__rate_interval])', "out · {{device}}")],
                 grid(16, 18, 8, 5), "bps", "Source: wan node_exporter netdev. Includes internal and physical interfaces; no radio association, SSID or signal metric is collected.")
    p.timeseries("Interfaces · errors and queue drops", [target('rate(node_network_receive_errs_total{device!="lo"}[$__rate_interval])', "RX error · {{node}} {{device}}"),
                                                          target('rate(node_network_transmit_errs_total{device!="lo"}[$__rate_interval])', "TX error · {{node}} {{device}}"),
                                                          target('rate(node_network_receive_drop_total{device!="lo"}[$__rate_interval])', "RX drop · {{node}} {{device}}"),
                                                          target('rate(node_network_transmit_drop_total{device!="lo"}[$__rate_interval])', "TX drop · {{node}} {{device}}")],
                 grid(0, 23, 12, 8), "pps", "Source: node_exporter netdev on scraped nodes. Interface errors/drops are queue or link failures, not pf policy drops; platforms may expose only some counters.")
    p.logs("Firewall and CARP changes", FW_CHANGES, grid(12, 23, 12, 8),
           "Source: fw syslogd via TLS to VictoriaLogs; CARP role transitions, ifstated and pfctl. The same role-transition filter is the disabled-by-default annotation.")
    p.footer(SCREEN_ROWS, "pf passed/blocked packets by rule label (fw-facts exports diagnostic counters only); DNS latency, RPZ hits and per-client queries; host/WAN default next hops; Wi-Fi radio/SSID/signal/PMF; BFD. Resolver up means unbound-control responds, not an external DNS query.")
    return p.dashboard("cv-network-path", "Convergent · Network", "Six CARP segments, pf, DNS, uplink and interface health.")
