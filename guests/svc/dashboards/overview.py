"""Owner health and actionable failures before resource histories."""
from dashlib import ACTIONABLE, BAD, Page, grid, guests_table, ov, target
from health import CHECKER, FW, HEALTH, RULES, WAN, fresh, known, verdict


def generate():
    p = Page()
    domains = [
        ('Network', 'path|dns', '(count(%s) == 2) and on() (%s) and on() (%s)' % (FW, WAN, fresh('internet', 180) + ' and on() (cv_https_probe_available == 1)'), '/d/cv-network-path'),
        ('Guests', 'compartments', '(up{job="incus"} == 1) and on() (' + CHECKER + ')', '/d/cv-compartments'),
        ('Host', 'hardware-capacity|storage|hardware-slow', fresh('storage', 7200) + ' and on() (' + fresh('daily', 129600) + ')', '/d/cv-host'),
        ('Security / Updates', 'security-time|security-slow|release.*|logs', fresh('boot', 315360000) + ' and on() (' + CHECKER + ') and on() (' + fresh('nts', 180) + ')', '/d/cv-security'),
        ('Monitoring', 'monitoring|log-health', '(count(up{job="monitoring"} == 1) == 3) and on() (' + fresh('cgroups', 180) + ')', '/d/cv-monitoring')]
    for i, (name, groups, gate, url) in enumerate(domains):
        value = verdict(groups, gate)
        if name == 'Security / Updates':
            release = '(max(cv_release_check_success) == 1) and (max(cv_release_check_timestamp_seconds) > time() - 172800) and (max(cv_release_check_timestamp_seconds) <= time() + 60) and (count(cv_release_status_verified == 1) == 2) and (min(cv_release_status_generated_seconds) > time() - 172800)'
            # Release status comes only from a manual check: stale or missing degrades, never blanks.
            value = 'clamp_max((' + value + ') + on() (2 * (count(cv_alert_active_since_seconds{alertname="CheckerFailed",severity="critical"}) or vector(0))) + on() ((max(cv_release_advisories) > bool 0) or vector(0)) + on() ((count(' + release + ') or vector(0)) == bool 0), 2)'
        panel = known(p.stat(name, [target(value, name)], grid(i * 5, 0, 4 if i == 4 else 5, 3),
                       'OK requires recent successful evidence and healthy rule evaluation. Failed collection is UNKNOWN; open the domain for source age and failures.', mappings=HEALTH))
        panel['links'] = [{'title': name, 'url': url + '?${__url_time_range}'}]
    known(p.stat('Firing alerts', [target('(count(cv_alert_active_since_seconds) or vector(0)) and on() (' + RULES + ')', 'firing')],
                 grid(0, 3, 5, 3), 'Includes log and metric rules. Zero requires all rule evaluations healthy and recent, a fresh API observation and no recent remote-write errors.', th=BAD))
    p.stat('Evidence age', [target('time() - cv_collector_timestamp_seconds{collector=~"rules|internet"}', '{{collector}}'),
                           target('time() - cv_checker_last_run_seconds', 'checker')], grid(5, 3, 19, 3),
           'Seconds since measurement, not scrape. Rules/Internet expire after 3m; checker after 36h.', unit='s')
    alerts = p.table('Active alerts - explanations', [target('(time() - cv_alert_active_since_seconds) and on() (' + RULES + ')',
                     optional='Empty only means healthy when the firing-alert count is zero.')], grid(0, 6, 24, 8),
                    ['severity', 'alertname', 'exported_node', 'project', 'name', 'object', 'summary', 'dashboard'], ['active for'],
                    'vmalert API summary and onset; duration includes pending time. Dashboard links retain time. An unhealthy evaluator hides the table; Monitoring has evaluation errors.',
                    [ov('active for', unit='s'), ov('alertname', links=[{'title': 'Evidence / recovery', 'url': '${__data.fields.dashboard}?${__url_time_range}&var-project=${__data.fields.project}&var-name=${__data.fields.name}'}])])
    alerts['options']['sortBy'] = [{'displayName': 'severity', 'desc': False}]
    guests_table(p, grid(0, 14, 24, 8), compact=True)
    p.logs('Recent actionable logs', ACTIONABLE, grid(0, 22, 24, 8),
           'Warnings, security denials and firewall transitions; raw evidence, not incident counts. Open the domain pages for context.')
    p.footer(30, 'DNS is tested from the host; HTTPS to the same named destination is available only while def already runs. Network is UNKNOWN without HTTPS evidence. Self-heal remains independent of monitoring. Hardware absence, collection failure and stale evidence are distinct on Host and Monitoring.')
    return p.dashboard('cv-overview', 'Convergent · Overview', 'Owner health, actionable alerts and guest state.')
