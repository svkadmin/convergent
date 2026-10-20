# Grafana dashboards

Edit the Python and regenerate the provisioned JSON; no runtime Python is installed in svc.
The four UIDs are retained. The shared core ports Archer's palette, 13/20 px stat type scale,
31-row screen budget (2400x1500 logical pixels, scale 1.2, less desktop/browser/Grafana chrome),
panel builders and Canvas elements. Navigation stays in the same order on every page.

```sh
python3 -I guests/svc/dashboards/build.py
python3 -I guests/svc/dashboards/build.py --check
```

Only the standard library is used; output is deterministic UTF-8 with LF endings.
`build/lint` checks drift, or reports a skip when python3 is unavailable. JSON is shipped by
the existing svc build. `build/test --guests-update` waits for scrapes after svc rollback and
runs `check-data` on the booted host against repository-copied JSON through svc. This checks
source queries, not installed dashboard packaging. It replaces rate/interval macros with 2m/1m
and selects default/svc for instance queries. Every
query error fails; an empty result fails unless its target has a `cvOptional` reason. Optional
currently means battery, hwmon sensors, NVMe health, or no firing alerts. Missing metrics are
never turned into a healthy zero, except explicit counts (alerts and closed browsers).

The log targets are LogsQL, not PromQL: VictoriaLogs `instant` fetches log lines, `stats`
returns the attention count. The checker also validates log panels and annotations against
VictoriaLogs; empty log results are normal. They are never sent as PromQL to VictoriaMetrics.
Syslog fields are hostname, app_name, level, severity and facility_keyword; source addresses
scope the four senders without assuming the host's name. Noise is filtered in queries, never
discarded at ingestion; all logs have an Explore link. CARP annotations are disabled by
default and use actual role-transition messages, not every nonzero CARP scrape. Percentage
graphs have fixed 0–100 bounds; other graphs have zero minima and unit-appropriate soft
maxima that expand with the data, so a traffic spike is not clipped. The host supplies curl/jq for
the integration check; svc needs neither client, Python nor the generators at runtime.

Security's single recent-events panel adds successful/failed authentication, sudo commands,
USBGuard decisions (including forwarded USER_DEVICE audit records), AppArmor denials, CARP
takeovers and host/guest update, bless and fallback messages. It keeps 50 lines, scoped to the
four infrastructure senders and selected time range, with no aggregation or deduplication.
Overview's attention count keeps its narrower failure filter. `check-data` already runs this
LogsQL target; empty event windows remain valid.

Sources: `tools/facts`, `tools/check`, firewall `fw-facts`, WAN `wan-check`, node_exporter's
configured/default collectors, Incus `/1.0/metrics`, and vmalert `ALERTS`. pf pass/block label
counters and Wi-Fi radio metrics are not collected. The descriptions and footers say so.

The [Incus metric reference](https://linuxcontainers.org/incus/docs/main/metrics/) describes
the endpoint's resource series. The [VictoriaLogs syslog reference](https://docs.victoriametrics.com/victorialogs/data-ingestion/syslog/)
describes its fields, and the [plugin query implementation](https://github.com/VictoriaMetrics/victorialogs-datasource/blob/main/pkg/plugin/query.go)
defines `instant` and `stats` target types. No Loki query syntax is used.
