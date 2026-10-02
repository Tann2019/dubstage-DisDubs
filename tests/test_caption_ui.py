# -*- coding: utf-8 -*-
"""
Whisper-Untertitel im Editor des Forks / Whisper captions in the fork's editor.

Kein Modell, kein Netz: transcription.transcribe wird ersetzt.
No model, no network: transcription.transcribe is patched.
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import transcription as tr  # noqa: E402
from test_app import load_app_module, Dialogs, HAVE_DISPLAY  # noqa: E402


def transcript():
    return tr.Transcript("fr", (tr.Segment(0, 2, "Bonjour monde", (
        tr.Word(.1, .9, " Bonjour"), tr.Word(1.1, 1.9, " monde"))),))


@unittest.skipUnless(HAVE_DISPLAY, "Tk display required")
class CaptionEditorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = load_app_module()
        cls.m.set_lang("en")
        # Eigene Einstellungsdatei - die echte bleibt unberuehrt.
        # Own settings file - the real one stays untouched.
        cls.tmp = tempfile.mkdtemp()
        cls.m.CFG_PATH = os.path.join(cls.tmp, "dubforge_settings.json")
        cls.m.save_cfg({"lang": "en"})

    @classmethod
    def tearDownClass(cls):
        cls.m.set_lang("en")
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.dlg = Dialogs().install(self.m)
        self.app = self.m.App()
        app = self.app
        app.duration = 4.0
        app.audio_path = "trimmed.wav"
        app.tracks = [app._new_track("Snake")]
        app.clips = [{"start": 0.0, "end": 2.0, "track": 0, "caption": ""}]
        app.selected = 0
        app.refresh_list()

    def tearDown(self):
        self.app.dirty = False
        self.app.destroy()

    def run_now(self):
        """_bg ohne Thread / _bg without a thread."""
        self.app._bg = lambda fn, on_done=None, **kw: (fn(), on_done and on_done())

    def test_generate_fills_and_remembers_transcript(self):
        app = self.app
        app.asr_language.set("fr")
        self.run_now()
        with patch.object(tr, "transcribe", return_value=transcript()) as rec:
            app.start_transcribe()
        self.assertEqual(rec.call_args.args[:4], ("trimmed.wav", "fr", "large-v3", "cpu"))
        self.assertEqual(app.clips[0]["caption"], "Bonjour monde")
        self.assertIsNotNone(app.transcript)
        app.undo()
        self.assertEqual(app.clips[0]["caption"], "")

    def test_prefers_separated_vocals(self):
        app = self.app
        app.vocals_path = "vocals.wav"
        app.asr_language.set("fr")
        self.run_now()
        with patch.object(tr, "transcribe", return_value=transcript()) as rec:
            app.start_transcribe()
        self.assertEqual(rec.call_args.args[0], "vocals.wav")

    def test_split_remaps_and_manual_edit_survives(self):
        app = self.app
        app.asr_language.set("fr")
        self.run_now()
        with patch.object(tr, "transcribe", return_value=transcript()):
            app.start_transcribe()
        app._split_selected()
        self.assertEqual([c["caption"] for c in app.clips], ["Bonjour", "monde"])
        app.selected = 0
        app._load_inspector()
        app.caption_var.set("Salut")
        app._caption_save()
        app.clips[0]["end"] = 1.95          # Zeiten aendern / change timing
        app.refresh_list()
        self.assertEqual(app.clips[0]["caption"], "Salut")

    def test_existing_caption_kept_unless_replace(self):
        app = self.app
        app.clips[0]["caption"] = "manuel"
        app.refresh_list()                  # Inspektor zeigt es / inspector shows it
        app.asr_language.set("fr")
        self.run_now()
        with patch.object(tr, "transcribe", return_value=transcript()):
            app.start_transcribe()
        self.assertEqual(app.clips[0]["caption"], "manuel")
        app.asr_replace.set(True)
        with patch.object(tr, "transcribe", return_value=transcript()):
            app.start_transcribe()
        self.assertEqual(app.clips[0]["caption"], "Bonjour monde")

    def test_failure_preserves_captions_and_transcript(self):
        app = self.app
        app.clips[0]["caption"] = "manuel"
        app.refresh_list()                  # Inspektor zeigt es / inspector shows it
        old = transcript()
        app.transcript = old
        app.asr_language.set("fr")
        self.run_now()
        with patch.object(tr, "transcribe", side_effect=RuntimeError("download failed")):
            with self.assertRaises(RuntimeError):
                app.start_transcribe()
        self.assertEqual(app.clips[0]["caption"], "manuel")
        self.assertIs(app.transcript, old)

    def test_language_switch_keeps_spoken_language(self):
        app = self.app
        app.asr_language.set("zh")
        app.lang_var.set("Deutsch")
        app._change_lang()
        self.assertEqual(app.asr_language.get(), "zh")
        self.m.set_lang("en")
        self.m.save_cfg({"lang": "en"})

    def test_build_gets_the_transcript(self):
        app = self.app
        app.transcript = transcript()
        app.backing_path = "x"              # keine Backing-Warnung / no warning
        self.dlg.answer = True
        app._bg = lambda fn, on_done=None, **kw: fn()
        with patch.object(app, "_do_build") as build:
            app.start_build()
        self.assertIs(build.call_args.args[3]["transcript"], app.transcript)


if __name__ == "__main__":
    unittest.main()
