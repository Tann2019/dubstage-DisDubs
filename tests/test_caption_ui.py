"""Exercise the actual editor widgets without displaying a window or networking."""

import os
import runpy
import shutil
import sys
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

import transcription as tr


@unittest.skipUnless(sys.platform == "win32" or os.environ.get("DISPLAY"), "Tk display required")
class CaptionEditorTests(unittest.TestCase):
    def setUp(self):
        namespace = runpy.run_path("DubForge.pyw", run_name="ui_test")
        self.App = namespace["App"]
        globals_ = self.App.__init__.__globals__
        original_init = tk.Tk.__init__

        def hidden_init(root, *args, **kwargs):
            original_init(root, *args, **kwargs)
            root.withdraw()

        self.patches = [
            patch.object(tk.Tk, "__init__", hidden_init),
            patch.dict(globals_, {"load_cfg": lambda: {"lang": "en", "check_updates": False},
                                  "save_cfg": lambda cfg: None}),
            patch.object(self.App, "_check_tools"),
            patch.object(self.App, "_check_update"),
        ]
        for context in self.patches:
            context.start()
            self.addCleanup(context.stop)
        self.app = self.App()
        self.addCleanup(lambda: shutil.rmtree(self.app.work, ignore_errors=True))
        self.addCleanup(self.app.destroy)
        self.app.clips = [{"name": "first", "start": 0., "end": 2., "caption": ""}]
        self.app.selected = 0
        self.app.refresh_list()
        self.app.transcript = tr.Transcript("fr", (tr.Segment(0, 2, "Bonjour monde", (
            tr.Word(.1, .9, " Bonjour"), tr.Word(1.1, 1.9, " monde"))),))

    def test_generated_caption_split_and_manual_edit(self):
        self.app._remap_captions()
        self.app.refresh_list()
        self.app._split_selected()
        self.assertEqual([c["caption"] for c in self.app.clips], ["Bonjour", "monde"])
        self.app.caption_var.set("Salut")
        self.app._caption_save()
        self.app.clips[0]["end"] = 2
        self.app._remap_captions()
        self.assertEqual(self.app.clips[0]["caption"], "Salut")

    def test_busy_blocks_edits_and_restores_readonly_selectors(self):
        self.app._set_busy(True)
        self.assertTrue(self.app.transcribe_btn.instate(["disabled"]))
        self.assertTrue(self.app.caption_entry.instate(["disabled"]))
        self.app._delete_selected()
        self.app._split_selected()
        self.assertEqual(len(self.app.clips), 1)
        self.app._set_busy(False)
        self.assertFalse(self.app.transcribe_btn.instate(["disabled"]))
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        models = [w for w in descendants(self.app.ui_root)
                  if isinstance(w, ttk.Combobox) and "large-v3" in w.cget("values")]
        self.assertEqual(len(models), 1)
        self.assertTrue(models[0].instate(["readonly", "!disabled"]))

    def test_generate_uses_main_thread_snapshot_and_commits_on_success(self):
        self.app.audio_path = "trimmed.wav"
        self.app.asr_language.set("fr")
        expected = self.app.transcript
        self.app.transcript = None
        self.app._bg = lambda fn, on_done: (fn(), on_done())
        with patch.object(tr, "transcribe", return_value=expected) as recognize:
            self.app.start_transcribe()
        self.assertEqual(recognize.call_args.args[:4], ("trimmed.wav", "fr", "large-v3", "cpu"))
        self.assertEqual(self.app.clips[0]["caption"], "Bonjour monde")
        self.assertEqual(self.app.caption_var.get(), "Bonjour monde")

    def test_generate_failure_preserves_captions_and_transcript(self):
        self.app.audio_path = "trimmed.wav"
        self.app.asr_language.set("fr")
        self.app.caption_var.set("manuel")
        expected = self.app.transcript
        self.app._bg = lambda fn, on_done: (fn(), on_done())
        with patch.object(tr, "transcribe", side_effect=RuntimeError("download failed")):
            with self.assertRaises(RuntimeError):
                self.app.start_transcribe()
        self.assertEqual(self.app.clips[0]["caption"], "manuel")
        self.assertIs(self.app.transcript, expected)

    def test_language_switch_preserves_spoken_language(self):
        self.app.asr_language.set("fr")
        self.app.lang_var.set("Deutsch")
        self.app._change_lang()
        self.assertEqual(self.app.asr_language.get(), "fr")
        self.assertEqual(self.app.transcribe_btn.cget("text"), "Untertitel generieren")

    def test_build_saves_pending_caption_before_snapshot(self):
        self.app.caption_var.set("Dernière correction")
        self.app._bg = lambda fn, on_done: fn()
        with patch.object(self.app, "_do_build") as build:
            self.app.start_build()
        self.assertEqual(build.call_args.args[1][0]["caption"], "Dernière correction")

    def test_redetect_preserves_manual_clip_and_remaps_other_clips(self):
        self.app.wave_data = [0, 1, 0]
        self.app.clips[0]["end"] = 1
        self.app.caption_var.set("Salut")
        with patch.object(self.App.redetect.__globals__["pc"], "detect_clips",
                          return_value=[(0, .8), (1, 2)]):
            self.app.redetect()
        self.assertEqual([c["caption"] for c in self.app.clips], ["Salut", "monde"])
        self.assertEqual(self.app.clips[0]["end"], 1)


if __name__ == "__main__":
    unittest.main()
