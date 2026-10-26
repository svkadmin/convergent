"""Shared evidence gates: missing or stale data never becomes a healthy zero."""
from dashlib import GREEN, AMBER, RED, vmap

HEALTH = vmap([(0, "OK", GREEN), (1, "DEGRADED", AMBER), (2, "FAILED", RED)])


def fresh(collector, seconds, success=True):
    stamp = 'cv_collector_timestamp_seconds{collector="%s"}' % collector
    gate = '(%s <= time() + 60) and (%s > time() - %d)' % (stamp, stamp, seconds)
    if success:
        gate += ' and (cv_collector_success{collector="%s"} == 1)' % collector
    if collector == 'boot':
        gate += ' and on(node) (%s >= on(node) group_left node_boot_time_seconds{node="host"})' % stamp
    return '(' + gate + ') and on(node) (up{job="node",node="host"} == 1)'


RULES = ('(cv_rules_healthy == 1) and on() (' + fresh('rules', 180) + ') '
         'and on() (up{job="vmalert"} == 1) '
         'and on() (increase(vmalert_remotewrite_errors_total[5m]) == 0)')
FW = ('(convergent_fw_facts_success == 1) and on(node) (up{job="node",node=~"fw1|fw2"} == 1) '
      'and on(node) (convergent_fw_facts_timestamp_seconds > time() - 180) '
      'and on(node) (convergent_fw_facts_timestamp_seconds <= time() + 60)')
WAN = ('(up{job="node",node="wan"} == 1) and on(node) '
       '(node_textfile_mtime_seconds{node="wan",file=~".*wan.prom"} > time() - 180) '
       'and on(node) (node_textfile_mtime_seconds{node="wan",file=~".*wan.prom"} <= time() + 60)')
CHECKER = ('(cv_checker_last_run_seconds > time() - 129600) '
           'and (cv_checker_last_run_seconds <= time() + 60) '
           'and on(node) (up{job="node",node="host"} == 1)')


def verdict(groups, gate):
    selector = 'alertgroup=~"%s"' % groups
    return ('clamp_max((count(cv_alert_active_since_seconds{%s,severity="warning"}) or vector(0)) + '
            '2 * (count(cv_alert_active_since_seconds{%s,severity="critical"}) or vector(0)), 2) '
            'and on() (%s) and on() (%s)') % (selector, selector, RULES, gate)


def known(panel):
    panel['fieldConfig']['defaults']['noValue'] = 'UNKNOWN'
    return panel
