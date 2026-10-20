"""Palette, type scale, panel builders and Canvas for Convergent."""
import json
from urllib.parse import quote

PROM = {"type": "prometheus", "uid": "metrics"}
LOGS = {"type": "victoriametrics-logs-datasource", "uid": "logs"}
CYAN, VIOLET, LILAC, GREEN, AMBER, RED, GRAY, NEUTRAL = (
    "#79BCF5", "#BDACF0", "#D9CCFF", "#89C98E", "#EDB873", "#F2495C", "#8A93A3", "#A6B0BC")
STRIP_TITLE, STRIP_VALUE = 13, 20
CARD, EDGE, INK = "#181b1f", "#2c3038", "#d5d9e0"
# 2400x1500 logical pixels at scale 1.2, less bar, browser and Grafana chrome.
SCREEN_ROWS = 31


def grid(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


def vmap(pairs):
    return [{"type": "value", "options": {str(v): {"text": t, "color": c}}} for v, t, c in pairs]


def thresholds(*steps):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in steps]}


TEXT_ONLY = thresholds(("text", None))
BAD = thresholds(("text", None), (AMBER, 1))
USE = thresholds(("text", None), (AMBER, 80), (RED, 95))
OK = vmap([(0, "FAILED", RED), (1, "OK", GREEN)])
UP = vmap([(0, "DOWN", RED), (1, "UP", GREEN)])
STATE = vmap([(0, "STOPPED", RED), (1, "RUNNING", GREEN)])
CARP = vmap([(0, "INIT", RED), (1, "BACKUP", NEUTRAL), (2, "MASTER", CYAN)])
HOST_CPU = '100 * (1 - avg(rate(node_cpu_seconds_total{node="host",mode="idle"}[$__rate_interval])))'
HOST_RAM = '100 * (1 - node_memory_MemAvailable_bytes{node="host"} / node_memory_MemTotal_bytes{node="host"})'
STATE_DISK = '100 * (1 - node_filesystem_avail_bytes{node="host",mountpoint="/var"} / node_filesystem_size_bytes{node="host",mountpoint="/var"})'
GUEST_STATE = ('(count by (project,name) (incus_cpu_seconds_total{job="incus"}) > bool 0 '
               'or max by (project,name) (cv_guest_expected_running) * 0) '
               'and on() (max(up{job="incus"}) == 1)')
INFRA = 'remote_ip:in("100.80.1.10","100.80.2.2","100.80.2.3","100.80.0.10")'
# Keep the first warning of a stack trace; exclude its continuation records and routine audit.
STACK = (r'^([[:space:]]|Call [Tt]race:|CPU: [0-9]|Hardware name:|Modules linked in:|'
         r'RIP:|RSP:|R[A-Z0-9]{2}:|EFLAGS:|FS:|GS:|CS:|CR[0-9]:|PKRU:|Code:|'
         r'---\[ end trace|</?(TASK|IRQ|NMI)>|[? ]*[a-zA-Z0-9_]+\+0x[0-9a-f]+/0x)')
QUIET = ('NOT _msg:~"(?i)(type=(EXECVE|SYSCALL|CWD|PATH|PROCTITLE)|type=13(00|02|07|09|27))" '
         'AND NOT (app_name:="kernel" AND _msg:~' + json.dumps(STACK) + ')')
ERRORS = INFRA + ' AND (severity:in("0","1","2","3","4") OR level:in("emerg","alert","crit","error","err","warn","warning")) AND ' + QUIET
SECURITY = (INFRA + ' AND (_msg:~' + json.dumps('apparmor="DENIED"|pam_faillock|authentication failure|Failed password') + ' '
            'OR (app_name:="usbguard" AND _msg:~"(?i)block|reject|denied") '
            'OR (app_name:="sudo" AND _msg:~"COMMAND=|incorrect password|not in the sudoers")) AND ' + QUIET)
CARP_CHANGES = INFRA + ' AND hostname:~"^fw[12]$" AND _msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> (MASTER|BACKUP|INIT)"'
FW_CHANGES = (INFRA + ' AND hostname:~"^fw[12]$" AND '
              '(_msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> (MASTER|BACKUP|INIT)" OR app_name:="ifstated" OR app_name:="pfctl") AND ' + QUIET)
SECURITY_EVENTS = (INFRA + ' AND ('
                   '(app_name:in("greetd","tuigreet","login","su","sudo","sshd") AND '
                   '_msg:~"(?i)session opened|successful su|accepted (password|publickey)|authentication (failure|failed|error|success)|failed (password|publickey|login|su)|pam_authenticate|pam_faillock|incorrect password|not in the sudoers|COMMAND=") '
                   'OR (_msg:~"type=(USER_AUTH|USER_LOGIN|USER_START|1100|1105|1112) " AND '
                   '_msg:~' + json.dumps(r'exe="[^"]*/(greetd|tuigreet|login|su|sudo|sshd)"') + ') '
                   'OR _msg:~' + json.dumps('apparmor="(DENIED|ALLOWED)"|type=(USER_DEVICE|1137) ') + ' '
                   'OR (app_name:~"^usbguard(-daemon)?$" AND _msg:~"(?i)allow|block|reject|denied") '
                   'OR app_name:in("slot","fetch-release","guests","convergent-watchdog","sys-firewall") '
                   'OR (hostname:~"^fw[12]$" AND _msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> MASTER")) AND ' + QUIET +
                   ' | replace (' + json.dumps('apparmor="ALLOWED"') + ', ' +
                   json.dumps('apparmor="ALLOWED" [complain]') + ')')
ACTIONABLE = '(' + ERRORS + ') OR (' + SECURITY + ') OR (' + FW_CHANGES + ')'


def ov(name, **props):
    fields = []
    for k, v in props.items():
        if k == "color":
            k, v = "color", {"mode": "fixed", "fixedColor": v}
        if k == "width":
            k = "custom.width"
        fields.append({"id": k, "value": v})
    return {"matcher": {"id": "byName", "options": name}, "properties": fields}


def target(expr, legend=None, ref="A", instant=False, optional="", ds=PROM, **extra):
    t = {"refId": ref, "expr": expr, "datasource": ds, "editorMode": "code"}
    if ds == PROM:
        t.update(instant=instant, range=not instant)
    if legend:
        t["legendFormat"] = legend
    if optional:
        t["cvOptional"] = optional
    t.update(extra)
    return t


def refs(targets):
    for i, t in enumerate(targets):
        if t["refId"] == "A":
            t["refId"] = chr(65 + i)
    return targets


def explore(ds, expr, query_type=None):
    q = {"refId": "A", "expr": expr, "datasource": ds}
    if query_type:
        q["queryType"] = query_type
    return "/explore?left=" + quote(json.dumps({"datasource": ds["uid"], "queries": [q],
                                               "range": {"from": "now-1h", "to": "now"}}, separators=(",", ":")))


def nav():
    pages = [("Overview", "/d/cv-overview"), ("Network", "/d/cv-network-path"),
             ("Guests", "/d/cv-compartments"), ("Security", "/d/cv-security"),
             ("Explore · all logs", explore(LOGS, "*", "instant"))]
    return [{"title": title, "type": "link", "url": url, "keepTime": True,
             "targetBlank": False, "icon": "dashboard", "asDropdown": False,
             "includeVars": False, "tags": []} for title, url in pages]


class Canvas:
    """Elements in percent horizontally (the panel reflows with the window) and
    in pixels vertically (the panel height is fixed by the grid)."""

    def __init__(self):
        self.elements = []
        self.targets = []
        self.overrides = []

    def field(self, name, expr, **props):
        self.targets.append({"refId": name, "expr": expr, "legendFormat": name,
                             "instant": True, "range": False, "datasource": PROM})
        if props:
            self.overrides.append(ov(name, **props))
        return name

    def _el(self, etype, name, left, width, top, height, cfg, border=None, links=None, background=None):
        e = {"type": etype, "name": name, "config": cfg,
             "constraint": {"horizontal": "scale", "vertical": "top"},
             "placement": {"left": round(left, 3), "right": round(100 - left - width, 3),
                           "top": top, "height": height},
             "background": background or {"color": {"fixed": "transparent"}},
             "border": border or {"color": {"fixed": "transparent"}, "width": 0}}
        if links:
            e["links"] = links
        self.elements.append(e)
        return e

    def text(self, left, width, top, text, size=14, align="left", colour=None, height=20):
        cfg = {"text": {"mode": "fixed", "fixed": text}, "size": size, "align": align, "valign": "middle"}
        if colour:
            cfg["color"] = {"fixed": colour}
        return self._el("text", "t%d" % len(self.elements), left, width, top, height, cfg)

    def value(self, left, width, top, field, size=14, align="right", coloured=False, height=20):
        cfg = {"text": {"mode": "field", "field": field, "fixed": ""}, "size": size,
               "align": align, "valign": "middle"}
        if coloured:
            cfg["color"] = {"field": field, "fixed": GRAY}
        return self._el("metric-value", "v%d" % len(self.elements), left, width, top, height, cfg)

    def box(self, name, col, top, height, links=None):
        return self._el("rectangle", name, col[0], col[1], top, height,
                        {"text": {"mode": "fixed", "fixed": ""}, "align": "center", "valign": "middle"},
                        border={"color": {"fixed": GRAY}, "width": 1, "radius": 0}, links=links)

    def card(self, name, left, width, top, height, fill, edge, radius=10, links=None):
        """A filled, rounded box: what a node is drawn on."""
        return self._el("rectangle", name, left, width, top, height,
                        {"text": {"mode": "fixed", "fixed": ""}, "align": "center", "valign": "middle"},
                        border={"color": {"fixed": edge}, "width": 1, "radius": radius},
                        background={"color": {"fixed": fill}}, links=links)

    def pill(self, left, width, top, field, height=22, size=13, ink="#111217"):
        """A state as a badge: the field's mapped colour behind dark text."""
        cfg = {"text": {"mode": "field", "field": field, "fixed": ""}, "size": size, "align": "center",
               "valign": "middle", "color": {"fixed": ink}}
        return self._el("metric-value", "p%d" % len(self.elements), left, width, top, height, cfg,
                        border={"color": {"fixed": "transparent"}, "width": 0, "radius": height // 2},
                        background={"color": {"field": field, "fixed": GRAY}})

    @staticmethod
    def link(src, target, sx=0.0, tx=0.0, colour_field=None):
        """A line down from src's bottom edge to target's top edge; sx and tx are
        each box's own -1..1 across, chosen so the line is vertical."""
        src.setdefault("connections", []).append({
            "source": {"x": round(sx, 4), "y": -1}, "target": {"x": round(tx, 4), "y": 1},
            "targetName": target["name"], "path": "straight",
            "color": {"field": colour_field, "fixed": GRAY} if colour_field else {"fixed": NEUTRAL},
            "size": {"fixed": 2, "min": 1, "max": 10},
            "direction": {"mode": "fixed", "fixed": "none"}})

    @staticmethod
    def connect(src, src_y, target, target_y=0, colour_field=None):
        """A line from src's right edge to target's left edge; the y values are
        each box's own -1..1 (1 = top), chosen so the line is horizontal."""
        src.setdefault("connections", []).append({
            "source": {"x": 1, "y": round(src_y, 4)}, "target": {"x": -1, "y": round(target_y, 4)},
            "targetName": target["name"], "path": "straight",
            "color": {"field": colour_field, "fixed": GRAY} if colour_field else {"fixed": NEUTRAL},
            "size": {"fixed": 2, "min": 1, "max": 10},
            "direction": {"mode": "fixed", "fixed": "both"}})


class Page:
    def __init__(self):
        self.panels = []

    def add(self, kind, title, gp, description, targets=(), defaults=None, overrides=(), options=None):
        p = {"id": len(self.panels) + 1, "type": kind, "title": title, "gridPos": gp,
             "description": description, "datasource": PROM, "targets": refs(list(targets)),
             "fieldConfig": {"defaults": {"unit": "none", "noValue": "—", "thresholds": TEXT_ONLY,
                                           "color": {"mode": "thresholds"}, **(defaults or {})},
                             "overrides": list(overrides)}, "options": options or {}}
        self.panels.append(p)
        return p

    def stat(self, title, targets, gp, description, unit="none", mappings=(), th=TEXT_ONLY, overrides=()):
        for t in targets:
            if t["datasource"] == PROM:
                t.update(instant=True, range=False)
        return self.add("stat", title, gp, description, targets,
                        {"unit": unit, "mappings": list(mappings), "thresholds": th}, overrides,
                        {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                         "colorMode": "value", "graphMode": "none", "textMode": "value_and_name",
                         "justifyMode": "auto", "orientation": "auto", "wideLayout": True,
                         "text": {"titleSize": STRIP_TITLE, "valueSize": STRIP_VALUE}})

    def timeseries(self, title, targets, gp, unit, description, min_=0, max_=None, overrides=()):
        by_label = any("{{" in t.get("legendFormat", "") for t in targets)
        soft_max = {"celsius": 100, "bytes": 1073741824, "Bps": 1048576, "bps": 1000000,
                    "reqps": 10, "pps": 10, "short": 100, "s": 0.1}.get(unit, 1)
        defaults = {"unit": unit, "min": min_, "max": max_, "color": {"mode": "palette-classic-by-name"} if by_label else
                    {"mode": "fixed", "fixedColor": CYAN},
                    "custom": {"lineWidth": 2, "fillOpacity": 10, "showPoints": "never", "spanNulls": False,
                               "gradientMode": "none", "axisSoftMax": soft_max if max_ is None else max_}}
        overrides = list(overrides)
        if not by_label and len(targets) > 1:
            overrides.append(ov(targets[1].get("legendFormat", "B"), color=VIOLET))
        return self.add("timeseries", title, gp, description, targets, defaults, overrides,
                        {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True,
                                    "calcs": ["last"]}, "tooltip": {"mode": "multi", "sort": "desc"}})

    def table(self, title, targets, gp, labels, columns, description, overrides=()):
        refs(targets)
        rename = {"Value #" + t["refId"]: col for t, col in zip(targets, columns)}
        if len(targets) == 1:
            rename["Value"] = columns[0]
        for t in targets:
            t.update(instant=True, range=False, format="table")
        p = self.add("table", title, gp, description, targets,
                     {"custom": {"align": "auto", "cellOptions": {"type": "color-text"}, "minWidth": 60}},
                     overrides, {"showHeader": True, "cellHeight": "md", "footer": {"show": False}})
        order = labels + ["Value #" + t["refId"] for t in targets]
        p["transformations"] = [{"id": "merge", "options": {}}, {"id": "organize", "options": {
            "excludeByName": {"Time": True, "__name__": True}, "renameByName": rename,
            "includeByName": {k: True for k in labels + list(rename)},
            "indexByName": {name: i for i, name in enumerate(order)}}}]
        return p

    def timeline(self, title, targets, gp, description, mappings=CARP):
        return self.add("state-timeline", title, gp, description, targets,
                        {"mappings": mappings, "min": 0, "max": 2,
                         "custom": {"fillOpacity": 80, "lineWidth": 0, "spanNulls": False}}, options={
                            "showValue": "always", "mergeValues": True, "rowHeight": 0.75,
                            "alignValue": "left", "legend": {"showLegend": False},
                            "tooltip": {"mode": "single"}})

    def logs(self, title, expr, gp, description):
        p = self.add("logs", title, gp, description,
                     [target(expr, ds=LOGS, queryType="instant", maxLines=50)], options={
                         "showTime": True, "showLabels": True, "wrapLogMessage": True,
                         "sortOrder": "Descending", "dedupStrategy": "signature", "enableLogDetails": True,
                         "showCommonLabels": False, "enableInfiniteScrolling": False})
        p["datasource"] = LOGS
        p["links"] = [{"title": "These lines in Explore", "url": explore(LOGS, expr, "instant")},
                      {"title": "All logs in Explore", "url": explore(LOGS, "*", "instant")}]
        return p

    def row(self, title, y):
        self.panels.append({"id": len(self.panels) + 1, "type": "row", "title": title,
                            "collapsed": False, "gridPos": grid(0, y, 24, 1), "panels": []})
        return y + 1

    def footer(self, y, content):
        self.panels.append({"id": len(self.panels) + 1, "type": "text", "title": "Not collected",
                            "description": "Collection boundaries: scrape.yaml, tools/facts, tools/check, fw-facts and wan-check.",
                            "gridPos": grid(0, y, 24, 3), "options": {"mode": "markdown", "content": content}})

    def dashboard(self, uid, title, description, variables=(), refresh="1m"):
        return {"uid": uid, "title": title, "description": description, "tags": ["convergent"],
                "timezone": "browser", "editable": False, "graphTooltip": 1, "refresh": refresh,
                "time": {"from": "now-1h", "to": "now"}, "schemaVersion": 41, "version": 1,
                "panels": self.panels, "templating": {"list": list(variables)}, "links": nav(),
                "annotations": {"list": [{"name": "CARP role changes · toggle", "enable": False, "hide": False,
                                          "iconColor": VIOLET, "datasource": LOGS,
                                          "target": target(CARP_CHANGES, ds=LOGS, queryType="instant", maxLines=100)}]}}


def guests_table(page, gp, compact=False):
    keys = "project,name"
    queries = [GUEST_STATE,
               'sum by (%s) (rate(incus_cpu_seconds_total{mode=~"user|system"}[2m]))' % keys,
               'max by (%s) (incus_memory_MemTotal_bytes - incus_memory_MemAvailable_bytes)' % keys,
               'max by (%s) (incus_memory_MemTotal_bytes)' % keys,
               '100 * max by (%s) (1 - incus_memory_MemAvailable_bytes / incus_memory_MemTotal_bytes)' % keys]
    names = ["state", "Incus cores", "Incus RAM", "RAM total", "RAM %"]
    if not compact:
        for metric, name, factor in [("incus_network_receive_bytes_total", "in", 8),
                                     ("incus_network_transmit_bytes_total", "out", 8),
                                     ("incus_disk_read_bytes_total", "read", 1),
                                     ("incus_disk_written_bytes_total", "written", 1)]:
            sel = '{device!="lo"}' if "network" in metric else ""
            queries.append('%d * sum by (%s) (rate(%s%s[2m]))' % (factor, keys, metric, sel))
            names.append(name)
    return page.table("Instances · now", [target(q) for q in queries], gp, ["project", "name"], names,
                      "Source: Incus /1.0/metrics; tools/check cv_guest_expected_running supplies autostart guests missing now. "
                      "A stopped guest is shown only while the Incus scrape answers. RAM is total minus available; "
                      "agentless fw/wan VMs report capped QEMU RSS against configured RAM. "
                      "Their CPU counts QEMU vCPU thread overhead, excluding guest execution. These are not guest utilization. Rates use two minutes.",
                      [ov("state", mappings=STATE),
                       ov("name", links=[{"title": "This instance", "url": "/d/cv-compartments?var-project=${__data.fields.project}&var-name=${__value.raw}&${__url_time_range}"}]),
                       ov("Incus cores", unit="suffix: cores", decimals=2),
                       ov("Incus RAM", unit="bytes"), ov("RAM total", unit="bytes"),
                       ov("RAM %", unit="percent", min=0, max=100, thresholds=USE),
                       ov("in", unit="bps"), ov("out", unit="bps"), ov("read", unit="Bps"), ov("written", unit="Bps")])


def query_var(name, query, default):
    return {"type": "query", "name": name, "label": name, "datasource": PROM, "definition": query,
            "query": {"query": query, "refId": "variable"}, "refresh": 2, "sort": 1,
            "multi": False, "includeAll": False, "options": [],
            "current": {"selected": True, "text": default, "value": default}}


