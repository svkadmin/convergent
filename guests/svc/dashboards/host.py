"""Storage evidence and laptop resource detail."""
from dashlib import BAD, HOST_CPU, HOST_RAM, OK, Page, grid, ov, target
from health import fresh, known


def generate():
    p = Page()
    known(p.stat('State storage', [target('(1 - node_filesystem_readonly{node="host",mountpoint="/var"}) and on(node) (up{job="node",node="host"} == 1)', 'writable'),
                   target('node_filesystem_avail_bytes{node="host",mountpoint="/var"}', 'available'),
                   target('time() - cv_collector_timestamp_seconds{collector="storage"}', 'evidence age')], grid(0, 0, 24, 3),
                   'Exporter reads /var continuously. Btrfs/quotas are read hourly; storage collector success and age must be checked alongside the values.',
                   overrides=[ov('writable', mappings=OK), ov('available', unit='bytes'), ov('evidence age', unit='s')]))
    p.table('Btrfs device errors', [target('cv_btrfs_device_errors_total and on() (' + fresh('storage', 7200) + ')')],
            grid(0, 3, 12, 7), ['kind'], ['errors'], 'Persistent per-filesystem totals from btrfs device stats; never reset by collection.', [ov('errors', thresholds=BAD)])
    p.stat('Scrub evidence', [target('cv_btrfs_scrub_recorded', 'record exists'), target('cv_btrfs_scrub_finished', 'finished without cancellation', optional='No completed scrub record on a fresh install.'),
                   target('time() - cv_btrfs_scrub_started_seconds', 'age since start', optional='No scrub record yet.'),
                   target('cv_btrfs_scrub_errors', 'errors', optional='No scrub record yet.')], grid(12, 3, 12, 7),
           'Read-only parsing of btrfs-progs scrub status for /var UUID. Monthly scheduled scrub; no record is unknown, never a clean result. A running scrub has finished=0.',
           overrides=[ov('age since start', unit='s'), ov('errors', thresholds=BAD)])
    p.table('svc volumes - qgroup headroom', [target('cv_volume_used_bytes'), target('cv_volume_limit_bytes'), target('cv_volume_limit_bytes - cv_volume_used_bytes')],
            grid(0, 10, 24, 7), ['volume'], ['referenced', 'limit', 'headroom'],
            'Actual Btrfs qgroup referenced usage and max_rfer, not global /var free space. Hourly snapshot; stale or failed collector means unknown.',
            [ov(n, unit='bytes') for n in ('referenced', 'limit', 'headroom')])
    p.stat('NVMe capability / collection', [target('cv_nvme_devices', 'devices'), target('cv_collector_success{collector="daily"}', 'daily collection'),
                target('time() - cv_collector_timestamp_seconds{collector="daily"}', 'measurement age')], grid(0, 17, 24, 3),
           'Zero detected devices explicitly means N/A (virtio/QEMU). A detected device missing SMART fields is a failed collection.',
           overrides=[ov('daily collection', mappings=OK), ov('measurement age', unit='s')])
    p.table('NVMe health', [target('cv_nvme_spare_percent', optional='N/A only when cv_nvme_devices=0.'),
                 target('cv_nvme_media_errors_total', optional='N/A only when cv_nvme_devices=0.'),
                 target('cv_nvme_critical_warning', optional='N/A only when cv_nvme_devices=0.')], grid(0, 20, 24, 6),
            ['device'], ['spare %', 'media errors', 'warning bits'], 'Missing on expected hardware is an alert, not N/A.', [ov('media errors', thresholds=BAD), ov('warning bits', thresholds=BAD)])
    p.table('Battery / applied state', [target('node_power_supply_capacity{node="host"}', optional='No battery in QEMU.')],
            grid(0, 26, 8, 6), ['power_supply'], ['charge %'], 'Battery charge; charging state is exposed in node_power_supply_info. Runtime/wear requires hardware-specific energy counters.')
    p.table('Battery status', [target('node_power_supply_info{node="host"}', optional='No power supply hardware in QEMU.')],
            grid(8, 26, 8, 6), ['power_supply', 'status'], ['present'], 'Status from sysfs, including Not charging at the configured charge cap.')
    p.timeseries('Temperatures - sensor detail', [target('node_hwmon_temp_celsius{node="host"}', '{{chip}} {{sensor}}', optional='No hwmon sensors in QEMU.')],
                 grid(16, 26, 8, 6), 'celsius', 'Raw sensor identities retained; no invented package-temperature aggregation.')
    for x, title, expr in [(0, 'CPU busy', HOST_CPU), (12, 'Memory used', HOST_RAM)]:
        p.timeseries(title, [target(expr, title)], grid(x, 32, 12, 7), 'percent', 'Host node_exporter measurements.', max_=100)
    p.timeseries('Host I/O latency', [target('rate(node_disk_read_time_seconds_total{node="host"}[4m]) / rate(node_disk_reads_completed_total{node="host"}[4m])', 'read {{device}}'),
                target('rate(node_disk_write_time_seconds_total{node="host"}[4m]) / rate(node_disk_writes_completed_total{node="host"}[4m])', 'write {{device}}')],
                grid(0, 39, 12, 7), 's', 'Mean block-I/O service time; zero operations yield no useful mean, not an error.')
    p.timeseries('Host memory pressure', [target('rate(node_pressure_memory_waiting_seconds_total{node="host"}[4m])', 'some'),
                target('rate(node_pressure_memory_stalled_seconds_total{node="host"}[4m])', 'full')], grid(12, 39, 12, 7), 'percentunit', 'Native PSI stall seconds per second.')
    p.footer(46, 'Battery runtime, wear, package energy and CPU thermal throttling are not yet collected. No storage mutation is performed by collectors. Inspect /var/lib/convergent/crash for archived pstore evidence; retain until acknowledged.')
    return p.dashboard('cv-host', 'Convergent · Host', 'Writable capacity, Btrfs, NVMe, power, temperature and pressure.')
