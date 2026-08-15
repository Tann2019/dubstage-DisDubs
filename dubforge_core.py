# -*- coding: utf-8 -*-
"""
dubforge_core.py  --  Kernlogik fuer DubForge / core logic.
Keine GUI hier drin, damit sich alles einzeln testen laesst.
"""

import os
import re
import sys
import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(APP_DIR, "tools")

IS_WIN = os.name == "nt"
_NOWINDOW = subprocess.CREATE_NO_WINDOW if IS_WIN else 0


# --------------------------------------------------------------------------
# Sprache / language
# --------------------------------------------------------------------------

LANG = "de"


def set_lang(code):
    """'de' oder 'en'."""
    global LANG
    LANG = "en" if str(code).lower().startswith("en") else "de"


_MSG = {
    "no_ffmpeg": (
        "ffmpeg wurde nicht gefunden.\n\n"
        "Bitte einmal Setup.bat ausfuehren, oder ffmpeg manuell installieren.",
        "ffmpeg was not found.\n\n"
        "Please run Setup.bat once, or install ffmpeg manually."),
    "no_ffprobe": (
        "ffprobe wurde nicht gefunden. Bitte Setup.bat ausfuehren.",
        "ffprobe was not found. Please run Setup.bat."),
    "no_ytdlp": (
        "yt-dlp wurde nicht gefunden. Bitte Setup.bat ausfuehren.",
        "yt-dlp was not found. Please run Setup.bat."),
    "cmd_failed": (
        "Befehl fehlgeschlagen (%s):\n%s",
        "Command failed (%s):\n%s"),
    "dl_empty": (
        "Download hat keine Datei erzeugt.",
        "The download produced no file."),
    "no_vocals": (
        "Demucs hat keine Vocals-Datei erzeugt.",
        "Demucs did not produce a vocals file."),
    "no_theora": (
        "Dieser ffmpeg kann kein OGV schreiben (libtheora/libvorbis fehlt).\n"
        "Bitte Setup.bat ausfuehren oder MP4 als Format waehlen.",
        "This ffmpeg cannot write OGV (libtheora/libvorbis missing).\n"
        "Please run Setup.bat or choose MP4 as the format."),
    "bad_time": (
        "Zeitangabe nicht verstanden: %r",
        "Could not understand the time value: %r"),
    "no_target": (
        "Zielordner existiert nicht: %s",
        "Target folder does not exist: %s"),
    "pack_exists": (
        "Pack existiert bereits: %s",
        "Pack already exists: %s"),
    "file_missing": (
        "Datei nicht gefunden: %s",
        "File not found: %s"),
    "cut_failed": (
        "Direkter Schnitt ging nicht, kodiere neu ...",
        "Direct cut failed, re-encoding ..."),
    "cut_off": (
        "Kopier-Schnitt ungenau (%.2fs statt %.2fs), kodiere neu ...",
        "Stream-copy cut was inaccurate (%.2fs instead of %.2fs), re-encoding ..."),
    "span": (
        "Zeitspanne: %.2f s",
        "Time span: %.2f s"),
    "no_pack": (
        "Kein Dub-Pack: %s\n(dub_video.* fehlt oder keine Clips mit Zeitstempel)",
        "Not a dub pack: %s\n(no dub_video.* or no clips carrying a timestamp)"),
}


def M(key, *args):
    pair = _MSG.get(key)
    if not pair:
        return key
    text = pair[1] if LANG == "en" else pair[0]
    return text % args if args else text


# --------------------------------------------------------------------------
# Externe Programme finden / locate external tools
# --------------------------------------------------------------------------

def _exe(name):
    return name + ".exe" if IS_WIN else name


def find_tool(name):
    """Sucht erst im mitgelieferten tools/-Ordner, dann im System-PATH."""
    local = os.path.join(TOOLS_DIR, _exe(name))
    if os.path.isfile(local):
        return local
    for root, _dirs, files in os.walk(TOOLS_DIR):
        if _exe(name) in files:
            return os.path.join(root, _exe(name))
    found = shutil.which(name)
    if found:
        return found
    return None


def ffmpeg():
    p = find_tool("ffmpeg")
    if not p:
        raise RuntimeError(M("no_ffmpeg"))
    return p


def ffprobe():
    p = find_tool("ffprobe")
    if not p:
        raise RuntimeError(M("no_ffprobe"))
    return p


def ffplay():
    return find_tool("ffplay")


def ytdlp():
    p = find_tool("yt-dlp")
    if p:
        return [p]
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       check=True, capture_output=True, creationflags=_NOWINDOW)
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return None


def ytdlp_version():
    """
    Gibt (Version, Alter in Tagen) zurueck. yt-dlp versioniert nach Datum,
    daraus laesst sich das Alter direkt ablesen.
    """
    yt = ytdlp()
    if not yt:
        return None, None
    out = capture(list(yt) + ["--version"]).strip()
    ver = None
    for line in out.splitlines():
        line = line.strip()
        if re.match(r"^\d{4}\.\d{2}\.\d{2}", line):
            ver = line
            break
    if not ver:
        return None, None
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", ver)
    try:
        import datetime
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return ver, (datetime.date.today() - d).days
    except Exception:
        return ver, None


def update_ytdlp(log=None):
    """
    Aktualisiert yt-dlp. Als eigenstaendige Datei in tools/ kann es sich
    selbst erneuern, ueber pip installiert muss pip ran.
    """
    local = os.path.join(TOOLS_DIR, _exe("yt-dlp"))
    if os.path.isfile(local):
        run([local, "-U"], log=log, check=False)
    else:
        run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            log=log, check=False)
    return ytdlp_version()


def run(cmd, log=None, check=True):
    """Fuehrt ein Kommando aus und streamt die Ausgabe an log(text)."""
    if log:
        log("$ " + " ".join(os.path.basename(str(c)) if i == 0 else str(c)
                            for i, c in enumerate(cmd)))
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, encoding="utf-8", errors="replace",
        creationflags=_NOWINDOW,
    )
    tail = []
    for line in proc.stdout:
        line = line.rstrip()
        tail.append(line)
        if len(tail) > 40:
            tail.pop(0)
        if log:
            log(line)
    proc.wait()
    if check and proc.returncode != 0:
        raise RuntimeError(M("cmd_failed", os.path.basename(str(cmd[0])),
                             "\n".join(tail[-15:])))
    return "\n".join(tail)


def capture(cmd):
    r = subprocess.run(cmd, capture_output=True, universal_newlines=True,
                       encoding="utf-8", errors="replace", creationflags=_NOWINDOW)
    return (r.stdout or "") + (r.stderr or "")


def check_encoders():
    """Prueft, ob der gefundene ffmpeg OGV (Theora+Vorbis) schreiben kann."""
    out = capture([ffmpeg(), "-hide_banner", "-encoders"])
    return ("libtheora" in out), ("libvorbis" in out)


# --------------------------------------------------------------------------
# Quelle beschaffen / obtain source
# --------------------------------------------------------------------------

def probe_duration(path):
    out = capture([ffprobe(), "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=nw=1:nk=1", path]).strip().splitlines()
    for line in out:
        try:
            return float(line.strip())
        except ValueError:
            continue
    return 0.0


def parse_time(text):
    """Akzeptiert '90', '1:30', '01:02:03.5', '1m30s'. Gibt Sekunden zurueck."""
    text = (text or "").strip()
    if not text:
        return None
    m = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?", text, re.I)
    if m and any(m.groups()):
        h, mi, s = m.groups()
        return int(h or 0) * 3600 + int(mi or 0) * 60 + float(s or 0)
    parts = text.replace(",", ".").split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        raise ValueError(M("bad_time", text))
    total = 0.0
    for p in parts:
        total = total * 60 + p
    return total


def fmt_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    if h:
        return "%d:%02d:%06.3f" % (h, m, s)
    return "%d:%06.3f" % (m, s)


def download_youtube(url, start, end, workdir, log=None):
    """Laedt den gewaehlten Ausschnitt als Videodatei herunter."""
    yt = ytdlp()
    if not yt:
        raise RuntimeError(M("no_ytdlp"))
    out_tmpl = os.path.join(workdir, "source.%(ext)s")
    cmd = list(yt) + [
        "--no-playlist",
        "--ffmpeg-location", os.path.dirname(ffmpeg()),
        "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
        "--merge-output-format", "mkv",
        "-o", out_tmpl,
    ]
    if start is not None or end is not None:
        s = 0.0 if start is None else float(start)
        e = "inf" if end is None else "%.3f" % float(end)
        cmd += ["--download-sections", "*%.3f-%s" % (s, e),
                "--force-keyframes-at-cuts"]
    cmd.append(url)
    run(cmd, log=log)
    for f in sorted(os.listdir(workdir)):
        if f.startswith("source."):
            return os.path.join(workdir, f)
    raise RuntimeError(M("dl_empty"))


def trim_local(path, start, end, workdir, log=None):
    """Schneidet einen lokalen Film auf die gewaehlte Zeitspanne."""
    if start is None and end is None:
        return path
    out = os.path.join(workdir, "source.mkv")
    src_dur = probe_duration(path)
    want = None
    if end is not None:
        want = max(0.05, float(end) - float(start or 0))
    elif src_dur > 0:
        want = max(0.05, src_dur - float(start or 0))

    cmd = [ffmpeg(), "-y", "-hide_banner"]
    if start:
        cmd += ["-ss", "%.3f" % float(start)]
    cmd += ["-i", path]
    if end is not None:
        cmd += ["-t", "%.3f" % want]
    cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-c", "copy",
            "-avoid_negative_ts", "make_zero", "-reset_timestamps", "1", out]
    try:
        run(cmd, log=log)
        got = probe_duration(out)
        # Der Kopier-Schnitt springt nur auf Keyframes und liegt manchmal
        # komplett daneben. Dann lieber sauber neu kodieren.
        if got > 0.1 and want and abs(got - want) <= max(0.75, want * 0.05):
            return out
        if log:
            log(M("cut_off", got, want or 0))
    except RuntimeError:
        if log:
            log(M("cut_failed"))

    cmd = [ffmpeg(), "-y", "-hide_banner"]
    if start:
        cmd += ["-ss", "%.3f" % float(start)]
    cmd += ["-i", path]
    if end is not None:
        cmd += ["-t", "%.3f" % max(0.05, float(end) - float(start or 0))]
    cmd += ["-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-crf", "18",
            "-preset", "veryfast", "-c:a", "pcm_s16le",
            "-avoid_negative_ts", "make_zero", out]
    run(cmd, log=log)
    if log:
        log(M("span", probe_duration(out)))
    return out


def extract_audio(video, out_wav, log=None):
    run([ffmpeg(), "-y", "-hide_banner", "-i", video, "-vn",
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", out_wav], log=log)
    return out_wav


# --------------------------------------------------------------------------
# Vocals trennen (Demucs)
# --------------------------------------------------------------------------

def separate_vocals(wav_path, workdir, log=None, model="htdemucs"):
    """Gibt (vocals_wav, no_vocals_wav) zurueck."""
    outdir = os.path.join(workdir, "demucs")
    os.makedirs(outdir, exist_ok=True)
    cmd = [sys.executable, "-m", "demucs", "--two-stems", "vocals",
           "-n", model, "-o", outdir, wav_path]
    run(cmd, log=log)
    stem = os.path.splitext(os.path.basename(wav_path))[0]
    for root, _dirs, files in os.walk(outdir):
        if "vocals.wav" in files and os.path.basename(root) == stem:
            return (os.path.join(root, "vocals.wav"),
                    os.path.join(root, "no_vocals.wav"))
    for root, _dirs, files in os.walk(outdir):
        if "vocals.wav" in files:
            return (os.path.join(root, "vocals.wav"),
                    os.path.join(root, "no_vocals.wav"))
    raise RuntimeError(M("no_vocals"))


# --------------------------------------------------------------------------
# Audio einlesen / analysieren
# --------------------------------------------------------------------------

def load_mono(path, sr=8000):
    """Dekodiert nach Mono-Float-Liste. Nutzt numpy wenn vorhanden."""
    tmp = tempfile.mktemp(suffix=".wav")
    try:
        run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", path,
             "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", tmp], check=True)
        with wave.open(tmp, "rb") as w:
            n = w.getnframes()
            raw = w.readframes(n)
        try:
            import numpy as np
            data = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
        except ImportError:
            data = [v / 32768.0 for v in struct.unpack("<%dh" % (len(raw) // 2), raw)]
        return data, sr
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def frame_rms(data, sr, frame_ms=20):
    """Liefert (rms_liste, frame_dauer_in_sekunden)."""
    hop = max(1, int(sr * frame_ms / 1000.0))
    try:
        import numpy as np
        arr = np.asarray(data, dtype="float32")
        usable = (len(arr) // hop) * hop
        if usable == 0:
            return [], hop / float(sr)
        blocks = arr[:usable].reshape(-1, hop)
        rms = np.sqrt((blocks ** 2).mean(axis=1))
        return rms, hop / float(sr)
    except ImportError:
        out = []
        for i in range(0, len(data) - hop + 1, hop):
            chunk = data[i:i + hop]
            out.append(math.sqrt(sum(v * v for v in chunk) / len(chunk)))
        return out, hop / float(sr)


def detect_clips(data, sr, min_silence=0.35, min_clip=0.30, max_clip=6.0,
                 pad=0.08, sensitivity=1.0):
    """
    Findet Sprechabschnitte. sensitivity: >1 = empfindlicher (mehr Clips).
    Gibt Liste von (start_s, end_s) zurueck.
    """
    rms, fdur = frame_rms(data, sr)
    if len(rms) == 0:
        return []

    try:
        import numpy as np
        r = np.asarray(rms, dtype="float32")
        peak = float(r.max())
        if peak <= 1e-6:
            return []
        floor = float(np.percentile(r, 20))
        loud = float(np.percentile(r, 95))
    except ImportError:
        r = list(rms)
        peak = max(r)
        if peak <= 1e-6:
            return []
        srt = sorted(r)
        floor = srt[int(len(srt) * 0.20)]
        loud = srt[int(len(srt) * 0.95)]

    thresh = max(floor * 2.5, loud * 0.10, peak * 0.015) / max(0.2, sensitivity)

    segs = []
    start = None
    silence_frames = 0
    need_silence = max(1, int(min_silence / fdur))
    for i, v in enumerate(r):
        if v >= thresh:
            if start is None:
                start = i
            silence_frames = 0
        else:
            if start is not None:
                silence_frames += 1
                if silence_frames >= need_silence:
                    segs.append((start, i - silence_frames + 1))
                    start = None
                    silence_frames = 0
    if start is not None:
        segs.append((start, len(r)))

    out = []
    for a, b in segs:
        s = max(0.0, a * fdur - pad)
        e = min(len(r) * fdur, b * fdur + pad)
        if e - s < min_clip:
            continue
        out.extend(_split_long(s, e, r, fdur, max_clip, min_clip))
    return out


def _split_long(s, e, r, fdur, max_clip, min_clip):
    """Zerlegt zu lange Abschnitte an der leisesten Stelle in der Mitte."""
    if e - s <= max_clip:
        return [(s, e)]
    a = int(s / fdur)
    b = int(e / fdur)
    lo = a + int((b - a) * 0.30)
    hi = a + int((b - a) * 0.70)
    if hi <= lo:
        mid = (s + e) / 2.0
        return _split_long(s, mid, r, fdur, max_clip, min_clip) + \
               _split_long(mid, e, r, fdur, max_clip, min_clip)
    window = list(r[lo:hi])
    cut = lo + window.index(min(window))
    cut_s = cut * fdur
    if cut_s - s < min_clip or e - cut_s < min_clip:
        return [(s, e)]
    return _split_long(s, cut_s, r, fdur, max_clip, min_clip) + \
           _split_long(cut_s, e, r, fdur, max_clip, min_clip)


def waveform_peaks(data, columns):
    """Liefert [(min,max), ...] fuer die Wellenform-Darstellung."""
    n = len(data)
    if n == 0 or columns <= 0:
        return []
    step = n / float(columns)
    peaks = []
    try:
        import numpy as np
        arr = np.asarray(data, dtype="float32")
        for c in range(columns):
            a = int(c * step)
            b = max(a + 1, int((c + 1) * step))
            chunk = arr[a:b]
            peaks.append((float(chunk.min()), float(chunk.max())))
    except ImportError:
        for c in range(columns):
            a = int(c * step)
            b = max(a + 1, int((c + 1) * step))
            chunk = data[a:b]
            peaks.append((min(chunk), max(chunk)))
    return peaks


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def measure_peak_db(path):
    out = capture([ffmpeg(), "-hide_banner", "-i", path, "-af", "volumedetect",
                   "-f", "null", "-"])
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", out)
    return float(m.group(1)) if m else None


def export_clip(src_wav, start, end, out_path, target_lufs=-12.0, log=None):
    """Schneidet einen Clip heraus und macht ihn laut."""
    tmp = out_path + ".tmp.wav"
    dur = max(0.05, float(end) - float(start))
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-ss", "%.3f" % float(start), "-i", src_wav, "-t", "%.3f" % dur,
         "-af", "loudnorm=I=%.1f:TP=-1.0:LRA=11" % target_lufs,
         "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", tmp], log=log)
    peak = measure_peak_db(tmp)
    if peak is not None and peak < -1.5:
        gain = min(12.0, -1.0 - peak)
        run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", tmp,
             "-af", "volume=%.2fdB" % gain,
             "-c:a", "pcm_s16le", out_path], log=log)
        os.remove(tmp)
    else:
        if os.path.exists(out_path):
            os.remove(out_path)
        os.replace(tmp, out_path)
    return out_path


def export_backing_track(no_vocals_wav, out_path, log=None):
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", no_vocals_wav,
         "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", out_path], log=log)
    return out_path


def convert_video(video, out_path, max_height=720, quality=20, log=None):
    """
    Schreibt das Video fuer den Pack. MP4/H.264 ist Standard: schnell,
    klein und scharf. Endet der Pfad auf .ogv, wird Theora+Vorbis
    geschrieben - fuer Packs, die das brauchen.
    """
    scale = "scale=-2:'min(%d,ih)'" % int(max_height)
    if out_path.lower().endswith(".ogv"):
        has_theora, has_vorbis = check_encoders()
        if not has_theora or not has_vorbis:
            raise RuntimeError(M("no_theora"))
        args = ["-c:v", "libtheora", "-q:v", "6",
                "-c:a", "libvorbis", "-q:a", "4"]
    else:
        args = ["-c:v", "libx264", "-crf", str(int(quality)),
                "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    run([ffmpeg(), "-y", "-hide_banner", "-i", video, "-vf", scale]
        + args + ["-map", "0:v:0", "-map", "0:a:0?", out_path], log=log)
    return out_path


# --------------------------------------------------------------------------
# Dateinamen / file names
# --------------------------------------------------------------------------

def safe_name(text, fallback="clip"):
    text = re.sub(r"[^\w\-. ]+", "", (text or "").strip(), flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    return text or fallback


CAPTION_FILE = "_captions.json"


def write_captions(folder, mapping):
    """
    Schreibt die Untertitel als _captions.json in den Pack.
    Schluessel ist der Dateiname des Clips.
    """
    data = {}
    for name, text in (mapping or {}).items():
        text = (text or "").strip()
        if text:
            data[name] = text
    path = os.path.join(folder, CAPTION_FILE)
    if not data:
        if os.path.exists(path):
            os.remove(path)
        return None
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def read_captions(folder):
    """Liest _captions.json; zusaetzlich .txt-Dateien neben den Clips."""
    out = {}
    path = os.path.join(folder, CAPTION_FILE)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, str) and v.strip():
                        out[k] = v.strip()
        except Exception:
            pass
    try:
        for f in os.listdir(folder):
            if not f.lower().endswith(".txt") or f.startswith("_"):
                continue
            stem = os.path.splitext(f)[0]
            for ext in (".wav", ".mp3", ".ogg", ".flac"):
                clip = stem + ext
                if clip in out or not os.path.isfile(os.path.join(folder, clip)):
                    continue
                try:
                    with open(os.path.join(folder, f), "r", encoding="utf-8",
                              errors="replace") as fh:
                        text = fh.read().strip()
                    if text:
                        out[clip] = text
                except Exception:
                    pass
    except Exception:
        pass
    return out


def clip_filename(index, label, start=None, dub=False):
    """
    Voice-Pack:  01_MeinClip
    Dub-Pack:    01_MeinClip_44-048   (Guide-Konvention: Zeitstempel im Namen)
    """
    base = "%02d_%s" % (index, safe_name(label, "clip%02d" % index))
    if dub and start is not None:
        base += "_%s" % ("%.3f" % float(start)).replace(".", "-")
    return base + ".wav"


# --------------------------------------------------------------------------
# Pack kopieren / copy a pack
# --------------------------------------------------------------------------

def copy_pack(src_folder, target_dir, overwrite=True):
    """Kopiert einen fertigen Pack in einen beliebigen Zielordner."""
    if not os.path.isdir(target_dir):
        raise RuntimeError(M("no_target", target_dir))
    dest = os.path.join(target_dir, os.path.basename(src_folder))
    if os.path.exists(dest):
        if not overwrite:
            raise RuntimeError(M("pack_exists", dest))
        shutil.rmtree(dest)
    shutil.copytree(src_folder, dest)
    return dest


# --------------------------------------------------------------------------
# Untertitel importieren / import subtitles (SRT, VTT)
# --------------------------------------------------------------------------

_SUB_TS_RE = re.compile(
    r"(\d+):(\d{2}):(\d{2})[.,](\d{1,3})|(\d{1,2}):(\d{2})[.,](\d{1,3})")


def _sub_ts(text):
    m = _SUB_TS_RE.match(text.strip())
    if not m:
        return None
    if m.group(1) is not None:
        h, mi, s, ms = m.group(1), m.group(2), m.group(3), m.group(4)
    else:
        h, mi, s, ms = 0, m.group(5), m.group(6), m.group(7)
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_subtitles(text):
    """
    Liest SRT oder WebVTT. Gibt [(start, end, text)] zurueck, sortiert.
    YouTube-Auto-Untertitel wiederholen die vorige Zeile in jedem Cue -
    davon bleibt nur die jeweils neue Zeile uebrig, Dubletten fallen weg.
    Reads SRT or WebVTT into [(start, end, text)]. YouTube auto-captions
    repeat the previous line in every cue; only the new line is kept.
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("﻿")
    is_vtt = text.lstrip().startswith("WEBVTT")
    cues = []
    block = []

    def flush(block):
        lines = [l for l in block if l.strip()]
        idx = None
        for i, l in enumerate(lines):
            if "-->" in l:
                idx = i
                break
        if idx is None:
            return
        left, right = lines[idx].split("-->", 1)
        a = _sub_ts(left)
        b = _sub_ts(right.split()[0]) if right.strip() else None
        if a is None or b is None:
            return
        clean = []
        for l in lines[idx + 1:]:
            l = re.sub(r"<[^>]+>", "", l)          # <c>, <i>, Zeit-Tags
            l = re.sub(r"\{\\[^}]*\}", "", l)      # ASS-Reste
            l = (l.replace("&nbsp;", " ").replace("&amp;", "&")
                  .replace("&lt;", "<").replace("&gt;", ">").strip())
            if l:
                clean.append(l)
        if clean:
            cues.append((a, b, clean))

    def has_body(block):
        seen = False
        for l in block:
            if seen and l.strip():
                return True
            if "-->" in l:
                seen = True
        return False

    for raw in text.split("\n"):
        # YouTube schreibt in Auto-Cues eine Zeile mit nur einem Leerzeichen
        # VOR dem Text - die darf den Block nicht beenden.
        # YouTube's auto cues carry a whitespace-only line before the text.
        if raw == "" or (raw.strip() == "" and (not block or has_body(block))):
            if block:
                flush(block)
                block = []
        else:
            block.append(raw)
    if block:
        flush(block)

    out = []
    rolling = (is_vtt and any(len(c[2]) > 1 for c in cues)
               and any((c[1] - c[0]) < 0.02 for c in cues))
    if rolling:
        # Auto-Untertitel: rollende Anzeige. Die letzte Zeile ist die neue.
        # Auto captions roll: the last line of each cue is the new one.
        last = None
        for a, b, lines in cues:
            if b - a < 0.02:
                continue
            txt = lines[-1].strip()
            if not txt or txt == last:
                continue
            last = txt
            out.append((a, b, txt))
    else:
        last = None
        for a, b, lines in cues:
            txt = " ".join(lines).strip()
            if not txt:
                continue
            if out and txt == last and a - out[-1][1] < 0.3:
                out[-1] = (out[-1][0], b, txt)
                continue
            last = txt
            out.append((a, b, txt))
    out.sort(key=lambda c: c[0])
    return out


def read_subtitle_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_subtitles(f.read())


def fetch_youtube_subs(url, workdir, langs=("en", "de"), log=None):
    """
    Holt Untertitel von YouTube (echte bevorzugt, sonst automatische).
    Gibt den Pfad der VTT-Datei zurueck oder None.
    Fetches subtitles from YouTube (manual preferred, auto as fallback).
    """
    yt = ytdlp()
    if not yt:
        raise RuntimeError(M("no_ytdlp"))
    outdir = os.path.join(workdir, "subs")
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    pattern = ",".join("%s.*" % l for l in langs) + "," + ",".join(langs)
    base = ["--no-playlist", "--skip-download", "--sub-format", "vtt/srt/best",
            "--sub-langs", pattern, "-o", os.path.join(outdir, "subs.%(ext)s")]
    run(list(yt) + base + ["--write-subs", url], log=log, check=False)
    found = _pick_sub_file(outdir, langs)
    if not found:
        run(list(yt) + base + ["--write-auto-subs", url], log=log, check=False)
        found = _pick_sub_file(outdir, langs)
    return found


def _pick_sub_file(outdir, langs):
    files = [f for f in os.listdir(outdir)
             if f.lower().endswith((".vtt", ".srt"))]
    if not files:
        return None

    def rank(f):
        low = f.lower()
        for i, l in enumerate(langs):
            if (".%s." % l) in low or (".%s-" % l) in low:
                return i
        return len(langs)
    files.sort(key=rank)
    return os.path.join(outdir, files[0])


def assign_captions(clips, cues, offset=0.0, overwrite=False):
    """
    Verteilt Untertitel-Cues auf Clips nach zeitlicher Ueberlappung.
    offset = Startzeit des Ausschnitts im Originalvideo.
    Gibt die Anzahl geaenderter Clips zurueck.
    Distributes cues over clips by overlap; returns how many changed.
    """
    changed = 0
    for c in clips:
        if c.get("caption") and not overwrite:
            continue
        a, b = c["start"] + offset, c["end"] + offset
        parts = []
        for ca, cb, txt in cues:
            ov = min(b, cb) - max(a, ca)
            if ov <= 0:
                continue
            mid_in = a <= (ca + cb) / 2.0 <= b
            if mid_in or ov >= 0.5 * (cb - ca) or ov >= 0.5 * (b - a):
                parts.append(txt)
        cap = " ".join(parts).strip()
        if cap and cap != c.get("caption", ""):
            c["caption"] = cap
            changed += 1
    return changed


# --------------------------------------------------------------------------
# Videobild / frame preview
# --------------------------------------------------------------------------

def has_video_stream(path):
    out = capture([ffprobe(), "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=codec_type", "-of", "csv=p=0", path])
    return "video" in out


def extract_frame(video, seconds, out_png, width=320):
    """Ein Standbild als PNG (Tk 8.6 zeigt PNG ohne Pillow an)."""
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-ss", "%.3f" % max(0.0, float(seconds)), "-i", video,
         "-frames:v", "1", "-vf", "scale=%d:-2" % int(width),
         "-f", "image2", out_png])
    return out_png


# --------------------------------------------------------------------------
# Projektdatei im Pack / project file inside the pack
# --------------------------------------------------------------------------

# Beginnt mit "_": DubStage und DisDubs ueberspringen die Datei.
# Starts with "_": both DubStage and DisDubs skip it.
PROJECT_FILE = "_dubforge.json"
PACK_INFO_FILE = "_pack_info.ini"


def write_project(folder, data):
    with open(os.path.join(folder, PROJECT_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_project(folder):
    path = os.path.join(folder, PROJECT_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def write_pack_info(folder, title, authors=None, subtitle=None):
    """
    _pack_info.ini im Choicer-Stil: DisDubs liest title, subtitle, authors.
    Choicer-style _pack_info.ini: DisDubs reads title, subtitle and authors.
    """
    def q(s):
        return '"%s"' % str(s).replace("\\", "\\\\").replace('"', '\\"')
    lines = ["title=%s" % q(title)]
    if subtitle:
        lines.append("subtitle=%s" % q(subtitle))
    authors = [a.strip() for a in (authors or []) if a and a.strip()]
    if authors:
        lines.append("authors=[%s]" % ", ".join(q(a) for a in authors))
    with open(os.path.join(folder, PACK_INFO_FILE), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


_TS_IN_NAME = re.compile(r"_(\d+)-(\d{1,3})$")


def timestamp_from_name(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    m = _TS_IN_NAME.search(stem)
    if not m:
        return None
    return float(m.group(1)) + float(m.group(2)) / (10 ** len(m.group(2)))


def label_from_name(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    stem = _TS_IN_NAME.sub("", stem)
    stem = re.sub(r"^\d+[_\-]", "", stem)
    return stem.replace("_", " ").strip()


def read_pack_for_edit(folder):
    """
    Liest einen fertigen Pack wieder ein, damit er weiterbearbeitet werden
    kann. Mit _dubforge.json exakt, sonst aus den Dateinamen rekonstruiert.
    Reads a built pack back for editing - exact with _dubforge.json,
    otherwise reconstructed from the file names.
    Gibt dict(video, backing, tracks, clips, meta) zurueck.
    """
    if not os.path.isdir(folder):
        raise RuntimeError(M("no_pack", folder))
    video = None
    for ext in (".mp4", ".ogv", ".mkv", ".webm", ".mov", ".avi"):
        cand = os.path.join(folder, "dub_video" + ext)
        if os.path.isfile(cand):
            video = cand
            break
    backing = None
    for f in os.listdir(folder):
        low = f.lower()
        if low.startswith("_backing_track") and \
                low.endswith((".wav", ".mp3", ".ogg", ".flac")):
            backing = os.path.join(folder, f)
            break

    proj = read_project(folder)
    captions = read_captions(folder)
    tracks, clips = [], []
    if proj and isinstance(proj.get("clips"), list):
        tracks = [dict(t) for t in proj.get("tracks", []) if isinstance(t, dict)]
        for c in proj["clips"]:
            try:
                clips.append({"start": float(c["start"]), "end": float(c["end"]),
                              "track": int(c.get("track", 0)),
                              "caption": str(c.get("caption", ""))})
            except Exception:
                continue
    if not clips:
        found = []
        for f in sorted(os.listdir(folder)):
            if f.startswith("_") or not f.lower().endswith(".wav"):
                continue
            ts = timestamp_from_name(f)
            if ts is None:
                continue
            dur = probe_duration(os.path.join(folder, f))
            found.append((ts, max(0.1, dur), label_from_name(f),
                          captions.get(f, "")))
        if not found:
            raise RuntimeError(M("no_pack", folder))
        names = []
        for ts, dur, label, cap in found:
            if label not in names:
                names.append(label)
        tracks = [{"name": n} for n in names]
        for ts, dur, label, cap in found:
            clips.append({"start": ts, "end": ts + dur,
                          "track": names.index(label), "caption": cap})
    if not tracks:
        tracks = [{"name": "Voice"}]
    for c in clips:
        c["track"] = max(0, min(len(tracks) - 1, int(c.get("track", 0))))
    clips.sort(key=lambda c: (c["start"], c["track"]))
    meta = (proj or {}).get("meta") or {}
    return {"video": video, "backing": backing, "tracks": tracks,
            "clips": clips, "meta": meta}


# --------------------------------------------------------------------------
# Zip fuer DisDubs / zip for DisDubs
# --------------------------------------------------------------------------

def zip_pack(pack_folder, out_zip=None):
    """
    Packt den Pack-Ordner als <Name>.zip mit dem Ordner als oberster Ebene -
    genau so nimmt DisDubs ihn beim Hochladen entgegen.
    Zips the pack folder as <Name>.zip with the folder at the top level.
    """
    pack_folder = os.path.abspath(pack_folder)
    root = os.path.dirname(pack_folder)
    name = os.path.basename(pack_folder)
    out_zip = out_zip or os.path.join(root, name + ".zip")
    if os.path.exists(out_zip):
        os.remove(out_zip)
    base = out_zip[:-4] if out_zip.lower().endswith(".zip") else out_zip
    made = shutil.make_archive(base, "zip", root_dir=root, base_dir=name)
    if os.path.abspath(made) != os.path.abspath(out_zip):
        os.replace(made, out_zip)
    return out_zip


# --------------------------------------------------------------------------
# Wiedergabe / playback helpers
# --------------------------------------------------------------------------

def sounddevice():
    """Gibt das sounddevice-Modul zurueck oder None / the module or None."""
    try:
        import sounddevice as sd
        return sd
    except Exception:
        return None


def decode_pcm(src, start, end, sr=44100, channels=2):
    """
    Dekodiert einen Ausschnitt als int16-PCM in den Speicher (numpy-Array
    der Form (n, channels)); ohne numpy None.
    Decodes a span to int16 PCM in memory; None without numpy.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    dur = max(0.05, float(end) - float(start))
    r = subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error",
         "-ss", "%.3f" % float(start), "-i", src, "-t", "%.3f" % dur,
         "-f", "s16le", "-ac", str(channels), "-ar", str(sr), "-"],
        capture_output=True, creationflags=_NOWINDOW)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(M("cmd_failed", "ffmpeg",
                             (r.stderr or b"").decode("utf-8", "replace")[-400:]))
    data = np.frombuffer(r.stdout, dtype="<i2")
    n = (len(data) // channels) * channels
    return data[:n].reshape(-1, channels)


def write_pcm_wav(path, data, sr=44100):
    """Schreibt ein int16-Array (n, ch) als WAV / writes int16 (n, ch) as WAV."""
    with wave.open(path, "wb") as w:
        w.setnchannels(data.shape[1] if data.ndim > 1 else 1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.astype("<i2").tobytes())
    return path


def extract_frames_range(video, start, end, outdir, fps=10, width=224):
    """
    Standbilder eines Ausschnitts als PNG-Folge f001.png, f002.png ...
    (fuer die bewegte Vorschau waehrend der Wiedergabe).
    A PNG sequence for the span - the moving preview during playback.
    """
    os.makedirs(outdir, exist_ok=True)
    dur = max(0.05, float(end) - float(start))
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
         "-ss", "%.3f" % max(0.0, float(start)), "-i", video, "-t", "%.3f" % dur,
         "-vf", "fps=%d,scale=%d:-2" % (int(fps), int(width)),
         "-f", "image2", os.path.join(outdir, "f%03d.png")])
    return outdir
