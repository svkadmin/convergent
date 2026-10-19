"""Incus now, then the selected instance over time."""
from dashlib import NEUTRAL, SCREEN_ROWS, UP, Page, grid, guests_table, ov, query_var, target, vmap


def generate():
    p = Page()
    p.stat("", [target('max(up{job="incus"})', "Incus scrape"),
                target('count(count by (project,name) (incus_cpu_seconds_total))', "running instances"),
                target('sum(cv_guest_expected_running)', "expected autostart")], grid(0, 0, 24, 2),
           "Source: VictoriaMetrics up, Incus /1.0/metrics CPU presence, tools/check autostart inventory. Expected does not include on-demand browsers.",
           overrides=[ov("Incus scrape", mappings=UP)])
    guests_table(p, grid(0, 2, 24, 9))
    p.row("Selected instance · $project / $name", 11)
    sel = 'project=~"${project:regex}",name=~"${name:regex}"'
    p.timeseries("CPU · Incus cores", [target('sum(rate(incus_cpu_seconds_total{%s,mode=~"user|system"}[$__rate_interval]))' % sel, "cores")],
                 grid(0, 12, 12, 7), "suffix: cores", "Source: Incus user plus system CPU time. For agentless fw/wan VMs this is QEMU vCPU thread overhead, excluding guest execution; it is not guest CPU utilization.")
    p.timeseries("Memory · Incus used / total", [target('max(incus_memory_MemTotal_bytes{%s} - incus_memory_MemAvailable_bytes{%s})' % (sel, sel), "Incus used"),
                                               target('max(incus_memory_MemTotal_bytes{%s})' % sel, "Incus total")],
                 grid(12, 12, 12, 7), "bytes", "Source: Incus MemTotal minus MemAvailable. Agentless fw/wan VMs report QEMU RSS capped at configured RAM, with configured RAM as total; this is not guest memory pressure. Containers use their memory limit.")
    p.timeseries("Network · by interface", [target('8 * rate(incus_network_receive_bytes_total{%s,device!="lo"}[$__rate_interval])' % sel, "in · {{device}}"),
                                             target('8 * rate(incus_network_transmit_bytes_total{%s,device!="lo"}[$__rate_interval])' % sel, "out · {{device}}")],
                 grid(0, 19, 12, 7), "bps", "Source: Incus network counters for the selected instance, excluding loopback.")
    p.timeseries("Disk · block throughput", [target('sum(rate(incus_disk_read_bytes_total{%s}[$__rate_interval]))' % sel, "read"),
                                               target('sum(rate(incus_disk_written_bytes_total{%s}[$__rate_interval]))' % sel, "written")],
                 grid(12, 19, 12, 7), "Bps", "Source: Incus disk counters. Throughput is block I/O, not filesystem fill; cache hits need no block read.")
    p.table("Expected autostart · now", [target('max by (project,name) (cv_guest_expected_running)')],
            grid(0, 26, 24, 5), ["project", "name"], ["policy"], "Source: tools/check snapshots Incus boot.autostart; one row per expected instance. Compare the live state table above.",
            [ov("policy", mappings=vmap([(1, "EXPECTED RUNNING", NEUTRAL)]))])
    p.footer(SCREEN_ROWS, "Stopped on-demand instances and their resource history are not an inventory source; only checker autostart expectations remain when stopped. Guest filesystem fill, image currency and storage-pool capacity are not collected. OpenBSD and wan have no Incus agent: their CPU is QEMU vCPU thread overhead and memory is capped QEMU RSS, not guest utilization.")
    variables = [query_var("project", "label_values(incus_cpu_seconds_total, project)", "default"),
                 query_var("name", 'label_values(incus_cpu_seconds_total{project=~"${project:regex}"}, name)', "svc")]
    return p.dashboard("cv-compartments", "Convergent · Guests", "Incus state and resource use; select a running instance.", variables)
