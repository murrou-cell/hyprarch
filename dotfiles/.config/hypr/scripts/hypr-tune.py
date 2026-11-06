#!/usr/bin/env python3
"""Local web UI that tunes the running Hyprland live, saves named profiles and arranges monitors."""
import http.server, json, os, re, shutil, socket, subprocess, sys, threading, time, webbrowser

PORT = 38800
HOST = "127.0.0.1"
HYPR = os.path.expanduser("~/.config/hypr")
REPO = os.path.expanduser("~/repos/hyprarch/dotfiles/.config/hypr")
NAME_FILE = os.path.join(HYPR, ".profile-name")
MON_FILE = os.path.join(HYPR, "monitors.lua")
PAPER = os.path.join(HYPR, "hyprpaper.conf")
HOME = os.path.expanduser("~")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
FITS = ("cover", "contain", "fill", "tile")
IDLE_SECONDS = 2 * 3600
COLOR8 = re.compile(r"^#[0-9a-f]{8}$")
COLOR6 = re.compile(r"^#[0-9a-f]{6}$")
NAME = re.compile(r"^[a-z0-9-]{1,32}$")
TEXT = re.compile(r"^[a-z0-9,_-]{1,32}$")
OUTPUT = re.compile(r"^[A-Za-z0-9._-]{1,32}$")


def E(k, p, t, l, tab, g, **kw):
    return dict(k=k, p=p, t=t, l=l, tab=tab, g=g, **kw)


# one row per tunable; UI, validation, live apply, Lua output and read-back all derive from it (spec = hand-written Lua)
SCHEMA = [
    E("gi", "general.gaps_in", "int", "gaps_in", "look", "General", lo=0, hi=60, st=1, d=5),
    E("go", "general.gaps_out", "int", "gaps_out", "look", "General", lo=0, hi=100, st=1, d=20),
    E("gw", "general.gaps_workspaces", "int", "gaps_workspaces", "look", "General", lo=0, hi=100, st=1, d=0),
    E("fg", "general.float_gaps", "int", "float_gaps", "look", "General", lo=0, hi=60, st=1, d=0),
    E("bw", "general.border_size", "int", "border_size", "look", "General", lo=0, hi=10, st=1, d=2),
    E("c1", "", "color6", "active border 1", "look", "General", d="#33ccff", spec=1),
    E("c2", "", "color6", "active border 2", "look", "General", d="#00ff99", spec=1),
    E("ang", "", "int", "border angle", "look", "General", lo=0, hi=360, st=5, d=45, spec=1),
    E("ic", "general.col.inactive_border", "color", "inactive border", "look", "General", d="#595959aa"),
    E("rob", "general.resize_on_border", "bool", "resize on border", "look", "General", d=False),
    E("ebg", "general.extend_border_grab_area", "int", "border grab area", "look", "General", lo=0, hi=50, st=1, d=15),
    E("hib", "general.hover_icon_on_border", "bool", "hover icon on border", "look", "General", d=True),
    E("rad", "decoration.rounding", "int", "rounding", "look", "Decoration", lo=0, hi=40, st=1, d=10),
    E("ao", "decoration.active_opacity", "float", "active_opacity", "look", "Decoration", lo=0.1, hi=1, st=0.01, d=1.0),
    E("io", "decoration.inactive_opacity", "float", "inactive_opacity", "look", "Decoration", lo=0.1, hi=1, st=0.01, d=1.0),
    E("dim", "", "float", "dim_inactive", "look", "Decoration", lo=0, hi=0.9, st=0.01, d=0.0, spec=1),
    E("shadow", "decoration.shadow.enabled", "bool", "shadow", "look", "Shadow", d=True),
    E("sr", "decoration.shadow.range", "int", "range", "look", "Shadow", lo=0, hi=100, st=1, d=4),
    E("sp", "decoration.shadow.render_power", "int", "power (1 = strongest)", "look", "Shadow", lo=1, hi=4, st=1, d=3),
    E("ssc", "decoration.shadow.scale", "float", "scale", "look", "Shadow", lo=0.1, hi=1, st=0.05, d=1.0),
    E("sox", "", "int", "offset x", "look", "Shadow", lo=-50, hi=50, st=1, d=0, spec=1),
    E("soy", "", "int", "offset y", "look", "Shadow", lo=-50, hi=50, st=1, d=0, spec=1),
    E("sharp", "decoration.shadow.sharp", "bool", "sharp", "look", "Shadow", d=False),
    E("scol", "decoration.shadow.color", "color", "color", "look", "Shadow", d="#1a1a1aee"),
    E("blur", "decoration.blur.enabled", "bool", "blur", "look", "Blur", d=True),
    E("bs", "decoration.blur.size", "int", "size", "look", "Blur", lo=1, hi=30, st=1, d=3),
    E("bp", "decoration.blur.passes", "int", "passes", "look", "Blur", lo=1, hi=8, st=1, d=1),
    E("vib", "decoration.blur.vibrancy", "float", "vibrancy", "look", "Blur", lo=0, hi=1, st=0.01, d=0.1696),
    E("bn", "decoration.blur.noise", "float", "noise", "look", "Blur", lo=0, hi=1, st=0.01, d=0.0117),
    E("bc", "decoration.blur.contrast", "float", "contrast", "look", "Blur", lo=0, hi=2, st=0.01, d=0.8916),
    E("bb", "decoration.blur.brightness", "float", "brightness", "look", "Blur", lo=0, hi=2, st=0.01, d=1.0),
    E("bsp", "decoration.blur.special", "bool", "special workspace", "look", "Blur", d=False),
    E("bpo", "decoration.blur.popups", "bool", "popups", "look", "Blur", d=False),
    E("bx", "decoration.blur.xray", "bool", "xray", "look", "Blur", d=False),
    E("bio", "decoration.blur.ignore_opacity", "bool", "ignore_opacity", "look", "Blur", d=True),
    E("bno", "decoration.blur.new_optimizations", "bool", "new_optimizations", "look", "Blur", d=True),
    E("layout", "general.layout", "enum", "layout", "layout", "Layout", c=["dwindle", "master"], d="dwindle"),
    E("mfact", "master.mfact", "float", "master size (mfact)", "layout", "Master", lo=0.1, hi=0.9, st=0.01, d=0.55),
    E("mor", "master.orientation", "enum", "orientation", "layout", "Master", c=["left", "right", "top", "bottom", "center"], d="left"),
    E("mnt", "master.new_on_top", "bool", "new window on top", "layout", "Master", d=False),
    E("mns", "master.new_status", "enum", "new window becomes", "layout", "Master", c=["master", "slave", "inherit"], d="master"),
    E("dps", "dwindle.preserve_split", "bool", "preserve_split", "layout", "Dwindle", d=True),
    E("dss", "dwindle.smart_split", "bool", "smart_split", "layout", "Dwindle", d=False),
    E("dfs", "dwindle.force_split", "enum", "force_split", "layout", "Dwindle", c=[0, 1, 2], d=0),
    E("dsr", "dwindle.default_split_ratio", "float", "default_split_ratio", "layout", "Dwindle", lo=0.1, hi=1.9, st=0.05, d=1.0),
    E("anim", "animations.enabled", "bool", "animations enabled", "anim", "Global", d=True),
    E("x0", "", "float", "curve x0", "anim", "Curve", lo=0, hi=1, st=0.01, d=0.23, spec=1),
    E("y0", "", "float", "curve y0", "anim", "Curve", lo=-1, hi=2, st=0.01, d=1.0, spec=1),
    E("x1", "", "float", "curve x1", "anim", "Curve", lo=0, hi=1, st=0.01, d=0.32, spec=1),
    E("y1", "", "float", "curve y1", "anim", "Curve", lo=-1, hi=2, st=0.01, d=1.0, spec=1),
    E("fm", "input.follow_mouse", "enum", "follow_mouse", "input", "Input", c=[0, 1, 2, 3], d=1),
    E("sens", "input.sensitivity", "float", "sensitivity", "input", "Input", lo=-1, hi=1, st=0.05, d=0.0),
    E("ns", "input.natural_scroll", "bool", "natural_scroll (mouse)", "input", "Input", d=False),
    E("rr", "input.repeat_rate", "int", "key repeat rate", "input", "Input", lo=1, hi=100, st=1, d=25),
    E("rd", "input.repeat_delay", "int", "key repeat delay", "input", "Input", lo=100, hi=2000, st=50, d=600),
    E("kbl", "input.kb_layout", "text", "kb_layout", "input", "Input", d="us"),
    E("acc", "input.accel_profile", "enum", "accel_profile", "input", "Input", c=["", "adaptive", "flat"], d=""),
    E("nl", "input.numlock_by_default", "bool", "numlock on start", "input", "Input", d=False),
    E("tns", "input.touchpad.natural_scroll", "bool", "natural_scroll", "input", "Touchpad", d=True),
    E("ttc", "input.touchpad.tap_to_click", "bool", "tap to click", "input", "Touchpad", d=True, ro="input:touchpad:tap-to-click"),
    E("tdt", "input.touchpad.disable_while_typing", "bool", "disable while typing", "input", "Touchpad", d=True),
    E("tsf", "input.touchpad.scroll_factor", "float", "scroll_factor", "input", "Touchpad", lo=0.1, hi=5, st=0.1, d=1.0),
    E("cit", "cursor.inactive_timeout", "float", "hide after idle (s, 0 = never)", "input", "Cursor", lo=0, hi=30, st=0.5, d=0.0),
    E("chk", "cursor.hide_on_key_press", "bool", "hide while typing", "input", "Cursor", d=False),
    E("cwp", "cursor.warp_on_change_workspace", "enum", "warp on workspace change", "input", "Cursor", c=[0, 1, 2], d=0),
    E("mhl", "misc.disable_hyprland_logo", "bool", "disable logo", "input", "Misc", d=False),
    E("mds", "misc.disable_splash_rendering", "bool", "disable splash text", "input", "Misc", d=False),
    E("mam", "misc.animate_manual_resizes", "bool", "animate manual resizes", "input", "Misc", d=False),
    E("mad", "misc.animate_mouse_windowdragging", "bool", "animate window dragging", "input", "Misc", d=False),
    E("mfa", "misc.focus_on_activate", "bool", "focus on activate", "input", "Misc", d=False),
]
BY_KEY = {e["k"]: e for e in SCHEMA}
CURVE_KEYS = {"x0", "y0", "x1", "y1"}
LEAVES = {
    "windows": ["popin 80%", "popin 60%", "slide", "gnomed"],
    "windowsMove": [],
    "layers": ["fade", "slide", "popin 80%"],
    "fade": [],
    "border": [],
    "borderangle": ["once", "loop"],
    "workspaces": ["slide", "slidevert", "fade", "slidefade", "slidefadevert"],
    "specialWorkspace": ["slidevert", "slide", "fade"],
}
MODES = ("default", "on", "off")


def default_lv():
    return {n: {"m": "on" if n == "windows" else "default", "speed": 3.0, "style": c[0] if c else ""} for n, c in LEAVES.items()}


DEFAULT = {e["k"]: e["d"] for e in SCHEMA}
DEFAULT["lv"] = default_lv()


def hyprctl(*args):
    r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=10)
    return (r.stdout + r.stderr).strip()


def clamp(v, lo, hi):
    return min(max(v, lo), hi)


def clean(raw):
    s = json.loads(json.dumps(DEFAULT))
    for e in SCHEMA:
        k, t = e["k"], e["t"]
        if k not in raw:
            continue
        v = raw[k]
        try:
            if t == "int":
                s[k] = int(round(clamp(float(v), e["lo"], e["hi"])))
            elif t == "float":
                s[k] = round(clamp(float(v), e["lo"], e["hi"]), 4)
            elif t == "bool":
                s[k] = bool(v)
            elif t == "enum":
                s[k] = next(c for c in e["c"] if c == v or str(c) == str(v))
            elif t == "color" and COLOR8.match(str(v).lower()):
                s[k] = str(v).lower()
            elif t == "color6" and COLOR6.match(str(v).lower()):
                s[k] = str(v).lower()
            elif t == "text" and TEXT.match(str(v)):
                s[k] = str(v)
        except (ValueError, TypeError, StopIteration):
            pass
    for n, c in LEAVES.items():
        r = (raw.get("lv") or {}).get(n) or {}
        d = s["lv"][n]
        if r.get("m") in MODES:
            d["m"] = r["m"]
        try:
            d["speed"] = round(clamp(float(r.get("speed", d["speed"])), 0.1, 15), 2)
        except (ValueError, TypeError):
            pass
        if r.get("style") in c:
            d["style"] = r["style"]
    return s


class Raw(str):
    pass


def lua_val(v, ind):
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, list):
        return "{ " + ", ".join(lua_val(x, ind) for x in v) + " }"
    pad = "    " * (ind + 1)
    return "{\n" + "".join(f"{pad}{k} = {lua_val(x, ind + 1)},\n" for k, x in v.items()) + "    " * ind + "}"


def put(tree, path, v):
    parts = path.split(".")
    for p in parts[:-1]:
        tree = tree.setdefault(p, {})
    tree[parts[-1]] = v


def lua_for(s, only=None):
    def want(*ks):
        return only is None or any(k in only for k in ks)
    tree = {}
    for e in SCHEMA:
        if e.get("spec") or not want(e["k"]):
            continue
        v = s[e["k"]]
        if e["t"] == "enum" and v == "":
            continue
        put(tree, e["p"], Raw(f'"rgba({v[1:]})"') if e["t"] == "color" else v)
    if want("c1", "c2", "ang"):
        put(tree, "general.col.active_border", Raw(f'{{ colors = {{"rgba({s["c1"][1:]}ee)", "rgba({s["c2"][1:]}ee)"}}, angle = {s["ang"]} }}'))
    if want("dim"):
        put(tree, "decoration.dim_inactive", s["dim"] > 0)
        put(tree, "decoration.dim_strength", s["dim"])
    if want("sox", "soy"):
        put(tree, "decoration.shadow.offset", [s["sox"], s["soy"]])
    out = f"hl.config({lua_val(tree, 0)})\n" if tree else ""
    if want(*CURVE_KEYS, "lv"):
        out += f'\nhl.curve("tune", {{ type = "bezier", points = {{ {{{s["x0"]}, {s["y0"]}}}, {{{s["x1"]}, {s["y1"]}}} }} }})\n'
        for n, c in LEAVES.items():
            d = s["lv"][n]
            if d["m"] == "default":
                continue
            style = f', style = "{d["style"]}"' if c else ""
            out += f'hl.animation({{ leaf = "{n}", enabled = {"true" if d["m"] == "on" else "false"}, speed = {d["speed"]}, bezier = "tune"{style} }})\n'
    return out


def lua_profile(s):
    return lua_for(s) + '\nhl.layer_rule({ name = "blur-waybar", match = { namespace = "waybar" }, blur = true })\n'


def live_eval(s, only):
    code = lua_for(s, only)
    if code:
        hyprctl("eval", code)
    if "mfact" in only:
        push_master(s)
    time.sleep(0.05)
    return hyprctl("configerrors")


def push_master(s):
    """Existing workspaces keep their own master size, so push the new values into each monitor's active workspace."""
    mons = [m["name"] for m in json.loads(hyprctl("monitors", "-j"))]
    cur = next((m["name"] for m in json.loads(hyprctl("monitors", "-j")) if m["focused"]), None)
    for n in mons:
        if not OUTPUT.match(n):
            continue
        hyprctl("dispatch", f'hl.dsp.focus({{ monitor = "{n}" }})')
        hyprctl("dispatch", f'hl.dsp.layout("mfact exact {s["mfact"]}")')
    if cur:
        hyprctl("dispatch", f'hl.dsp.focus({{ monitor = "{cur}" }})')


def opt_value(e):
    name = e.get("ro") or e["p"].replace(".", ":")
    try:
        d = json.loads(hyprctl("getoption", name, "-j"))
    except Exception:
        return None
    for key in ("int", "float", "bool", "str"):
        if key in d:
            return "" if d[key] == "[[EMPTY]]" else d[key]
    if "css" in d:
        return int(d["css"].split()[0])
    if "gradient" in d:
        m = re.match(r"([0-9a-f]{2})([0-9a-f]{6})", d["gradient"])
        return "#" + m.group(2) + m.group(1) if m else None
    return None


def read_live():
    """Read the running compositor's values back, falling back to schema defaults."""
    raw = {}
    for e in SCHEMA:
        if e.get("spec"):
            continue
        v = opt_value(e)
        if v is not None:
            raw[e["k"]] = v
    try:
        d = json.loads(hyprctl("getoption", "decoration:dim_inactive", "-j"))
        d2 = json.loads(hyprctl("getoption", "decoration:dim_strength", "-j"))
        raw["dim"] = d2.get("float", 0) if d.get("bool", d.get("int")) else 0
        v = json.loads(hyprctl("getoption", "decoration:shadow:offset", "-j")).get("vec2")
        if v:
            raw["sox"], raw["soy"] = v
        g = json.loads(hyprctl("getoption", "general:col.active_border", "-j")).get("gradient", "")
        m = re.match(r"[0-9a-f]{2}([0-9a-f]{6}) [0-9a-f]{2}([0-9a-f]{6}) (\d+)deg", g)
        if m:
            raw["c1"], raw["c2"], raw["ang"] = "#" + m.group(1), "#" + m.group(2), int(m.group(3))
    except Exception:
        pass
    lv = {}
    try:
        anims, beziers = json.loads(hyprctl("animations", "-j"))
        for a in anims:
            if a["name"] in LEAVES and a.get("overridden") and a.get("bezier") == "tune":
                lv[a["name"]] = {"m": "on" if a["enabled"] else "off", "speed": a["speed"], "style": a["style"]}
        bz = next((b for b in beziers if b["name"] == "tune"), None)
        if bz:
            raw["x0"], raw["y0"], raw["x1"], raw["y1"] = bz["X0"], bz["Y0"], bz["X1"], bz["Y1"]
    except Exception:
        pass
    raw["lv"] = lv
    return clean(raw)


def profiles():
    names = sorted(f[7:-4] for f in os.listdir(HYPR) if f.startswith("config-") and f.endswith(".lua"))
    active = open(NAME_FILE).read().strip() if os.path.exists(NAME_FILE) and os.path.exists(os.path.join(HYPR, "profile.lua")) else "default"
    return names, active


def activate(name):
    prof = os.path.join(HYPR, "profile.lua")
    if name == "default":
        for f in (prof, NAME_FILE):
            if os.path.exists(f):
                os.remove(f)
    else:
        shutil.copy(os.path.join(HYPR, f"config-{name}.lua"), prof)
        open(NAME_FILE, "w").write(name)
    hyprctl("reload")
    time.sleep(0.4)


def snapshot(extra=None):
    names, active = profiles()
    s = read_live()
    d = {"state": s, "lua": lua_profile(s), "profiles": names, "active": active, "errors": hyprctl("configerrors"),
         "schema": SCHEMA, "leaves": LEAVES}
    d.update(extra or {})
    return d


# ---- monitors ----
def mode_str(m):
    return re.sub(r"Hz$", "", m)


def read_monitors():
    out = []
    for m in json.loads(hyprctl("monitors", "-j")):
        modes = []
        for x in m.get("availableModes", []):
            if mode_str(x) not in modes:
                modes.append(mode_str(x))
        cur = f'{m["width"]}x{m["height"]}'
        same = [x for x in modes if x.startswith(cur + "@")]
        mode = min(same, key=lambda x: abs(float(x.split("@")[1]) - m["refreshRate"])) if same else f'{cur}@{m["refreshRate"]:.2f}'
        if mode not in modes:
            modes.insert(0, mode)
        out.append({"name": m["name"], "desc": m.get("description", ""), "x": m["x"], "y": m["y"],
                    "scale": round(m["scale"], 3), "tr": m["transform"], "mode": mode, "modes": modes, "focused": m.get("focused", False)})
    return out


def clean_monitors(raw):
    known = {m["name"]: m for m in read_monitors()}
    out = []
    for r in raw:
        name = str(r.get("name", ""))
        if not OUTPUT.match(name) or name not in known:
            raise ValueError(f"unknown monitor {name!r}")
        mode = str(r.get("mode", ""))
        if mode not in known[name]["modes"]:
            raise ValueError(f"{name}: mode {mode!r} not supported")
        out.append({"name": name, "mode": mode, "x": int(clamp(round(float(r["x"])), -16000, 16000)),
                    "y": int(clamp(round(float(r["y"])), -16000, 16000)), "scale": round(clamp(float(r["scale"]), 0.25, 4), 3),
                    "tr": int(clamp(int(r["tr"]), 0, 7))})
    if not out:
        raise ValueError("no monitors")
    return out


def monitors_lua(ms):
    return "".join(
        f'hl.monitor({{ output = "{m["name"]}", mode = "{m["mode"]}", position = "{m["x"]}x{m["y"]}", scale = {m["scale"]}, transform = {m["tr"]} }})\n'
        for m in ms)


# ---- wallpaper ----
def list_images():
    out = []
    for d in (HYPR, os.path.join(HYPR, "wallpapers"), HOME + "/Pictures", HOME + "/Pictures/wallpapers", HOME + "/Downloads"):
        try:
            for f in sorted(os.listdir(d)):
                fp = os.path.join(d, f)
                if f.lower().endswith(IMG_EXT) and os.path.isfile(fp) and fp not in out:
                    out.append(fp)
        except OSError:
            pass
    return out[:300]


def safe_image(path):
    """Accept only an existing image file under the home directory."""
    rp = os.path.realpath(str(path))
    if not rp.startswith(HOME + os.sep) or not rp.lower().endswith(IMG_EXT) or not os.path.isfile(rp) or "\n" in rp:
        raise ValueError(f"not a usable image: {path!r}")
    return rp


def read_wall():
    conf = open(PAPER).read() if os.path.exists(PAPER) else ""
    cur = {}
    for blk in re.findall(r"wallpaper\s*\{([^}]*)\}", conf):
        kv = dict(re.findall(r"^\s*(\w+)\s*=\s*(.*?)\s*$", blk, re.M))
        if kv.get("monitor") is not None:
            cur[kv["monitor"]] = {"path": kv.get("path", ""), "fit": kv.get("fit_mode", "cover")}
    return [{"name": m["name"], "path": cur.get(m["name"], {}).get("path", ""), "fit": cur.get(m["name"], {}).get("fit", "cover")}
            for m in read_monitors()]


def apply_wall(walls):
    names = {m["name"] for m in read_monitors()}
    blocks = []
    for w in walls:
        name = str(w.get("name", ""))
        if name not in names or not OUTPUT.match(name):
            raise ValueError(f"unknown monitor {name!r}")
        if not w.get("path"):
            continue
        fit = w.get("fit") if w.get("fit") in FITS else "cover"
        blocks.append(f"wallpaper {{\n    monitor = {name}\n    path = {safe_image(w['path'])}\n    fit_mode = {fit}\n}}\n")
    if not blocks:
        raise ValueError("pick at least one wallpaper")
    text = "\n".join(blocks)
    for d in (HYPR, REPO):
        if os.path.isdir(d):
            open(os.path.join(d, "hyprpaper.conf"), "w").write(text)
    subprocess.run(["pkill", "-x", "hyprpaper"], capture_output=True)
    time.sleep(0.3)
    subprocess.Popen(["hyprpaper"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)


# ---- http ----
class Handler(http.server.BaseHTTPRequestHandler):
    last = time.time()

    def log_message(self, *a):
        pass

    def ok_origin(self):
        allowed = {f"{HOST}:{PORT}", f"localhost:{PORT}"}
        if self.headers.get("Host") not in allowed:
            return False
        o = self.headers.get("Origin")
        return o is None or o.replace("http://", "") in allowed

    def send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        Handler.last = time.time()
        if not self.ok_origin():
            return self.send(403, "forbidden", "text/plain")
        if self.path == "/":
            return self.send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self.send(200, json.dumps(snapshot()))
        if self.path == "/api/monitors":
            return self.send(200, json.dumps({"monitors": read_monitors()}))
        if self.path == "/api/wall":
            return self.send(200, json.dumps({"walls": read_wall(), "images": list_images(), "fits": FITS, "live": hyprctl("hyprpaper", "listactive")}))
        if self.path.startswith("/api/img?p="):
            from urllib.parse import unquote
            try:
                rp = safe_image(unquote(self.path[11:]))
                if os.path.getsize(rp) > 60 * 1024 * 1024:
                    raise ValueError("too large")
                ct = "image/png" if rp.lower().endswith(".png") else "image/webp" if rp.lower().endswith(".webp") else "image/jpeg"
                return self.send(200, open(rp, "rb").read(), ct)
            except Exception:
                return self.send(404, "not found", "text/plain")
        self.send(404, "not found", "text/plain")

    def do_POST(self):
        Handler.last = time.time()
        if not self.ok_origin() or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(403, "forbidden", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            p = self.path
            if p == "/api/apply":
                s = clean(body.get("state", {}))
                only = {k for k in body.get("only", []) if k in BY_KEY or k == "lv"}
                err = live_eval(s, only) if only else hyprctl("configerrors")
                return self.send(200, json.dumps({"lua": lua_profile(s), "errors": err, "state": s}))
            if p == "/api/save":
                name, s = str(body.get("name", "")), clean(body.get("state", {}))
                if not NAME.match(name) or name == "default":
                    return self.send(400, json.dumps({"error": "name must be a-z, 0-9, dash (not 'default')"}))
                text = lua_profile(s)
                for d in (HYPR, REPO):
                    if os.path.isdir(d):
                        open(os.path.join(d, f"config-{name}.lua"), "w").write(text)
                activate(name)
                return self.send(200, json.dumps(snapshot({"saved": name})))
            if p == "/api/profile":
                name = str(body.get("name", ""))
                if name != "default" and not (NAME.match(name) and os.path.exists(os.path.join(HYPR, f"config-{name}.lua"))):
                    return self.send(400, json.dumps({"error": "unknown profile"}))
                activate(name)
                return self.send(200, json.dumps(snapshot()))
            if p == "/api/delete":
                name = str(body.get("name", ""))
                if NAME.match(name):
                    for d in (HYPR, REPO):
                        f = os.path.join(d, f"config-{name}.lua")
                        if os.path.exists(f):
                            os.remove(f)
                    if profiles()[1] == name:
                        activate("default")
                return self.send(200, json.dumps(snapshot()))
            if p == "/api/revert":
                hyprctl("reload")
                time.sleep(0.4)
                return self.send(200, json.dumps(snapshot()))
            if p == "/api/monitors/apply":
                ms = clean_monitors(body.get("monitors", []))
                hyprctl("eval", monitors_lua(ms))
                time.sleep(0.5)
                return self.send(200, json.dumps({"monitors": read_monitors(), "errors": hyprctl("configerrors")}))
            if p == "/api/monitors/save":
                ms = clean_monitors(body.get("monitors", []))
                bak = MON_FILE + ".bak-tune"
                if os.path.exists(MON_FILE) and not os.path.exists(bak):
                    shutil.copy(MON_FILE, bak)
                open(MON_FILE, "w").write("-- written by hypr-tune.py\n" + monitors_lua(ms))
                return self.send(200, json.dumps({"saved": True}))
            if p == "/api/wall/apply":
                apply_wall(body.get("walls", []))
                return self.send(200, json.dumps({"walls": read_wall(), "live": hyprctl("hyprpaper", "listactive")}))
            if p == "/api/quit":
                self.send(200, "{}")
                threading.Thread(target=self.server.shutdown).start()
                return
        except Exception as e:
            return self.send(500, json.dumps({"error": str(e)}))
        self.send(404, "not found", "text/plain")


def serve():
    srv = http.server.ThreadingHTTPServer((HOST, PORT), Handler)

    def idle():
        while True:
            time.sleep(60)
            if time.time() - Handler.last > IDLE_SECONDS:
                srv.shutdown()
                return
    threading.Thread(target=idle, daemon=True).start()
    srv.serve_forever()


def up():
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, PORT)) == 0


def main():
    if "--serve" in sys.argv:
        return serve()
    if not up():
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--serve"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if up():
                break
            time.sleep(0.1)
    webbrowser.open(f"http://{HOST}:{PORT}/")


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hypr Tune</title>
<style>
:root{--bg:#0e1116;--panel:#161b22;--line:#262d38;--text:#d7dde6;--dim:#8a94a3;--accent:#33ccff;--ok:#00ff99;--warn:#ffb454;--bad:#ff7a8a;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif;padding:20px 16px 48px}
.wrap{max-width:1180px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
h1{font:700 24px ui-monospace,monospace;margin:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px;align-items:start}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:10px}
h3{margin:0;font:600 12px ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.row{display:grid;grid-template-columns:150px minmax(0,1fr) 64px;gap:10px;align-items:center}
.row label{color:var(--dim);font-size:13px} .row output{font:600 12px ui-monospace,monospace;text-align:right}
.chg{color:var(--warn)}
input.num{width:100%;min-width:0;padding:4px 8px;-moz-appearance:textfield;appearance:textfield;font:600 12px ui-monospace,monospace;color:var(--text);background:#0d1117;border:1px solid var(--line);border-radius:6px;text-align:right}
input.num.chg{border-color:var(--warn)}
input.num::-webkit-inner-spin-button,input.num::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
input.num:focus{border-color:var(--accent)}
input[type=range]{width:100%;accent-color:var(--accent)}
button,select,input[type=text]{font:600 13px ui-monospace,monospace;color:var(--text);background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:7px 12px}
button{cursor:pointer} button:hover{border-color:var(--accent)} button.on{border-color:var(--accent);color:var(--accent)}
button.primary{border-color:var(--ok);color:var(--ok)} button.danger:hover{border-color:var(--bad);color:var(--bad)}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tog{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.pill{font:600 12px ui-monospace,monospace;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}
.pill.dirty{color:var(--warn);border-color:var(--warn)} .pill.clean{color:var(--ok);border-color:var(--ok)}
input[type=color]{width:36px;height:26px;border:1px solid var(--line);border-radius:6px;background:none;padding:0}
pre{margin:0;background:#0a0d12;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;font:12.5px/1.6 ui-monospace,monospace;color:#b9c4d4;max-height:340px}
.err{color:var(--bad);font:12px ui-monospace,monospace;white-space:pre-wrap}
.prof{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.prof.active{border-color:var(--ok)}
.note{color:var(--dim);font-size:12.5px}
.ctl{display:grid;grid-template-columns:150px 1fr;gap:10px;align-items:center}
.ctl label{color:var(--dim);font-size:13px}
.lv{display:grid;grid-template-columns:130px 100px minmax(120px,1fr) 64px 140px;gap:8px;align-items:center}
.rig{position:relative;width:100%;border-radius:8px;overflow:hidden;background:#05060a;border:1px solid var(--line)}
.mon{position:absolute;top:0;overflow:hidden;outline:1px solid #2c3340}
.mon.hd{background:radial-gradient(80% 90% at 30% 20%,#2a2f72 0%,transparent 60%),radial-gradient(70% 80% at 80% 90%,#3a1d5c 0%,transparent 60%),#0c0f26}
.mon.ed{background:#000;color:#cfcfcf;display:flex;align-items:center;justify-content:center;font:12px system-ui}
.bar{position:absolute;left:0;right:0;top:0;display:flex;align-items:center;justify-content:flex-end;gap:.9em;padding-right:.6em;color:#fff;z-index:6;font-family:system-ui;white-space:nowrap;overflow:hidden;background:rgba(14,17,24,.55);backdrop-filter:blur(10px)}
.win{position:absolute;cursor:pointer}
.win::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:var(--bw);background:var(--bcol);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;z-index:2}
.win .in{position:absolute;inset:0;border-radius:inherit;overflow:hidden;background:rgba(18,20,28,var(--op));padding:calc(var(--bw) + .5em);font:var(--fs) ui-monospace,monospace;color:#cfd8e6;line-height:1.4}
.win.blur .in{backdrop-filter:blur(var(--blur)) saturate(var(--sat))}
.win .g{color:#00ff99}.win .d{color:#7f8a9c}
@keyframes pop{from{transform:scale(.8);opacity:0}to{transform:scale(1);opacity:1}}
.win.pop{animation:pop var(--dur) var(--ease)}
.marea{position:relative;width:100%;background:#0a0d12;border:1px solid var(--line);border-radius:8px;overflow:hidden;touch-action:none}
.mbox{position:absolute;border:2px solid #3a4456;border-radius:6px;background:#1b2230;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;cursor:grab;user-select:none;font:600 12px ui-monospace,monospace;overflow:hidden}
.mbox.sel{border-color:var(--accent);background:#17303b}
.mbox small{color:var(--dim);font-weight:400}
.banner{border:1px solid var(--warn);border-radius:8px;padding:10px 12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;color:var(--warn)}
</style></head><body><div class="wrap">
<header><h1>hypr-tune</h1><div class="tog"><span class="pill" id="dirty">live</span><button id="revert">revert to saved</button><button id="quit" class="danger">quit server</button></div></header>
<div class="panel"><h3>Preview</h3><div class="rig" id="rig"></div>
  <div class="tog"><button id="addw">+ window</button><button id="remw">- window</button><button id="replay">replay open animation</button><span class="note">approximation of your two screens (HDMI left, laptop right); click a window to focus it</span></div></div>
<div class="tabs" id="tabs"></div>
<div id="pages"></div>
<div class="panel"><h3>Generated Lua (profile)</h3><div class="err" id="err"></div><pre id="lua"></pre></div>
</div>
<script>
const $=id=>document.getElementById(id);
const TABS=[['look','Look'],['layout','Layout'],['anim','Animations'],['input','Input & misc'],['mon','Monitors'],['wall','Wallpaper'],['prof','Profiles']];
const PRESETS={'ease-out snappy':[0.23,1,0.32,1],'overshoot':[0.34,1.56,0.64,1],'linear':[0,0,1,1],'default-ish':[0.25,0.1,0.25,1]};
let SCHEMA=[],LEAVES={},S={},SAVED={},LAST={},timer=null,TAB=TABS.some(t=>t[0]===location.hash.slice(1))?location.hash.slice(1):'look';
const CTRL={};
const dec=st=>String(st).includes('.')?String(st).split('.')[1].length:0;
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json();}
function el(tag,cls,html){const e=document.createElement(tag);if(cls)e.className=cls;if(html!==undefined)e.innerHTML=html;return e;}

function control(e){
  const k=e.k,box=el('div'),mark=()=>S[k]!==SAVED[k];
  if(e.t==='int'||e.t==='float'){
    box.className='row';
    box.innerHTML=`<label for="s-${k}">${e.l}</label><input id="s-${k}" type="range" min="${e.lo}" max="${e.hi}" step="${e.st}"><input type="number" class="num" aria-label="${e.l} value" min="${e.lo}" max="${e.hi}" step="${e.st}">`;
    const i=box.querySelector('[type=range]'),o=box.querySelector('.num');
    i.oninput=()=>{S[k]=parseFloat(i.value);changed();};
    o.onchange=()=>{const v=parseFloat(o.value);if(isNaN(v))return paint();S[k]=Math.min(e.hi,Math.max(e.lo,v));changed();};
    CTRL[k]=()=>{i.value=S[k];if(document.activeElement!==o)o.value=Number(S[k]).toFixed(dec(e.st));o.classList.toggle('chg',mark());};
  }else if(e.t==='bool'){
    box.className='ctl';box.innerHTML=`<label>${e.l}</label>`;const b=el('button');box.appendChild(b);
    b.onclick=()=>{S[k]=!S[k];changed();};
    CTRL[k]=()=>{b.textContent=S[k]?'on':'off';b.className=S[k]?'on':'';b.style.borderStyle=mark()?'dashed':'solid';};
  }else if(e.t==='enum'){
    box.className='ctl';box.innerHTML=`<label>${e.l}</label>`;const s=el('select',null,e.c.map(c=>`<option value="${c}">${c===''?'(unset)':c}</option>`).join(''));box.appendChild(s);
    s.onchange=()=>{S[k]=e.c.find(c=>String(c)===s.value);changed();};
    CTRL[k]=()=>{s.value=S[k];s.style.borderColor=mark()?'var(--warn)':'';};
  }else if(e.t==='text'){
    box.className='ctl';box.innerHTML=`<label>${e.l}</label><input type="text" maxlength="32">`;const i=box.querySelector('input');
    i.onchange=()=>{if(/^[a-z0-9,_-]{1,32}$/.test(i.value)){S[k]=i.value;changed();}else i.value=S[k];};
    CTRL[k]=()=>{i.value=S[k];};
  }else if(e.t==='color6'||e.t==='color'){
    box.className='ctl';box.innerHTML=`<label>${e.l}</label><div class="tog"><input type="color"></div>`;const c=box.querySelector('input'),w=box.querySelector('.tog');let a=null;
    c.oninput=()=>{S[k]=e.t==='color'?c.value+S[k].slice(7):c.value;changed();};
    if(e.t==='color'){a=el('input');a.type='range';a.min=0;a.max=255;a.style.width='120px';a.setAttribute('aria-label',e.l+' alpha');a.oninput=()=>{S[k]=S[k].slice(0,7)+(+a.value).toString(16).padStart(2,'0');changed();};w.appendChild(a);}
    CTRL[k]=()=>{c.value=S[k].slice(0,7);if(a)a.value=parseInt(S[k].slice(7),16);};
  }
  return box;
}
function leafPanel(){
  const p=el('div','panel');p.style.gridColumn='1/-1';p.innerHTML='<h3>Per-animation overrides</h3><p class="note">default = leave Hyprland default (switching back to default takes effect after save or revert). Overrides share the curve above.</p>';
  Object.entries(LEAVES).forEach(([n,styles])=>{
    const r=el('div','lv');
    r.innerHTML=`<span>${n}</span><select data-m aria-label="${n} mode">${['default','on','off'].map(m=>`<option>${m}</option>`).join('')}</select><input type="range" data-s min="0.1" max="15" step="0.1" aria-label="${n} speed"><input type="number" class="num" min="0.1" max="15" step="0.1" aria-label="${n} speed value">`;
    const st=el('select',null,styles.map(x=>`<option>${x}</option>`).join(''));st.setAttribute('aria-label',n+' style');if(!styles.length)st.style.visibility='hidden';r.appendChild(st);
    const m=r.querySelector('[data-m]'),sp=r.querySelector('[data-s]'),o=r.querySelector('.num');
    o.onchange=()=>{const v=parseFloat(o.value);if(isNaN(v))return paint();S.lv[n].speed=Math.min(15,Math.max(0.1,v));changed();};
    m.onchange=()=>{S.lv[n].m=m.value;changed();};sp.oninput=()=>{S.lv[n].speed=parseFloat(sp.value);changed();};st.onchange=()=>{S.lv[n].style=st.value;changed();};
    CTRL['lv_'+n]=()=>{m.value=S.lv[n].m;sp.value=S.lv[n].speed;if(document.activeElement!==o)o.value=S.lv[n].speed;st.value=S.lv[n].style;r.style.opacity=S.lv[n].m==='default'?.6:1;};
    p.appendChild(r);
  });
  return p;
}
function buildPages(){
  const tabs=$('tabs'),pages=$('pages');tabs.innerHTML='';pages.innerHTML='';
  TABS.forEach(([id,label])=>{
    const b=el('button',null,label);b.dataset.t=id;b.onclick=()=>{TAB=id;showTab();};tabs.appendChild(b);
    const pg=el('div','grid');pg.id='pg-'+id;pages.appendChild(pg);
    const groups={};SCHEMA.filter(e=>e.tab===id).forEach(e=>{(groups[e.g]=groups[e.g]||[]).push(e);});
    Object.entries(groups).forEach(([g,es])=>{const p=el('div','panel',`<h3>${g}</h3>`);es.forEach(e=>p.appendChild(control(e)));pg.appendChild(p);});
    if(id==='anim'){
      const cp=[...pg.querySelectorAll('.panel')].find(p=>p.firstChild.textContent==='Curve');
      const t=el('div','tog');Object.entries(PRESETS).forEach(([n,v])=>{const b=el('button',null,n);b.onclick=()=>{[S.x0,S.y0,S.x1,S.y1]=v;changed();};t.appendChild(b);});cp.appendChild(t);
      pg.appendChild(leafPanel());
    }
    if(id==='mon')pg.appendChild(monPanel());
    if(id==='wall')pg.appendChild(wallPanel());
    if(id==='prof')pg.appendChild(profPanel());
  });
  showTab();
}
function showTab(){document.querySelectorAll('#pages>div').forEach(d=>d.style.display=d.id==='pg-'+TAB?'grid':'none');document.querySelectorAll('#tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t===TAB));if(TAB==='mon')monLoad();if(TAB==='wall')wallLoad();}
function paint(){
  Object.values(CTRL).forEach(f=>f());preview();
  const dirty=JSON.stringify(S)!==JSON.stringify(SAVED);
  $('dirty').textContent=dirty?'unsaved live changes':'matches saved';$('dirty').className='pill '+(dirty?'dirty':'clean');
}
function changed(){
  paint();clearTimeout(timer);
  timer=setTimeout(async()=>{
    const only=Object.keys(S).filter(k=>JSON.stringify(S[k])!==JSON.stringify(LAST[k]));
    LAST=JSON.parse(JSON.stringify(S));
    const d=await api('/api/apply',{state:S,only});$('lua').textContent=d.lua;$('err').textContent=d.errors||'';
  },60);
}
function profPanel(){
  const p=el('div','panel','<h3>Profiles</h3><div id="profs" class="tog" style="flex-direction:column;align-items:stretch"></div><div class="tog"><input type="text" id="pname" placeholder="new-profile-name" aria-label="profile name" maxlength="32"><button id="save" class="primary">save as new &amp; activate</button></div><p class="note">Changes apply live as you drag. Save as new writes config-NAME.lua; overwrite replaces an existing profile with the current settings. Either one becomes the profile loaded at login. Revert reloads the saved profile.</p>');
  p.querySelector('#save').onclick=async()=>{const n=$('pname').value.trim();if(!n)return $('pname').focus();const d=await api('/api/save',{name:n,state:S});if(d.error)return $('err').textContent=d.error;$('pname').value='';load(d);};
  return p;
}
function profs(d){
  const box=$('profs');box.innerHTML='';
  ['default',...d.profiles].forEach(n=>{
    const row=el('div','prof'+(n===d.active?' active':''),`<span>${n}${n===d.active?' (active)':''}</span><span class="tog"></span>`);
    const t=row.querySelector('.tog');
    if(n!==d.active){const a=el('button',null,'apply');a.onclick=async()=>load(await api('/api/profile',{name:n}));t.appendChild(a);}
    if(n!=='default'){const o=el('button','primary','overwrite');o.title='save current settings into '+n;o.onclick=async()=>{if(!confirm('Overwrite profile '+n+' with the current settings?'))return;const r=await api('/api/save',{name:n,state:S});if(r.error)return $('err').textContent=r.error;load(r);};t.appendChild(o);
      const x=el('button','danger','delete');x.onclick=async()=>{if(confirm('Delete profile '+n+'?'))load(await api('/api/delete',{name:n}));};t.appendChild(x);}
    box.appendChild(row);
  });
}
function load(d){
  if(d.schema&&!SCHEMA.length){SCHEMA=d.schema;LEAVES=d.leaves;S=d.state;buildPages();}
  S=d.state;SAVED=JSON.parse(JSON.stringify(d.state));LAST=JSON.parse(JSON.stringify(d.state));
  $('lua').textContent=d.lua;$('err').textContent=d.errors||'';profs(d);paint();
}
$('revert').onclick=async()=>load(await api('/api/revert',{}));
$('quit').onclick=async()=>{await api('/api/quit',{});document.body.innerHTML='<p style="padding:2rem">hypr-tune stopped. Press the keybind to start it again.</p>';};

/* ---- preview ---- */
let NW=2,FOC=0,POP=-1;
const rgba=h=>`rgba(${parseInt(h.slice(1,3),16)},${parseInt(h.slice(3,5),16)},${parseInt(h.slice(5,7),16)},${(parseInt(h.slice(7,9)||'ff',16)/255).toFixed(2)})`;
const lay=(n,x,y,w,h)=>{
  if(S.layout==='master'){if(n===1)return[[x,y,w,h]];const f=S.mfact,o=[],m=S.mor;
    if(m==='right'){o.push([x+w*(1-f),y,w*f,h]);for(let i=1;i<n;i++)o.push([x,y+(i-1)*h/(n-1),w*(1-f),h/(n-1)]);}
    else if(m==='top'){o.push([x,y,w,h*f]);for(let i=1;i<n;i++)o.push([x+(i-1)*w/(n-1),y+h*f,w/(n-1),h*(1-f)]);}
    else if(m==='bottom'){o.push([x,y+h*(1-f),w,h*f]);for(let i=1;i<n;i++)o.push([x+(i-1)*w/(n-1),y,w/(n-1),h*(1-f)]);}
    else{o.push([x,y,w*f,h]);for(let i=1;i<n;i++)o.push([x+w*f,y+(i-1)*h/(n-1),w*(1-f),h/(n-1)]);}
    return o;}
  const o=[];for(let i=0;i<n;i++){if(i===n-1){o.push([x,y,w,h]);break;}if(w>=h){o.push([x,y,w/2,h]);x+=w/2;w/=2;}else{o.push([x,y,w,h/2]);y+=h/2;h/=2;}}return o;};
const rig=$('rig'),mh=document.createElement('div'),me=document.createElement('div'),wins=[];
mh.className='mon hd';me.className='mon ed';me.textContent='This text is random.';
for(const m of[mh,me]){const b=document.createElement('div');b.className='bar';b.innerHTML='<span>CPU 22%</span><span>us</span><b>23:56</b>';m.appendChild(b);m._bar=b;rig.appendChild(m);}
const APPS=[['murrou@laptop ~','$ kubectl get nodes','k3s-master   Ready','k3s-worker-2 Ready','k3s-gpu      Ready','$ _'],['claude','> tune the desktop','* applying live...','auto mode on'],['dolphin','~/repos/home-cloud','ansible/','argocd/','terraform/']];
function preview(){
  if(!SCHEMA.length)return;
  const W=rig.clientWidth,s=W/3200;rig.style.height=(1080*s)+'px';
  mh.style.left='0px';mh.style.width=(1920*s)+'px';mh.style.height=(1080*s)+'px';
  me.style.left=(1920*s)+'px';me.style.width=(1280*s)+'px';me.style.height=(720*s)+'px';
  const bp=Math.max(24*s,12);for(const m of[mh,me]){m._bar.style.height=bp+'px';m._bar.style.fontSize=Math.max(7,13*s)+'px';}
  const lw=S.lv.windows,dur=S.anim?(lw.m==='on'?lw.speed:4)*100:0,ease=`cubic-bezier(${S.x0},${S.y0},${S.x1},${S.y1})`,go=S.go*s,gi=S.gi*s;
  while(wins.length<NW){const e=document.createElement('div');e.className='win';e.onclick=()=>{FOC=wins.indexOf(e);preview();};wins.push(e);mh.appendChild(e);}
  while(wins.length>NW)wins.pop().remove();
  if(FOC>=NW)FOC=NW-1;
  const r=lay(NW,go-gi/2,bp+go-gi/2,1920*s-2*go+gi,1080*s-bp-2*go+gi);
  wins.forEach((e,i)=>{const[x,y,w,h]=r[i],g=gi/2,act=i===FOC,t=e.style;
    t.transition=dur?`left ${dur}ms ${ease},top ${dur}ms ${ease},width ${dur}ms ${ease},height ${dur}ms ${ease}`:'none';
    t.left=(x+g)+'px';t.top=(y+g)+'px';t.width=Math.max(0,w-2*g)+'px';t.height=Math.max(0,h-2*g)+'px';
    t.borderRadius=(S.rad*s)+'px';t.setProperty('--bw',(S.bw*s)+'px');
    t.setProperty('--bcol',act?`linear-gradient(${S.ang}deg,${S.c1},${S.c2})`:rgba(S.ic));
    t.setProperty('--op',Math.min(1,(act?S.ao:S.io)*(act?1:1-S.dim)));t.setProperty('--fs',Math.max(6,11*s)+'px');
    t.setProperty('--blur',(S.bs*S.bp*2.6*s)+'px');t.setProperty('--sat',1+S.vib*2);t.setProperty('--dur',dur+'ms');t.setProperty('--ease',ease);
    const k=(S.sharp?.4:1)*S.ssc;
    t.boxShadow=S.shadow?`${S.sox*s}px ${S.soy*s}px ${S.sr*s*2.5*k}px ${S.sr*s*.3*(5-S.sp)*S.ssc}px ${rgba(S.scol)}`:'none';
    t.zIndex=act?3:2;e.classList.toggle('blur',S.blur);
    const a=APPS[i%APPS.length];e.innerHTML=`<div class="in"><div class="g">${a[0]}</div>${a.slice(1).map(l=>`<div class="d">${l}</div>`).join('')}</div>`;
    if(i===POP&&S.anim){e.classList.remove('pop');void e.offsetWidth;e.classList.add('pop');}});
  POP=-1;
}
$('addw').onclick=()=>{NW=Math.min(5,NW+1);POP=NW-1;preview();};
$('remw').onclick=()=>{NW=Math.max(1,NW-1);preview();};
$('replay').onclick=()=>{POP=FOC;preview();};
window.addEventListener('resize',()=>{preview();monDraw();});

/* ---- monitors ---- */
let MW=[],MSEL=null,MTIMER=null;
const SCALES=[0.5,0.75,1,1.25,1.5,1.6,1.75,2,2.5,3];
const TR=['normal','90°','180°','270°','flipped','flipped 90°','flipped 180°','flipped 270°'];
const mdims=m=>{const[w,h]=m.mode.split('@')[0].split('x').map(Number);const sw=m.tr%2===1;return[(sw?h:w)/m.scale,(sw?w:h)/m.scale];};
const clone=o=>JSON.parse(JSON.stringify(o));
function monPanel(){
  const p=el('div','panel');p.style.gridColumn='1/-1';
  p.innerHTML=`<h3>Monitors</h3><div class="marea" id="marea"></div>
  <p class="note">Drag a monitor to place it (edges snap to the neighbour). Select one to change its mode, scale or rotation. Apply is live and asks you to keep it, otherwise it reverts after 15 s.</p>
  <div class="tog" id="mctl"></div><div class="tog"><button id="mapply" class="primary">apply live</button><button id="msave">save to monitors.lua</button><button id="mreset">reload from compositor</button></div>
  <div id="mbanner"></div><div class="err" id="merr"></div>`;
  p.querySelector('#mapply').onclick=monApply;
  p.querySelector('#msave').onclick=async()=>{const d=await api('/api/monitors/save',{monitors:MW});$('merr').textContent=d.error||'saved to ~/.config/hypr/monitors.lua (loaded at login)';};
  p.querySelector('#mreset').onclick=monLoad;
  return p;
}
async function monLoad(){const d=await api('/api/monitors');MW=d.monitors;if(!MSEL||!MW.find(m=>m.name===MSEL))MSEL=(MW.find(m=>m.focused)||MW[0]).name;monDraw();}
function monDraw(){
  const area=$('marea');if(!area||!MW.length||$('pg-mon').style.display==='none')return;
  const d=MW.map(m=>({m,s:mdims(m)}));
  const minX=Math.min(...d.map(o=>o.m.x)),maxX=Math.max(...d.map(o=>o.m.x+o.s[0])),minY=Math.min(...d.map(o=>o.m.y)),maxY=Math.max(...d.map(o=>o.m.y+o.s[1]));
  const padX=(maxX-minX)*.25+200,padY=(maxY-minY)*.25+200,W=area.clientWidth,f=W/(maxX-minX+2*padX);
  const ox=minX-padX,oy=minY-padY;area.style.height=Math.max(220,(maxY-minY+2*padY)*f)+'px';area.innerHTML='';
  d.forEach(({m,s})=>{
    const b=el('div','mbox'+(m.name===MSEL?' sel':''),`${m.name}<small>${m.mode.split('@')[0]} · x${m.scale}</small><small class="pos">${m.x},${m.y}</small>`);
    b.style.cssText+=`;left:${(m.x-ox)*f}px;top:${(m.y-oy)*f}px;width:${s[0]*f}px;height:${s[1]*f}px`;
    b.onpointerdown=ev=>{MSEL=m.name;b.setPointerCapture(ev.pointerId);const sx=ev.clientX,sy=ev.clientY,px=m.x,py=m.y;
      b.onpointermove=e2=>{let nx=px+(e2.clientX-sx)/f,ny=py+(e2.clientY-sy)/f;[nx,ny]=snap(m,nx,ny,s);m.x=Math.round(nx);m.y=Math.round(ny);
        b.style.left=((m.x-ox)*f)+'px';b.style.top=((m.y-oy)*f)+'px';b.querySelector('.pos').textContent=m.x+','+m.y;};
      b.onpointerup=()=>{b.onpointermove=null;monDraw();};};
    area.appendChild(b);
  });
  monCtl();
}
function snap(m,x,y,s){
  const T=30;let bx=x,by=y,dx=T,dy=T;
  MW.filter(o=>o!==m).forEach(o=>{const[ow,oh]=mdims(o);
    [o.x+ow,o.x-s[0],o.x,o.x+ow-s[0]].forEach(c=>{if(Math.abs(c-x)<dx){dx=Math.abs(c-x);bx=c;}});
    [o.y+oh,o.y-s[1],o.y,o.y+oh-s[1]].forEach(c=>{if(Math.abs(c-y)<dy){dy=Math.abs(c-y);by=c;}});});
  return[bx,by];
}
function monCtl(){
  const m=MW.find(o=>o.name===MSEL);const c=$('mctl');if(!m||!c)return;
  const sc=[...new Set([...SCALES,m.scale])].sort((a,b)=>a-b);
  c.innerHTML=`<span class="note">${m.name}</span><select id="mm" aria-label="mode">${m.modes.map(x=>`<option${x===m.mode?' selected':''}>${x}</option>`).join('')}</select>
   <select id="ms" aria-label="scale">${sc.map(x=>`<option${x===m.scale?' selected':''}>${x}</option>`).join('')}</select>
   <select id="mt" aria-label="rotation">${TR.map((x,i)=>`<option value="${i}"${i===m.tr?' selected':''}>${x}</option>`).join('')}</select>`;
  $('mm').onchange=e=>{m.mode=e.target.value;monDraw();};$('ms').onchange=e=>{m.scale=parseFloat(e.target.value);monDraw();};$('mt').onchange=e=>{m.tr=parseInt(e.target.value);monDraw();};
}
async function monApply(){
  const d0=await api('/api/monitors');const prev=d0.monitors;
  const d=await api('/api/monitors/apply',{monitors:MW});
  if(d.error){$('merr').textContent=d.error;return;}
  MW=d.monitors;$('merr').textContent=d.errors||'';monDraw();
  let n=15;const b=$('mbanner');clearInterval(MTIMER);
  const revert=async()=>{clearInterval(MTIMER);b.innerHTML='';const r=await api('/api/monitors/apply',{monitors:prev});if(r.monitors){MW=r.monitors;monDraw();}};
  const draw=()=>{b.innerHTML=`<div class="banner"><span>Keep this layout? Reverting in ${n}s</span><button id="mkeep" class="primary">keep</button><button id="mrev">revert now</button></div>`;
    $('mkeep').onclick=()=>{clearInterval(MTIMER);b.innerHTML='';};$('mrev').onclick=revert;};
  draw();MTIMER=setInterval(()=>{n--;if(n<=0)revert();else draw();},1000);
}

/* ---- wallpaper ---- */
let WALL=[],IMGS=[],FITS=[];
const imgUrl=p=>'/api/img?p='+encodeURIComponent(p);
function wallPanel(){
  const p=el('div','panel');p.style.gridColumn='1/-1';
  p.innerHTML=`<h3>Wallpaper (hyprpaper)</h3><div id="wcards" class="grid"></div>
  <p class="note">Each monitor needs its own entry, a monitor with none shows Hyprland's default background with the logo and splash text. Pick from images found in ~/.config/hypr, ~/Pictures and ~/Downloads, or type a full path under your home folder. Apply rewrites hyprpaper.conf and restarts hyprpaper (about a second).</p>
  <div class="tog"><button id="wapply" class="primary">apply wallpapers</button></div><div class="err" id="werr"></div><div class="note" id="wlive"></div>`;
  p.querySelector('#wapply').onclick=async()=>{$('werr').textContent='';const d=await api('/api/wall/apply',{walls:WALL});if(d.error)return $('werr').textContent=d.error;WALL=d.walls;$('wlive').textContent='active: '+d.live.replace(/\n/g,' | ');wallDraw();};
  return p;
}
async function wallLoad(){const d=await api('/api/wall');WALL=d.walls;IMGS=d.images;FITS=d.fits;$('wlive').textContent='active: '+d.live.replace(/\n/g,' | ');wallDraw();}
function wallDraw(){
  const box=$('wcards');if(!box)return;box.innerHTML='';
  WALL.forEach(w=>{
    const c=el('div','panel');
    const opts=['',...IMGS.includes(w.path)||!w.path?IMGS:[w.path,...IMGS]];
    c.innerHTML=`<h3>${w.name}</h3><div class="wthumb" style="aspect-ratio:16/9;background:#05060a;border:1px solid var(--line);border-radius:8px;overflow:hidden">${w.path?`<img loading="lazy" alt="wallpaper preview" style="width:100%;height:100%;object-fit:cover" src="${imgUrl(w.path)}">`:'<div class="note" style="padding:12px">none set, shows the Hyprland default</div>'}</div>
    <select aria-label="${w.name} image">${opts.map(o=>`<option value="${o}"${o===w.path?' selected':''}>${o?o.replace(/^\/home\/[^/]+/,'~'):'(none)'}</option>`).join('')}</select>
    <input type="text" aria-label="${w.name} custom path" placeholder="or type a full path under your home folder" style="width:100%" maxlength="400">
    <div class="ctl"><label>fit</label><select data-f>${FITS.map(f=>`<option${f===w.fit?' selected':''}>${f}</option>`).join('')}</select></div>`;
    c.querySelector('select').onchange=e=>{w.path=e.target.value;wallDraw();};
    c.querySelector('input').onchange=e=>{if(e.target.value.trim()){w.path=e.target.value.trim();wallDraw();}};
    c.querySelector('[data-f]').onchange=e=>{w.fit=e.target.value;};
    box.appendChild(c);
  });
}

api('/api/state').then(load);
</script></body></html>
"""

if __name__ == "__main__":
    main()
