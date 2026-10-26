"""Signed release evidence from the existing update check."""
from dashlib import AMBER, BAD, UP, grid, ov, target, thresholds


def panels(p, y):
    y = p.row("Release", y)
    p.table("Installed vs latest release", [target('max by (role,release) (cv_release_info)')],
            grid(0, y, 8, 5), ["role", "release"], ["known"],
            "Source: kernel command line and verified channel latest. These identify release inventories, not live guest/package state after partial updates.")
    p.stat("Advisory evidence", [target('max(cv_release_check_success)', "latest check"),
                                target('max by (role) (cv_release_status_verified)', "verified · {{role}}"),
                                target('max by (role) (time() - cv_release_status_generated_seconds)', "scan age · {{role}}"),
                                target('max(time() - cv_release_check_timestamp_seconds)', "check age"),
                                target('max by (role) (cv_release_advisories)', "open · {{role}}")],
           grid(8, y, 16, 5),
           "Only channel-signed, schema-checked status is shown. Missing/invalid/fetch-failed status is unverified, never zero advisories. Scan/check ages warn after two days; cached signatures cannot prove the mirror has the newest scan. Advisory exceptions remain visible. No laptop notification.",
           overrides=[ov("latest check", mappings=UP), ov("check age", unit="s", thresholds=thresholds(("text", None), (AMBER, 172800)))] +
                     [o for role in ("installed", "latest") for o in
                      (ov("verified · " + role, mappings=UP), ov("open · " + role, thresholds=BAD),
                       ov("scan age · " + role, unit="s", thresholds=thresholds(("text", None), (AMBER, 172800))))])
    queries = [target('max by (target,package,%s) (label_replace(cv_release_package_info{role="%s"}, "%s", "$1", "version", "(.+)"))' %
                      (role, role, role)) for role in ("installed", "latest")]
    table = p.table("Key package versions · release inventories", queries, grid(0, y + 5, 24, 6),
                    ["target", "package", "installed", "latest"], ["installed present", "latest present"],
                    "Source: signed status generated from retained host packages and signed guest inventories/manifests. Versions are release contents, not a live package audit. Missing packages/old status schemas leave a blank cell.")
    table["transformations"][-1]["options"]["includeByName"] = {k: True for k in ("target", "package", "installed", "latest")}
    p.table("Open advisories · installed and latest", [target('max by (role,release,target,package,installed_version,advisory,severity,fixed_in) (cv_release_advisory_info)')],
            grid(0, y + 11, 24, 9), ["role", "release", "target", "package", "installed_version", "advisory", "severity", "fixed_in"], ["open"],
            "Source: Gentoo GLSA, Alpine secdb and OpenBSD errata, re-scanned daily by the operator. fixed_in=none and severity=unknown mean upstream supplied no value. No rows means no findings only when both status verification and freshness above are healthy. Source coverage is the existing advisory gate, not every possible CVE feed.")
    for panel in p.panels:
        if panel["gridPos"]["y"] >= y:
            for query in panel.get("targets", []):
                query["cvOptional"] = "No verified online status yet, no findings, or package absent from this inventory; read evidence freshness."
    return y + 20
