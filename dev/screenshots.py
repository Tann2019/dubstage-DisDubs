# -*- coding: utf-8 -*-
"""
screenshots.py - erzeugt die Bilder in docs/ mit den echten Programmen.
screenshots.py - renders the images in docs/ with the real apps.

Laeuft unter Windows (GitHub Actions: .github/workflows/screenshots.yml),
damit Schrift und Darstellung genau so aussehen wie beim Nutzer:

  1. DubForge laedt einen Ausschnitt aus dem Video, erkennt die Clips,
     erzeugt Untertitel mit der eingebauten Spracherkennung  -> dubforge.png
  2. DubForge baut daraus einen Pack
  3. DubStage: Menue mit dem Pack                             -> dubstage-menu.png
  4. DubStage: eine Zeile waehrend der Aufnahme               -> dubstage-record.png
  5. DubStage: das Finale                                     -> dubstage-finale.png

Die "Aufnahmen" sind die Originalzeilen, leicht verschoben - im Runner gibt
es kein Mikrofon.

    python dev/screenshots.py --video tos.mov --start 0:10 --end 1:05
"""

import argparse
import json
import os
import runpy
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import numpy as np
from PIL import ImageGrab

import dubforge_core as pc
import dubstage_core as ds
import transcription as tr

W, H = 1280, 1000


def pump(win, seconds):
    end = time.time() + seconds
    while time.time() < end:
        win.update()
        time.sleep(0.03)


def grab(win, path):
    win.lift()
    win.attributes("-topmost", True)
    pump(win, 0.6)
    x, y = win.winfo_rootx(), win.winfo_rooty()
    w, h = win.winfo_width(), win.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(path)
    print("  ->", path, "%dx%d" % (w, h), flush=True)


def settings(name, data):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        json.dump(data, f)


# ==========================================================================
def forge(args):
    settings("dubforge_settings.json", {
        "lang": "en", "check_updates": False, "src_mode": "file",
        "last_url": os.path.abspath(args.video), "separate": False,
        "t_start": args.start, "t_end": args.end, "pack_name": args.pack,
        "asr_language": "en", "asr_model": args.model})
    ns = runpy.run_path("DubForge.pyw", run_name="screenshots")
    App = ns["App"]
    App._check_update = lambda self: None
    app = App()
    app.geometry("%dx%d+0+0" % (W, H))
    pump(app, 1.0)

    print("DubForge: analyse", flush=True)
    t0, t1 = pc.parse_time(args.start), pc.parse_time(args.end)
    app._do_analyze(os.path.abspath(args.video), "file", t0, t1, False)
    app._after_analyze()

    print("DubForge: transcribe", flush=True)
    transcript = tr.transcribe(app.audio_path, "en", args.model, "cpu",
                               lambda m, p: None)
    # Clips so, wie man sie nach dem Durchsehen hat: eine Sprechzeile je
    # Clip, zu lange Saetze an der Wortgrenze geteilt.
    clips = []
    for seg in transcript.segments:
        words = [w for w in seg.words if w.end > w.start] or []
        if not words:
            continue
        cur = [words[0]]
        for w in words[1:]:
            if w.end - cur[0].start > 5.5:
                clips.append(cur)
                cur = [w]
            else:
                cur.append(w)
        clips.append(cur)
    app.clips = [{"start": max(0.0, c[0].start - 0.08),
                  "end": min(app.duration, c[-1].end + 0.12),
                  "name": "clip%02d" % (i + 1),
                  "caption": "".join(w.text for w in c).strip()}
                 for i, c in enumerate(clips)]
    app.transcript = transcript
    print("  %d clips" % len(app.clips), flush=True)
    for c in app.clips:
        print("   %6.2f %6.2f  %s" % (c["start"], c["end"], c["caption"]))
    if not app.clips:
        raise SystemExit("Keine Sprache im Ausschnitt gefunden.")

    app.selected = min(3, len(app.clips) - 1)
    app._zoom_all()
    app.refresh_list()
    app._load_caption()
    app.draw_wave()
    app.status.configure(text="Analysis finished.")
    app.prog.configure(value=100)
    pump(app, 1.0)
    grab(app, os.path.join(args.out, "dubforge.png"))

    print("DubForge: build pack", flush=True)
    app._do_build(args.pack, sorted([dict(c) for c in app.clips],
                                    key=lambda c: c["start"]))
    pump(app, 0.5)
    app.destroy()


# ==========================================================================
def stage(args):
    settings("dubstage_settings.json", {"lang": "en", "check_updates": False})
    ns = runpy.run_path("DubStage.pyw", run_name="screenshots")
    Game = ns["Game"]
    g_ = Game.__init__.__globals__
    Game._check_update = lambda self: None
    g = Game()
    g.geometry("1200x900+0+0")
    pump(g, 4.0)                       # Vorschaubilder entstehen im Hintergrund
    grab(g, os.path.join(args.out, "dubstage-menu.png"))

    names = [p.name for p in g.packs]
    g.sel_pack = names.index(args.pack)
    if not g.mic.available:            # ohne sounddevice: nur fuer die Pruefung
        import tkinter as tk
        g.mic.sd = object()
        g.mic_var = tk.StringVar(g, "")
    print("DubStage: load pack", flush=True)
    g.start_round()
    end = time.time() + 180
    while g.screen != "stage" and time.time() < end:
        pump(g, 0.2)
    if g.screen != "stage":
        raise SystemExit("DubStage hat den Pack nicht geladen.")
    pump(g, 0.5)

    lines = g.pack.lines
    rng = np.random.default_rng(7)

    def fake_take(line, shift=0.12):
        pad = np.zeros(int(shift * ds.SR), dtype=np.float32)
        noise = rng.normal(0, 0.004, len(line.audio)).astype(np.float32)
        return np.concatenate([pad, line.audio * 0.85 + noise])

    # --- Aufnahme laeuft: die ersten Zeilen sind schon eingesprochen.
    cur = min(2, len(lines) - 1)
    for l in lines[:cur]:
        l.take = fake_take(l)
    g.line_i = cur
    line = lines[cur]
    elapsed = line.duration * 0.55
    take = fake_take(line)[:int((elapsed) * ds.SR)]
    step = int(ds.SR * ds.ENV_MS / 1000.0)
    k = len(take) // step
    env = np.abs(take[:k * step].reshape(k, step)).max(axis=1)
    g.mic._env = env.tolist()
    g.mic._env_step = step
    g._set_phase("record", 30)
    g._play = None
    g.sync()
    g.show_frame(line.start + elapsed)
    g._overlay(g_["t"]("recording"), g_["RED"], 34)
    g._draw_strip_take(live=True)
    g._strip_head(elapsed)
    pump(g, 0.3)
    grab(g, os.path.join(args.out, "dubstage-record.png"))

    # --- Finale mitten in einer Zeile mit Untertitel.
    g._force_idle()
    g.mic._env = []
    for l in lines:
        l.take = fake_take(l)
    g.mic.play = lambda data: None
    g.mic.stop_play = lambda: None
    g.build_finale()
    pump(g, 0.6)
    target = next((l for l in lines[len(lines) // 2:] if l.caption), lines[-1])
    if g._play:
        g._play["t0"] = time.perf_counter() - (target.start + 0.4)
    pump(g, 0.4)
    grab(g, os.path.join(args.out, "dubstage-finale.png"))
    g._force_idle()
    g.destroy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", default="0:10")
    ap.add_argument("--end", default="1:05")
    ap.add_argument("--pack", default="Tears_of_Steel")
    ap.add_argument("--model", default="small")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    forge(args)
    stage(args)


if __name__ == "__main__":
    main()
