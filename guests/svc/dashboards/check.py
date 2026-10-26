#!/usr/bin/env python3
"""Offline dashboard structure and collector regressions; live queries use check-data."""
import ast
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from build import PAGES


def run(args, text=None):
    return subprocess.run(args, input=text, text=True, encoding='utf-8', capture_output=True, check=True).stdout


def main():
    for source in HERE.glob('*.py'):
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    counts = {}
    for module, name in PAGES:
        dashboard = importlib.import_module(module).generate()
        panels = dashboard['panels']
        flat = panels + [c for p in panels for c in p.get('panels',[])]
        assert len({p['id'] for p in flat}) == len(flat)
        assert len(dashboard['links']) == 7
        for i, p in enumerate(panels):
            a = p['gridPos']
            assert a['x'] >= 0 and a['x'] + a['w'] <= 24
            for q in panels[i+1:]:
                b = q['gridPos']
                assert not (a['x'] < b['x']+b['w'] and b['x'] < a['x']+a['w'] and
                            a['y'] < b['y']+b['h'] and b['y'] < a['y']+a['h']), (module,p['title'],q['title'])
            refs = [t['refId'] for t in p.get('targets',[])]
            assert len(refs) == len(set(refs)), (module,p['title'])
            for t in p.get('targets',[]):
                if 'incus_' in t.get('expr','') or 'convergent_unbound_' in t.get('expr',''):
                    assert '[2m]' not in t['expr']
        counts[name] = dict(visible=sum(len(p.get('targets',[])) for p in panels), total=sum(len(p.get('targets',[])) for p in flat))
    from health import RULES, fresh
    assert 'cv_rules_healthy == 1' in RULES and 'remotewrite_errors_total' in RULES
    assert 'node_boot_time_seconds' in fresh('boot',315360000)
    assert '> time() - 180' in fresh('rules',180) and '<= time() + 60' in fresh('rules',180)
    from dashlib import explore, LOGS
    assert '${__from}' in explore(LOGS,'*') and 'now-1h' not in explore(LOGS,'*')
    facts = (REPO/'tools/facts').read_text()
    assert 'daily;' not in facts.split('nts() {',1)[1].split('\n}',1)[0]
    nvme = facts.split('fact_nvme() {',1)[1].split('\n}',1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        absent = nvme.replace('/sys/class/nvme/nvme[0-9]*', work.as_posix()+'/absent/nvme[0-9]*')
        result = run(['sh'], 'm() { printf "%s\\n" "$*"; }; bad() { exit 9; }; fact_nvme() {'+absent+'\n}\nfact_nvme\n')
        assert result.strip() == 'cv_nvme_devices 0', result
        observe = (REPO/'tools/observe').read_text()
        script = observe.split("    awk '\n",1)[1].split("\n    ' \"$@\"",1)[0]
        checker = work/'checker.prom'; pending=work/'pending'
        checker.write_text('cv_guest_expected_running{project="default",name="svc"} 1\ncv_guest_expected_running{project="default",name="int"} 0\n')
        pending.write_text('svc before image\n')
        result = run(['awk',script,str(checker),str(pending)])
        assert 'name="svc"} 2' in result and 'name="int"} 0' in result, result
    scrub = facts.split("awk -F'|' '",1)[1].split("' \"$scrub\"",1)[0]
    data = 'scrub status:1\n'
    for device, start, errors in [(1,1000,0),(2,1100,3)]:
        data += 'fs:%d|t_start:%d|finished:1|canceled:0|uncorrectable_errors:%d|read_errors:0|csum_errors:0|verify_errors:0\n' % (device,start,errors)
    result = run(['awk','-F|',scrub],data)
    assert 'cv_btrfs_scrub_started_seconds 1000' in result and 'cv_btrfs_scrub_errors 3' in result
    broken = 'scrub status:1\nfs:1|t_start:1000|finished:1\n'
    assert subprocess.run(['awk','-F|',scrub],input=broken,text=True,capture_output=True).returncode != 0
    fw = (REPO/'guests/fw/site/usr/local/libexec/convergent/fw-facts').read_text()
    capture = fw.split('capture() {',1)[1].split('\n}',1)[0]
    result = run(['sh'], 'ok=1; data=stale; capture() {'+capture+'\n}\ncapture test false || :\nprintf "ok=%s data=%s\\n" "$ok" "$data"\n')
    assert 'section="test"} 0' in result and 'ok=0 data=\n' in result
    assert fw.count('unbound-control stats_noreset') == 1
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        registry = work/'segments'
        registry.write_text('carp0 1 vio0 host 100.80.1.0/28 100.80.1.1 system\n')
        script = fw.replace('/var/node_exporter/textfile',work.as_posix())
        script = script.replace('/usr/local/libexec/convergent/carp.awk',(REPO/'rootfs/usr/lib/convergent/incus/carp.awk').as_posix())
        script = script.replace('/usr/local/libexec/convergent/interface-bytes.awk',(REPO/'guests/fw/site/usr/local/libexec/convergent/interface-bytes.awk').as_posix())
        script = script.replace('/etc/convergent/segments',registry.as_posix())
        mocks = r'''
ifconfig() {
    case "$*" in
    "") printf 'carp0: flags=41<UP,RUNNING>\n groups: carp wanwatch upgrade\n carp: MASTER carpdev vio0 vhid 1 advskew 0\n' ;;
    "-g "*) echo 'carp: carp demote count 0' ;;
    pfsync0) printf 'pfsync0: flags=41<UP,RUNNING>\n defer: on\n' ;;
    esac
}
sysctl() { echo 1; }
rcctl() { return 0; }
pfctl() {
    case $1 in
    -si) [ "${FAIL_PF:-0}" = 0 ] || return 1; printf 'Status: Enabled\n current entries 12\nCounters\n  match 12\n' ;;
    -sm) echo 'states hard limit 10000' ;;
    -sr) echo pass ;;
    esac
}
sha256() { cat >/dev/null; echo abc; }
route() { echo 'default 100.80.0.10'; }
unbound-control() {
    [ "$1" != status ] || return 0
    printf 'total.num.queries=1\ntotal.num.cachehits=0\nnum.answer.rcode.SERVFAIL=0\nnum.answer.rcode.NXDOMAIN=0\ntotal.recursion.time.avg=0.01\n'
}
stat() { echo 1000; }
netstat() { printf 'Name Mtu Network Address Ibytes Obytes\nvio0 1500 <Link> aa:bb 123 456\n'; }
'''
        # File hashing must not consume the remaining script on stdin.
        mocks = mocks.replace('sha256() { cat >/dev/null; echo abc; }', 'sha256() { [ "$#" != 0 ] || cat >/dev/null; echo abc; }')
        run(['sh'],mocks+script)
        result = (work/'convergent_fw.prom').read_text()
        assert 'convergent_fw_facts_success 1' in result, result
        assert 'convergent_carp_group_present{group="handoff"} 0' in result
        run(['sh'],'FAIL_PF=1\n'+mocks+script)
        result = (work/'convergent_fw.prom').read_text()
        assert 'convergent_fw_section_success{section="pf"} 0' in result
        assert 'convergent_fw_facts_success 0' in result and 'convergent_pf_enabled' not in result
    if shutil.which('jq'):
        import datetime
        now=2000000000
        stamp=datetime.datetime.fromtimestamp(now-30,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        rule=dict(health='ok',lastEvaluation=stamp,alerts=[])
        payload=dict(status='success',data=dict(groups=[dict(name='fast',interval=30,rules=[rule])]))
        args=['jq','-er','--argjson','now',str(now),'-f',str(REPO/'rootfs/usr/lib/convergent/monitoring.jq')]
        assert 'cv_rules_healthy 1' in run(args,json.dumps(payload))
        for change in [dict(health='err'),dict(lastEvaluation='2000-01-01T00:00:00Z'),dict(lastEvaluation='2099-01-01T00:00:00Z')]:
            payload['data']['groups'][0]['rules']=[dict(rule,**change)]
            assert 'cv_rules_healthy 0' in run(args,json.dumps(payload))
        payload['data']['groups']=[]
        assert subprocess.run(args,input=json.dumps(payload),text=True,capture_output=True).returncode != 0
    else:
        print('dashboards: SKIP rule API jq fixtures (jq unavailable)')
    print('dashboards: syntax, layout, missing hardware, failed collector and update journal fixtures passed')
    print('dashboards: query targets '+json.dumps(counts,sort_keys=True))


if __name__ == '__main__':
    main()
