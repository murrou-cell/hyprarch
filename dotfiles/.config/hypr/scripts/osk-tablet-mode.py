#!/usr/bin/env python3
# Run squeekboard only while the laptop is in tablet mode (SW_TABLET_MODE).
import fcntl, glob, os, re, struct, subprocess, sys

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
lp = None
last = None
WB = os.path.expanduser("~/.config/waybar")
RT = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
TOUCH_CSS = "* { font-size: 20px; } #custom-launcher, #custom-close, #clock, #battery, #network, #pulseaudio, #bluetooth, #language, #workspaces button { padding: 0 16px; }"

def restart_waybar(tablet):
    subprocess.run(["pkill", "-x", "waybar"])
    args = ["waybar"]
    if tablet:
        cfg, css = RT + "/waybar-touch.json", RT + "/waybar-touch.css"
        txt = re.sub(r'"height":\s*\d+', '"height": 52', open(WB + "/config").read(), 1)
        txt = txt.replace('"modules-left": [', '"modules-left": [\n"custom/launcher", "custom/close",', 1)
        open(cfg, "w").write(txt)
        open(css, "w").write(open(WB + "/style.css").read() + "\n" + TOUCH_CSS)
        args += ["-c", cfg, "-s", css]
    subprocess.Popen(args, start_new_session=True)

# Squeekboard layouts mirror hyprland kb_layout/kb_variant.
subprocess.run(["gsettings", "set", "org.gnome.desktop.input-sources", "sources", "[('xkb', 'us'), ('xkb', 'bg+phonetic')]"])

def apply(tablet):
    global proc, last, lp
    if tablet != last and (last is not None or tablet):
        restart_waybar(tablet)
    last = tablet
    if lp and lp.poll() is not None:
        lp = None
    if tablet and not lp:
        lp = subprocess.Popen([os.path.dirname(os.path.abspath(__file__)) + "/touch-longpress.py"], start_new_session=True)
    elif not tablet and lp:
        lp.terminate()
        lp.wait()
        lp = None
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
