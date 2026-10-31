#!/usr/bin/env python3
"""Disposable VNC clipboard peer and Wayland keyboard for the real Remmina session."""
import array
import ctypes
import os
from pathlib import Path
import select
import socket
import struct
import sys
import time


def read(sock, length):
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise EOFError("peer closed")
        data += chunk
    return data


def vnc(sock, state):
    sock.settimeout(10)
    sock.sendall(b"RFB 003.008\n")
    assert read(sock, 12) == b"RFB 003.008\n"
    sock.sendall(b"\x01\x01")
    assert read(sock, 1) == b"\x01"
    sock.sendall(bytes(4))
    read(sock, 1)
    name = b"CV remote clipboard"
    pixel = struct.pack("!BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    sock.sendall(struct.pack("!HH", 640, 480) + pixel + struct.pack("!I", len(name)) + name)
    sent = False
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if (state / "send").exists() and not sent:
            text = b"cv-remote-clipboard"
            sock.sendall(struct.pack("!B3xI", 3, len(text)) + text)
            sent = True
        if not select.select([sock], [], [], 0.1)[0]:
            continue
        message = read(sock, 1)[0]
        if message == 0:
            read(sock, 3)
            pixel = read(sock, 16)
        elif message == 2:
            _, count = struct.unpack("!BH", read(sock, 3))
            read(sock, count * 4)
        elif message == 3:
            read(sock, 9)
            if not (state / "connected").exists():
                sock.sendall(struct.pack("!BBHHHHHi", 0, 0, 1, 0, 0, 640, 480, 0) + bytes(640 * 480 * (pixel[0] // 8)))
                (state / "connected").touch()
        elif message == 4:
            read(sock, 7)
        elif message == 5:
            read(sock, 5)
        elif message == 6:
            length = struct.unpack("!3xI", read(sock, 7))[0]
            assert length <= 4096, "unexpected clipboard length"
            text = read(sock, length)
            assert text != b"cv-host-clipboard", "host clipboard leaked to VNC"
            if text == b"cv-remmina-clipboard":
                assert sent, "clipboard order"
                (state / "received").touch()
                return
        else:
            raise AssertionError(f"unexpected RFB message {message}")
    raise TimeoutError("VNC clipboard")


def keyboard(path, state):
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(10)
    sock.connect(path)

    def send(obj, opcode, payload=b"", fd=None):
        message = struct.pack("=II", obj, ((8 + len(payload)) << 16) | opcode) + payload
        ancillary = [] if fd is None else [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", [fd]))]
        assert sock.sendmsg([message], ancillary) == len(message)

    def string(text):
        data = text.encode() + b"\0"
        return struct.pack("=I", len(data)) + data + bytes((-len(data)) % 4)

    send(1, 1, struct.pack("=I", 2))
    send(1, 0, struct.pack("=I", 3))
    globals_ = {}
    while True:
        obj, header = struct.unpack("=II", read(sock, 8))
        payload = read(sock, (header >> 16) - 8)
        if obj == 1 and header & 65535 == 0:
            raise AssertionError(f"Wayland error: {payload!r}")
        if obj == 2:
            name, length = struct.unpack_from("=II", payload)
            interface = payload[8:8 + length - 1].decode()
            globals_[interface] = name
        if obj == 3:
            break
    for obj, interface in ((4, "wl_seat"), (5, "zwp_virtual_keyboard_manager_v1")):
        send(2, 0, struct.pack("=I", globals_[interface]) + string(interface) + struct.pack("=II", 1, obj))
    send(5, 0, struct.pack("=II", 4, 6))
    xkb = ctypes.CDLL("libxkbcommon.so.0")
    xkb.xkb_context_new.restype = ctypes.c_void_p
    xkb.xkb_keymap_new_from_names.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    xkb.xkb_keymap_new_from_names.restype = ctypes.c_void_p
    xkb.xkb_keymap_get_as_string.argtypes = [ctypes.c_void_p, ctypes.c_int]
    xkb.xkb_keymap_get_as_string.restype = ctypes.c_char_p
    context = xkb.xkb_context_new(0)
    keymap = xkb.xkb_keymap_new_from_names(context, None, 0)
    data = xkb.xkb_keymap_get_as_string(keymap, 1) + b"\0"
    fd = os.memfd_create("cv-keymap")
    os.write(fd, data)
    send(6, 0, struct.pack("=II", 1, len(data)), fd)
    os.close(fd)
    (state / "keyboard-ready").touch()
    until = time.monotonic() + 180
    while not (state / "unlock").exists():
        if time.monotonic() > until:
            raise TimeoutError("unlock dialog")
        time.sleep(0.1)
    for key in (20, 18, 31, 20, 28):  # test, Enter
        for pressed in (1, 0):
            send(6, 1, struct.pack("=III", int(time.monotonic() * 1000) & 0xFFFFFFFF, key, pressed))
        time.sleep(0.05)
    while not (state / "done").exists() and time.monotonic() < until:
        if select.select([sock], [], [], 0.1)[0]:
            obj, header = struct.unpack("=II", read(sock, 8))
            payload = read(sock, (header >> 16) - 8)
            if obj == 1 and header & 65535 == 0:
                raise AssertionError(f"Wayland error: {payload!r}")


if __name__ == "__main__":
    state = Path(sys.argv[3])
    if sys.argv[1] == "keyboard":
        keyboard(sys.argv[2], state)
    elif sys.argv[1] == "vnc":
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((sys.argv[2], 5900))
            listener.listen(1)
            # Remmina connects after its container, keyring unlock and launcher start.
            listener.settimeout(180)
            (state / "listening").touch()
            with listener.accept()[0] as client:
                vnc(client, state)
    else:
        raise SystemExit("unknown fixture mode")
