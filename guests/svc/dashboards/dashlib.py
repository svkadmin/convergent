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
BAD = thresholds(("text", None), (RED, 1))
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
INFRA = 'remote_ip:in("100.80.1.10","100.80.2.2","100.80.2.3","100.80.0.10","127.0.0.1")'
FIREWALLS = 'remote_ip:in("100.80.2.2","100.80.2.3")'
# Message hostnames are untrusted, including in retained stream labels.
LOG_IDENTITY = (' | copy remote_ip as hostname'
                ' | format if (remote_ip:="100.80.1.10") "host" as hostname'
                ' | format if (remote_ip:="100.80.2.2") "fw1" as hostname'
                ' | format if (remote_ip:="100.80.2.3") "fw2" as hostname'
                ' | format if (remote_ip:="100.80.0.10") "wan" as hostname'
                ' | format if (remote_ip:="127.0.0.1") "svc" as hostname'
                ' | set_stream_fields hostname, app_name')
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
CARP_CHANGES = FIREWALLS + ' AND _msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> (MASTER|BACKUP|INIT)"'
FW_CHANGES = (FIREWALLS + ' AND '
              '(_msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> (MASTER|BACKUP|INIT)" OR app_name:="wan-watch" OR app_name:="pfctl") AND ' + QUIET)
SECURITY_EVENTS = (INFRA + ' AND ('
                   '(app_name:in("greetd","tuigreet","login","su","sudo","sshd") AND '
                   '_msg:~"(?i)session opened|successful su|accepted (password|publickey)|authentication (failure|failed|error|success)|failed (password|publickey|login|su)|pam_authenticate|pam_faillock|incorrect password|not in the sudoers|COMMAND=") '
                   'OR (_msg:~"type=(USER_AUTH|USER_LOGIN|USER_START|1100|1105|1112) " AND '
                   '_msg:~' + json.dumps(r'exe="[^"]*/(greetd|tuigreet|login|su|sudo|sshd)"') + ') '
                   'OR _msg:~' + json.dumps('apparmor="(DENIED|ALLOWED)"|type=(USER_DEVICE|1137) ') + ' '
                   'OR (app_name:~"^usbguard(-daemon)?$" AND _msg:~"(?i)allow|block|reject|denied") '
                   'OR _msg:~"key=.(identity|usb|guestkeys)." OR app_name:in("incus-audit","slot","fetch-release","guests","convergent-watchdog","sys-firewall") '
                   'OR (' + FIREWALLS + ' AND _msg:~"carp[0-9]+:.*(MASTER|BACKUP|INIT) -> MASTER")) AND ' + QUIET +
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
        if any(name in expr for name in ("incus_", "convergent_", "cv_guest_")):
            t["interval"] = "1m"
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
                                               "range": {"from": "${__from}", "to": "${__to}"}}, separators=(",", ":")), safe="$:{}")


def nav():
    pages = [("Overview", "/d/cv-overview"), ("Network", "/d/cv-network-path"),
             ("Guests", "/d/cv-compartments"), ("Host", "/d/cv-host"),
             ("Security", "/d/cv-security"), ("Monitoring", "/d/cv-monitoring"),
             ("Explore · all logs", explore(LOGS, "*", "instant"))]
    return [{"title": title, "type": "link", "url": url, "keepTime": True,
             "targetBlank": False, "icon": "dashboard", "asDropdown": False,
             "includeVars": True, "tags": []} for title, url in pages]


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
        expr += LOG_IDENTITY
        p = self.add("logs", title, gp, description,
                     [target(expr, ds=LOGS, queryType="instant", maxLines=50)], options={
                         "showTime": True, "showLabels": True, "wrapLogMessage": True,
                         "sortOrder": "Descending", "dedupStrategy": "signature", "enableLogDetails": True,
                         "showCommonLabels": False, "enableInfiniteScrolling": False})
        p["datasource"] = LOGS
        p["links"] = [{"title": "These lines in Explore", "url": explore(LOGS, expr, "instant")},
                      {"title": "All logs in Explore", "url": explore(LOGS, "*" + LOG_IDENTITY, "instant")}]
        return p

    def row(self, title, y):
        self.panels.append({"id": len(self.panels) + 1, "type": "row", "title": title,
                            "collapsed": False, "gridPos": grid(0, y, 24, 1), "panels": []})
        return y + 1

    def collapse(self, title, titles):
        children = [p for p in self.panels if p['title'] in titles]
        if not children:
            return
        next_id = max(p['id'] for p in self.panels) + 1
        self.panels = [p for p in self.panels if p not in children]
        index = next((i for i,p in enumerate(self.panels) if p['type'] == 'text'), len(self.panels))
        self.panels.insert(index, {'id': next_id, 'type': 'row', 'title': title,
                                  'collapsed': True, 'gridPos': grid(0,0,24,1), 'panels': children})

    def reflow(self):
        def pack(panels, y):
            x = height = 0
            for panel in panels:
                g = panel['gridPos']
                if x + g['w'] > 24:
                    y += height; x = height = 0
                g['x'], g['y'] = x, y
                x += g['w']; height = max(height, g['h'])
                if panel.get('collapsed'):
                    pack(panel['panels'], y+1)
        pack(self.panels, 0)

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
                                          "target": target(CARP_CHANGES + LOG_IDENTITY, ds=LOGS, queryType="instant", maxLines=100)}]}}


def guest_labels(expr):
    return 'max by(project,name) (label_replace(label_replace(%s, "name", "$1", "node", "(.+)"), "project", "default", "node", ".+"))' % expr


def guests_table(page, gp, compact=False):
    from health import CHECKER, FW, fresh
    policy = 'max by (project,name) (cv_guest_expected_running) and on() (' + CHECKER + ')'
    cpu = guest_labels('100 * (1 - avg by(node) (rate(node_cpu_seconds_total{node=~"fw1|fw2|wan",mode="idle"}[4m])))')
    ram = guest_labels('(100 * (1 - node_memory_MemAvailable_bytes{node="wan"} / node_memory_MemTotal_bytes{node="wan"})) or (100 * (node_memory_active_bytes{node=~"fw1|fw2"} + node_memory_wired_bytes{node=~"fw1|fw2"}) / node_memory_size_bytes{node=~"fw1|fw2"})')
    cpu += ' or (100 * sum by(project,name) (rate(incus_cpu_seconds_total{type="container",mode=~"user|system"}[4m])))'
    ram += ' or (100 * cv_guest_memory_current_bytes / cv_guest_memory_max_bytes)'
    disk = guest_labels('min by(node) (node_filesystem_avail_bytes{node=~"fw1|fw2|wan",fstype!~"tmpfs|devtmpfs"})')
    queries = ['clamp_min((' + policy + ') - (' + GUEST_STATE + '), 0)', policy, GUEST_STATE,
               guest_labels('max by(node) (up{job="node",node=~"fw1|fw2|wan"})'), cpu, ram, disk]
    names = ['missing expected', 'autostart', 'running', 'exporter', 'guest CPU %', 'guest RAM %', 'filesystem free']
    service = guest_labels('(convergent_pf_enabled * convergent_unbound_up) and on(node) (' + FW + ')')
    service += ' or label_replace(label_replace(min(up{node="svc"}), "name", "svc", "", ""), "project", "default", "", "")'
    if compact:
        queries, names = queries[:4], names[:4]
    queries += [service, 'cv_guest_update_phase and on() (' + fresh('guest_updates',180) + ')']
    names += ['services', 'update phase']
    if not compact:
        queries.append(guest_labels('time() - node_boot_time_seconds{node=~"fw1|fw2|wan"}'))
        names.append('VM uptime')
    table = page.table('Guest health matrix', [target(q, optional='No native exporter for containers; resource gaps are N/A, not zero.') if i > 2 else target(q) for i,q in enumerate(queries)],
                      gp, ['project','name'], names,
                      'Inventory includes stopped on-demand guests as of the last checker scan. Blank policy means inventory is stale. VM CPU is measured inside the VM; container CPU is percent of one core (may exceed 100). OpenBSD RAM is active+wired / pages, WAN uses MemAvailable; container RAM includes cache. svc free is its tightest qgroup headroom; other containers have no filesystem exporter. Exporter is scrape health, not a service probe; Network and Monitoring show services. Updates/restarts are in the lifecycle log below.',
                      [ov('missing expected', thresholds=BAD), ov('autostart', mappings=vmap([(0,'ON DEMAND',NEUTRAL),(1,'EXPECTED',CYAN)])),
                       ov('running', mappings=vmap([(0,'STOPPED',NEUTRAL),(1,'RUNNING',GREEN)])),
                       ov('exporter', mappings=UP), ov('services', mappings=OK), ov('VM uptime',unit='s'), ov('update phase',mappings=vmap([(0,'IDLE',NEUTRAL),(1,'PREPARING',AMBER),(2,'PENDING',AMBER),(3,'COMMITTED',CYAN)])), ov('guest CPU %',unit='percent'), ov('guest RAM %',unit='percent'),
                       ov('filesystem free',unit='bytes'),
                       ov('name',links=[{'title':'This instance','url':'/d/cv-compartments?var-project=${__data.fields.project}&var-name=${__value.raw}&${__url_time_range}'}])])
    table['options']['sortBy'] = [{'displayName':'missing expected','desc':True}]
    return table


def query_var(name, query, default):
    return {"type": "query", "name": name, "label": name, "datasource": PROM, "definition": query,
            "query": {"query": query, "refId": "variable"}, "refresh": 2, "sort": 1,
            "multi": False, "includeAll": False, "options": [],
            "current": {"selected": True, "text": default, "value": default}}
