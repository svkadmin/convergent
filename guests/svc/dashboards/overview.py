"""Home: the path, what needs attention, and the machine beside it."""
from dashlib import (
    ACTIONABLE, AMBER, BAD, CARD, CARP, CYAN, EDGE, ERRORS, GRAY, HOST_CPU, HOST_RAM, INK, LOGS,
    NEUTRAL, OK, SCREEN_ROWS, STATE, STATE_DISK, UP, Canvas, Page,
    grid, guests_table, ov, target, thresholds, vmap)


def path(page):
    c = Canvas()

    def field(name, expr, **props):
        c.field(name, expr, **props)

    def card(name, title, subtitle, top, height, rows, left=3, width=94):
        box = c.card(name, left, width, top, height, CARD, EDGE)
        c.text(left + 3, width - 6, top + 8, title, size=16, colour=INK)
        c.text(left + 3, width - 6, top + 31, subtitle, size=13, colour=NEUTRAL)
        for i, (label, value) in enumerate(rows):
            c.text(left + 3, width * 0.58, top + 56 + i * 23, label, size=13)
            c.value(left + width * 0.57, width * 0.39, top + 56 + i * 23, value, size=14, coloured=True)
        return box

    field("uplink", 'max(convergent_wan_upstream_up{node="wan"})', mappings=UP)
    field("wan", 'max(up{job="node",node="wan"})', mappings=UP)
    field("overlap", 'max(convergent_wan_upstream_overlap{node="wan"})', mappings=vmap([(0, "clear", NEUTRAL), (1, "REFUSED", AMBER)]))
    radio = card("radio", "Radio / wired uplink", "Owned by wan · radio details not collected", 6, 84, [("upstream lease", "uplink")])
    wan = card("wan_box", "wan", "Alpine VM · the only NAT", 116, 107, [("exporter", "wan"), ("reserved overlap", "overlap")])
    Canvas.link(radio, wan)
    fws = []
    for i, n in enumerate(("fw1", "fw2")):
        field(n, 'min(convergent_carp_state{node="%s"})' % n, mappings=CARP)
        field(n + "_max", 'max(convergent_carp_state{node="%s"})' % n, mappings=CARP)
        field(n + "_pf", 'max(convergent_pf_enabled{node="%s"})' % n, mappings=UP)
        box = card(n + "_box", n, "OpenBSD · CARP + pf", 252, 130,
                   [("lowest role", n), ("highest role", n + "_max"), ("pf", n + "_pf")], 3 + i * 49, 45)
        Canvas.link(wan, box, sx=-0.5 if i == 0 else 0.5, colour_field=n)
        fws.append(box)
    c.text(3, 94, 397, "Six CARP gateways · mixed roles need attention", size=13, align="center")
    field("host", 'max(up{job="node",node="host"})', mappings=UP)
    field("cpu", HOST_CPU.replace("$__rate_interval", "2m"), unit="percent", decimals=0)
    field("ram", HOST_RAM, unit="percent", decimals=0)
    host = card("host_box", "host", "Incus host · host segment only", 438, 130,
                [("exporter", "host"), ("CPU busy", "cpu"), ("RAM used", "ram")])
    for i, fw in enumerate(fws):
        Canvas.link(fw, host, tx=-0.5 if i == 0 else 0.5, colour_field=("fw1", "fw2")[i])
    field("svc", '(count(incus_cpu_seconds_total{project="default",name="svc"}) > bool 0) and on() (max(up{job="incus"}) == 1)', mappings=STATE)
    svc = card("svc_box", "svc", "Metrics · logs · alerts · Grafana", 596, 84, [("Incus state", "svc")])
    Canvas.link(host, svc)
    c.text(3, 94, 696, "Downstream segments route through CARP", size=13, align="center")
    browser_rows = []
    for n in ("web", "admin", "tmp", "portal"):
        field(n, '((count(incus_cpu_seconds_total{project="default",name="%s"}) > bool 0) or on() vector(0)) and on() (max(up{job="incus"}) == 1)' % n,
              mappings=vmap([(0, "closed", NEUTRAL), (1, "RUNNING", CYAN)]))
        browser_rows.append((n, n))
    browsers = card("browsers", "Browsers", "web / tmp / portal · web segment; admin · admin", 734, 153, browser_rows)
    Canvas.link(host, browsers, sx=0.9, tx=0.9)
    p = page.add("canvas", "The network path", grid(0, 0, 7, SCREEN_ROWS),
                 "Source: node up, Incus CPU series, fw-facts CARP/pf and wan-check upstream lease. "
                 "This is a logical path, not host forwarding: each downstream segment uses a CARP gateway. "
                 "Both roles agree when all six interfaces have the same role; Network shows each segment. "
                 "UP on wan means an accepted lease, not a Wi-Fi association or an Internet probe.",
                 c.targets, {"noValue": "UNKNOWN"}, c.overrides,
                 {"inlineEditing": False, "showAdvancedTypes": True, "panZoom": False,
                  "infinitePan": False, "zoomToContent": False,
                  "tooltip": {"mode": "none", "disableForOneClick": True},
                  "root": {"type": "frame", "name": "path", "elements": c.elements,
                           "background": {"color": {"fixed": "transparent"}},
                           "border": {"color": {"fixed": "transparent"}, "width": 0},
                           "constraint": {"horizontal": "left", "vertical": "top"},
                           "placement": {"left": 0, "top": 0, "width": 100, "height": 100}}})
    p["transparent"] = True
    return p


def generate():
    p = Page()
    path(p)
    p.stat("", [target('count(ALERTS{alertstate="firing"}) or on() vector(0)', "firing alerts")],
           grid(7, 0, 5, 2), "Source: vmalert ALERTS, firing only; zero means no firing series.", th=BAD)
    q = target(ERRORS + ' AND _time:1h | stats count() as errors', "error / warning lines · 1 h", ds=LOGS, queryType="stats")
    p.stat("", [q], grid(12, 0, 6, 2),
           "Source: VictoriaLogs syslog severity 0–4, last hour; routine audit records and kernel stack continuations excluded. Lines, not incidents.", th=BAD)["datasource"] = LOGS
    p.stat("", [target('min(cv_collector_success)', "collectors", instant=True),
                target('max(time() - node_textfile_mtime_seconds{file=~".*(audit|convergent_fw|wan)[.]prom"})', "live facts age")],
           grid(18, 0, 6, 2), "Source: tools/facts collector success and node_exporter textfile mtimes. Live facts update each minute; amber after three minutes. Daily/boot facts are on Security.",
           overrides=[ov("collectors", mappings=OK), ov("live facts age", unit="s", thresholds=thresholds(("text", None), (AMBER, 180)))])
    p.table("Active alerts · now", [target('max by (alertname,node,severity) (ALERTS{alertstate="firing"})', optional="No firing alerts is normal.")],
            grid(7, 2, 17, 5), ["alertname", "node", "severity"], ["state"],
            "Source: vmalert ALERTS instant query; one row per alert name, node and severity. Empty means no alerts firing.",
            [ov("state", mappings=vmap([(1, "FIRING", AMBER)]))])
    for title, expr, gp, unit, maximum, optional in [
            ("Host CPU · busy", HOST_CPU, grid(7, 7, 8, 5), "percent", 100, ""),
            ("Host RAM · used", HOST_RAM, grid(15, 7, 9, 5), "percent", 100, ""),
            ("State disk · /var", STATE_DISK, grid(7, 12, 6, 5), "percent", 100, ""),
            ("Battery · charge", 'node_power_supply_capacity{node="host"}', grid(13, 12, 5, 5), "percent", 100, "No battery in QEMU."),
            ("Host temperature", 'node_hwmon_temp_celsius{node="host"}', grid(18, 12, 6, 5), "celsius", None, "Hardware sensors are absent in QEMU.")]:
        p.timeseries(title, [target(expr, "{{chip}} {{sensor}}" if unit == "celsius" else title, optional=optional)],
                     gp, unit, "Source: host node_exporter CPU, meminfo, filesystem, power_supply or hwmon collector, as named by the query. Hardware-only series may be absent.", max_=maximum)
    guests_table(p, grid(7, 17, 17, 7), compact=True)
    p.logs("Recent actionable logs", ACTIONABLE, grid(7, 24, 17, 7),
           "Source: VictoriaLogs TLS syslog from host, wan, fw1/fw2. Warnings/errors, AppArmor denials, USB blocks, faillock, sudo and firewall changes. Routine EXECVE and kernel stack continuation records excluded; all records remain in Explore.")
    p.footer(SCREEN_ROWS, "Wi-Fi SSID, signal, security and PMF; Internet reachability probes; pf passed/blocked counters by label; configured VM memory limits; browser internals. Hardware sensors and battery show a dash when absent. The path is logical: the host does not forward traffic between segments.")
    return p.dashboard("cv-overview", "Convergent · Overview", "The path, attention, host and guests on one screen.")
