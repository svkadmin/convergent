# Grafana dashboards

Edit the Python, then regenerate JSON. The four existing UIDs remain; Host and Monitoring are new.
Navigation is Overview / Network / Guests / Host / Security / Monitoring. No runtime Python in svc.

```sh
python3 -I guests/svc/dashboards/build.py
python3 -I guests/svc/dashboards/build.py --check
python3 -I guests/svc/dashboards/check.py
sh build/test-observability
```

Output is deterministic UTF-8/LF. `build/lint` checks drift. `check.py` checks all page layouts,
query references, absent NVMe, failed firewall commands, optional demotion groups and update journals.
Its rule API fixtures need jq. The existing observability suite also covers the network parsers and
advisory gate; its current advisory fixture expects six findings after adding a fourth Alpine target,
so that unrelated assertion fails on the unchanged baseline.

Run `check-data <json-dir> [query-proxy-url]` on the host after real scrapes and all slow rule groups
have evaluated (allow ten minutes after restarting svc). It visits collapsed panels too, substitutes
4m/1m rate/interval macros and default/svc/wan/eth0 variables, and checks MetricsQL and LogsQL.
Errors always fail; optional emptiness is documented per target. It also checks synthetic forged
sender hostnames without storing test events. Live checks need QEMU and the laptop, including stale
collectors, no NVMe/battery, stopped on-demand guests, failed probes and the owner's actual viewport.

Overview's zero requires a fresh host observation of the complete vmalert rule API, healthy and
recent evaluations (including recording rules), a working scrape, and no recent remote-write errors.
Alert summaries, objects, onset and dashboard links come from that same API snapshot. Boot facts
must belong to this boot; checker expires at 36h; firewall/WAN/probe observations at 3m. Unknown is
never coerced to healthy. Rule groups run at 30s (path/DNS), 1m (capacity/monitoring/logs), or 5m
(boot/certificate/NVMe/scrub). An unavailable svc cannot alert through itself; the bar remains unknown.

`tools/observe` is a read-only minute job, independent of self-heal. It checks the host resolver and, only while def already runs,
verified HTTPS to example.com from that existing network namespace using the resolved IPv4 address, observes rule health, cgroup memory/PSI/OOM/throttling, and guest update
journal phases. Host and WAN policy deny ordinary outbound HTTPS. No policy table is opened and no browser is started;
closed def means N/A for HTTPS and UNKNOWN for the full Network verdict. One endpoint is not proof
that every Internet destination works. `facts` reads audit
status each minute, storage/qgroups hourly, and daily hardware/certificates after 20h; failed daily
work retries hourly. NVMe capability distinguishes expected absence from missing SMART data.
The bar refreshes at 5s, inputs at 10s and alerts at 30s. No wan-watch/healing cadence changes.

Native VM CPU/memory/filesystems are primary; QEMU accounting is uncoloured secondary detail.
Stopped on-demand guests remain selectable through inventory/history. Incus scrapes at 60s with
four-minute rates. Initial Overview query count is 16; Network 28, with 23 diagnostic queries hidden
behind a collapsed row. Counts include logs; expanding details adds load. Host collectors are explicit;
PSI and diskstats have consumers. Existing memory/cache limits and retention remain unchanged.

VM/VL/vmalert/vmauth self-metrics have bounded allowlists. Host/WAN/firewalls send minute log heartbeats.
svc forwards its RAM syslog ring over loopback UDP to VL; warnings persist when VL is available, with
no durable replay while it is down. Stream labels use connection IP and app name. Dashboards derive
hostnames from connection IP; app names/messages remain sender claims. Security audit filters include
identity and guest-key events. Explore and navigation retain selected time; network diagnostics have
node/device selectors. TLS, forwarding policy and pf rules are unchanged.

Monitoring shows actual svc cgroup memory versus its 350 MiB idle / 768 MiB admin-browser limit,
process RSS/heap, PSI, ingestion errors and effective log retention. Host shows /var writable/free,
Btrfs errors, scrub record/age and actual svc volume qgroup headroom. A missing scrub record is not
clean; no collector starts a scrub or changes quotas. Queue depth/drop accounting, durable svc replay,
battery runtime/wear and automated incident/failover correlation remain gaps.
