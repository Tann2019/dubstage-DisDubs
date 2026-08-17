# -*- coding: utf-8 -*-
"""
Kern-Tests fuer dubforge_core / core tests.

    python -m unittest discover tests -v

Tests, die ffmpeg brauchen, werden uebersprungen, wenn keins da ist.
Tests needing ffmpeg are skipped when it is missing.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import dubforge_core as pc  # noqa: E402

HAVE_FFMPEG = bool(pc.find_tool("ffmpeg") and pc.find_tool("ffprobe"))


def make_test_video(path, seconds=12):
    """Testbild + Sinuston in drei Bursts / test pattern + tone bursts."""
    pc.run([pc.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=%d" % seconds,
            "-f", "lavfi", "-i", "sine=frequency=440:duration=%d" % seconds,
            "-af", "volume='if(between(t,1,2.5)+between(t,4,6)+between(t,8,9.2),"
                   "1,0.001)':eval=frame",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", path])
    return path


class SubtitleParsing(unittest.TestCase):

    def test_srt(self):
        cues = pc.parse_subtitles(
            "1\n00:00:01,000 --> 00:00:02,500\nHallo\nWelt\n\n"
            "2\n00:00:03,000 --> 00:00:04,000\nZwei\n")
        self.assertEqual(cues, [(1.0, 2.5, "Hallo Welt"), (3.0, 4.0, "Zwei")])

    def test_vtt_tags_stripped(self):
        cues = pc.parse_subtitles(
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.500\n<c>Hello</c> <i>there</i>\n")
        self.assertEqual(cues, [(1.0, 2.5, "Hello there")])

    def test_vtt_short_timestamps(self):
        cues = pc.parse_subtitles("WEBVTT\n\n00:01.000 --> 00:02.000\nx\n")
        self.assertEqual(cues, [(1.0, 2.0, "x")])

    def test_youtube_rolling_auto_captions(self):
        v = ("WEBVTT\n\n"
             "00:00:00.000 --> 00:00:01.500 align:start position:0%\n \n"
             "hello<00:00:00.500><c> there</c>\n\n"
             "00:00:01.500 --> 00:00:01.510 align:start position:0%\n"
             "hello there\n \n\n"
             "00:00:01.510 --> 00:00:03.000 align:start position:0%\n"
             "hello there\ngeneral<00:00:02.000><c> kenobi</c>\n\n"
             "00:00:03.000 --> 00:00:03.010\ngeneral kenobi\n \n")
        cues = pc.parse_subtitles(v)
        self.assertEqual([c[2] for c in cues], ["hello there", "general kenobi"])
        self.assertAlmostEqual(cues[0][0], 0.0)
        self.assertAlmostEqual(cues[1][0], 1.51)

    def test_assign_captions_by_overlap_and_offset(self):
        cues = [(11.0, 12.5, "A"), (14.0, 15.0, "B")]
        clips = [{"start": 1.0, "end": 2.4, "caption": ""},
                 {"start": 4.1, "end": 4.9, "caption": "keep"},
                 {"start": 7.0, "end": 8.0, "caption": ""}]
        n = pc.assign_captions(clips, cues, offset=10.0)
        self.assertEqual(n, 1)
        self.assertEqual(clips[0]["caption"], "A")
        self.assertEqual(clips[1]["caption"], "keep")
        self.assertEqual(clips[2]["caption"], "")
        n = pc.assign_captions(clips, cues, offset=10.0, overwrite=True)
        self.assertEqual(clips[1]["caption"], "B")


class FileNames(unittest.TestCase):

    def test_clip_filename_carries_speaker_and_cue(self):
        fn = pc.clip_filename(3, "Solid Snake", 5.46, dub=True)
        self.assertEqual(fn, "03_Solid_Snake_5-460.wav")
        self.assertEqual(pc.timestamp_from_name(fn), 5.46)
        self.assertEqual(pc.label_from_name(fn), "Solid Snake")

    def test_voice_pack_has_no_cue(self):
        fn = pc.clip_filename(1, "Voice", 5.46, dub=False)
        self.assertEqual(fn, "01_Voice.wav")
        self.assertIsNone(pc.timestamp_from_name(fn))

    def test_safe_name_and_long_labels(self):
        self.assertEqual(pc.safe_name("Mei Ling!"), "Mei_Ling")
        self.assertEqual(pc.safe_name("!!!", "clip"), "clip")
        long = "A" * 45
        fn = pc.clip_filename(1, long, 1.0, dub=True)
        self.assertEqual(pc.label_from_name(fn), long)
        self.assertEqual(pc.timestamp_from_name(fn), 1.0)

    def test_progress_parsing(self):
        self.assertAlmostEqual(pc._progress_of("[download]  45.2% of 10MiB", None), 0.452)
        self.assertAlmostEqual(pc._progress_of("frame=1 time=00:00:06.00 x", 12.0), 0.5)
        self.assertAlmostEqual(pc._progress_of(" 33%|###   | 5.8/17.5", None), 0.33)
        self.assertIsNone(pc._progress_of("hello", 10))

    def test_ytdlp_error_classes(self):
        self.assertEqual(pc.classify_ytdlp_error(
            "ERROR: Sign in to confirm you" + chr(39) + "re not a bot")[0], "yt_signin")
        self.assertEqual(pc.classify_ytdlp_error("HTTP Error 403: Forbidden"), ("yt_403", True))
        self.assertEqual(pc.classify_ytdlp_error("Video unavailable")[0], "yt_unavail")
        self.assertEqual(pc.classify_ytdlp_error("random")[0], None)

    def test_matches_dubstage_reader_convention(self):
        # DubStage/DisDubs: fraction scaled by its own length
        self.assertEqual(pc.timestamp_from_name("01_x_5-2.wav"), 5.2)
        self.assertEqual(pc.timestamp_from_name("01_x_5-002.wav"), 5.002)


class DisDubsCheck(unittest.TestCase):

    def clips(self, tracks_per_clip):
        return [{"start": i * 2.0, "end": i * 2.0 + 1.0, "track": tr, "caption": "x"}
                for i, tr in enumerate(tracks_per_clip)]

    def test_half_rule(self):
        tracks = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        self.assertEqual(pc.disdubs_parts(tracks, self.clips([0, 1, 2, 0, 1])), 1)
        self.assertEqual(pc.disdubs_parts(tracks, self.clips([0, 1, 2, 0, 1, 2])), 3)
        w = pc.disdubs_check(tracks, self.clips([0, 1, 2, 0, 1]))
        self.assertTrue(any("EINE" in x or "ONE" in x for x in w))

    def test_names(self):
        tracks = [{"name": "Snake"}, {"name": "snake"}, {"name": "!!!"},
                  {"name": "x" * 41}]
        w = "\n".join(pc.disdubs_check(tracks, self.clips([0, 1, 2, 3] * 3)))
        self.assertIn("Snake / snake", w)
        self.assertIn("!!!", w)
        self.assertIn("40", w)

    def test_clean_pack_has_no_warnings(self):
        tracks = [{"name": "Snake"}, {"name": "Otacon"}]
        self.assertEqual(pc.disdubs_check(tracks, self.clips([0, 1, 0, 1]),
                                          duration=60, has_backing=True,
                                          has_video=True), [])

    def test_length_and_overlap(self):
        tracks = [{"name": "Snake"}]
        clips = [{"start": 0, "end": 2.5, "track": 0, "caption": "a"},
                 {"start": 2.0, "end": 4.0, "track": 0, "caption": "b"}]
        w = pc.disdubs_check(tracks, clips, duration=200)
        self.assertEqual(len([x for x in w if "3:00" in x]), 1)
        self.assertTrue(any("1 s" in x for x in w))


class CutClips(unittest.TestCase):
    """Clips in die neue Zeitrechnung schieben / clips into the new time."""

    def test_shift_drop_and_clamp(self):
        clips = [{"start": 0.5, "end": 1.5, "caption": "weg"},
                 {"start": 1.8, "end": 2.6, "caption": "kante"},
                 {"start": 3.0, "end": 4.0, "caption": "drin"},
                 {"start": 7.5, "end": 8.5, "caption": "kante2"},
                 {"start": 9.0, "end": 9.8, "caption": "auch weg"}]
        kept, dropped = pc.cut_clips(clips, 2.0, 8.0)
        self.assertEqual(dropped, 2)
        self.assertEqual([c["caption"] for c in kept],
                         ["kante", "drin", "kante2"])
        # verschoben / shifted
        self.assertAlmostEqual(kept[1]["start"], 1.0)
        self.assertAlmostEqual(kept[1]["end"], 2.0)
        # an den Kanten gekappt / clamped at the edges
        self.assertAlmostEqual(kept[0]["start"], 0.0)
        self.assertAlmostEqual(kept[2]["end"], 6.0)
        # die Vorlage bleibt unberuehrt / the input is not touched
        self.assertAlmostEqual(clips[2]["start"], 3.0)

    def test_too_short_leftovers_are_dropped(self):
        kept, dropped = pc.cut_clips([{"start": 1.99, "end": 3.0}], 2.0, 8.0)
        self.assertEqual(len(kept), 1)
        kept, dropped = pc.cut_clips([{"start": 1.0, "end": 2.02}], 2.0, 8.0)
        self.assertEqual((kept, dropped), ([], 1))


class I18n(unittest.TestCase):
    """Beide Sprachen muessen dieselben Platzhalter tragen / same placeholders."""

    def _pairs(self, table, name):
        import re
        bad = []
        fmt = re.compile(r"%(?:\(\w+\))?[-#0 +]*\d*(?:\.\d+)?[sdifr%]")
        for key, pair in table.items():
            if not (isinstance(pair, tuple) and len(pair) == 2):
                bad.append("%s.%s: not a (de, en) pair" % (name, key))
                continue
            de, en = pair
            if sorted(fmt.findall(de)) != sorted(fmt.findall(en)):
                bad.append("%s.%s: placeholders differ" % (name, key))
        return bad

    def test_core_messages(self):
        self.assertEqual(self._pairs(pc._MSG, "M"), [])

    def test_app_strings(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "dubforge_app_i18n", os.path.join(os.path.dirname(HERE), "DubForge.pyw"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(self._pairs(mod.T, "T"), [])


class PackFiles(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="dfcore_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_pack_info_ini(self):
        pc.write_pack_info(self.d, 'My "Scene"', ["Me", "", None])
        txt = open(os.path.join(self.d, "_pack_info.ini"), encoding="utf-8").read()
        self.assertIn('title="My \\"Scene\\""', txt)
        self.assertIn('authors=["Me"]', txt)

    def test_project_roundtrip(self):
        data = {"version": 1, "tracks": [{"name": "A"}], "clips": []}
        pc.write_project(self.d, data)
        self.assertEqual(pc.read_project(self.d), data)
        self.assertTrue(pc.PROJECT_FILE.startswith("_"))
        self.assertTrue(pc.PACK_INFO_FILE.startswith("_"))

    def test_zip_has_folder_at_top_level(self):
        pack = os.path.join(self.d, "MyPack")
        os.makedirs(pack)
        open(os.path.join(pack, "dub_video.mp4"), "wb").write(b"x")
        z = pc.zip_pack(pack)
        names = zipfile.ZipFile(z).namelist()
        self.assertTrue(all(n.startswith("MyPack/") for n in names))
        self.assertIn("MyPack/dub_video.mp4", names)


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not found")
class WithFfmpeg(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="dfmedia_")
        cls.video = make_test_video(os.path.join(cls.d, "src.mp4"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_probe_and_video_stream(self):
        self.assertAlmostEqual(pc.probe_duration(self.video), 12.0, delta=0.3)
        self.assertTrue(pc.has_video_stream(self.video))

    def test_detect_clips_finds_bursts(self):
        wav = os.path.join(self.d, "a.wav")
        pc.extract_audio(self.video, wav)
        data, sr = pc.load_mono(wav)
        found = pc.detect_clips(data, sr)
        self.assertEqual(len(found), 3, found)
        self.assertAlmostEqual(found[0][0], 1.0, delta=0.15)

    def test_cut_media_is_frame_accurate(self):
        # Der Schnitt muss genau sitzen: die Clips der Sitzung rechnen
        # danach in der neuen Zeit weiter.
        # Toene liegen bei 1-2.5, 4-6 und 8-9.2 s; [3, 7] faengt in der
        # Stille an und haelt genau den mittleren Ton.
        out = os.path.join(self.d, "cut.mkv")
        pc.cut_media(self.video, 3.0, 7.0, out)
        self.assertAlmostEqual(pc.probe_duration(out), 4.0, delta=0.12)
        self.assertTrue(pc.has_video_stream(out))

        # Der Ton wandert mit: der mittlere Ton beginnt bei 4 s, nach dem
        # Schnitt ab 3 s also bei 1 s.
        wav = os.path.join(self.d, "cut.wav")
        pc.extract_audio(out, wav)
        data, sr = pc.load_mono(wav)
        found = pc.detect_clips(data, sr)
        self.assertTrue(found, "no clips in the cut span")
        self.assertAlmostEqual(found[0][0], 1.0, delta=0.2)
        self.assertEqual(len(found), 1, found)

        # Nur Ton (wav): sample-genau.
        wav_cut = os.path.join(self.d, "cut2.wav")
        pc.cut_media(wav, 1.0, 2.0, wav_cut, video=False)
        self.assertAlmostEqual(pc.probe_duration(wav_cut), 1.0, delta=0.05)

    def test_decode_pcm(self):
        d = pc.decode_pcm(self.video, 1.0, 2.5)
        self.assertEqual(d.shape[1], 2)
        self.assertAlmostEqual(d.shape[0] / 44100.0, 1.5, delta=0.05)
        self.assertGreater(int(abs(d.astype("int32")).max()), 1000)

    def test_frames(self):
        png = os.path.join(self.d, "f.png")
        pc.extract_frame(self.video, 1.0, png, width=160)
        self.assertGreater(os.path.getsize(png), 100)
        seq = os.path.join(self.d, "seq")
        pc.extract_frames_range(self.video, 1.0, 2.0, seq, fps=10, width=160)
        self.assertGreaterEqual(len(os.listdir(seq)), 9)

    def test_export_clip_and_reopen_legacy(self):
        pack = os.path.join(self.d, "Legacy")
        os.makedirs(pack, exist_ok=True)
        wav = os.path.join(self.d, "a.wav")
        pc.extract_audio(self.video, wav)
        pc.export_clip(wav, 1.0, 2.5, os.path.join(pack, "01_Snake_1-000.wav"))
        pc.export_clip(wav, 4.0, 6.0, os.path.join(pack, "02_Otacon_4-000.wav"))
        shutil.copy(self.video, os.path.join(pack, "dub_video.mp4"))
        pc.write_captions(pack, {"01_Snake_1-000.wav": "hi"})
        info = pc.read_pack_for_edit(pack)
        self.assertEqual([t["name"] for t in info["tracks"]], ["Snake", "Otacon"])
        self.assertEqual(len(info["clips"]), 2)
        self.assertEqual(info["clips"][0]["caption"], "hi")
        self.assertAlmostEqual(info["clips"][0]["end"], 2.5, delta=0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
