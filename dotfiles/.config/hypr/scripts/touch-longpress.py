#!/usr/bin/env python3
# Turn a still one-finger long press on the touchscreen into a right click via uinput.
import fcntl, glob, json, os, subprocess, select, struct, sys, time

HOLD, SLOP = 0.6, 0.015
EV_SYN, EV_KEY, EV_REL, EV_ABS = 0, 1, 2, 3
BTN_RIGHT = 0x111
SLOT, TRACK, POSX, POSY = 0x2F, 0x39, 0x35, 0x36

def ioctl_in(fd, req, size):
    buf = bytearray(size)
    fcntl.ioctl(fd, req, buf)
    return bytes(buf)

def find_touch():
    for p in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
            name = ioctl_in(fd, 0x80ff4506, 255).split(b"\0")[0].decode()  # EVIOCGNAME
            abs_bits = int.from_bytes(ioctl_in(fd, 0x80084523, 8), "little")  # EVIOCGBIT(EV_ABS)
            if "finger" in name.lower() and abs_bits >> POSX & 1 and abs_bits >> TRACK & 1:
                return fd
        except OSError:
            pass
    sys.exit("no touchscreen found")

def abs_range(fd, code):
    _, mn, mx, *_ = struct.unpack("iiiiii", ioctl_in(fd, 0x80184540 + code, 24))  # EVIOCGABS
    return mx - mn

def make_mouse():
    u = os.open("/dev/uinput", os.O_WRONLY)
    fcntl.ioctl(u, 0x40045564, EV_KEY)
    fcntl.ioctl(u, 0x40045565, BTN_RIGHT)
    fcntl.ioctl(u, 0x40045564, EV_REL)
    fcntl.ioctl(u, 0x40045566, 0)
    fcntl.ioctl(u, 0x40045566, 1)
    os.write(u, struct.pack("80sHHHHi", b"touch-longpress", 3, 1, 1, 1, 0) + bytes(256 * 4))
    fcntl.ioctl(u, 0x5501)
    return u

def emit(u, t, c, v):
    os.write(u, struct.pack("llHHi", 0, 0, t, c, v))

def warp_to_touch():
    m = json.loads(subprocess.check_output(["hyprctl", "-j", "monitors"]))[0]
    w, h = m["width"] / m["scale"], m["height"] / m["scale"]
    nx, ny = pos.get(POSX, 0) / rx, pos.get(POSY, 0) / ry
    t = m["transform"] % 4
    nx, ny = [(nx, ny), (ny, 1 - nx), (1 - nx, 1 - ny), (1 - ny, nx)][t]
    if t % 2:
        w, h = h, w
    x, y = m["x"] + nx * w, m["y"] + ny * h
    subprocess.run(["hyprctl", "dispatch", "hl.dsp.cursor.move({ x = %d, y = %d })" % (x, y)], capture_output=True)
    time.sleep(0.05)

def right_click(u):
    print(time.strftime('%X'), 'right click fired', flush=True)
    for v in (1, 0):
        emit(u, EV_KEY, BTN_RIGHT, v)
        emit(u, EV_SYN, 0, 0)

tfd = find_touch()
rx, ry = abs_range(tfd, POSX), abs_range(tfd, POSY)
mouse = make_mouse()
time.sleep(0.5)

pos = {}
slot, contacts, start, deadline, fired, grabbed = 0, {}, None, None, False, False
while True:
    timeout = None if deadline is None else max(0, deadline - time.monotonic())
    ready, _, _ = select.select([tfd], [], [], timeout)
    if not ready:
        warp_to_touch()
        right_click(mouse)
        fcntl.ioctl(tfd, 0x40044590, 1)
        grabbed = True
        deadline, fired = None, True
        continue
    try:
        data = os.read(tfd, 24 * 64)
    except BlockingIOError:
        continue
    for off in range(0, len(data) - 23, 24):
        _, _, t, c, v = struct.unpack("llHHi", data[off:off + 24])
        if t != EV_ABS:
            continue
        if c == SLOT:
            slot = v
        elif c == TRACK:
            if v < 0:
                contacts.pop(slot, None)
                if grabbed and not contacts:
                    fcntl.ioctl(tfd, 0x40044590, 0)
                    grabbed = False
            else:
                contacts[slot] = True
            if len(contacts) == 1 and v >= 0:
                start, deadline, fired = None, time.monotonic() + HOLD, False
                pos.clear()
            else:
                deadline = None
        elif c in (POSX, POSY) and deadline is not None:
            pos[c] = v
            if start is None and POSX in pos and POSY in pos:
                start = dict(pos)
            elif start and (abs(pos.get(POSX, 0) - start[POSX]) > rx * SLOP or abs(pos.get(POSY, 0) - start[POSY]) > ry * SLOP):
                deadline = None
