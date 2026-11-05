#!/usr/bin/env python3
# Rotate the screen and touchscreen from the accelerometer (iio-sensor-proxy); reset on exit.
import json, os, signal, subprocess, sys

TRANSFORM = {"normal": 0, "right-up": 3, "bottom-up": 2, "left-up": 1}

def set_transform(name, n):
    subprocess.run(["hyprctl", "eval", 'hl.monitor({ output = "%s", mode = "preferred", position = "auto", scale = "auto", transform = %d })' % (name, n)], capture_output=True)
    subprocess.run(["hyprctl", "eval", "hl.config({ input = { touchdevice = { transform = %d } } })" % n], capture_output=True)

def set_bar(portrait):
    subprocess.run([os.path.dirname(os.path.abspath(__file__)) + "/waybar-touch.py", "portrait" if portrait else "landscape"])

mon = json.loads(subprocess.check_output(["hyprctl", "-j", "monitors"]))[0]["name"]
sensor = subprocess.Popen(["stdbuf", "-oL", "monitor-sensor", "--accel"], stdout=subprocess.PIPE, text=True)

def stop(*_):
    sensor.terminate()
    set_transform(mon, 0)
    sys.exit(0)

signal.signal(signal.SIGTERM, stop)
portrait = False
for line in sensor.stdout:
    if "orientation changed:" in line:
        o = line.rsplit(":", 1)[1].strip()
        if o in TRANSFORM:
            set_transform(mon, TRANSFORM[o])
            if (TRANSFORM[o] % 2 == 1) != portrait:
                portrait = not portrait
                set_bar(portrait)
stop()
