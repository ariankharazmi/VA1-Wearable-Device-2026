"""
Aries Launcher (CTk) — CoverFlow fluid (circular icons, fast + smooth)
- Loads icons from: VisionAriesAssets (Fall 2025, Color)
- 5 icons visible, bounce-free glide
- On-demand cache with quantized sizes/alpha (low churn)
"""

import os, time, threading
from datetime import datetime
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
try:
    import psutil
except Exception:
    psutil = None
try:
    import requests
except Exception:
    requests = None

import platform
IS_PI = platform.machine().startswith(("armv7l","armv6l","aarch64")) and "raspberrypi" in platform.platform().lower()

if IS_PI:
    WIDTH, HEIGHT = 640, 400
    TARGET_FPS    = 30
    BASE_ICON     = 112
    SPACING       = 148
    FLOW_LAMBDA   = 18.0
    SIZE_STEP_PX  = 4
    ALPHA_STEP_8  = 32

# ---------- Configuration -------------
WIDTH, HEIGHT = 1280, 720
TARGET_FPS     = 144
ASSETS_DIR     = os.path.join(os.getcwd(), "VisionAriesAssets (Fall 2025, Color)")

APPS = [
    ("assistant.png",     "Assistant"),
    ("augreality.png",    "AugReality"),
    ("avatar.png",        "Avatar"),
    ("bluetooth.png",     "Bluetooth"),
    ("camera.png",        "Camera"),
    ("eyetrack.png",      "EyeTrack"),
    ("gesture.png",       "Gesture"),
    ("gps.png",           "GPS"),
    ("livestream.png",    "LiveStream"),
    ("localassistant.png","LocalAI"),
    ("music.png",         "Music"),
    ("phone.png",         "Phone"),
    ("photo.png",         "Photo"),
    ("plugin.png",        "Plugin"),
    ("settings.png",      "Settings"),
    ("spatialaudio.png",  "SpatialAudio"),
    ("theme.png",         "Theme"),
    ("track.png",         "Track"),
    ("translate.png",     "Translate"),
    ("video.png",         "Video"),
]

LOGO_PATH = os.path.join(ASSETS_DIR, "logonew.png")
MIC_PATH  = os.path.join(ASSETS_DIR, "mic.png")

BUILD_STR   = "VA-OS1.1 · Pandora Build · Oct 2025"


LABEL_COLOR = "black"
SPACING     = 180
BASE_ICON   = 132
SCALE_DROP  = 0.14
ALPHA_DROP  = 0.22
FLOW_LAMBDA = 26.0
SIZE_STEP_PX  = 2
ALPHA_STEP_8  = 8

def load_image(path):
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None

def circle_crop_rgba(img: Image.Image, size: int) -> Image.Image:
    img = img.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out

def make_soft_glow(radius: int, alpha: int = 140) -> Image.Image:
    w = h = radius * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    layers = [
        (0.55, alpha),
        (1.15, int(alpha * 0.70)),
        (2.00, int(alpha * 0.40)),
        (3.00, int(alpha * 0.18)),
    ]
    for scale, a in layers:
        r = radius * scale
        d.ellipse((w/2-r, h/2-r, w/2+r, h/2+r), fill=(255,255,255,a))
    img = img.filter(ImageFilter.GaussianBlur(int(radius * 0.30)))
    return img

def safe_batt():
    if psutil and hasattr(psutil, "sensors_battery"):
        try:
            b = psutil.sensors_battery()
            if b: return f"{int(b.percent)}%"
        except Exception: pass
    return "–%"

def safe_cpu():
    if psutil:
        try: return f"{psutil.cpu_percent():.0f}%"
        except Exception: pass
    return "–%"

def safe_ram():
    if psutil:
        try: return f"{psutil.virtual_memory().percent:.0f}%"
        except Exception: pass
    return "–%"

# ---------- User Interface ----------
class StatusBar:
    def __init__(self, canvas: ctk.CTkCanvas):
        self.cv = canvas
        self.console = []
        self.weather = "…"
        self.text_id = None
        self._last_update = 0.0

    def append(self, line: str):
        self.console.append(line); self.console = self.console[-3:]

    def tick(self):
        nowt = time.perf_counter()
        if nowt - self._last_update < 0.25:
            return
        self._last_update = nowt
        now = datetime.now().strftime("%-I:%M %p")
        lines = "\n".join(self.console)
        txt = f"{now} · {safe_batt()} · {self.weather} · CPU {safe_cpu()} · RAM {safe_ram()}\n{BUILD_STR}"
        if lines: txt += "\n" + lines
        if self.text_id is None:
            self.text_id = self.cv.create_text(16, 84, anchor="nw",
                                               fill="white", font=("Helvetica", 12), text=txt)
        else:
            self.cv.itemconfigure(self.text_id, text=txt)

class CoverFlow:
    def __init__(self, canvas: ctk.CTkCanvas, apps,
                 base_icon=BASE_ICON, spacing=SPACING):
        self.cv = canvas
        self.base_icon = base_icon
        self.spacing   = spacing
        self.sel = 0
        self.sel_anim = 0.0

        self.icons = []
        self._img_refs = [None]*5
        self.label_id = None

        # Load assets
        self.apps = []
        for fn, label in apps:
            img = load_image(os.path.join(ASSETS_DIR, fn)) or Image.new("RGBA",(base_icon,base_icon),(200,200,200,255))
            self.apps.append({
                "id": os.path.splitext(fn)[0],
                "label": label,
                "img": img,
                "cache": {}
            })

        # Strong glow effect under center
        glow_img = make_soft_glow(int(base_icon*1.2), 140)
        self._glow_tk = ImageTk.PhotoImage(glow_img)
        self.glow_id = self.cv.create_image(0, 0, image=self._glow_tk, anchor="nw")

        # five icon slots + label
        for _ in range(5):
            self.icons.append(self.cv.create_image(0, 0, image=None, anchor="nw"))
        self.label_id = self.cv.create_text(0, 0, text="", fill=LABEL_COLOR,
                                            font=("Helvetica", 16, "bold"))

    def _get_tkimg(self, app, size_px: int, alpha: float):
        size_q  = max(14, int(round(size_px / SIZE_STEP_PX) * SIZE_STEP_PX))
        a255    = int(max(0, min(255, round(alpha * 255 / ALPHA_STEP_8) * ALPHA_STEP_8)))
        key = (size_q, a255)
        cache = app["cache"]
        if key in cache:
            return cache[key]
        # build
        circ = circle_crop_rgba(app["img"], size_q)
        if a255 < 255:
            am = circ.split()[-1].point(lambda p, a=a255: int(p * a / 255))
            circ.putalpha(am)
        tkimg = ImageTk.PhotoImage(circ)
        cache[key] = tkimg
        return tkimg

    def step(self, dt):
        n = len(self.apps)
        if n == 0: return
        d = self.sel - self.sel_anim
        if d >  n/2: d -= n
        if d < -n/2: d += n
        dt = max(1/480, dt)
        alpha = 1.0 - pow(2.718281828, -FLOW_LAMBDA * dt)
        self.sel_anim += d * alpha
        if abs(d) < 1e-4:
            self.sel_anim = round(self.sel_anim)
        self._redraw_icons()

    def update_selection(self, delta):
        if self.apps:
            self.sel = (self.sel + delta) % len(self.apps)

    def current_app(self):
        if not self.apps: return None
        return self.apps[self.sel % len(self.apps)]

    def _redraw_icons(self):
        midx, midy = WIDTH//2, HEIGHT//2 - 10
        x0   = midx - 2*self.spacing
        frac = self.sel_anim - round(self.sel_anim)
        order = (0, 4, 1, 3, 2)

        positions = []
        for slot, i in enumerate(order):
            idx = int(round(self.sel_anim) - 2 + i) % len(self.apps)
            app = self.apps[idx]
            dist  = abs(i - 2 + frac)
            scale = max(0.70, 1.0 - SCALE_DROP*dist)
            alpha = max(0.46, 1.0 - ALPHA_DROP*dist)

            size  = int(self.base_icon * scale)
            tkimg = self._get_tkimg(app, size, alpha)

            cx, cy = x0 + i*self.spacing, midy
            self.cv.itemconfigure(self.icons[slot], image=tkimg)
            self.cv.coords(self.icons[slot], int(cx - tkimg.width()/2), int(cy - tkimg.height()/2))
            self._img_refs[slot] = tkimg  # keep ref

            if i == 2:
                gx = int(cx - self._glow_tk.width()/2)
                gy = int(cy - self._glow_tk.height()/2 + self.base_icon*0.03)
                self.cv.coords(self.glow_id, gx, gy)

            positions.append((cx, cy, tkimg.width(), app["label"]))

        # Label
        for cx, cy, size_w, label in positions:
            if abs(cx - midx) < 2:
                self.cv.itemconfigure(self.label_id, text=label, fill=LABEL_COLOR)
                self.cv.coords(self.label_id, cx, cy + size_w/2 + 28)
                break

class VAApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.title("Aries Launcher")
        self.resizable(False, False)

        self.cv = ctk.CTkCanvas(self, width=WIDTH, height=HEIGHT, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.status = StatusBar(self.cv)
        self.cflow  = CoverFlow(self.cv, APPS)
        self.current_view = "home"

        # Keys / wheel
        self.bind("<Left>",  lambda e: self.nav(-1))
        self.bind("<Right>", lambda e: self.nav(+1))
        self.bind("<Return>", lambda e: self.open_current())
        self.bind("<space>",  lambda e: self.open_current())
        self.bind("h",        lambda e: self.go_home())
        self.bind("<Escape>", lambda e: self.quit())
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", lambda e: self.nav(+1))
        self.bind_all("<Button-5>", lambda e: self.nav(-1))

        # time-step loop
        self._last_time = time.perf_counter()
        self._tick()

    def nav(self, d):
        if self.current_view == "home":
            self.cflow.update_selection(d)

    def open_current(self):
        app = self.cflow.current_app()
        if app:
            self.status.append(f"Opened {app['label']}")

    def go_home(self):
        self.current_view = "home"

    def _wheel(self, e):
        self.nav(1 if e.delta > 0 else -1)

    def _set_weather(self, txt):
        self.status.weather = txt

    def _tick(self):
        now = time.perf_counter()
        dt  = max(1e-3, now - self._last_time)
        self._last_time = now
        if self.current_view == "home":
            self.cflow.step(dt)
        self.status.tick()
        delay_ms = max(1, int(1000 / TARGET_FPS))
        self.after(delay_ms, self._tick)

if __name__ == "__main__":
    app = VAApp()
    app.mainloop()
