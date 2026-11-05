#!/usr/bin/env python3
# Run squeekboard only while the laptop is in tablet mode (SW_TABLET_MODE).
import fcntl, glob, os, struct, subprocess, sys

EV_SW, SW_TABLET_MODE = 0x05, 0x01

def eviocgsw(fd):
    buf = bytearray(8)
    fcntl.ioctl(fd, (2 << 30) | (len(buf) << 16) | (ord("E") << 8) | 0x1B, buf)
    return bool(buf[0] & (1 << SW_TABLET_MODE))

def has_tablet_switch(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        caps = bytearray(8)
        fcntl.ioctl(fd, (2 << 30) | (len(caps) << 16) | (ord("E") << 8) | (0x20 + EV_SW), caps)
        return bool(caps[0] & (1 << SW_TABLET_MODE))
    except OSError:
        return False
    finally:
        os.close(fd)

proc = None
kids = {}
last = None
SELF = os.path.dirname(os.path.abspath(__file__))

def restart_waybar(tablet):
    subprocess.run([SELF + "/waybar-touch.py", "landscape" if tablet else "normal"])

def apply(tablet):
    global proc, last
    prev, last = last, tablet
    for script in ("touch-longpress.py", "tablet-rotate.py"):
        child = kids.get(script)
        if child and child.poll() is not None:
            child = kids[script] = None
        if tablet and not child:
            kids[script] = subprocess.Popen([os.path.join(os.path.dirname(os.path.abspath(__file__)), script)], start_new_session=True)
        elif not tablet and child:
            child.terminate()
            child.wait()
            kids[script] = None
    if tablet != prev and (prev is not None or tablet):
        restart_waybar(tablet)
    if proc and proc.poll() is not None:
        proc = None
    subprocess.run(["gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-keyboard-enabled", "true" if tablet else "false"])
    if tablet and not proc:
        proc = subprocess.Popen(["squeekboard"], start_new_session=True)
    elif not tablet and proc:
        proc.terminate()
        proc.wait()
        proc = None

dev = next((p for p in sorted(glob.glob("/dev/input/event*")) if has_tablet_switch(p)), None)
if not dev:
    sys.exit("no device with SW_TABLET_MODE found (is the user in the input group?)")

fd = os.open(dev, os.O_RDONLY)
apply(eviocgsw(fd))
while True:
    data = os.read(fd, 24 * 16)
    for off in range(0, len(data) - 23, 24):
        _, _, etype, code, value = struct.unpack("llHHi", data[off:off + 24])
        if etype == EV_SW and code == SW_TABLET_MODE:
            apply(bool(value))
