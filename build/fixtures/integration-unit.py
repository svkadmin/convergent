#!/usr/bin/env python3
"""Offline checks of the live packet, VNC and shutdown test helpers."""
import ast
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import types

here = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def module(name):
    spec = importlib.util.spec_from_file_location(name, here / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


binary = here / "pf-l2-bin"
if binary.is_file():
    subprocess.run([str(binary), "--selftest"], check=True)
else:
    with tempfile.TemporaryDirectory() as directory:
        binary = Path(directory) / "pf-l2-bin"
        subprocess.run(["gcc", "-O2", "-static", "-Wall", "-Werror", "-std=c99",
                        str(here / "pf-l2.c"), "-o", str(binary)], check=True)
        subprocess.run([str(binary), "--selftest"], check=True)
remote = module("remmina")
driver = (here.parent / "test").read_text()
start = driver.index("import json, os, re, select, signal, socket, subprocess, time\n")
driver = driver[start:driver.index("\nEOF", start)]
compile(driver, "QEMU driver", "exec")
gate = next(node for node in ast.walk(ast.parse(driver)) if isinstance(node, ast.If)
            and ast.unparse(node.test).startswith("drain_test and powered_off"))
code = compile(ast.Module(body=[gate], type_ignores=[]), "shutdown verdict", "exec")
for result, drain, off, reboot, armed, want in (
        (0, 0, True, False, 1, "guests-0"), (1, 0, True, False, 1, "guests-1"),
        (None, 0, True, False, 1, "guests-1"), (0, None, True, False, 1, "guests-1"),
        (0, 1, True, False, 1, "guests-1"), (0, 0, False, False, 1, "stopped"),
        (0, 0, True, True, 1, "stopped"), (0, 0, True, False, None, "stopped")):
    values = dict(drain_test=True, powered_off=off, rebooted=reboot, drain_started=armed,
                  result=result, drain_result=drain, goal="guests", ended="stopped",
                  time=types.SimpleNamespace(monotonic=lambda: 10))
    with contextlib.redirect_stdout(io.StringIO()):
        exec(code, values)
    assert values["ended"] == want
print("CV-SHUTDOWN offline QEMU verdicts passed")
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    for leak in (False, True):
        server, client = socket.socketpair()
        client.settimeout(5)
        failures = []

        def serve():
            try:
                remote.vnc(server, work)
            except Exception as error:
                failures.append(error)
            finally:
                server.close()

        thread = threading.Thread(target=serve)
        thread.start()
        assert remote.read(client, 12) == b"RFB 003.008\n"
        client.sendall(b"RFB 003.008\n")
        assert remote.read(client, 2) == b"\x01\x01"
        client.sendall(b"\x01")
        assert remote.read(client, 4) == bytes(4)
        client.sendall(b"\x01")
        header = remote.read(client, 24)
        assert struct.unpack_from("!HH", header) == (640, 480)
        remote.read(client, struct.unpack_from("!I", header, 20)[0])
        client.sendall(struct.pack("!BBH", 2, 0, 1) + bytes(4))
        client.sendall(struct.pack("!BBHHHH", 3, 0, 0, 0, 640, 480))
        assert remote.read(client, 16) == struct.pack("!BBHHHHHi", 0, 0, 1, 0, 0, 640, 480, 0)
        assert len(remote.read(client, 640 * 480 * 4)) == 640 * 480 * 4
        (work / "send").touch()
        assert remote.read(client, 8) == struct.pack("!B3xI", 3, 19)
        assert remote.read(client, 19) == b"cv-remote-clipboard"
        text = b"cv-host-clipboard" if leak else b"cv-remmina-clipboard"
        client.sendall(struct.pack("!B3xI", 6, len(text)) + text)
        thread.join(5)
        assert not thread.is_alive()
        client.close()
        if leak:
            assert len(failures) == 1 and "host clipboard leaked" in str(failures[0])
            assert not (work / "received").exists()
        else:
            assert not failures, failures
            assert (work / "received").exists()
        for path in work.iterdir():
            path.unlink()
    print("CV-REMOTE offline VNC round-trip and host-leak rejection passed")

    source = (here / "shutdown").read_text()
    program = source.split("awk -v check=\"$release/shutdown-test\" '\n", 1)[1].split("' \"$state/original\"", 1)[0]
    original = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "--without-jq" else here.parent.parent / "rootfs/usr/lib/convergent/incus/shutdown"
    production = original.read_text()
    for fault in ("none", "missing", "duplicate"):
        sample = production
        if fault == "missing":
            sample = sample.replace('    note "stopping $project/$node"', "")
        if fault == "duplicate":
            sample += '\nnote "stopping $project/$node"\n'
        result = subprocess.run(["awk", "-v", "check=/test/check", program], input=sample, text=True, capture_output=True)
        assert (result.returncode == 0) == (fault == "none"), result.stderr
        if fault == "none":
            assert result.stdout.count('sh /test/check observe "$project" "$node"') == 1
            assert result.stdout.count('sh /test/check finish "$result"') == 1
            subprocess.run(["sh", "-n"], input=result.stdout, text=True, check=True)
    program = (here / "remmina-session").read_text().split("base=$(awk '", 1)[1].split("' /etc/convergent/segments", 1)[0]
    result = subprocess.check_output(["awk", program], input="carp6 7 vlan320 coding-a 100.80.40.0/26 100.80.40.62 dev\n", text=True)
    assert result.strip() == "100.80.40"
    print("CV-SHUTDOWN offline instrumentation and configured work prefix passed")

    if "--without-jq" in sys.argv:
        print("CV-SHUTDOWN SKIP jq (explicit local interpreter-only run)")
        raise SystemExit(0)
    assert shutil.which("jq"), "jq is required for shutdown observer samples"
    names = ["def", "int", "remmina", "tmp-98", "svc", "wan", "fw1", "fw2"]
    phases = dict(zip(names, [1, 1, 1, 1, 2, 3, 4, 4]))
    before = [{"name": name, "status": "Running", "ephemeral": name == "tmp-98", "config": {}}
              for name in names]
    for row in before:
        if row["name"] in ("wan", "fw2"):
            row["config"] = {"boot.autorestart": "false", "user.convergent.autorestart": "true"}
    (work / "before").write_text(json.dumps(before))

    def accepts(stage, rows):
        result = subprocess.run(["jq", "-e", "--argjson", "stage", str(stage), "--slurpfile", "before", str(work / "before"),
                                 "-f", str(here / "shutdown-check.jq")], input=json.dumps(rows), text=True, capture_output=True)
        assert result.returncode in (0, 1), result.stderr
        return result.returncode == 0

    for stage in range(1, 6):
        rows = copy.deepcopy(before)
        for row in rows:
            if phases[row["name"]] < stage:
                row["status"] = "Stopped"
        rows = [row for row in rows if not (row["ephemeral"] and row["status"] == "Stopped")]
        assert accepts(stage, rows)
        for index, row in enumerate(rows):
            phase = phases[row["name"]]
            if phase == stage:
                continue
            bad = copy.deepcopy(rows)
            bad[index]["status"] = "Running" if phase < stage else "Stopped"
            assert not accepts(stage, bad), (stage, row["name"])
            assert not accepts(stage, rows[:index] + rows[index + 1:])
            if phase < stage:
                for key in ("boot.autorestart", "user.convergent.autorestart"):
                    bad = copy.deepcopy(rows)
                    bad[index]["config"][key] = "wrong"
                    assert not accepts(stage, bad), (stage, row["name"], key)
        if stage > 1:
            assert not accepts(stage, rows + [before[3]])
    print("CV-SHUTDOWN offline ordering, ephemeral deletion and retained holds passed")
