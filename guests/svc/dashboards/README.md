# Grafana dashboards

Edit Python, regenerate JSON and preserve UIDs. Pages: Overview / Network / Guests / Host /
Security / Monitoring. No runtime Python in svc.

```sh
python3 -I guests/svc/dashboards/build.py
python3 -I guests/svc/dashboards/build.py --check
python3 -I guests/svc/dashboards/check.py
sh build/test-observability
```

Output is deterministic UTF-8/LF. `build/lint` checks drift. `check.py` checks all page layouts,
query references, absent NVMe, failed firewall commands, optional demotion groups and update journals.
Rule API fixtures need jq. The observability suite also covers network parsers and the advisory gate.

Run `check-data <json-dir> [query-proxy-url]` on the host after real scrapes and all slow rule groups
have evaluated (allow ten minutes after restarting svc). It includes collapsed panels, substitutes
4m/1m rate/interval macros and default/svc/wan/eth0 variables, and checks MetricsQL and LogsQL.
Errors fail; optional emptiness is documented per target. Forged-sender checks store no test events.
Live checks need QEMU and laptop testing, including stale
collectors, no NVMe/battery, stopped on-demand guests, failed probes and the owner's actual viewport.

Overview's zero requires a fresh, complete vmalert rule API observation, recent healthy evaluations
(including recording rules), a working scrape and no recent remote-write errors.
Alert summaries, objects, onset and dashboard links share that snapshot. Boot facts
must belong to this boot; checker expires at 36h; firewall/WAN/probe observations at 3m. Unknown is
never coerced to healthy. Rule groups run at 30s (path/DNS), 1m (capacity/monitoring/logs), or 5m
(boot/certificate/NVMe/scrub). An unavailable svc cannot alert through itself; the bar remains unknown.

`tools/observe` runs read-only each minute, independently of self-heal. It checks host DNS, rule
health, cgroup memory/PSI/OOM/throttling and guest update journals. While def runs, it checks verified
HTTPS to example.com through def's network namespace using the resolved IPv4 address. Host/WAN policy
denies ordinary outbound HTTPS; observe neither opens policy tables nor starts browsers.
Closed def means HTTPS N/A and Network UNKNOWN. One endpoint cannot prove all Internet access.
`facts` reads audit status each minute, storage/qgroups hourly, and daily hardware/certificates after
20h; failed daily work retries hourly. NVMe capability distinguishes expected absence from missing SMART data.
The bar refreshes at 5s, inputs at 10s and alerts at 30s. Observation does not alter wan-watch/healing cadence.

Native VM CPU/memory/filesystems are primary; QEMU accounting is uncoloured secondary detail.
Stopped on-demand guests remain selectable through inventory/history. Incus scrapes at 60s with
four-minute rates. Initial Overview query count is 16; Network 29, with 23 diagnostic queries hidden
behind a collapsed row. Counts include logs; expanding details adds load. Host collectors are explicit;
PSI and diskstats feed dashboards. [Memory/cache limits](../../../ARCHITECTURE.md#11-resource-budget-unmeasured-estimates)
and [retention](../../../ARCHITECTURE.md#8-observability) bound collection.

VM/VL/vmalert/vmauth self-metrics have bounded allowlists. Host/WAN/firewalls send minute log heartbeats.
svc forwards its RAM syslog ring over loopback UDP to VL; warnings persist when VL is available, with
no durable replay while it is down. Stream labels use connection IP and app name. Dashboards derive
hostnames from connection IP; app names/messages remain sender claims. Security audit filters include
identity and guest-key events. Explore/navigation retain selected time; network diagnostics have
node/device selectors. Collection uses existing TLS, forwarding and PF policy.

Monitoring shows actual svc cgroup memory versus its 350 MiB idle / 768 MiB admin-browser limit,
process RSS/heap, PSI, ingestion errors and effective log retention. Host shows /var writable/free,
Btrfs errors, scrub record/age and actual svc volume qgroup headroom. A missing scrub record is not
clean; no collector starts a scrub or changes quotas. Queue depth/drop accounting, durable svc replay,
battery runtime/wear and automated incident/failover correlation remain gaps.
