# -*- coding: utf-8 -*-
"""
GUI-Tests fuer DubForge / GUI tests. Oeffnen ein echtes Tk-Fenster.

    python -m unittest discover tests -v

Uebersprungen ohne Anzeige oder ohne ffmpeg / skipped without a display
or ffmpeg. Der komplette Ablauf: analysieren -> Spuren -> abspielen ->
bauen -> DubStage laedt -> zip -> wieder oeffnen -> neu bauen.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import dubforge_core as pc  # noqa: E402
from test_core import make_test_video, HAVE_FFMPEG  # noqa: E402

try:
    import tkinter as tk
    _probe = tk.Tk()
    _probe.destroy()
    HAVE_DISPLAY = True
except Exception:
    HAVE_DISPLAY = False


def load_app_module():
    spec = importlib.util.spec_from_file_location(
        "dubforge_app", os.path.join(ROOT, "DubForge.pyw"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD_OPTS = {"dub": True, "author": "Tester", "vheight": 720, "has_video": True}


class E:
    """Minimales Maus-Event / minimal mouse event."""
    def __init__(self, x, y):
        self.x, self.y = x, y


@unittest.skipUnless(HAVE_DISPLAY, "no display")
class AppSmoke(unittest.TestCase):
    """Nur die Oberflaeche, ohne ffmpeg / UI only, synthetic data."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()
        cls.m.set_lang("en")

    def setUp(self):
        import numpy as np
        self.app = self.m.App()
        app = self.app
        sr = 8000
        tt = np.arange(0, 20 * sr) / sr
        env = (np.sin(tt * 1.3) > 0.2) * 1.0
        app.wave_data = (np.sin(tt * 1400) * env * 0.8).astype("float32")
        app.wave_sr, app.duration = sr, 20.0
        app.tracks = [app._new_track("Snake")]
        app.clips = [{"start": 1.0, "end": 2.4, "track": 0, "caption": "a"},
                     {"start": 4.0, "end": 6.0, "track": 0, "caption": ""},
                     {"start": 9.5, "end": 10.2, "track": 0, "caption": "c"}]
        app.selected = 0
        app._after_analyze()
        app.update()

    def tearDown(self):
        self.app.dirty = False
        self.app.destroy()

    def test_tracks_and_moves(self):
        app = self.app
        self.assertEqual(app.add_track("Otacon"), 1)
        app.selected = 1
        app._move_selected_track(1)
        self.assertEqual(app.clips[1]["track"], 1)
        # drag a new clip into lane 1, overlapping clip 0 in lane 0
        y = app._lane_top(1) + 10
        app._canvas_down(E(app._t2x(1.5), y))
        app._canvas_move(E(app._t2x(3.0), y))
        app._canvas_up(E(app._t2x(3.0), y))
        app.update()
        lane1 = [c for c in app.clips if c["track"] == 1]
        self.assertEqual(len(lane1), 2)
        self.assertTrue(any(abs(c["start"] - 1.5) < 0.05 for c in lane1))
        # move a clip body across lanes with the mouse
        idx = next(i for i, c in enumerate(app.clips) if abs(c["start"] - 1.5) < 0.05)
        cx = app._t2x(2.0)
        app._canvas_down(E(cx, app._lane_top(1) + 12))
        self.assertEqual(app.selected, idx)
        app._canvas_move(E(cx + 40, app._lane_top(0) + 12))
        app._canvas_up(E(cx + 40, app._lane_top(0) + 12))
        moved = app.clips[app.selected]
        self.assertEqual(moved["track"], 0)
        self.assertGreater(moved["start"], 1.5)

    def test_undo_redo_split_dup_delete(self):
        app = self.app
        n = len(app.clips)
        app._split_selected(); self.assertEqual(len(app.clips), n + 1)
        app.undo(); self.assertEqual(len(app.clips), n)
        app.redo(); self.assertEqual(len(app.clips), n + 1)
        app._duplicate_selected(); self.assertEqual(len(app.clips), n + 2)
        app._delete_selected(); self.assertEqual(len(app.clips), n + 1)
        app.undo(); app.undo(); app.undo()
        self.assertEqual(len(app.clips), n)

    def test_caption_flow_and_stats(self):
        app = self.app
        app.caption_var.set("typed"); app._caption_save()
        self.assertEqual(app.clips[0]["caption"], "typed")
        app._caption_next()
        self.assertEqual(app.selected, 1)
        self.assertIn("3 clips", app.stats_lbl.cget("text"))

    def test_language_switch_keeps_state(self):
        app = self.app
        app.lang_var.set("Deutsch"); app._change_lang(); app.update()
        self.assertEqual(len(app.clips), 3)
        self.assertEqual(len(app.tree.get_children()), 3)
        app.lang_var.set("English"); app._change_lang(); app.update()

    def test_hit_testing_and_cursor(self):
        app = self.app
        kind, ref = app._hit(app._t2x(1.7), app._lane_top(0) + 10)
        self.assertEqual((kind, ref), ("body", 0))
        kind, ref = app._hit(app._t2x(2.4), app._lane_top(0) + 10)
        self.assertEqual(kind, "edge_end")
        kind, ref = app._hit(app._t2x(3.0), app._lane_top(0) + 10)
        self.assertEqual((kind, ref), ("lane", 0))
        kind, ref = app._hit(20, app._lane_top(0) + 10)
        self.assertEqual((kind, ref), ("gutter", 0))

    def test_tools_missing_state(self):
        app = self.app
        app._on_tools({"ffmpeg": False, "ytdlp": False, "demucs": False},
                      None, None, None)
        app.update()
        self.assertEqual(str(app.analyze_btn.cget("state")), "disabled")
        self.assertTrue(app.warn_lbl.winfo_ismapped())
        self.assertFalse(app.sep_var.get())
        self.assertEqual(str(app.sep_chk.cget("state")), "disabled")
        app._on_tools({"ffmpeg": True, "ytdlp": True, "demucs": True},
                      (True, True), "2026.08.01", 3)
        app.update()
        self.assertEqual(str(app.analyze_btn.cget("state")), "normal")
        self.assertFalse(app.warn_lbl.winfo_ismapped())

    def test_pump_survives_bad_callback(self):
        app = self.app

        def boom():
            raise RuntimeError("callback exploded")
        app.msgq.put(("done", boom))
        app.update(); time.sleep(0.15); app.update()
        app.msgq.put(("log", "still alive"))
        time.sleep(0.15); app.update()
        self.assertIn("still alive", app.log.get("1.0", "end"))
        self.assertIsNotNone(app._pump_id)

    def test_redetect_keeps_track_and_caption(self):
        app = self.app
        app.add_track("Otacon")
        app.clips[1]["track"] = 1
        app.clips[1]["caption"] = "kept"
        app.redetect(quiet=True)
        near = [c for c in app.clips if abs(c["start"] - 4.0) < 1.0]
        self.assertTrue(near)
        self.assertEqual(near[0]["track"], 1)
        self.assertEqual(near[0]["caption"], "kept")

    def test_url_change_clears_span(self):
        app = self.app
        app.src_mode.set("url")
        app.url_var.set("https://youtu.be/one"); app.update()
        app.t_start.set("1:00"); app.t_end.set("2:00")
        app.url_var.set("https://youtu.be/two"); app.update()
        self.assertEqual(app.t_start.get(), "")
        self.assertEqual(app.t_end.get(), "")

    def test_track_menu_ops(self):
        app = self.app
        app.add_track("B")
        app.move_track(0, 1)
        self.assertEqual([t["name"] for t in app.tracks], ["B", "Snake"])
        self.assertTrue(all(c["track"] == 1 for c in app.clips))
        app.recolor_track(0)
        app.delete_track(0)
        self.assertEqual(len(app.tracks), 1)
        self.assertEqual(len(app.clips), 3)


@unittest.skipUnless(HAVE_DISPLAY and HAVE_FFMPEG, "needs display and ffmpeg")
class FullRun(unittest.TestCase):
    """Der komplette Ablauf mit echtem Video / the full run with a real video."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()
        cls.m.set_lang("en")
        cls.d = tempfile.mkdtemp(prefix="dfrun_")
        cls.video = make_test_video(os.path.join(cls.d, "src.mp4"))
        cls.m.OUT_DIR = os.path.join(cls.d, "packs")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def pump(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.app.update()
            time.sleep(0.03)

    def test_full_run(self):
        m = self.m
        app = self.app = m.App()
        try:
            app.update()
            app.sep_var.set(False)
            app._do_analyze(self.video, "file", None, None, False,
                            {"maxlen": 6.0, "sens": 1.0})
            app._after_analyze(); app.update()
            self.assertEqual(len(app.clips), 3)
            self.assertTrue(app.video_has_stream)

            # --- Standbild / still preview arrives
            self.pump(1.5)
            self.assertTrue(app.preview.find_all(), "no preview image drawn")

            # --- Wiedergabe / playback: backend chosen, playhead moves,
            #     frames animate, stops by itself
            c = app.clips[0]
            app._play_selected()
            self.pump(0.8)
            self.assertIsNotNone(app._play, "playback did not start")
            self.assertIn(getattr(app, "_last_backend", None),
                          ("sounddevice", "ffplay", "winsound"))
            self.assertGreater(app.playhead, c["start"] + 0.2)
            self.pump(0.6)
            self.assertGreater(app._play_frame_idx, 0, "preview did not animate")
            self.pump(c["end"] - c["start"])
            self.assertIsNone(app._play, "playback did not stop")

            # --- Spuren / tracks
            app.tracks[0]["name"] = "Snake"
            app.add_track("Otacon")
            app.clips[1]["track"] = 1
            app.clips.append({"start": 1.8, "end": 3.2, "track": 1,
                              "caption": "overlap"})
            app.clips[0]["caption"] = "first"
            app.refresh_list(); app.update()

            # --- bauen / build
            app.pack_name.set("Run"); app.author.set("Tester")
            clips = sorted([dict(x) for x in app.clips],
                           key=lambda x: (x["start"], x["track"]))
            app._do_build("Run", clips, [dict(t) for t in app.tracks], BUILD_OPTS)
            app._build_then = lambda: None       # kein Dialog im Test / no dialog
            app._after_build()
            dest = app.built_path
            self.assertTrue(dest and os.path.isdir(dest))
            self.assertFalse(os.path.isdir(dest + ".building"))
            files = sorted(os.listdir(dest))
            self.assertIn("01_Snake_0-940.wav", files)
            self.assertIn("02_Otacon_1-800.wav", files)
            for f in ("dub_video.mp4", "_captions.json", "_TIMESTAMPS.txt",
                      "_pack_info.ini", "_dubforge.json", "_README.txt"):
                self.assertIn(f, files)

            # --- DubStage liest es / DubStage loads it
            import dubstage_core as sc
            pack = sc.load_pack(dest)
            self.assertIsNotNone(pack)
            self.assertEqual(len(pack.lines), 4)
            self.assertEqual([l.name for l in pack.lines][:2], ["Snake", "Otacon"])
            self.assertEqual(pack.lines[0].caption, "first")

            # --- zip
            z = pc.zip_pack(dest)
            self.assertTrue(os.path.isfile(z))

            # --- wieder oeffnen / reopen, exact round trip, rebuild in place
            before = [(round(x["start"], 3), round(x["end"], 3), x["track"],
                       x["caption"]) for x in clips]
            app._do_open_pack(dest); app._after_open(); app.update()
            after = [(round(x["start"], 3), round(x["end"], 3), x["track"],
                      x["caption"]) for x in app.clips]
            self.assertEqual(after, before)
            self.assertEqual(app.author.get(), "Tester")
            self.assertTrue(app.video_from_pack)
            clips = sorted([dict(x) for x in app.clips],
                           key=lambda x: (x["start"], x["track"]))
            app._do_build("Run", clips, [dict(t) for t in app.tracks], BUILD_OPTS)
            app._build_then = lambda: None
            app._after_build()
            self.assertTrue(os.path.isfile(os.path.join(dest, "dub_video.mp4")))
            self.assertEqual(app.built_path, dest)

            # Wiedergabe nach dem Wiederoeffnen / playback after reopening
            app._play_selected(); self.pump(0.8)
            self.assertIsNotNone(app._play)
            app._stop_play()
            self.assertIsNone(app._play)

            # --- Abbrechen: ein langer ffmpeg-Job wird gekillt und die
            #     Oberflaeche wird wieder frei / cancel kills a long job
            long_out = os.path.join(self.d, "long.wav")

            def slow():
                pc.run([pc.ffmpeg(), "-y", "-loglevel", "error", "-re", "-f", "lavfi",
                        "-i", "sine=frequency=440:duration=600",
                        "-c:a", "pcm_s16le", long_out], log=app._log)
            app._bg(slow, what="slow")
            self.pump(0.6)
            self.assertTrue(app.busy)
            app.cancel_job()
            self.pump(1.5)
            self.assertFalse(app.busy, "cancel did not free the UI")
            self.assertEqual(str(app.cancel_btn.cget("state")), "disabled")

            # --- fehlgeschlagene Analyse laesst die Sitzung heil /
            #     a failed analyse keeps the session intact
            n_before = len(app.clips)
            work_before = app.work
            try:
                app._do_analyze(os.path.join(self.d, "nope.mp4"), "file",
                                None, None, False, {"maxlen": 6.0, "sens": 1.0})
            except Exception:
                pass
            self.assertEqual(len(app.clips), n_before)
            self.assertEqual(app.work, work_before)
            self.assertTrue(os.path.isfile(app.audio_path))
        finally:
            app.dirty = False
            app.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
