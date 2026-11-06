#!/usr/bin/env python3
"""Local web UI that tunes the running Hyprland live and saves named profiles."""
import http.server, json, os, re, shutil, socket, subprocess, sys, threading, time, webbrowser

PORT = 38800
HOST = "127.0.0.1"
HYPR = os.path.expanduser("~/.config/hypr")
REPO = os.path.expanduser("~/repos/hyprarch/dotfiles/.config/hypr")
NAME_FILE = os.path.join(HYPR, ".profile-name")
IDLE_SECONDS = 2 * 3600

# key: (min, max, type); every value reaching Lua is validated against this table
NUM = {
    "gi": (0, 40, int), "go": (0, 80, int), "bw": (0, 10, int), "ang": (0, 360, int),
    "rad": (0, 40, int), "ao": (0.3, 1, float), "io": (0.3, 1, float), "dim": (0, 0.8, float),
    "sr": (0, 60, int), "sp": (1, 4, int), "bs": (1, 20, int), "bp": (1, 6, int), "vib": (0, 1, float),
    "speed": (0.1, 15, float), "x0": (0, 1, float), "y0": (-1, 2, float), "x1": (0, 1, float), "y1": (-1, 2, float),
}
BOOL = ("shadow", "blur", "anim", "barblur", "animws", "animfade")
DEFAULT = dict(gi=5, go=20, bw=2, ang=45, c1="#33ccff", c2="#00ff99", layout="dwindle", rad=10, ao=1.0, io=1.0,
               dim=0.0, sr=4, sp=3, bs=3, bp=1, vib=0.1696, shadow=True, blur=True, anim=True, barblur=False,
               speed=3.0, x0=0.23, y0=1.0, x1=0.32, y1=1.0, style="popin 80%", animws=False, animfade=False)
STYLES = ("popin 80%", "popin 60%", "slide", "gnomed")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
NAME = re.compile(r"^[a-z0-9-]{1,32}$")


def hyprctl(*args):
    r = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=10)
    return (r.stdout + r.stderr).strip()


def clean(raw):
    s = dict(DEFAULT)
    for k, (lo, hi, t) in NUM.items():
        if k in raw:
            s[k] = t(min(max(float(raw[k]), lo), hi))
    for k in BOOL:
        if k in raw:
            s[k] = bool(raw[k])
    for k in ("c1", "c2"):
        if k in raw and COLOR.match(str(raw[k])):
            s[k] = str(raw[k]).lower()
    if raw.get("layout") in ("dwindle", "master"):
        s["layout"] = raw["layout"]
    if raw.get("style") in STYLES:
        s["style"] = raw["style"]
    return s


def lua_for(s):
    b = lambda v: "true" if v else "false"
    out = f'''hl.config({{
    general = {{
        gaps_in = {s["gi"]},
        gaps_out = {s["go"]},
        border_size = {s["bw"]},
        col = {{ active_border = {{ colors = {{"rgba({s["c1"][1:]}ee)", "rgba({s["c2"][1:]}ee)"}}, angle = {s["ang"]} }} }},
        layout = "{s["layout"]}",
    }},
    decoration = {{
        rounding = {s["rad"]},
        active_opacity = {s["ao"]},
        inactive_opacity = {s["io"]},
        dim_inactive = {b(s["dim"] > 0)}, dim_strength = {s["dim"]},
        shadow = {{ enabled = {b(s["shadow"])}, range = {s["sr"]}, render_power = {s["sp"]} }},
        blur = {{ enabled = {b(s["blur"])}, size = {s["bs"]}, passes = {s["bp"]}, vibrancy = {s["vib"]} }},
    }},
    animations = {{ enabled = {b(s["anim"])} }},
}})

hl.curve("tune", {{ type = "bezier", points = {{ {{{s["x0"]}, {s["y0"]}}}, {{{s["x1"]}, {s["y1"]}}} }} }})
hl.animation({{ leaf = "windows", enabled = true, speed = {s["speed"]}, bezier = "tune", style = "{s["style"]}" }})
'''
    if s["animws"]:
        out += f'hl.animation({{ leaf = "workspaces", enabled = true, speed = {s["speed"]}, bezier = "tune", style = "slide" }})\n'
    if s["animfade"]:
        out += f'hl.animation({{ leaf = "fade", enabled = true, speed = {s["speed"]}, bezier = "tune" }})\n'
    if s["barblur"]:
        out += '\nhl.layer_rule({ name = "blur-waybar", match = { namespace = "waybar" }, blur = true })\n'
    return out


def live_eval(s):
    """Apply to the running session without touching files; returns config errors."""
    code = "\n".join(l for l in lua_for(s).splitlines() if "layer_rule" not in l)
    res = hyprctl("eval", code)
    time.sleep(0.05)
    err = hyprctl("configerrors")
    return res, err


def read_live():
    """Read the running compositor's values back, falling back to defaults."""
    s = dict(DEFAULT)

    def opt(name):
        try:
            return json.loads(hyprctl("getoption", name, "-j"))
        except Exception:
            return {}
    first_int = lambda d: int(d.get("css", "0").split()[0]) if "css" in d else None
    for key, name in (("gi", "general:gaps_in"), ("go", "general:gaps_out")):
        v = first_int(opt(name))
        if v is not None:
            s[key] = v
    ints = {"bw": "general:border_size", "rad": "decoration:rounding", "sr": "decoration:shadow:range",
            "sp": "decoration:shadow:render_power", "bs": "decoration:blur:size", "bp": "decoration:blur:passes"}
    for k, name in ints.items():
        d = opt(name)
        if "int" in d:
            s[k] = d["int"]
    floats = {"ao": "decoration:active_opacity", "io": "decoration:inactive_opacity", "vib": "decoration:blur:vibrancy"}
    for k, name in floats.items():
        d = opt(name)
        if "float" in d:
            s[k] = round(d["float"], 4)
    d = opt("decoration:dim_inactive")
    d2 = opt("decoration:dim_strength")
    s["dim"] = round(d2.get("float", 0), 2) if d.get("bool") else 0.0
    for k, name in (("shadow", "decoration:shadow:enabled"), ("blur", "decoration:blur:enabled"), ("anim", "animations:enabled")):
        d = opt(name)
        if "bool" in d:
            s[k] = d["bool"]
    d = opt("general:layout")
    if d.get("str") in ("dwindle", "master"):
        s["layout"] = d["str"]
    m = re.match(r"([0-9a-f]{2})([0-9a-f]{6}) ([0-9a-f]{2})([0-9a-f]{6}) (\d+)deg", opt("general:col.active_border").get("gradient", ""))
    if m:
        s["c1"], s["c2"], s["ang"] = "#" + m.group(2), "#" + m.group(4), int(m.group(5))
    try:
        anims, beziers = json.loads(hyprctl("animations", "-j"))
        w = next(a for a in anims if a["name"] == "windows")
        if w.get("overridden"):
            s["speed"], s["style"] = float(w["speed"]), w["style"] or s["style"]
            bz = next((b for b in beziers if b["name"] == w["bezier"]), None)
            if bz:
                s["x0"], s["y0"], s["x1"], s["y1"] = bz["X0"], bz["Y0"], bz["X1"], bz["Y1"]
    except Exception:
        pass
    prof = os.path.join(HYPR, "profile.lua")
    if os.path.exists(prof) and "layer_rule" in open(prof).read():
        s["barblur"] = True
    return clean(s)


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
    d = {"state": s, "lua": lua_for(s), "profiles": names, "active": active, "errors": hyprctl("configerrors")}
    d.update(extra or {})
    return d


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
        self.send(404, "not found", "text/plain")

    def do_POST(self):
        Handler.last = time.time()
        if not self.ok_origin() or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(403, "forbidden", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/apply":
                s = clean(body.get("state", {}))
                _, err = live_eval(s)
                return self.send(200, json.dumps({"lua": lua_for(s), "errors": err, "state": s}))
            if self.path == "/api/save":
                name, s = str(body.get("name", "")), clean(body.get("state", {}))
                if not NAME.match(name) or name == "default":
                    return self.send(400, json.dumps({"error": "name must be a-z, 0-9, dash (not 'default')"}))
                text = lua_for(s)
                for d in (HYPR, REPO):
                    if os.path.isdir(d):
                        open(os.path.join(d, f"config-{name}.lua"), "w").write(text)
                activate(name)
                return self.send(200, json.dumps(snapshot({"saved": name})))
            if self.path == "/api/profile":
                name = str(body.get("name", ""))
                if name != "default" and not os.path.exists(os.path.join(HYPR, f"config-{name}.lua")):
                    return self.send(400, json.dumps({"error": "unknown profile"}))
                activate(name)
                return self.send(200, json.dumps(snapshot()))
            if self.path == "/api/delete":
                name = str(body.get("name", ""))
                if NAME.match(name):
                    for d in (HYPR, REPO):
                        f = os.path.join(d, f"config-{name}.lua")
                        if os.path.exists(f):
                            os.remove(f)
                    if profiles()[1] == name:
                        activate("default")
                return self.send(200, json.dumps(snapshot()))
            if self.path == "/api/revert":
                hyprctl("reload")
                time.sleep(0.4)
                return self.send(200, json.dumps(snapshot()))
            if self.path == "/api/quit":
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
.wrap{max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
h1{font:700 24px ui-monospace,monospace;margin:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;display:flex;flex-direction:column;gap:10px}
h3{margin:0;font:600 12px ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.row{display:grid;grid-template-columns:120px 1fr 56px;gap:10px;align-items:center}
.row label{color:var(--dim)} .row output{font:600 12px ui-monospace,monospace;text-align:right}
.chg{color:var(--warn)}
input[type=range]{width:100%;accent-color:var(--accent)}
button,select,input[type=text]{font:600 13px ui-monospace,monospace;color:var(--text);background:#0d1117;border:1px solid var(--line);border-radius:8px;padding:7px 12px}
button{cursor:pointer} button:hover{border-color:var(--accent)} button.on{border-color:var(--accent);color:var(--accent)}
button.primary{border-color:var(--ok);color:var(--ok)} button.danger:hover{border-color:var(--bad);color:var(--bad)}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tog{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.pill{font:600 12px ui-monospace,monospace;padding:3px 10px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}
.pill.dirty{color:var(--warn);border-color:var(--warn)} .pill.clean{color:var(--ok);border-color:var(--ok)}
input[type=color]{width:36px;height:26px;border:1px solid var(--line);border-radius:6px;background:none;padding:0}
pre{margin:0;background:#0a0d12;border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;font:12.5px/1.6 ui-monospace,monospace;color:#b9c4d4;max-height:340px}
.err{color:var(--bad);font:12px ui-monospace,monospace;white-space:pre-wrap}
.prof{display:flex;gap:8px;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.prof.active{border-color:var(--ok)}
.note{color:var(--dim);font-size:12.5px}
.rig{position:relative;width:100%;border-radius:8px;overflow:hidden;background:#05060a;border:1px solid var(--line)}
.mon{position:absolute;top:0;overflow:hidden;outline:1px solid #2c3340}
.mon.hd{background:radial-gradient(80% 90% at 30% 20%,#2a2f72 0%,transparent 60%),radial-gradient(70% 80% at 80% 90%,#3a1d5c 0%,transparent 60%),#0c0f26}
.mon.ed{background:#000;color:#cfcfcf;display:flex;align-items:center;justify-content:center;font:12px system-ui}
.bar{position:absolute;left:0;right:0;top:0;display:flex;align-items:center;justify-content:flex-end;gap:.9em;padding-right:.6em;color:#fff;z-index:6;font-family:system-ui;white-space:nowrap;overflow:hidden}
.bar.bg{background:rgba(14,17,24,.55);backdrop-filter:blur(10px)}
.win{position:absolute;cursor:pointer}
.win::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:var(--bw);background:var(--bcol);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;z-index:2}
.win .in{position:absolute;inset:0;border-radius:inherit;overflow:hidden;background:rgba(18,20,28,var(--op));padding:calc(var(--bw) + .5em);font:var(--fs) ui-monospace,monospace;color:#cfd8e6;line-height:1.4}
.win.blur .in{backdrop-filter:blur(var(--blur)) saturate(var(--sat))}
.win .g{color:#00ff99}.win .d{color:#7f8a9c}
@keyframes pop{from{transform:scale(.8);opacity:0}to{transform:scale(1);opacity:1}}
.win.pop{animation:pop var(--dur) var(--ease)}
</style></head><body><div class="wrap">
<header><h1>hypr-tune</h1><div class="tog"><span class="pill" id="dirty">live</span><button id="revert">revert to saved</button><button id="quit" class="danger">quit server</button></div></header>
<div class="panel"><h3>Preview</h3><div class="rig" id="rig"></div>
  <div class="tog"><button id="addw">+ window</button><button id="remw">- window</button><button id="replay">replay open animation</button><span class="note">approximation of your two screens (HDMI left, laptop right); click a window to focus it</span></div></div>
<div class="grid">
  <div class="panel" id="p-general"><h3>General</h3></div>
  <div class="panel" id="p-deco"><h3>Decoration</h3></div>
  <div class="panel" id="p-anim"><h3>Animations</h3></div>
  <div class="panel"><h3>Profiles</h3><div id="profs" class="tog" style="flex-direction:column;align-items:stretch"></div>
    <div class="tog"><input type="text" id="pname" placeholder="new-profile-name" aria-label="profile name" maxlength="32"><button id="save" class="primary">save as new &amp; activate</button></div>
    <p class="note">Changes apply live as you drag. Save as new writes config-NAME.lua; overwrite replaces an existing profile with the current settings. Either one becomes the profile loaded at login. Revert reloads the saved profile.</p></div>
</div>
<div class="panel"><h3>Generated Lua</h3><div class="err" id="err"></div><pre id="lua"></pre></div>
</div>
<script>
const SL={
 general:[['gi','gaps_in',0,40,1],['go','gaps_out',0,80,1],['bw','border_size',0,10,1],['ang','border angle',0,360,5]],
 deco:[['rad','rounding',0,40,1],['ao','active_opacity',0.3,1,0.01],['io','inactive_opacity',0.3,1,0.01],['dim','dim_inactive',0,0.8,0.01],['sr','shadow range',0,60,1],['sp','shadow power',1,4,1],['bs','blur size',1,20,1],['bp','blur passes',1,6,1],['vib','blur vibrancy',0,1,0.01]],
 anim:[['speed','speed (x100ms)',0.1,15,0.1],['x0','curve x0',0,1,0.01],['y0','curve y0',-1,2,0.01],['x1','curve x1',0,1,0.01],['y1','curve y1',-1,2,0.01]]
};
const PRESETS={'ease-out snappy':[0.23,1,0.32,1],'overshoot':[0.34,1.56,0.64,1],'linear':[0,0,1,1],'default-ish':[0.25,0.1,0.25,1]};
let S={},SAVED={},timer=null;
const $=id=>document.getElementById(id);
function build(){
  for(const [g,rows] of Object.entries(SL)){
    const p=$('p-'+g);
    rows.forEach(([k,l,min,max,st])=>{
      const r=document.createElement('div');r.className='row';
      r.innerHTML=`<label for="s-${k}">${l}</label><input id="s-${k}" type="range" min="${min}" max="${max}" step="${st}"><output id="o-${k}"></output>`;
      r.querySelector('input').oninput=e=>{S[k]=parseFloat(e.target.value);changed();};
      p.appendChild(r);
    });
  }
  $('p-general').insertAdjacentHTML('beforeend',`<div class="tog"><span class="note">border colors</span><input type="color" id="c1" aria-label="border color 1"><input type="color" id="c2" aria-label="border color 2"></div><div class="tog"><span class="note">layout</span><button data-l="dwindle">dwindle</button><button data-l="master">master</button></div>`);
  $('p-deco').insertAdjacentHTML('beforeend',`<div class="tog"><button data-t="shadow">shadow</button><button data-t="blur">blur</button><button data-t="barblur">blur waybar (layer rule)</button></div>`);
  $('p-anim').insertAdjacentHTML('beforeend',`<div class="tog"><button data-t="anim">animations on</button><button data-t="animws">+ workspaces</button><button data-t="animfade">+ fade</button></div><div class="tog"><span class="note">style</span><select id="style"><option>popin 80%</option><option>popin 60%</option><option>slide</option><option>gnomed</option></select></div><div class="tog" id="presets"></div>`);
  Object.entries(PRESETS).forEach(([n,v])=>{const b=document.createElement('button');b.textContent=n;b.onclick=()=>{[S.x0,S.y0,S.x1,S.y1]=v;changed();};$('presets').appendChild(b);});
  document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{S[b.dataset.t]=!S[b.dataset.t];changed();});
  document.querySelectorAll('[data-l]').forEach(b=>b.onclick=()=>{S.layout=b.dataset.l;changed();});
  $('c1').oninput=e=>{S.c1=e.target.value;changed();};$('c2').oninput=e=>{S.c2=e.target.value;changed();};
  $('style').onchange=e=>{S.style=e.target.value;changed();};
}
function paint(){
  for(const rows of Object.values(SL))rows.forEach(([k])=>{$('s-'+k).value=S[k];const o=$('o-'+k);o.textContent=S[k];o.className=S[k]!==SAVED[k]?'chg':'';});
  $('c1').value=S.c1;$('c2').value=S.c2;$('style').value=S.style;
  document.querySelectorAll('[data-t]').forEach(b=>b.classList.toggle('on',!!S[b.dataset.t]));
  document.querySelectorAll('[data-l]').forEach(b=>b.classList.toggle('on',b.dataset.l===S.layout));
  preview();
  const dirty=JSON.stringify(S)!==JSON.stringify(SAVED);
  $('dirty').textContent=dirty?'unsaved live changes':'matches saved';$('dirty').className='pill '+(dirty?'dirty':'clean');
}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});return r.json();}
function changed(){paint();clearTimeout(timer);timer=setTimeout(async()=>{const d=await api('/api/apply',{state:S});$('lua').textContent=d.lua;$('err').textContent=d.errors||'';},60);}
function profs(d){
  const box=$('profs');box.innerHTML='';
  ['default',...d.profiles].forEach(n=>{
    const row=document.createElement('div');row.className='prof'+(n===d.active?' active':'');
    row.innerHTML=`<span>${n}${n===d.active?' (active)':''}</span><span class="tog"></span>`;
    const t=row.querySelector('.tog');
    if(n!==d.active){const a=document.createElement('button');a.textContent='apply';a.onclick=async()=>load(await api('/api/profile',{name:n}));t.appendChild(a);}
    if(n!=='default'){const o=document.createElement('button');o.textContent='overwrite';o.title='save current settings into '+n;o.className='primary';o.onclick=async()=>{if(!confirm('Overwrite profile '+n+' with the current settings?'))return;const r=await api('/api/save',{name:n,state:S});if(r.error)return $('err').textContent=r.error;load(r);};t.appendChild(o);}
    if(n!=='default'){const x=document.createElement('button');x.textContent='delete';x.className='danger';x.onclick=async()=>{if(confirm('Delete profile '+n+'?'))load(await api('/api/delete',{name:n}));};t.appendChild(x);}
    box.appendChild(row);
  });
}
function load(d){S=d.state;SAVED=JSON.parse(JSON.stringify(d.state));$('lua').textContent=d.lua;$('err').textContent=d.errors||'';profs(d);paint();}
$('save').onclick=async()=>{const n=$('pname').value.trim();if(!n)return $('pname').focus();const d=await api('/api/save',{name:n,state:S});if(d.error)return $('err').textContent=d.error;$('pname').value='';load(d);};
$('revert').onclick=async()=>load(await api('/api/revert',{}));
$('quit').onclick=async()=>{await api('/api/quit',{});document.body.innerHTML='<p style="padding:2rem">hypr-tune stopped. Press the keybind to start it again.</p>';};

let NW=2,FOC=0,POP=-1;
const CURVEMAP=()=>`cubic-bezier(${S.x0},${S.y0},${S.x1},${S.y1})`;
const lay=(n,x,y,w,h)=>{if(S.layout==='master'){if(n===1)return[[x,y,w,h]];const o=[[x,y,w*.55,h]];for(let i=1;i<n;i++)o.push([x+w*.55,y+(i-1)*h/(n-1),w*.45,h/(n-1)]);return o;}
  const o=[];for(let i=0;i<n;i++){if(i===n-1){o.push([x,y,w,h]);break;}if(w>=h){o.push([x,y,w/2,h]);x+=w/2;w/=2;}else{o.push([x,y,w,h/2]);y+=h/2;h/=2;}}return o;};
const rig=$('rig'),mh=document.createElement('div'),me=document.createElement('div'),wins=[];
mh.className='mon hd';me.className='mon ed';me.textContent='This text is random.';
for(const m of[mh,me]){const b=document.createElement('div');b.className='bar';b.innerHTML='<span>CPU 22%</span><span>us</span><b>23:56</b>';m.appendChild(b);m._bar=b;rig.appendChild(m);}
const APPS=[['murrou@laptop ~','$ kubectl get nodes','k3s-master   Ready','k3s-worker-2 Ready','k3s-gpu      Ready','$ _'],['claude','> tune the desktop','* applying live...','auto mode on'],['dolphin','~/repos/home-cloud','ansible/','argocd/','terraform/']];
function preview(){
  const W=rig.clientWidth,s=W/3200;rig.style.height=(1080*s)+'px';
  mh.style.left='0px';mh.style.width=(1920*s)+'px';mh.style.height=(1080*s)+'px';
  me.style.left=(1920*s)+'px';me.style.width=(1280*s)+'px';me.style.height=(720*s)+'px';
  const bp=Math.max(24*s,12);for(const m of[mh,me]){m._bar.style.height=bp+'px';m._bar.style.fontSize=Math.max(7,13*s)+'px';m._bar.classList.toggle('bg',S.barblur);}
  const dur=S.anim?S.speed*100:0,ease=CURVEMAP(),go=S.go*s,gi=S.gi*s;
  while(wins.length<NW){const e=document.createElement('div');e.className='win';e.onclick=()=>{FOC=wins.indexOf(e);preview();};wins.push(e);mh.appendChild(e);}
  while(wins.length>NW)wins.pop().remove();
  if(FOC>=NW)FOC=NW-1;
  const r=lay(NW,go-gi/2,bp+go-gi/2,1920*s-2*go+gi,1080*s-bp-2*go+gi);
  wins.forEach((e,i)=>{const[x,y,w,h]=r[i],g=gi/2,act=i===FOC,t=e.style;
    t.transition=dur?`left ${dur}ms ${ease},top ${dur}ms ${ease},width ${dur}ms ${ease},height ${dur}ms ${ease}`:'none';
    t.left=(x+g)+'px';t.top=(y+g)+'px';t.width=Math.max(0,w-2*g)+'px';t.height=Math.max(0,h-2*g)+'px';
    t.borderRadius=(S.rad*s)+'px';t.setProperty('--bw',(S.bw*s)+'px');
    t.setProperty('--bcol',act?`linear-gradient(${S.ang}deg,${S.c1},${S.c2})`:'rgba(89,89,89,.67)');
    t.setProperty('--op',Math.min(1,(act?S.ao:S.io)*(act?1:1-S.dim)));t.setProperty('--fs',Math.max(6,11*s)+'px');
    t.setProperty('--blur',(S.bs*S.bp*2.6*s)+'px');t.setProperty('--sat',1+S.vib*2);t.setProperty('--dur',dur+'ms');t.setProperty('--ease',ease);
    t.boxShadow=S.shadow?`0 ${S.sr*s*.5}px ${S.sr*s*2.5}px ${S.sr*s*.3*(5-S.sp)}px rgba(0,0,0,${.18+.1*(5-S.sp)})`:'none';
    t.zIndex=act?3:2;e.classList.toggle('blur',S.blur);
    const a=APPS[i%APPS.length];e.innerHTML=`<div class="in"><div class="g">${a[0]}</div>${a.slice(1).map(l=>`<div class="d">${l}</div>`).join('')}</div>`;
    if(i===POP&&S.anim){e.classList.remove('pop');void e.offsetWidth;e.classList.add('pop');}});
  POP=-1;
}
$('addw').onclick=()=>{NW=Math.min(5,NW+1);POP=NW-1;preview();};
$('remw').onclick=()=>{NW=Math.max(1,NW-1);preview();};
$('replay').onclick=()=>{POP=FOC;preview();};
window.addEventListener('resize',preview);
build();api('/api/state').then(load);
</script></body></html>
"""

if __name__ == "__main__":
    main()
