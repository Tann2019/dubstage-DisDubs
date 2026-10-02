# -*- coding: utf-8 -*-
"""
snap_forge.py - DubForge mit einem echten Pack oeffnen und abfotografieren.
snap_forge.py - open a real pack in DubForge and take a screenshot.

Fuer die Arbeit an der Oberflaeche: die eigenen Einstellungen bleiben
unberuehrt (eigene Einstellungsdatei im Temp-Ordner).
For UI work: your own settings stay untouched (temp settings file).

    python dev/snap_forge.py "packs/ED - Emo Yeah Emo why Emo" out.png [WxH] [en|de]
    python dev/snap_forge.py - empty.png          # nothing loaded
"""

import os
import runpy
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from PIL import ImageGrab  # noqa: E402


def pump(win, seconds):
    end = time.time() + seconds
    while time.time() < end:
        win.update()
        time.sleep(0.03)


def screen_factor(win):
    """Ohne DPI-Bewusstsein skaliert Windows das Fenster hoch; ImageGrab
    arbeitet in echten Pixeln. / Windows stretches DPI-unaware windows."""
    if os.name != "nt":
        return 1.0
    import ctypes
    try:
        aware = ctypes.c_int()
        ctypes.windll.shcore.GetProcessDpiAwareness(None, ctypes.byref(aware))
        if aware.value:
            return 1.0
        hdc = ctypes.windll.user32.GetDC(0)
        real = ctypes.windll.gdi32.GetDeviceCaps(hdc, 118)    # DESKTOPHORZRES
        virt = ctypes.windll.gdi32.GetDeviceCaps(hdc, 8)      # HORZRES
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return real / float(virt) if virt else 1.0
    except Exception:
        return 1.0


def main():
    pack, out = sys.argv[1], sys.argv[2]
    size = sys.argv[3] if len(sys.argv) > 3 else "1440x1000"
    lang = sys.argv[4] if len(sys.argv) > 4 else "en"
    w, h = (int(v) for v in size.split("x"))   # bei 100 % / at 100 %

    ns = runpy.run_path("DubForge.pyw", run_name="snap")
    tmp = tempfile.mkdtemp()
    cfg = os.path.join(tmp, "dubforge_settings.json")
    ns["App"].__init__.__globals__["CFG_PATH"] = cfg
    ns["save_cfg"]({"lang": lang, "check_updates": False, "src_mode": "file",
                    "log_open": False, "pack_name": "Emo",
                    "geometry": "%dx%d+0+0" % (w, h)})
    ns["appwin"].set_dpi_aware()       # wie _main / like _main
    App = ns["App"]
    App._check_update = lambda self: None
    app = App()
    app.geometry("%dx%d+0+0" % (ns["px"](w), ns["px"](h)))
    pump(app, 1.0)
    if pack != "-":
        folder = os.path.abspath(pack)
        app._bg(lambda: app._do_open_pack(folder, None),
                on_done=app._after_open, what="open")
        end = time.time() + 120
        while app.busy and time.time() < end:
            pump(app, 0.2)
        pump(app, 1.0)
        if app.clips:
            app.selected = min(2, len(app.clips) - 1)
            app.refresh_list()
            app.draw_wave()
    app.lift()
    app.attributes("-topmost", True)
    pump(app, 1.5)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    ww, hh = app.winfo_width(), app.winfo_height()
    f = screen_factor(app)
    ImageGrab.grab(bbox=(int(x * f), int(y * f), int((x + ww) * f),
                         int((y + hh) * f)), all_screens=True).save(out)
    print("saved", out, ww, hh)
    app.dirty = False
    app.destroy()


if __name__ == "__main__":
    main()
