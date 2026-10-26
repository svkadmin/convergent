"""Inventory and measured guest pressure; Incus accounting stays secondary."""
from dashlib import Page, grid, guests_table, ov, query_var, target


def generate():
    p = Page()
    guests_table(p, grid(0, 0, 24, 9))
    p.stat('Inventory age', [target('time() - cv_checker_last_run_seconds', 'checker / policy age')],
           grid(0, 9, 24, 2), 'Autostart/on-demand inventory updates with the checker; unknown after 36h. Historical series retain stopped instance selectors.', unit='s')
    sel = 'project=~"${project:regex}",name=~"${name:regex}"'
    p.logs('Selected instance - lifecycle / updates', 'remote_ip:="100.80.1.10" app_name:in("incus-audit","guests","sys-firewall") _msg:~"${name:regex}"',
           grid(0, 11, 24, 8), 'Incus lifecycle forwarding already exists. Guest update start, failure, deferred and success messages share this view. Match is a name search; inspect the resource field for the exact instance.')
    p.timeseries('Native VM CPU', [target('100 * (1 - avg by(node) (rate(node_cpu_seconds_total{node=~"${name:regex}",mode="idle"}[4m])))', '{{node}}', optional='Native exporter exists only for fw1/fw2/wan; stopped guests have no fresh data.')],
                 grid(0, 19, 12, 7), 'percent', 'Inside-VM CPU idle, including guest execution. Not QEMU thread accounting.', max_=100)
    p.timeseries('Container cgroup memory', [target('cv_guest_memory_current_bytes{%s}' % sel, 'current', optional='Only running svc/browser cgroups.'),
                 target('cv_guest_memory_max_bytes{%s}' % sel, 'hard limit', optional='Only running svc/browser cgroups.')],
                 grid(12, 19, 12, 7), 'bytes', 'Host cgroup memory includes cache; memory.events/PSI on Monitoring distinguish reclaim pressure from OOM.')
    p.table('VM filesystem headroom', [target('node_filesystem_avail_bytes{node=~"${name:regex}",fstype!~"tmpfs|devtmpfs"}', optional='No node exporter in containers; svc volume qgroups are on Host.')],
            grid(0, 26, 24, 6), ['node','mountpoint','device'], ['available'], 'Guest filesystems measured inside fw/wan; host volume quotas can fill independently.', [ov('available',unit='bytes')])
    p.timeseries('Network - selected interface', [target('8 * rate(incus_network_receive_bytes_total{%s,device!="lo"}[4m])' % sel, 'in {{device}}'),
                 target('8 * rate(incus_network_transmit_bytes_total{%s,device!="lo"}[4m])' % sel, 'out {{device}}')],
                 grid(0, 32, 12, 7), 'bps', 'Incus 60s scrape; four-minute window.')
    p.timeseries('Block I/O - selected instance', [target('sum(rate(incus_disk_read_bytes_total{%s}[4m]))' % sel, 'read'),
                 target('sum(rate(incus_disk_written_bytes_total{%s}[4m]))' % sel, 'write')], grid(12, 32, 12, 7), 'Bps', 'Throughput is not filesystem capacity.')
    p.timeseries('Incus host cost - CPU', [target('sum(rate(incus_cpu_seconds_total{%s,mode=~"user|system"}[4m]))' % sel, 'cores')],
                 grid(0, 39, 12, 7), 'suffix: cores', 'Agentless VM QEMU thread accounting excludes guest execution; secondary host cost only.')
    p.timeseries('Incus host cost - memory', [target('max(incus_memory_MemTotal_bytes{%s} - incus_memory_MemAvailable_bytes{%s})' % (sel,sel), 'used')],
                 grid(12, 39, 12, 7), 'bytes', 'QEMU RSS is capped at configured RAM; deliberately no pressure colors.')
    p.footer(46, 'A stopped on-demand guest is normal. Missing expected guests alert only while Incus is reachable. svc has service metrics on Monitoring; guest image currency remains release inventory evidence, not a live package audit.')
    p.collapse('Secondary Incus accounting', ['Incus host cost - CPU', 'Incus host cost - memory'])
    p.reflow()
    variables = [query_var('project', 'label_values({__name__=~"cv_guest_expected_running|incus_cpu_seconds_total"}, project)', 'default'),
                 query_var('name', 'label_values({__name__=~"cv_guest_expected_running|incus_cpu_seconds_total",project=~"${project:regex}"}, name)', 'svc')]
    return p.dashboard('cv-compartments', 'Convergent · Guests', 'Guest health, lifecycle, native pressure and secondary host cost.', variables)
