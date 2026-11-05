#!/usr/bin/env python3
# Restart waybar as the touch bar (landscape or portrait), or plain with "normal".
import os, re, subprocess, sys

mode = sys.argv[1] if len(sys.argv) > 1 else "landscape"
WB = os.path.expanduser("~/.config/waybar")
RT = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
TOUCH_CSS = "* { font-size: %dpx; } #custom-launcher, #custom-close, #clock, #battery, #network, #pulseaudio, #bluetooth, #language, #workspaces button { padding: 0 %dpx; }"
PORTRAIT = {
    "modules-left": '"custom/launcher", "custom/close"',
    "modules-center": '"hyprland/workspaces"',
    "modules-right": '"tray", "pulseaudio", "network", "battery", "hyprland/language", "clock"',
}

subprocess.run(["pkill", "-x", "waybar"])
args = ["waybar"]
if mode != "normal":
    portrait = mode == "portrait"
    txt = re.sub(r'"height":\s*\d+', '"height": 52', open(WB + "/config").read(), count=1)
    if portrait:
        for key, val in PORTRAIT.items():
            txt = re.sub(r'"%s":\s*\[.*?\]' % key, '"%s": [%s]' % (key, val), txt, count=1, flags=re.S)
    else:
        txt = txt.replace('"modules-left": [', '"modules-left": [\n"custom/launcher", "custom/close",', 1)
    cfg, css = RT + "/waybar-touch.json", RT + "/waybar-touch.css"
    open(cfg, "w").write(txt)
    open(css, "w").write(open(WB + "/style.css").read() + "\n" + TOUCH_CSS % ((18, 8) if portrait else (20, 16)))
    args += ["-c", cfg, "-s", css]
subprocess.Popen(args, start_new_session=True)
