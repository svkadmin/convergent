#!/usr/bin/env python3
"""Generate the provisioned dashboards, or check them for drift."""
import argparse
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
# -I omits the script directory; import only these trusted sibling generators.
sys.path.insert(0, str(HERE))
PAGES = (("overview", "overview"), ("network", "network-path"),
         ("guests", "compartments"), ("host", "host"),
         ("security", "security"), ("monitoring", "monitoring"))
OUTPUT = HERE.parent / "rootfs/usr/share/grafana/dashboards"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated JSON differs")
    args = parser.parse_args()
    drift = False
    for module, name in PAGES:
        dashboard = importlib.import_module(module).generate()
        data = (json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        path = OUTPUT / (name + ".json")
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                print("dashboards: drift: " + path.name)
                drift = True
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            print("dashboards: %s: %d panels" % (path.name, len(dashboard["panels"])))
    if drift:
        print("dashboards: regenerate with python3 -I guests/svc/dashboards/build.py")
    return int(drift)


if __name__ == "__main__":
    sys.exit(main())
