# -*- coding: utf-8 -*-
"""
DubForge - Dub-Packs aus Videos bauen.
DubForge - build dub packs from video.

Ablauf / flow:
  Quelle -> Analysieren -> Clips pruefen -> Pack bauen.
  Source -> Analyse -> Review clips -> Build pack.
"""

import os
import sys
import json
import queue
import shutil
import threading
import traceback
import tempfile
import subprocess

import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dubforge_core as pc
import updater as upd
import appwin
import transcription as tr

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(APP_DIR, "packs")
CFG_PATH = os.path.join(APP_DIR, "dubforge_settings.json")

# Farben wie in DubStage, damit beide Werkzeuge zusammengehoeren.
PAGE = "#0e1019"         # Fensterhintergrund / window background
PAGE_HI = "#1a1e30"
CARD = "#161a29"         # Karten je Schritt / step cards
CARD_HI = "#20253a"
FIELD = "#0f121d"        # Eingabefelder, Tabelle, Protokoll
ROW_ALT = "#131727"
EDGE = "#2a3050"
EDGE_HI = "#3a4270"
BTN = "#252a42"
BTN_HI = "#30375a"
SCROLL = "#2c3250"
SCROLL_HI = "#3d4570"
FG = "#eef1ff"
DIM = "#8a92b4"
MUTED = "#555c7c"
LOG_FG = "#8f98bd"
ACC = "#7c5cff"
ACC_HI = "#9b83ff"
ACC2 = "#25d3a4"
ACC2_HI = "#4ee5bb"
BG = PAGE                # Altname / legacy name
BG2 = CARD

WAVE_BG = "#0b0d16"
WAVE = "#3c4470"         # Welle ausserhalb der Clips
WAVE_IN = "#b9adff"      # Welle innerhalb eines Clips
CLIP_FILL = "#1f1a45"
CLIP_EDGE = "#4a3fa0"
CLIP_SEL = "#33287a"
BAN = "#332e5e"          # Update-Banner / update banner
BAN_TXT = "#241f47"

if os.name == "nt":
    UI_FONT, UI_FONT_SB, MONO_FONT = "Segoe UI", "Segoe UI Semibold", "Consolas"
else:
    UI_FONT, UI_FONT_SB, MONO_FONT = "DejaVu Sans", "DejaVu Sans", "DejaVu Sans Mono"


# ==========================================================================
#  Sprache / language
# ==========================================================================

LANG = "de"
LANG_NAMES = {"de": "Deutsch", "en": "English"}


def set_lang(code):
    global LANG
    LANG = "en" if str(code).lower().startswith("en") else "de"
    pc.set_lang(LANG)


# (deutsch, english)
T = {
    "asr_language": ("Gesprochene Sprache (Code):", "Spoken language (code):"),
    "asr_model": ("Modell:", "Model:"),
    "asr_device": ("Gerät:", "Device:"),
    "asr_generate": ("Untertitel generieren", "Generate captions"),
    "asr_replace": ("Vorhandene ersetzen", "Replace existing"),
    "asr_hint": ("fr = Französisch, en = Englisch, de = Deutsch. Erstmalig Modell-Download; Audio bleibt lokal.\n"
                 "SRT/VTT enthalten das gesamte Transkript. Clip-Korrekturen ändern nur den Text in DubStage.",
                 "fr = French, en = English, de = German. First use downloads the model; audio stays local.\n"
                 "SRT/VTT contain the full transcript. Clip corrections only change the text in DubStage."),
    "asr_language_required": ("Bitte Sprachcode eingeben, z.B. fr für Französisch.",
                              "Enter a spoken language code, e.g. fr for French."),
    "asr_empty": ("Keine Sprache zugeordnet: %s", "No recognized speech mapped to: %s"),
    "asr_error": ("Spracherkennung fehlgeschlagen. Vorhandene Untertitel bleiben erhalten.\n%s",
                  "Speech recognition failed. Existing captions are preserved.\n%s"),
    "title":        ("DubForge  -  Dub-Packs aus Videos bauen",
                     "DubForge  -  build dub packs from video"),
    "lang_label":   ("Sprache:", "Language:"),

    # --- Schritt 1
    "tagline":      ("Dub-Packs aus Videos bauen", "Build dub packs from video"),
    "s1":           ("Quelle", "Source"),
    "s1_hint":      ("Woraus soll der Pack werden?",
                     "What should the pack be made from?"),
    "src_url":      ("YouTube-Link", "YouTube link"),
    "src_file":     ("Datei auf der Platte (MP4/MKV/...)",
                     "File on disk (MP4/MKV/...)"),
    "pick_file":    ("Datei wählen ...", "Choose file ..."),
    "from":         ("Von:", "From:"),
    "to":           ("Bis:", "To:"),
    "time_hint":    ("(z.B. 1:30  oder  0:02:15.5  -  leer = alles)",
                     "(e.g. 1:30  or  0:02:15.5  -  empty = everything)"),
    "sep_voc":      ("Stimmen von Musik trennen (Demucs)",
                     "Separate vocals from music (Demucs)"),
    "analyze":      ("Laden und analysieren", "Load and analyse"),
    "upd_ytdlp":    ("yt-dlp aktualisieren", "Update yt-dlp"),
    "ytdlp_ver":    ("yt-dlp %s (%d Tage alt)", "yt-dlp %s (%d days old)"),
    "ytdlp_old":    ("yt-dlp ist %d Tage alt. YouTube ändert ständig etwas - "
                     "bei Download-Problemen zuerst aktualisieren.",
                     "yt-dlp is %d days old. YouTube keeps changing things - "
                     "update it first if downloads fail."),
    "st_upd":       ("Aktualisiere yt-dlp ...", "Updating yt-dlp ..."),
    "upd_done":     ("Jetzt: yt-dlp %s", "Now: yt-dlp %s"),
    "ytdlp_fail":   ("Aktualisierung hat nichts geändert. Im Terminal:\n"
                     "\"%s\" -m pip install --upgrade yt-dlp",
                     "The update changed nothing. In a terminal:\n"
                     "\"%s\" -m pip install --upgrade yt-dlp"),
    "upd_same":     ("Die Version ist unverändert: %s\n\n"
                     "Meist liegt eine ältere yt-dlp.exe im PATH und hat "
                     "Vorrang vor der Installation, die pip erneuert hat. "
                     "Welche Datei benutzt wird, steht im Protokoll - diese "
                     "Datei entfernen oder direkt erneuern.",
                     "The version has not changed: %s\n\n"
                     "Usually an older yt-dlp.exe sits in PATH and takes "
                     "precedence over the installation pip just updated. "
                     "The log shows which file is in use - remove or update "
                     "that file."),
    "dl_hint":      ("Der Download ist fehlgeschlagen. yt-dlp ist %d Tage alt - "
                     "das könnte die Ursache sein, wenn oben ein Fehler beim "
                     "Auslesen der Seite steht.",
                     "The download failed. yt-dlp is %d days old - that may be "
                     "the cause if the log shows an error while reading the "
                     "page."),
    "demucs_hint":  ("Erster Lauf mit Demucs dauert länger (Modell wird geladen).",
                     "The first Demucs run takes longer (the model is downloaded)."),

    # --- Schritt 2
    "s2":           ("Clips prüfen und anpassen", "Review and adjust the clips"),
    "canvas_empty": ("Noch nichts geladen  -  oben Quelle wählen und auf "
                     "'Laden und analysieren' klicken",
                     "Nothing loaded yet  -  choose a source above and click "
                     "'Load and analyse'"),
    "zoom_in":      ("Zoom +", "Zoom +"),
    "zoom_out":     ("Zoom -", "Zoom -"),
    "zoom_all":     ("Alles zeigen", "Fit all"),
    "mouse_hint":   ("Ziehen = neuer Clip   |   Rand ziehen = trimmen   |   "
                     "Doppelklick = anhören",
                     "Drag = new clip   |   drag an edge = trim   |   "
                     "double-click = listen"),
    "col_nr":       ("#", "#"),
    "col_name":     ("Name", "Name"),
    "col_start":    ("Start", "Start"),
    "col_end":      ("Ende", "End"),
    "col_len":      ("Länge", "Length"),
    "col_caption":  ("Untertitel", "Subtitle"),
    "caption":      ("Untertitel:", "Subtitle:"),
    "caption_hint": ("Enter = speichern und zum nächsten Clip",
                     "Enter = save and go to the next clip"),
    "btn_play":     ("Anhören", "Play"),
    "btn_stop":     ("Stopp", "Stop"),
    "btn_rename":   ("Umbenennen", "Rename"),
    "btn_split":    ("Teilen", "Split"),
    "btn_delete":   ("Löschen", "Delete"),
    "sensitivity":  ("Empfindlichkeit", "Sensitivity"),
    "maxlen":       ("Max. Cliplänge (s)", "Max. clip length (s)"),
    "redetect":     ("Neu erkennen", "Detect again"),

    # --- Schritt 3
    "s3":           ("Pack bauen", "Build the pack"),
    "pack_name":    ("Pack-Name:", "Pack name:"),
    "is_dub":       ("Mit Video (für DubStage)", "With video (for DubStage)"),
    "vheight":      ("Video-Höhe:", "Video height:"),
    "target_dir":   ("Zielordner:", "Target folder:"),
    "browse":       ("Wählen", "Browse"),
    "build":        ("Pack bauen", "Build pack"),
    "install":      ("In Zielordner kopieren", "Copy to target folder"),
    "open_out":     ("Pack-Ordner öffnen", "Open pack folder"),

    # --- Status / Log
    "ready":        ("Bereit.", "Ready."),
    "missing":      ("FEHLT: %s  ->  bitte das Setup erneut ausführen.",
                     "MISSING: %s  ->  please run the setup again."),
    "ff_ready":     ("ffmpeg bereit (Theora: %s, Vorbis: %s)",
                     "ffmpeg ready (Theora: %s, Vorbis: %s)"),
    "yes":          ("ja", "yes"),
    "no_caps":      ("NEIN", "NO"),

    "st_download":  ("Lade Video ...", "Downloading video ..."),
    "st_trim":      ("Schneide Zeitspanne ...", "Cutting the time span ..."),
    "st_audio":     ("Ton extrahieren ...", "Extracting audio ..."),
    "st_demucs":    ("Trenne Stimmen von Musik (Demucs, dauert) ...",
                     "Separating vocals from music (Demucs, takes a while) ..."),
    "st_wave":      ("Analysiere Wellenform ...", "Analysing waveform ..."),
    "st_detect":    ("Suche Clips ...", "Looking for clips ..."),
    "st_done_an":   ("Fertig analysiert.", "Analysis finished."),
    "st_clip":      ("Exportiere Clip %d/%d ...", "Exporting clip %d/%d ..."),
    "st_backing":   ("Schreibe _backing_track ...", "Writing _backing_track ..."),
    "st_ogv":       ("Konvertiere Video (dauert am längsten) ...",
                     "Converting the video (this takes the longest) ..."),
    "st_built":     ("Pack gebaut: %s", "Pack built: %s"),
    "log_len":      ("Länge: %.2f s", "Length: %.2f s"),
    "log_voc_ok":   ("Vocals getrennt.", "Vocals separated."),
    "log_voc_fail": ("Demucs fehlgeschlagen (%s) - nutze den Originalton.",
                     "Demucs failed (%s) - falling back to the original audio."),
    "log_found":    ("%d Clips gefunden.", "Found %d clips."),
    "log_redet":    ("Neu erkannt: %d Clips.", "Detected again: %d clips."),
    "log_copied":   ("Kopiert nach: %s", "Copied to: %s"),
    "log_noplay":   ("Wiedergabe nicht möglich: %s", "Playback not possible: %s"),

    # --- Dialoge
    "dlg_busy_t":   ("Moment", "One moment"),
    "dlg_busy":     ("Es läuft gerade schon etwas.",
                     "Something is already running."),
    "dlg_err":      ("Fehler", "Error"),
    "dlg_missing_t": ("Fehlt", "Missing"),
    "dlg_no_src":   ("Bitte einen Link oder eine Datei angeben.",
                     "Please provide a link or a file."),
    "dlg_time_t":   ("Zeitangabe", "Time value"),
    "dlg_time_order": ("'Bis' muss größer als 'Von' sein.",
                       "'To' must be greater than 'From'."),

    "dlg_first_t":  ("Erst analysieren", "Analyse first"),
    "dlg_first":    ("Bitte zuerst eine Quelle laden und analysieren.",
                     "Please load and analyse a source first."),
    "dlg_rename_t": ("Umbenennen", "Rename"),
    "dlg_rename":   ("Name für diesen Clip:", "Name for this clip:"),
    "dlg_noclips_t": ("Keine Clips", "No clips"),
    "dlg_noclips":  ("Es gibt noch keine Clips.", "There are no clips yet."),
    "dlg_done_t":   ("Fertig", "Finished"),
    "dlg_done":     ("Pack liegt in:\n%s\n\nJetzt in den Zielordner kopieren?",
                     "Pack is located at:\n%s\n\nCopy it to the target folder now?"),
    "dlg_nobuild_t": ("Noch nichts da", "Nothing there yet"),
    "dlg_nobuild":  ("Bitte zuerst 'Pack bauen'.", "Please use 'Build pack' first."),
    "dlg_notgt_t":  ("Zielordner fehlt", "Target folder missing"),
    "dlg_notgt":    ("Es ist kein Zielordner gesetzt.\n\n"
                     "Oben einen Ordner wählen, in den der fertige Pack "
                     "kopiert werden soll.",
                     "No target folder is set.\n\n"
                     "Choose a folder above to copy the finished pack into."),
    "dlg_copyfail": ("Kopieren fehlgeschlagen", "Copying failed"),
    "dlg_copied_t": ("Kopiert", "Copied"),
    "dlg_copied":   ("Kopiert nach:\n%s\n\nOrdner öffnen?",
                     "Copied to:\n%s\n\nOpen the folder?"),

    "dlg_video_t":  ("Video oder Audio wählen", "Choose video or audio"),
    "dlg_filter":   ("Video/Audio", "Video/audio"),
    "dlg_allfiles": ("Alle Dateien", "All files"),
    "dlg_target_t": ("Zielordner wählen", "Choose the target folder"),

    # --- Dateien im Pack
    "ts_head":      ("# %s\n# Übersicht der Clips\n#\n"
                     "# Datei | Startzeit im Video (Sekunden) | Länge | "
                     "Untertitel\n",
                     "# %s\n# Overview of the clips\n#\n"
                     "# File | start time in the video (seconds) | length | "
                     "subtitle\n"),
    "readme":       ("Pack: %s\nTyp: %s\nClips: %d\n\n"
                     "Mit DubStage öffnen und die Szene selbst einsprechen.\n",
                     "Pack: %s\nType: %s\nClips: %d\n\n"
                     "Open it in DubStage and dub the scene yourself.\n"),
    "readme_dub":   ("\nDie Startzeit jedes Clips steht im Dateinamen\n"
                     "(z.B. 07_MyClip_44-048 = 44.048 Sekunden) und in\n"
                     "_TIMESTAMPS.txt. Untertitel liegen in _captions.json.\n",
                     "\nEach clip's start time is in its file name\n"
                     "(e.g. 07_MyClip_44-048 = 44.048 seconds) and in\n"
                     "_TIMESTAMPS.txt. Subtitles live in _captions.json.\n"),
    "type_dub":     ("Dub-Pack", "Dub pack"),
    "type_voice":   ("Clip-Pack", "Clip pack"),

    # --- Zielformat
    "fmt_label":    ("Zielformat:", "Target format:"),
    "fmt_ds":       ("DubStage", "DubStage"),
    "fmt_cv":       ("The Choicer Voicer", "The Choicer Voicer"),
    "fmt_hint_ds":  ("Zeitstempel im Dateinamen, Untertitel in _captions.json, "
                     "Video als MP4.",
                     "Timestamp in the file name, subtitles in _captions.json, "
                     "video as MP4."),
    "fmt_hint_cv":  ("Eine .txt je Sprechzeile, Bild je Figur, _pack_info.ini, "
                     "Video als OGV.",
                     "One .txt per line, one image per character, "
                     "_pack_info.ini, video as OGV."),
    "col_char":     ("Figur", "Character"),
    "character":    ("Figur:", "Character:"),
    "char_hint":    ("Name des Sprechers - bestimmt Dateinamen und Bild",
                     "Name of the speaker - drives file name and image"),
    "btn_frame":    ("Bild aus Szene", "Grab image"),
    "frame_none":   ("Erst einen Clip wählen und eine Figur eintragen.",
                     "Select a clip and enter a character first."),
    "frame_ok":     ("Bild für %s aus Sekunde %.1f gesetzt.",
                     "Image for %s taken at second %.1f."),
    "frame_icon":   ("Pack-Symbol aus Sekunde %.1f gesetzt.",
                     "Pack icon taken at second %.1f."),
    "btn_icon":     ("Symbol aus Szene", "Grab icon"),
    "pack_title":   ("Titel im Spiel:", "Title in game:"),
    "pack_authors": ("Autoren:", "Authors:"),
    "authors_hint": ("mehrere mit Komma trennen", "separate several with commas"),
    "pack_readme":  ("Beschreibung:", "Description:"),
    "chars_found":  ("Figuren: %s", "Characters: %s"),
    "chars_none":   ("noch keine Figuren vergeben", "no characters assigned yet"),
    "cv_nochar":    ("Für das Choicer-Voicer-Format braucht jeder Clip eine "
                     "Figur. Ohne Angabe wird der Clipname genommen.",
                     "The Choicer Voicer format needs a character per clip. "
                     "Without one the clip name is used."),

    # --- Update
    "upd_head":     ("Version %s ist da", "Version %s is out"),
    "upd_sub":      ("Du hast %s", "You have %s"),
    "upd_more":     ("Was ist neu", "What's new"),
    "upd_less":     ("Zuklappen", "Collapse"),
    "upd_now":      ("Jetzt aktualisieren", "Update now"),
    "upd_later":    ("Später", "Later"),
    "upd_page":     ("Auf GitHub", "On GitHub"),
    "upd_nonotes":  ("Zu dieser Version wurde kein Text hinterlegt.",
                     "No description was published for this version."),
    "upd_ask_t":    ("Update einspielen?", "Install update?"),
    "upd_ask":      ("DubForge und DubStage werden auf %s aktualisiert.\n\n"
                     "Die App schließt sich, die Dateien werden getauscht "
                     "und die App startet neu.\n"
                     "Packs, Aufnahmen und Einstellungen bleiben unberührt.\n\n"
                     "Fortfahren?",
                     "DubForge and DubStage will be updated to %s.\n\n"
                     "The app closes, the files are replaced and the app "
                     "starts again.\n"
                     "Packs, recordings and settings are left untouched.\n\n"
                     "Continue?"),
    "upd_dl":       ("Lade %s ... %d%%", "Downloading %s ... %d%%"),
    "upd_check":    ("Prüfe das Archiv ...", "Checking the archive ..."),
    "upd_swap":     ("Tausche Dateien - die App startet gleich neu ...",
                     "Replacing files - the app will restart shortly ..."),
    "upd_fail_t":   ("Update fehlgeschlagen", "Update failed"),
    "upd_fail":     ("Es hat nicht geklappt:\n\n%s\n\n"
                     "Du kannst die Version auch von Hand von der "
                     "Release-Seite laden.",
                     "It did not work:\n\n%s\n\n"
                     "You can also download the version by hand from the "
                     "release page."),
}


def t(key, *args):
    pair = T.get(key)
    if not pair:
        return key
    text = pair[1] if LANG == "en" else pair[0]
    return text % args if args else text


# ==========================================================================
def load_cfg():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ==========================================================================
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        appwin.set_icon(self, "DubForge")
        self.cfg = load_cfg()
        set_lang(self.cfg.get("lang", "de"))

        # Fensterhoehe an den Bildschirm anpassen - auf einem 1080p-Schirm
        # bleiben nach Taskleiste und Titelzeile keine 880 Pixel uebrig.
        sh = self.winfo_screenheight()
        self.geometry("1180x%d" % min(880, max(560, sh - 130)))
        # Klein darf es werden: der Inhalt scrollt jetzt.
        self.minsize(900, 480)
        self.configure(bg=BG)

        self.msgq = queue.Queue()
        self.busy = False
        self.player = None

        self.work = tempfile.mkdtemp(prefix="packforge_")
        self.video_path = None
        self.audio_path = None       # kompletter Ton / full audio
        self.vocals_path = None      # nur Stimmen / vocals only
        self.backing_path = None     # alles ausser Stimmen / everything else
        self.wave_data = []
        self.wave_sr = 8000
        self.duration = 0.0
        # [{'start':float,'end':float,'name':str,'caption':str}]
        self.clips = []
        self.transcript = None
        self._busy_widgets = []
        self.selected = None
        self._caption_for = None
        self._ytdlp_age = None
        self.built_path = None

        self.upd_info = None        # gefundenes Release / found release
        self.upd_open = False       # Changelog aufgeklappt?
        self.upd_busy = False
        self.upd_dismissed = False

        # Choicer-Voicer-Profil: Bilder je Figur, Symbol des Packs
        self.char_images = {}       # {"Woody": "C:/.../woody.png"}
        self.pack_icon = None

        self.view_a = 0.0
        self.view_b = 1.0
        self._drag = None
        self._peak_cache = (None, None)
        self._syncing = False

        self._build_style()
        self._init_vars()
        self._build_ui()
        # Mausrad global: die Seite scrollt, ausser ueber Widgets, die
        # selbst scrollen (siehe _wheel).
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Button-4>", self._wheel)
        self.bind("<Button-5>", self._wheel)
        self.after(80, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._check_tools()
        self.after(1200, self._check_update)

    # -------------------------------------------------- Variablen (einmalig)
    def _init_vars(self):
        c = self.cfg
        self.lang_var = tk.StringVar(value=LANG_NAMES.get(LANG, "Deutsch"))
        self.src_mode = tk.StringVar(value=c.get("src_mode", "url"))
        self.url_var = tk.StringVar(value=c.get("last_url", ""))
        self.t_start = tk.StringVar(value=c.get("t_start", ""))
        self.t_end = tk.StringVar(value=c.get("t_end", ""))
        self.sep_var = tk.BooleanVar(value=c.get("separate", True))
        self.sens = tk.DoubleVar(value=c.get("sens", 1.0))
        self.maxlen = tk.DoubleVar(value=c.get("maxlen", 6.0))
        self.pack_name = tk.StringVar(value=c.get("pack_name", "Mein_Pack"))
        self.is_dub = tk.BooleanVar(value=c.get("is_dub", True))
        self.vheight = tk.StringVar(value=c.get("vheight", "720"))
        self.target_dir = tk.StringVar(value=c.get("target_dir", ""))
        self.caption_var = tk.StringVar(value="")
        self.asr_language = tk.StringVar(value=c.get("asr_language", ""))
        self.asr_model = tk.StringVar(value=c.get("asr_model", "large-v3"))
        self.asr_device = tk.StringVar(value=c.get("asr_device", "cpu"))
        self.asr_replace = tk.BooleanVar(value=False)
        self.fmt = tk.StringVar(value=c.get("fmt", "dubstage"))
        self.char_var = tk.StringVar(value="")
        self.pack_title = tk.StringVar(value=c.get("pack_title", ""))
        self.pack_authors = tk.StringVar(value=c.get("pack_authors", ""))
        self.pack_readme = tk.StringVar(value=c.get("pack_readme", ""))

    # ------------------------------------------------------------------ UI
    def _build_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass

        # Nicht jede Tk-Fassung kennt jede Farboption. Ein unbekannter Name
        # wuerde sonst beim Start eine Ausnahme werfen - fuer reine Optik ist
        # das zu teuer. Schlaegt eine Zeile fehl, bleibt es bei der Vorgabe.
        def cfg(style, **kw):
            try:
                s.configure(style, **kw)
            except Exception:
                pass

        def mp(style, **kw):
            try:
                s.map(style, **kw)
            except Exception:
                pass

        def lay(style, spec):
            try:
                s.layout(style, spec)
            except Exception:
                pass

        # Aufbau: dunkle Seite (PAGE), darauf Karten (CARD) je Schritt.
        # Die Grundfarbe aller Widgets ist die Kartenfarbe - dann muss nicht
        # jedes Kaestchen und Etikett in einer Karte eigens umgestellt werden.
        # Was direkt auf der Seite liegt, nimmt die Page-Stile.
        cfg(".", background=CARD, foreground=FG, fieldbackground=FIELD,
            bordercolor=EDGE, lightcolor=CARD, darkcolor=CARD,
            troughcolor=FIELD, selectbackground=ACC,
            selectforeground="#ffffff", insertcolor=FG, focuscolor=ACC,
            font=(UI_FONT, 10))
        cfg("TFrame", background=CARD)
        cfg("Page.TFrame", background=PAGE)
        cfg("Card.TFrame", background=CARD)
        cfg("TLabel", background=CARD, foreground=FG)
        cfg("Dim.TLabel", background=CARD, foreground=DIM, font=(UI_FONT, 9))
        cfg("Title.TLabel", background=CARD, foreground=FG,
            font=(UI_FONT_SB, 12))
        cfg("Field.TLabel", background=CARD, foreground=DIM,
            font=(UI_FONT, 9))
        cfg("Page.TLabel", background=PAGE, foreground=FG)
        cfg("PageDim.TLabel", background=PAGE, foreground=DIM,
            font=(UI_FONT, 9))
        cfg("App.TLabel", background=PAGE, foreground=FG,
            font=(UI_FONT_SB, 17))
        cfg("Status.TLabel", background=CARD, foreground=DIM,
            font=(UI_FONT, 9))

        # Knoepfe: flach, grosszuegig gepolstert, Hover eine Stufe heller.
        cfg("TButton", background=BTN, foreground=FG, padding=(14, 7),
            borderwidth=0, relief="flat", focusthickness=0,
            focuscolor=BTN, font=(UI_FONT, 10))
        mp("TButton",
           background=[("disabled", CARD_HI), ("pressed", BTN_HI),
                       ("active", BTN_HI)],
           foreground=[("disabled", MUTED)],
           focuscolor=[("active", BTN_HI)])
        for name, bg, hi, fg in (("Accent", ACC, ACC_HI, "#ffffff"),
                                 ("Go", ACC2, ACC2_HI, "#08241a")):
            cfg(name + ".TButton", background=bg, foreground=fg,
                padding=(18, 9), font=(UI_FONT_SB, 10), focuscolor=bg)
            mp(name + ".TButton",
               background=[("disabled", CARD_HI), ("pressed", hi),
                           ("active", hi)],
               foreground=[("disabled", MUTED)],
               focuscolor=[("active", hi)])
        cfg("Ghost.TButton", background=CARD, foreground=DIM,
            padding=(10, 6), focuscolor=CARD)
        mp("Ghost.TButton",
           background=[("active", CARD_HI), ("pressed", CARD_HI)],
           foreground=[("active", FG), ("disabled", MUTED)],
           focuscolor=[("active", CARD_HI)])

        # Eingabefelder liegen eine Stufe tiefer als die Karte, der Rahmen
        # leuchtet im Fokus in der Akzentfarbe.
        field = dict(fieldbackground=FIELD, foreground=FG, insertcolor=FG,
                     bordercolor=EDGE, lightcolor=FIELD, darkcolor=FIELD,
                     padding=(8, 6))
        cfg("TEntry", **field)
        # "readonly" und "disabled" haben eigene Farben, die configure()
        # nicht erreicht - sonst wird das Feld hell und der Text unsichtbar.
        mp("TEntry",
           fieldbackground=[("readonly", CARD_HI), ("disabled", CARD)],
           foreground=[("readonly", DIM), ("disabled", MUTED)],
           bordercolor=[("focus", ACC), ("hover", EDGE_HI)],
           lightcolor=[("focus", ACC)], darkcolor=[("focus", ACC)])
        # Comboboxen: der Zustand "readonly" hat eigene Farben, die
        # configure() nicht erreicht - deshalb zusaetzlich map().
        cfg("TCombobox", background=FIELD, arrowcolor=DIM, arrowsize=12,
            selectbackground=FIELD, selectforeground=FG, **field)
        mp("TCombobox",
           fieldbackground=[("readonly", FIELD), ("disabled", CARD)],
           background=[("readonly", FIELD), ("active", FIELD)],
           foreground=[("readonly", FG), ("disabled", MUTED)],
           selectbackground=[("readonly", FIELD), ("focus", FIELD)],
           selectforeground=[("readonly", FG), ("focus", FG)],
           bordercolor=[("focus", ACC), ("hover", EDGE_HI)],
           arrowcolor=[("active", FG), ("disabled", MUTED)])
        # Die aufklappende Liste ist ein Tk-Listbox-Widget und wird von
        # ttk nicht mitgestaltet - die muss ueber Optionen gesetzt werden.
        self.option_add("*TCombobox*Listbox.background", CARD_HI)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACC)
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.borderWidth", 0)
        self.option_add("*TCombobox*Listbox.font", (UI_FONT, 10))
        cfg("TSpinbox", background=FIELD, arrowcolor=DIM, arrowsize=10,
            **field)
        mp("TSpinbox",
           fieldbackground=[("readonly", FIELD), ("disabled", CARD)],
           background=[("active", FIELD), ("readonly", FIELD)],
           foreground=[("disabled", MUTED)],
           bordercolor=[("focus", ACC), ("hover", EDGE_HI)],
           arrowcolor=[("active", ACC_HI), ("disabled", MUTED)])

        # Kaestchen und Punkte: clam faerbt sie beim Ueberfahren hell ein,
        # dann steht dunkler Text auf weissem Grund. Alle Zustaende setzen.
        for kind in ("TCheckbutton", "TRadiobutton"):
            cfg(kind, background=CARD, foreground=FG, indicatorsize=14,
                indicatorbackground=FIELD, indicatorforeground="#ffffff",
                indicatormargin=(0, 0, 8, 0), upperbordercolor=EDGE_HI,
                lowerbordercolor=EDGE_HI, focuscolor=CARD, padding=(2, 3))
            mp(kind,
               background=[("active", CARD), ("pressed", CARD)],
               foreground=[("disabled", MUTED), ("active", FG)],
               indicatorbackground=[("selected", ACC), ("pressed", ACC),
                                    ("active", CARD_HI),
                                    ("disabled", CARD)],
               indicatorforeground=[("selected", "#ffffff"),
                                    ("disabled", MUTED)])

        # Segmentschalter fuer das Zielformat: Radioknoepfe als Kacheln.
        lay("Seg.TRadiobutton",
            [("Radiobutton.padding", {"sticky": "nswe", "children": [
                ("Radiobutton.label", {"sticky": "nswe"})]})])
        cfg("Seg.TRadiobutton", background=PAGE_HI, foreground=DIM,
            padding=(14, 6), anchor="center", font=(UI_FONT, 10))
        mp("Seg.TRadiobutton",
           background=[("selected", ACC), ("active", CARD_HI)],
           foreground=[("selected", "#ffffff"), ("active", FG),
                       ("disabled", MUTED)])

        # Tabelle: ruhige Zeilen im Wechsel, Kopf ohne Kanten.
        cfg("Treeview", background=FIELD, fieldbackground=FIELD,
            foreground=FG, rowheight=30, borderwidth=0, relief="flat",
            font=(UI_FONT, 10))
        lay("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        cfg("Treeview.Heading", background=CARD_HI, foreground=DIM,
            relief="flat", borderwidth=0, padding=(8, 6),
            font=(UI_FONT_SB, 9))
        # Spaltenkopf wird beim Ueberfahren sonst weiss.
        mp("Treeview.Heading",
           background=[("active", CARD_HI), ("pressed", CARD_HI)],
           foreground=[("active", FG), ("pressed", FG)],
           relief=[("active", "flat"), ("pressed", "flat")])
        mp("Treeview",
           background=[("selected", ACC)],
           foreground=[("selected", "#ffffff")])

        cfg("TProgressbar", background=ACC, troughcolor=FIELD,
            bordercolor=FIELD, lightcolor=ACC, darkcolor=ACC,
            borderwidth=0, thickness=6)
        cfg("TSeparator", background=EDGE)

        # Schmale Scrollbalken ohne Pfeile, wie in modernen Oberflaechen.
        for orient, side in (("Vertical", "ns"), ("Horizontal", "we")):
            lay(orient + ".TScrollbar",
                [(orient + ".Scrollbar.trough", {"sticky": side, "children": [
                    (orient + ".Scrollbar.thumb",
                     {"expand": "1", "sticky": "nswe"})]})])
            cfg(orient + ".TScrollbar", background=SCROLL, troughcolor=CARD,
                bordercolor=CARD, lightcolor=SCROLL, darkcolor=SCROLL,
                arrowsize=10, gripcount=0, borderwidth=0)
            mp(orient + ".TScrollbar",
               background=[("active", SCROLL_HI), ("pressed", ACC)],
               lightcolor=[("active", SCROLL_HI), ("pressed", ACC)],
               darkcolor=[("active", SCROLL_HI), ("pressed", ACC)])
        cfg("Page.Vertical.TScrollbar", troughcolor=PAGE, bordercolor=PAGE)

        # Schieberegler: schmale Spur, Griff in der Akzentfarbe. Der Griff
        # kommt aus "background", der beim Ueberfahren hell werden wuerde.
        cfg("TScale", background=ACC, troughcolor=FIELD, bordercolor=FIELD,
            lightcolor=ACC, darkcolor=ACC, gripcount=0, sliderlength=22,
            sliderthickness=12, troughrelief="flat", borderwidth=0)
        mp("TScale",
           background=[("disabled", MUTED), ("active", ACC_HI),
                       ("pressed", ACC_HI)],
           lightcolor=[("active", ACC_HI)], darkcolor=[("active", ACC_HI)])

        cfg("Ban.TFrame", background=BAN)
        cfg("Ban.TLabel", background=BAN, foreground=FG)
        cfg("BanHead.TLabel", background=BAN, foreground="#ffffff",
            font=(UI_FONT_SB, 11))
        cfg("BanDim.TLabel", background=BAN, foreground="#b6b1dc")
        cfg("Ban.TButton", background="#4b4590", foreground=FG,
            padding=(12, 6), borderwidth=0, focuscolor="#4b4590")
        mp("Ban.TButton", background=[("active", "#5d56ad")],
           focuscolor=[("active", "#5d56ad")])

    # --------------------------------------------------------- Bausteine
    def _card(self, parent, number, title, hint=None, expand=False):
        """Eine Karte mit nummeriertem Kopf. Gibt den Inhaltsbereich zurueck."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=(18, 14, 18, 16))
        card.pack(fill="both" if expand else "x", expand=expand, pady=(0, 12))
        head = ttk.Frame(card)
        head.pack(fill="x", pady=(0, 12))
        if number:
            badge = tk.Canvas(head, width=26, height=26, bg=CARD,
                              highlightthickness=0, takefocus=0)
            badge.create_oval(1, 1, 25, 25, fill=ACC, outline="")
            badge.create_text(13, 13, text=str(number), fill="#ffffff",
                              font=(UI_FONT_SB, 10))
            badge.pack(side="left", padx=(0, 10))
        ttk.Label(head, text=title, style="Title.TLabel").pack(side="left")
        if hint:
            ttk.Label(head, text=hint, style="Dim.TLabel").pack(
                side="left", padx=(12, 0), pady=(3, 0))
        body = ttk.Frame(card)
        body.pack(fill="both", expand=True)
        return body

    def _logo(self, size=34):
        """Das App-Symbol fuer die Kopfzeile (ohne Pillow: keines)."""
        if getattr(self, "_logo_img", None) is None:
            self._logo_img = False
            try:
                from PIL import Image, ImageTk
                im = Image.open(os.path.join(APP_DIR, "assets", "dubforge.png"))
                im = im.convert("RGBA").resize((size, size), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(im)
            except Exception:
                pass
        return self._logo_img or None

    def _build_ui(self):
        self.title(t("title"))
        cvmode = self.fmt.get() == "cv"

        # Der Inhalt liegt in einem Canvas mit Scrollbalken. Ohne das war
        # Schritt 3 bei nicht maximiertem Fenster schlicht nicht erreichbar.
        outer = ttk.Frame(self, style="Page.TFrame")
        outer.pack(fill="both", expand=True)
        self.ui_root = outer

        # Das Update-Banner liegt bewusst ausserhalb des Scrollbereichs,
        # damit es nicht weggescrollt werden kann.
        self.banner = ttk.Frame(outer, style="Ban.TFrame")
        self.upd_text = None
        self.upd_status = None

        host = ttk.Frame(outer, style="Page.TFrame")
        host.pack(fill="both", expand=True)
        self.scroll_host = host

        # yscrollincrement macht das Mausrad berechenbar: 3 Einheiten = 60 px
        self.vcanvas = tk.Canvas(host, bg=PAGE, highlightthickness=0,
                                 takefocus=0, yscrollincrement=20)
        self.vcanvas.pack(side="left", fill="both", expand=True)
        vbar = ttk.Scrollbar(host, orient="vertical", command=self.vcanvas.yview,
                             style="Page.Vertical.TScrollbar")
        vbar.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.vcanvas.configure(yscrollcommand=vbar.set)

        root = ttk.Frame(self.vcanvas, style="Page.TFrame", padding=(20, 16))
        self._root_win = self.vcanvas.create_window((0, 0), window=root,
                                                    anchor="nw")
        self.root_frame = root
        root.bind("<Configure>", self._scroll_geom)
        self.vcanvas.bind("<Configure>", self._scroll_geom)

        # ---------------- Kopfzeile: Logo, Name, Zielformat, Sprache
        top = ttk.Frame(root, style="Page.TFrame")
        top.pack(fill="x", pady=(0, 16))
        logo = self._logo()
        if logo:
            tk.Label(top, image=logo, bg=PAGE, bd=0).pack(side="left",
                                                          padx=(0, 10))
        ttk.Label(top, text="DubForge", style="App.TLabel").pack(side="left")
        ttk.Label(top, text=t("tagline"), style="PageDim.TLabel").pack(
            side="left", padx=(12, 0), pady=(6, 0))

        self.lang_box = ttk.Combobox(top, textvariable=self.lang_var, width=9,
                                     state="readonly",
                                     values=("Deutsch", "English"))
        self.lang_box.pack(side="right")
        self.lang_box.bind("<<ComboboxSelected>>", self._change_lang)
        ttk.Label(top, text=t("lang_label"),
                  style="PageDim.TLabel").pack(side="right", padx=(0, 8))

        seg = ttk.Frame(top, style="Page.TFrame")
        seg.pack(side="right", padx=(0, 24))
        ttk.Label(seg, text=t("fmt_label"),
                  style="PageDim.TLabel").pack(side="left", padx=(0, 8))
        for val, key in (("dubstage", "fmt_ds"), ("cv", "fmt_cv")):
            ttk.Radiobutton(seg, text=t(key), value=val, variable=self.fmt,
                            style="Seg.TRadiobutton",
                            command=self._change_fmt).pack(side="left")

        # ---------------- Schritt 1: Quelle
        step1 = self._card(root, 1, t("s1"), hint=t("s1_hint"))

        row = ttk.Frame(step1)
        row.pack(fill="x")
        ttk.Radiobutton(row, text=t("src_url"), value="url",
                        variable=self.src_mode,
                        command=self._sync_src).pack(side="left", padx=(0, 18))
        ttk.Radiobutton(row, text=t("src_file"), value="file",
                        variable=self.src_mode,
                        command=self._sync_src).pack(side="left")
        ttk.Label(row, text=t("fmt_hint_cv") if cvmode else t("fmt_hint_ds"),
                  style="Dim.TLabel").pack(side="right")

        r2 = ttk.Frame(step1)
        r2.pack(fill="x", pady=(10, 0))
        self.url_entry = ttk.Entry(r2, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.file_btn = ttk.Button(r2, text=t("pick_file"), command=self._pick_file)
        self.file_btn.pack(side="left", padx=(8, 0))

        r3 = ttk.Frame(step1)
        r3.pack(fill="x", pady=(10, 0))
        ttk.Label(r3, text=t("from"), style="Field.TLabel").pack(side="left")
        ttk.Entry(r3, textvariable=self.t_start, width=11).pack(
            side="left", padx=(6, 14))
        ttk.Label(r3, text=t("to"), style="Field.TLabel").pack(side="left")
        ttk.Entry(r3, textvariable=self.t_end, width=11).pack(
            side="left", padx=(6, 10))
        ttk.Label(r3, text=t("time_hint"),
                  style="Dim.TLabel").pack(side="left", padx=(4, 0))
        ttk.Checkbutton(r3, text=t("sep_voc"),
                        variable=self.sep_var).pack(side="right")

        r4 = ttk.Frame(step1)
        r4.pack(fill="x", pady=(14, 0))
        self.analyze_btn = ttk.Button(r4, text=t("analyze"),
                                      style="Accent.TButton",
                                      command=self.start_analyze)
        self.analyze_btn.pack(side="left")
        ttk.Label(r4, text=t("demucs_hint"),
                  style="Dim.TLabel").pack(side="left", padx=12)
        self.upd_btn = ttk.Button(r4, text=t("upd_ytdlp"), style="Ghost.TButton",
                                  command=self.update_ytdlp)
        self.upd_btn.pack(side="right")

        # ---------------- Schritt 2: Clips
        step2 = self._card(root, 2, t("s2"), hint=t("mouse_hint"), expand=True)

        self.canvas = tk.Canvas(step2, height=180, bg=WAVE_BG,
                                highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="x")
        self.canvas.bind("<Configure>", lambda e: self.draw_wave())
        self.canvas.bind("<ButtonPress-1>", self._canvas_down)
        self.canvas.bind("<B1-Motion>", self._canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_up)
        self.canvas.bind("<MouseWheel>", self._canvas_wheel)
        self.canvas.bind("<Double-Button-1>", lambda e: self._play_selected())

        nav = ttk.Frame(step2)
        nav.pack(fill="x", pady=(8, 0))
        ttk.Button(nav, text=t("zoom_in"), style="Ghost.TButton",
                   command=lambda: self._zoom(0.6)).pack(side="left")
        ttk.Button(nav, text=t("zoom_out"), style="Ghost.TButton",
                   command=lambda: self._zoom(1.7)).pack(side="left", padx=4)
        ttk.Button(nav, text=t("zoom_all"), style="Ghost.TButton",
                   command=self._zoom_all).pack(side="left")
        self.hscroll = ttk.Scale(nav, from_=0.0, to=1.0, orient="horizontal",
                                 command=self._scroll_to)
        self.hscroll.pack(side="left", fill="x", expand=True, padx=(14, 0))

        mid = ttk.Frame(step2)
        mid.pack(fill="both", expand=True, pady=(12, 0))

        spec = [("nr", "col_nr", 44), ("name", "col_name", 170)]
        if cvmode:
            spec.append(("char", "col_char", 110))
        spec += [("start", "col_start", 85), ("end", "col_end", 85),
                 ("len", "col_len", 70), ("caption", "col_caption", 300)]
        cols = tuple(s[0] for s in spec)
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=8)
        for c, key, w in spec:
            self.tree.heading(c, text=t(key).upper() if c != "nr" else "#")
            self.tree.column(
                c, width=w,
                anchor="w" if c in ("name", "char", "caption") else "center")
        self.tree.tag_configure("odd", background=ROW_ALT)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        sb.pack(side="left", fill="y", padx=(4, 0))
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._tree_select)
        self.tree.bind("<Double-Button-1>", self._rename_selected)

        side = ttk.Frame(mid, padding=(14, 0, 0, 0))
        side.pack(side="left", fill="y")
        for key, cmd in (("btn_play", self._play_selected),
                         ("btn_stop", self._stop_play),
                         ("btn_rename", self._rename_selected),
                         ("btn_split", self._split_selected),
                         ("btn_delete", self._delete_selected)):
            ttk.Button(side, text=t(key), width=15, command=cmd).pack(
                fill="x", pady=(0, 6))
        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=(6, 10))
        ttk.Label(side, text=t("sensitivity"), style="Field.TLabel").pack(
            anchor="w")
        ttk.Scale(side, from_=0.4, to=2.5, variable=self.sens,
                  orient="horizontal", length=150).pack(fill="x", pady=(4, 0))
        ttk.Label(side, text=t("maxlen"), style="Field.TLabel").pack(
            anchor="w", pady=(10, 0))
        ttk.Spinbox(side, from_=1.0, to=30.0, increment=0.5,
                    textvariable=self.maxlen, width=8).pack(fill="x",
                                                            pady=(4, 0))
        ttk.Button(side, text=t("redetect"), width=15,
                   command=self.redetect).pack(fill="x", pady=(12, 0))

        cap = ttk.Frame(step2)
        cap.pack(fill="x", pady=(12, 0))
        ttk.Label(cap, text=t("caption"), style="Field.TLabel").pack(side="left")
        self.caption_entry = ttk.Entry(cap, textvariable=self.caption_var)
        self.caption_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.caption_entry.bind("<Return>", self._caption_next)
        self.caption_entry.bind("<FocusOut>", lambda e: self._caption_save())
        ttk.Label(cap, text=t("caption_hint"),
                  style="Dim.TLabel").pack(side="left")

        # ---------------- Figur und Figurenbild (nur Choicer Voicer)
        self.char_entry = None
        self.char_thumb = None
        if cvmode:
            ch = ttk.Frame(step2)
            ch.pack(fill="x", pady=(8, 0))
            ttk.Label(ch, text=t("character"), style="Field.TLabel").pack(
                side="left")
            self.char_entry = ttk.Entry(ch, textvariable=self.char_var,
                                        width=20)
            self.char_entry.pack(side="left", padx=8)
            self.char_entry.bind("<Return>", lambda e: self._char_save())
            self.char_entry.bind("<FocusOut>", lambda e: self._char_save())
            ttk.Button(ch, text=t("btn_frame"),
                       command=self._grab_char_image).pack(side="left")
            self.char_thumb = tk.Label(ch, bg=CARD, bd=0)
            self.char_thumb.pack(side="left", padx=10)
            ttk.Label(ch, text=t("char_hint"),
                      style="Dim.TLabel").pack(side="left")

        # Automatische Untertitel: eigene Leiste, klar abgesetzt.
        ttk.Separator(step2, orient="horizontal").pack(fill="x", pady=(14, 0))
        asr = ttk.Frame(step2, padding=(0, 12, 0, 0))
        asr.pack(fill="x")
        ttk.Label(asr, text=t("asr_language"), style="Field.TLabel").pack(
            side="left")
        ttk.Combobox(asr, textvariable=self.asr_language, values=tr.LANGUAGES,
                     width=5).pack(side="left", padx=(6, 14))
        ttk.Label(asr, text=t("asr_model"), style="Field.TLabel").pack(
            side="left")
        ttk.Combobox(asr, textvariable=self.asr_model, values=tr.MODELS,
                     state="readonly", width=10).pack(side="left", padx=(6, 14))
        ttk.Label(asr, text=t("asr_device"), style="Field.TLabel").pack(
            side="left")
        ttk.Combobox(asr, textvariable=self.asr_device, values=("cpu", "cuda"),
                     state="readonly", width=5).pack(side="left", padx=(6, 14))
        ttk.Checkbutton(asr, text=t("asr_replace"),
                        variable=self.asr_replace).pack(side="left")
        self.transcribe_btn = ttk.Button(asr, text=t("asr_generate"),
                                         command=self.start_transcribe)
        self.transcribe_btn.pack(side="right")
        ttk.Label(step2, text=t("asr_hint"), style="Dim.TLabel",
                  wraplength=1000).pack(anchor="w", pady=(6, 0))

        # ---------------- Schritt 3: Bauen
        step3 = self._card(root, 3, t("s3"))

        g = ttk.Frame(step3)
        g.pack(fill="x")
        pad = dict(pady=(0, 10))
        ttk.Label(g, text=t("pack_name"), style="Field.TLabel").grid(
            row=0, column=0, sticky="w", **pad)
        ttk.Entry(g, textvariable=self.pack_name, width=28).grid(
            row=0, column=1, sticky="w", padx=8, **pad)
        ttk.Checkbutton(g, text=t("is_dub"), variable=self.is_dub).grid(
            row=0, column=2, padx=(16, 6), sticky="w", **pad)
        vh = ttk.Frame(g)
        vh.grid(row=0, column=3, columnspan=2, sticky="e", **pad)
        ttk.Label(vh, text=t("vheight"), style="Field.TLabel").pack(
            side="left", padx=(10, 8))
        ttk.Combobox(vh, textvariable=self.vheight, width=6, state="readonly",
                     values=("1080", "720", "540", "480", "360")).pack(
            side="left")

        ttk.Label(g, text=t("target_dir"), style="Field.TLabel").grid(
            row=1, column=0, sticky="w", **pad)
        ttk.Entry(g, textvariable=self.target_dir, width=52).grid(
            row=1, column=1, columnspan=3, sticky="we", padx=8, **pad)
        ttk.Button(g, text=t("browse"),
                   command=self._pick_target).grid(row=1, column=4,
                                                   sticky="we", **pad)
        self.chars_lbl = None
        if cvmode:
            ttk.Label(g, text=t("pack_title"), style="Field.TLabel").grid(
                row=2, column=0, sticky="w", **pad)
            ttk.Entry(g, textvariable=self.pack_title).grid(
                row=2, column=1, columnspan=3, sticky="we", padx=8, **pad)
            ttk.Button(g, text=t("btn_icon"),
                       command=self._grab_pack_icon).grid(row=2, column=4,
                                                          sticky="we", **pad)

            ttk.Label(g, text=t("pack_authors"), style="Field.TLabel").grid(
                row=3, column=0, sticky="w", **pad)
            ttk.Entry(g, textvariable=self.pack_authors, width=30).grid(
                row=3, column=1, sticky="we", padx=8, **pad)
            ttk.Label(g, text=t("authors_hint"), style="Dim.TLabel").grid(
                row=3, column=2, columnspan=2, sticky="w", **pad)

            ttk.Label(g, text=t("pack_readme"), style="Field.TLabel").grid(
                row=4, column=0, sticky="w", **pad)
            ttk.Entry(g, textvariable=self.pack_readme).grid(
                row=4, column=1, columnspan=3, sticky="we", padx=8, **pad)

            self.chars_lbl = ttk.Label(g, text=t("chars_none"),
                                       style="Dim.TLabel")
            self.chars_lbl.grid(row=5, column=1, columnspan=3, sticky="w",
                                padx=8, **pad)

        g.columnconfigure(3, weight=1)

        act = ttk.Frame(step3)
        act.pack(fill="x", pady=(6, 0))
        self.build_btn = ttk.Button(act, text=t("build"),
                                    style="Accent.TButton", command=self.start_build)
        self.build_btn.pack(side="left")
        self.install_btn = ttk.Button(act, text=t("install"),
                                      style="Go.TButton", command=self.install)
        self.install_btn.pack(side="left", padx=8)
        ttk.Button(act, text=t("open_out"), style="Ghost.TButton",
                   command=self._open_out).pack(side="left")

        # ---------------- Fortschritt und Protokoll
        logc = ttk.Frame(root, style="Card.TFrame", padding=(18, 14, 18, 16))
        logc.pack(fill="both", expand=False)
        srow = ttk.Frame(logc)
        srow.pack(fill="x")
        self.status = ttk.Label(srow, text=t("ready"), style="Status.TLabel")
        self.status.pack(side="left")
        self.prog = ttk.Progressbar(logc, mode="determinate", maximum=100)
        self.prog.pack(fill="x", pady=(8, 10))

        logf = ttk.Frame(logc)
        logf.pack(fill="both", expand=False)
        self.log = tk.Text(logf, height=7, bg=FIELD, fg=LOG_FG,
                           insertbackground=FG, relief="flat", bd=0,
                           padx=12, pady=10, highlightthickness=0,
                           selectbackground=ACC, font=(MONO_FONT, 9),
                           wrap="none")
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(logf, orient="vertical", command=self.log.yview)
        lsb.pack(side="left", fill="y", padx=(4, 0))
        self.log.configure(yscrollcommand=lsb.set)

        self._sync_src()
        self.after_idle(self._scroll_geom)
        if self.upd_info:
            self._show_banner()

    # ------------------------------------------------------------- Scrollen
    def _scroll_geom(self, _e=None):
        """Inhaltsbreite ans Fenster koppeln, Hoehe mitwachsen lassen."""
        try:
            c, f = self.vcanvas, self.root_frame
            w = max(1, c.winfo_width())
            # Mindestens fensterhoch, damit expand=True weiter greift,
            # solange Platz da ist; darueber hinaus so hoch wie noetig.
            h = max(c.winfo_height(), f.winfo_reqheight())
            c.itemconfigure(self._root_win, width=w, height=h)
            c.configure(scrollregion=(0, 0, w, h))
        except Exception:
            pass

    def _wheel(self, event):
        """Mausrad scrollt die Seite - ausser das Widget scrollt selbst."""
        num = getattr(event, "num", 0)
        if num == 4:
            step = -1
        elif num == 5:
            step = 1
        else:
            step = -1 if getattr(event, "delta", 0) > 0 else 1

        w = event.widget
        for _ in range(30):                      # Schutz gegen Endlosschleife
            if w is None or w is self:
                break
            if w is getattr(self, "canvas", None):
                return                           # Wellenform zoomt selbst
            try:
                if w.winfo_class() in ("TSpinbox", "Spinbox"):
                    return                       # Spinbox zaehlt selbst
            except Exception:
                pass
            if w in (getattr(self, "tree", None), getattr(self, "log", None),
                     getattr(self, "upd_text", None)) and w is not None:
                first, last = w.yview()
                if (step < 0 and first > 0.0) or (step > 0 and last < 1.0):
                    return                       # hat noch Weg
                break                            # am Anschlag: Seite scrollen
            try:
                parent = w.winfo_parent()
                w = self.nametowidget(parent) if parent else None
            except Exception:
                break

        try:
            self.vcanvas.yview_scroll(step * 3, "units")
        except Exception:
            pass

    # ---------------------------------------------------------- Update
    def _check_update(self):
        """Beim Start nachsehen, ob es etwas Neues gibt."""
        # Zuerst der zuletzt gemerkte Stand - dann steht das Banner sofort,
        # auch wenn gerade nicht nachgefragt wird.
        cache = self.cfg.get("upd_cache") or {}
        if cache.get("tag") and upd.is_newer(cache["tag"]):
            self.upd_info = cache
            self._show_banner()

        if not upd.due(self.cfg):
            return

        def work():
            try:
                info = upd.check_latest()
            except Exception:
                return                      # kein Netz, kein Drama
            self.msgq.put(("update", info))

        threading.Thread(target=work, daemon=True).start()

    def _show_banner(self):
        info = self.upd_info
        b = getattr(self, "banner", None)
        if b is None:
            return
        for c in b.winfo_children():
            c.destroy()
        self.upd_text = None
        self.upd_status = None
        if not info or self.upd_dismissed:
            b.pack_forget()
            return

        head = ttk.Frame(b, style="Ban.TFrame", padding=(12, 8))
        head.pack(fill="x")
        ttk.Label(head, text=t("upd_head", info.get("version", "?")),
                  style="BanHead.TLabel").pack(side="left")
        ttk.Label(head, text="    " + t("upd_sub", upd.VERSION),
                  style="BanDim.TLabel").pack(side="left")

        ttk.Button(head, text=t("upd_later"), style="Ban.TButton",
                   command=self._hide_banner).pack(side="right", padx=(6, 0))
        ttk.Button(head, text=t("upd_page"), style="Ban.TButton",
                   command=lambda: webbrowser.open(
                       info.get("page") or upd.RELEASES_PAGE)
                   ).pack(side="right", padx=6)
        self.upd_go = ttk.Button(head, text=t("upd_now"), style="Go.TButton",
                                 command=self._do_update)
        self.upd_go.pack(side="right", padx=6)
        ttk.Button(head, text=t("upd_less") if self.upd_open else t("upd_more"),
                   style="Ban.TButton",
                   command=self._toggle_notes).pack(side="right")

        if self.upd_open:
            body = ttk.Frame(b, style="Ban.TFrame", padding=(12, 0, 12, 10))
            body.pack(fill="x")
            txt = tk.Text(body, height=12, wrap="word", bg=BAN_TXT,
                          fg="#ded9ff", relief="flat", padx=10, pady=8,
                          highlightthickness=0, font=("Segoe UI", 9))
            txt.insert("1.0", upd.plain_notes(info.get("notes"))
                       or t("upd_nonotes"))
            txt.configure(state="disabled")
            txt.pack(side="left", fill="both", expand=True)
            sb = ttk.Scrollbar(body, orient="vertical", command=txt.yview)
            sb.pack(side="left", fill="y")
            txt.configure(yscrollcommand=sb.set)
            self.upd_text = txt

        self.upd_status = ttk.Label(b, text="", style="BanDim.TLabel",
                                    padding=(12, 0, 12, 8))
        if self.upd_busy:
            self.upd_status.pack(fill="x")

        b.pack(side="top", fill="x", before=self.scroll_host)

    def _toggle_notes(self):
        self.upd_open = not self.upd_open
        self._show_banner()

    def _hide_banner(self):
        self.upd_dismissed = True
        self._show_banner()

    def _upd_say(self, text):
        if self.upd_status is None:
            return
        self.upd_status.configure(text=text)
        if not self.upd_status.winfo_ismapped():
            self.upd_status.pack(fill="x")

    def _do_update(self):
        info = self.upd_info
        if not info or self.upd_busy:
            return
        if not info.get("zip"):
            webbrowser.open(info.get("page") or upd.RELEASES_PAGE)
            return
        if not messagebox.askyesno(t("upd_ask_t"),
                                   t("upd_ask", info.get("tag", "?"))):
            return

        self.upd_busy = True
        try:
            self.upd_go.configure(state="disabled")
        except Exception:
            pass
        self._upd_say(t("upd_dl", info.get("tag", "?"), 0))

        def work():
            wd = tempfile.mkdtemp(prefix="dubstage_upd_")
            try:
                zp = os.path.join(wd, "release.zip")

                def prog(done, total):
                    pct = int(done * 100 / total) if total else 0
                    self.msgq.put(("upd_say",
                                   t("upd_dl", info.get("tag", "?"), pct)))

                upd.download_zip(info["zip"], zp, progress=prog)
                self.msgq.put(("upd_say", t("upd_check")))
                root = upd.stage(zp, os.path.join(wd, "neu"))
                self.msgq.put(("upd_say", t("upd_swap")))
                upd.apply(root, APP_DIR, which="DubForge",
                          tag=info.get("tag", ""))
                self.msgq.put(("upd_quit", None))
            except Exception as e:
                self.msgq.put(("upd_error", "%s" % e))

        threading.Thread(target=work, daemon=True).start()

    # -------------------------------------------------------- Sprachwechsel
    def _change_lang(self, _e=None):
        code = "en" if self.lang_var.get().startswith("English") else "de"
        if code == LANG:
            return
        set_lang(code)
        self.cfg["lang"] = code
        save_cfg(self.cfg)
        self._rebuild_ui()

    def _change_fmt(self):
        """Zielformat gewechselt - die Oberflaeche zeigt andere Felder."""
        self._caption_save()
        self._char_save()
        self.cfg["fmt"] = self.fmt.get()
        save_cfg(self.cfg)
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Oberflaeche neu aufbauen, Protokoll und Auswahl behalten."""
        keep = self.log.get("1.0", "end-1c")
        self.ui_root.destroy()
        self._build_ui()
        if keep.strip():
            self.log.insert("end", keep + "\n")
            self.log.see("end")
        self.refresh_list()
        self.draw_wave()
        self._update_chars_label()
        self._set_busy(self.busy)

    # -------------------------------------------------------------- Helfer
    def _sync_src(self):
        url = self.src_mode.get() == "url"
        self.url_entry.configure(state="normal" if url else "readonly")
        self.file_btn.configure(state="disabled" if url else "normal")

    def _pick_file(self):
        p = filedialog.askopenfilename(
            title=t("dlg_video_t"),
            filetypes=[(t("dlg_filter"), "*.mp4 *.mkv *.mov *.avi *.webm *.m4v "
                                         "*.wav *.mp3 *.ogg *.m4a *.flac"),
                       (t("dlg_allfiles"), "*.*")])
        if p:
            self.url_var.set(p)
            self.src_mode.set("file")
            self._sync_src()

    def _pick_target(self):
        p = filedialog.askdirectory(title=t("dlg_target_t"))
        if p:
            self.target_dir.set(p)

    def _open_out(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        self._open_folder(OUT_DIR)

    @staticmethod
    def _open_folder(path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _check_tools(self):
        # Im Hintergrund: yt-dlp und ffmpeg mehrfach zu starten dauert ein
        # paar Sekunden - so lange soll das Fenster nicht auf sich warten
        # lassen. _log geht ueber die Warteschlange, ist also threadsicher.
        def work():
            try:
                self._check_tools_work()
            except Exception:
                self._log(traceback.format_exc())
        threading.Thread(target=work, daemon=True).start()

    def _check_tools_work(self):
        missing = []
        if not pc.find_tool("ffmpeg"):
            missing.append("ffmpeg")
        yt = pc.ytdlp()
        if not yt:
            missing.append("yt-dlp")
        if missing:
            self._log(t("missing", ", ".join(missing)))
        else:
            th, vo = pc.check_encoders()
            self._log(t("ff_ready",
                        t("yes") if th else t("no_caps"),
                        t("yes") if vo else t("no_caps")))
        if not yt:
            return
        ver, age = pc.ytdlp_version()
        self._ytdlp_age = age
        if ver and age is not None:
            where = yt[0] if len(yt) == 1 else os.path.dirname(sys.executable)
            self._log(t("ytdlp_ver", ver, age) + "   -   " + str(where))
            if age > 60:
                self._log(t("ytdlp_old", age))

    def update_ytdlp(self):
        """Holt die aktuelle yt-dlp-Version nach."""
        before = pc.ytdlp_version()[0]

        def work():
            self._set_status(t("st_upd"), 30)
            ver, age = pc.update_ytdlp(log=self._log)
            self._new_ytdlp = ver
            self._ytdlp_age = age
            self._set_status(t("st_upd"), 100)

        def done():
            ver = getattr(self, "_new_ytdlp", None)
            if ver and ver != before:
                self._log(t("upd_done", ver))
                messagebox.showinfo(t("title"), t("upd_done", ver))
            elif ver:
                # Gleiche Version wie vorher - das ist fast immer eine
                # aeltere Datei im PATH, die die pip-Installation verdeckt.
                self._log(t("upd_same", ver))
                messagebox.showwarning(t("title"), t("upd_same", ver))
            else:
                messagebox.showwarning(t("title"),
                                       t("ytdlp_fail", pc.console_python()))
        self._bg(work, on_done=done)

    # -------------------------------------------------- Thread-Kommunikation
    def _log(self, text):
        self.msgq.put(("log", str(text)))

    def _set_status(self, text, pct=None):
        self.msgq.put(("status", (text, pct)))

    def _pump(self):
        try:
            while True:
                kind, payload = self.msgq.get_nowait()
                if kind == "log":
                    self.log.insert("end", payload + "\n")
                    self.log.see("end")
                    if int(self.log.index("end-1c").split(".")[0]) > 600:
                        self.log.delete("1.0", "200.0")
                elif kind == "status":
                    text, pct = payload
                    self.status.configure(text=text)
                    if pct is not None:
                        self.prog.configure(value=max(0, min(100, pct)))
                elif kind == "done":
                    self._set_busy(False)
                    payload()
                elif kind == "error":
                    self._set_busy(False)
                    messagebox.showerror(t("dlg_err"), payload)
                elif kind == "update":
                    upd.note_checked(self.cfg)
                    self.cfg["upd_cache"] = payload
                    save_cfg(self.cfg)
                    if payload.get("newer") and not self.upd_dismissed:
                        self.upd_info = payload
                        self._show_banner()
                elif kind == "upd_say":
                    self._upd_say(payload)
                elif kind == "upd_quit":
                    self._upd_say(t("upd_swap"))
                    self.after(700, self._on_close)
                elif kind == "upd_error":
                    self.upd_busy = False
                    try:
                        self.upd_go.configure(state="normal")
                    except Exception:
                        pass
                    self._upd_say("")
                    messagebox.showerror(t("upd_fail_t"), t("upd_fail", payload))
        except queue.Empty:
            pass
        self.after(80, self._pump)

    def _set_busy(self, flag):
        self.busy = flag
        if flag:
            self._drag = None
            def disable(widget):
                if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Checkbutton,
                                       ttk.Radiobutton, ttk.Scale, ttk.Treeview)):
                    if not widget.instate(["disabled"]):
                        self._busy_widgets.append(widget)
                        widget.state(["disabled"])
                for child in widget.winfo_children():
                    disable(child)
            disable(self.ui_root)
        else:
            for widget in self._busy_widgets:
                if widget.winfo_exists():
                    widget.state(["!disabled"])
            self._busy_widgets = []
        if not flag:
            self.prog.configure(value=0)

    def _bg(self, fn, on_done=None):
        if self.busy:
            messagebox.showinfo(t("dlg_busy_t"), t("dlg_busy"))
            return
        self._set_busy(True)

        def wrapper():
            try:
                fn()
                self.msgq.put(("done", on_done or (lambda: None)))
            except Exception as ex:
                self._log(traceback.format_exc())
                self.msgq.put(("error", str(ex)))
        threading.Thread(target=wrapper, daemon=True).start()

    # ------------------------------------------------------------ ANALYSE
    def start_transcribe(self):
        if self.busy:
            return
        if not self.audio_path or not self.clips:
            messagebox.showinfo(t("dlg_first_t"), t("dlg_first"))
            return
        language = self.asr_language.get().strip().lower()
        if not language:
            messagebox.showinfo(t("title"), t("asr_language_required"))
            return
        self._caption_save()
        self._save_cfg()
        media, model, device = self.audio_path, self.asr_model.get(), self.asr_device.get()
        clips = [dict(c) for c in self.clips]
        overwrite = self.asr_replace.get()
        result = {}

        def progress(message, percent):
            self._log(message)
            self._set_status(message, percent)

        def work():
            try:
                transcript = tr.transcribe(media, language, model, device, progress)
                captions = tr.map_captions(transcript, clips)
                tr.apply_captions(clips, captions, overwrite=overwrite)
                result.update(transcript=transcript, clips=clips, captions=captions)
            except Exception as exc:
                raise RuntimeError(t("asr_error", exc)) from exc

        def done():
            self.transcript = result["transcript"]
            self.clips = result["clips"]
            self.refresh_list()
            empty = [c["name"] for c, text in zip(self.clips, result["captions"]) if not text]
            if empty:
                self._log(t("asr_empty", ", ".join(empty)))

        self._bg(work, on_done=done)

    def _remap_captions(self):
        if self.transcript is not None:
            tr.apply_captions(self.clips, tr.map_captions(self.transcript, self.clips), remap=True)

    def start_analyze(self):
        if self.busy:
            return
        src = self.url_var.get().strip()
        if not src:
            messagebox.showinfo(t("dlg_missing_t"), t("dlg_no_src"))
            return
        try:
            t0 = pc.parse_time(self.t_start.get())
            t1 = pc.parse_time(self.t_end.get())
        except ValueError as ex:
            messagebox.showerror(t("dlg_time_t"), str(ex))
            return
        if t0 is not None and t1 is not None and t1 <= t0:
            messagebox.showerror(t("dlg_time_t"), t("dlg_time_order"))
            return
        self._save_cfg()
        mode = self.src_mode.get()
        sep = self.sep_var.get()
        self._bg(lambda: self._do_analyze(src, mode, t0, t1, sep),
                 on_done=self._after_analyze)

    def _do_analyze(self, src, mode, t0, t1, separate):
        self.transcript = None
        shutil.rmtree(self.work, ignore_errors=True)
        os.makedirs(self.work, exist_ok=True)
        self.backing_path = None

        if mode == "url":
            self._set_status(t("st_download"), 5)
            try:
                self.video_path = pc.download_youtube(src, t0, t1, self.work,
                                                      log=self._log)
            except Exception:
                age = getattr(self, "_ytdlp_age", None)
                if age is not None and age > 30:
                    self._log(t("dl_hint", age))
                raise
        else:
            if not os.path.isfile(src):
                raise RuntimeError(pc.M("file_missing", src))
            self._set_status(t("st_trim"), 5)
            self.video_path = pc.trim_local(src, t0, t1, self.work, log=self._log)

        self._set_status(t("st_audio"), 20)
        self.audio_path = os.path.join(self.work, "audio.wav")
        pc.extract_audio(self.video_path, self.audio_path, log=self._log)
        self.duration = pc.probe_duration(self.audio_path)
        self._log(t("log_len", self.duration))

        cut_source = self.audio_path
        if separate:
            self._set_status(t("st_demucs"), 30)
            try:
                voc, nov = pc.separate_vocals(self.audio_path, self.work,
                                              log=self._log)
                self.vocals_path = voc
                self.backing_path = nov
                cut_source = voc
                self._log(t("log_voc_ok"))
            except Exception as ex:
                self._log(t("log_voc_fail", str(ex).splitlines()[0][:70]))
                self.vocals_path = None
        else:
            self.vocals_path = None

        self._set_status(t("st_wave"), 78)
        self.wave_data, self.wave_sr = pc.load_mono(cut_source)
        self._peak_cache = (None, None)

        self._set_status(t("st_detect"), 88)
        found = pc.detect_clips(self.wave_data, self.wave_sr,
                                max_clip=float(self.maxlen.get()),
                                sensitivity=float(self.sens.get()))
        self.clips = [{"start": a, "end": b, "name": "clip%02d" % (i + 1),
                       "caption": ""}
                      for i, (a, b) in enumerate(found)]
        self._log(t("log_found", len(self.clips)))
        self._set_status(t("st_done_an"), 100)

    def _after_analyze(self):
        self.selected = 0 if self.clips else None
        self._zoom_all()
        self.refresh_list()
        self.draw_wave()

    def redetect(self):
        if self.busy:
            return
        if not len(self.wave_data):
            messagebox.showinfo(t("dlg_first_t"), t("dlg_first"))
            return
        found = pc.detect_clips(self.wave_data, self.wave_sr,
                                max_clip=float(self.maxlen.get()),
                                sensitivity=float(self.sens.get()))
        self._caption_save()
        previous = self.clips
        self.clips = [{"start": a, "end": b, "name": "clip%02d" % (i + 1),
                       "caption": ""}
                      for i, (a, b) in enumerate(found)]
        # Preserve manually edited clips verbatim through redetection. Replace
        # new detections overlapping them with those reviewed clip boundaries.
        manual = [dict(c) for c in previous if c.get("_manual_caption") or (
            c.get("caption") and c.get("caption") != c.get("_generated_caption"))]
        self.clips = [c for c in self.clips if not any(
            min(c["end"], m["end"]) > max(c["start"], m["start"]) for m in manual)]
        self.clips.extend(manual)
        self.clips.sort(key=lambda c: c["start"])
        self._remap_captions()
        self.selected = 0 if self.clips else None
        self._log(t("log_redet", len(self.clips)))
        self.refresh_list()
        self.draw_wave()

    # ---------------------------------------------------------- Clip-Liste
    def refresh_list(self):
        cvmode = self.fmt.get() == "cv"
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.clips):
            row = [i + 1, c["name"]]
            if cvmode:
                row.append(c.get("character", ""))
            row += ["%.3f" % c["start"], "%.3f" % c["end"],
                    "%.2f" % (c["end"] - c["start"]), c.get("caption", "")]
            self.tree.insert("", "end", iid=str(i), values=tuple(row),
                             tags=("odd",) if i % 2 else ())
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            self.tree.selection_set(str(self.selected))
            self.tree.see(str(self.selected))
        self._load_caption()

    def _tree_select(self, _e=None):
        sel = self.tree.selection()
        if sel:
            self._caption_save()          # noch mit der vorherigen Auswahl
            self._char_save()
            self.selected = int(sel[0])
            self._load_caption()
            self.draw_wave()

    # ------------------------------------------------------------ Untertitel
    def _load_caption(self):
        """Holt den Untertitel des gewaehlten Clips ins Eingabefeld."""
        self._caption_for = self.selected
        c = None
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            c = self.clips[self.selected]
        self.caption_var.set((c or {}).get("caption", ""))
        self.char_var.set((c or {}).get("character", ""))
        self._show_thumb((c or {}).get("character", ""))

    def _char_save(self):
        """Figur des gewaehlten Clips uebernehmen."""
        i = self._caption_for
        if i is None or not (0 <= i < len(self.clips)):
            return
        new = self.char_var.get().strip()
        if self.clips[i].get("character", "") != new:
            self.clips[i]["character"] = new
            try:
                self.tree.set(str(i), "char", new)
            except Exception:
                pass
        self._show_thumb(new)

    def _show_thumb(self, character):
        """Kleine Vorschau des Figurenbildes neben dem Eingabefeld."""
        lbl = getattr(self, "char_thumb", None)
        if lbl is None:
            return
        path = self.char_images.get((character or "").strip())
        self._thumb_img = None
        if not path or not os.path.isfile(path):
            lbl.configure(image="", text="", width=0)
            return
        try:
            from PIL import Image, ImageTk
            im = Image.open(path)
            im.thumbnail((84, 48))
            self._thumb_img = ImageTk.PhotoImage(im)
            lbl.configure(image=self._thumb_img, text="", width=0)
        except Exception:
            lbl.configure(image="", text=os.path.basename(path),
                          fg=DIM, width=0)

    def _grab_char_image(self):
        """Einzelbild beim gewaehlten Clip holen und der Figur zuordnen."""
        self._char_save()
        i = self.selected
        who = self.char_var.get().strip()
        if i is None or not (0 <= i < len(self.clips)) or not who:
            messagebox.showinfo(t("title"), t("frame_none"))
            return
        if not self.video_path or not os.path.isfile(self.video_path):
            messagebox.showinfo(t("title"), t("frame_none"))
            return
        c = self.clips[i]
        at = c["start"] + min(0.4, max(0.0, (c["end"] - c["start"]) / 2.0))
        out = os.path.join(self.work, "char_%s.png" % pc.safe_name(who, "figur"))
        try:
            pc.grab_frame(self.video_path, at, out, log=self._log)
        except Exception as ex:
            messagebox.showerror(t("dlg_err"), "%s" % ex)
            return
        self.char_images[who] = out
        self._show_thumb(who)
        self._log(t("frame_ok", who, at))

    def _grab_pack_icon(self):
        """Einzelbild als Symbol des Packs setzen."""
        i = self.selected
        at = 0.0
        if i is not None and 0 <= i < len(self.clips):
            at = self.clips[i]["start"]
        if not self.video_path or not os.path.isfile(self.video_path):
            messagebox.showinfo(t("title"), t("frame_none"))
            return
        out = os.path.join(self.work, "pack_icon.png")
        try:
            pc.grab_frame(self.video_path, at, out, log=self._log)
        except Exception as ex:
            messagebox.showerror(t("dlg_err"), "%s" % ex)
            return
        self.pack_icon = out
        self._log(t("frame_icon", at))
        self._update_chars_label()

    def _update_chars_label(self):
        lbl = getattr(self, "chars_lbl", None)
        if lbl is None:
            return
        names = self._characters()
        lbl.configure(text=t("chars_found", ", ".join(names))
                      if names else t("chars_none"))

    def _characters(self):
        """Alle vergebenen Figuren in der Reihenfolge des ersten Auftretens."""
        out = []
        for c in self.clips:
            who = (c.get("character") or "").strip()
            if who and who not in out:
                out.append(who)
        return out

    def _caption_save(self):
        """Schreibt das Eingabefeld in den Clip, zu dem es geladen wurde."""
        i = self._caption_for
        if i is None or not (0 <= i < len(self.clips)):
            return
        new = self.caption_var.get().strip()
        if self.clips[i].get("caption", "") != new:
            self.clips[i]["caption"] = new
            self.clips[i]["_manual_caption"] = True
            self.clips[i].pop("_generated_caption", None)
            try:
                self.tree.set(str(i), "caption", new)
            except Exception:
                pass

    def _caption_next(self, _e=None):
        self._caption_save()
        if self.selected is not None and self.selected < len(self.clips) - 1:
            nxt = str(self.selected + 1)
            self.tree.selection_set(nxt)
            self.tree.see(nxt)
            self.caption_entry.focus_set()
            self.caption_entry.selection_range(0, "end")
        return "break"

    def _rename_selected(self, _e=None):
        if self.busy:
            return
        if self.selected is None:
            return
        c = self.clips[self.selected]
        new = simpledialog.askstring(t("dlg_rename_t"), t("dlg_rename"),
                                     initialvalue=c["name"], parent=self)
        if new:
            c["name"] = new.strip()
            self.refresh_list()

    def _delete_selected(self):
        if self.busy:
            return
        if self.selected is None:
            return
        self._caption_save()
        del self.clips[self.selected]
        self.selected = min(self.selected, len(self.clips) - 1)
        if self.selected < 0:
            self.selected = None
        self._remap_captions()
        self.refresh_list()
        self.draw_wave()

    def _split_selected(self):
        if self.busy:
            return
        if self.selected is None:
            return
        self._caption_save()
        c = self.clips[self.selected]
        mid = (c["start"] + c["end"]) / 2.0
        if mid - c["start"] < 0.1 or c["end"] - mid < 0.1:
            return
        new = dict(c, start=mid, name=c["name"] + "_b")
        c["end"] = mid
        self.clips.insert(self.selected + 1, new)
        self._remap_captions()
        self.refresh_list()
        self.draw_wave()

    def _play_selected(self):
        if self.selected is None or not self.audio_path:
            return
        c = self.clips[self.selected]
        self._stop_play()
        src = self.vocals_path or self.audio_path
        fp = pc.ffplay()
        try:
            if fp:
                self.player = subprocess.Popen(
                    [fp, "-nodisp", "-autoexit", "-loglevel", "quiet",
                     "-ss", "%.3f" % c["start"],
                     "-t", "%.3f" % (c["end"] - c["start"]), src],
                    creationflags=pc._NOWINDOW)
            elif os.name == "nt":
                tmp = os.path.join(self.work, "_preview.wav")
                pc.run([pc.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", "%.3f" % c["start"], "-i", src,
                        "-t", "%.3f" % (c["end"] - c["start"]),
                        "-c:a", "pcm_s16le", tmp])
                import winsound
                winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as ex:
            self._log(t("log_noplay", ex))

    def _stop_play(self):
        if self.player and self.player.poll() is None:
            try:
                self.player.terminate()
            except Exception:
                pass
        self.player = None
        if os.name == "nt":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass

    # ------------------------------------------------------------ Wellenform
    def _zoom_all(self):
        self.view_a, self.view_b = 0.0, max(0.5, self.duration)
        self.draw_wave()

    def _zoom(self, factor):
        if self.duration <= 0:
            return
        centre = (self.view_a + self.view_b) / 2.0
        span = max(0.5, min(self.duration, (self.view_b - self.view_a) * factor))
        self.view_a = max(0.0, centre - span / 2)
        self.view_b = min(self.duration, self.view_a + span)
        self.view_a = max(0.0, self.view_b - span)
        self.draw_wave()

    def _scroll_to(self, value):
        if self.duration <= 0 or self._syncing:
            return
        span = self.view_b - self.view_a
        if span >= self.duration:
            return
        start = float(value) * (self.duration - span)
        self.view_a, self.view_b = start, start + span
        self.draw_wave()

    def _canvas_wheel(self, event):
        self._zoom(0.8 if event.delta > 0 else 1.25)

    def _x2t(self, x):
        w = max(1, self.canvas.winfo_width())
        return self.view_a + (x / w) * (self.view_b - self.view_a)

    def _t2x(self, tt):
        w = max(1, self.canvas.winfo_width())
        span = max(1e-6, self.view_b - self.view_a)
        return (tt - self.view_a) / span * w

    def draw_wave(self):
        cv = self.canvas
        cv.delete("all")
        w = max(1, cv.winfo_width())
        h = max(1, cv.winfo_height())
        top, bot = 10, h - 22               # Bereich der Welle, darunter Zeitachse
        mid = (top + bot) / 2.0

        if not len(self.wave_data) or self.duration <= 0:
            # Angedeutete Welle als Platzhalter, damit die Flaeche nicht tot wirkt.
            for x in range(0, w, 6):
                amp = 6 + 5 * abs(((x // 6) % 14) - 7) / 7.0
                cv.create_line(x, mid - amp, x, mid + amp, fill="#1b1f33",
                               width=3, capstyle="round")
            cv.create_text(w / 2, mid, fill=DIM, text=t("canvas_empty"),
                           font=(UI_FONT, 11))
            return

        span = max(1e-6, self.view_b - self.view_a)
        n = len(self.wave_data)
        a = int(self.view_a / self.duration * n)
        b = int(self.view_b / self.duration * n)
        b = max(a + 2, min(n, b))
        key = (a, b, w)
        if self._peak_cache[0] == key:
            peaks = self._peak_cache[1]
        else:
            peaks = pc.waveform_peaks(self.wave_data[a:b], w)
            self._peak_cache = (key, peaks)

        # Clips als Flaechen hinter der Welle; welche Spalten in einem Clip
        # liegen, bestimmt die Farbe der Welle darueber.
        inside = [False] * len(peaks)
        labels = []
        for i, c in enumerate(self.clips):
            if c["end"] < self.view_a or c["start"] > self.view_b:
                continue
            x0, x1 = self._t2x(c["start"]), self._t2x(c["end"])
            sel = (i == self.selected)
            cv.create_rectangle(x0, top, x1, bot,
                                fill=CLIP_SEL if sel else CLIP_FILL,
                                outline=ACC if sel else CLIP_EDGE,
                                width=2 if sel else 1)
            # Griffe an den Raendern: zeigen, dass man hier ziehen kann.
            for gx in (x0, x1):
                cv.create_line(gx, mid - 12, gx, mid + 12,
                               fill=ACC_HI if sel else CLIP_EDGE, width=3,
                               capstyle="round")
            for x in range(max(0, int(x0)), min(len(inside), int(x1) + 1)):
                inside[x] = True
            if x1 - x0 > 26:
                labels.append((x0, i + 1, sel))

        cv.create_line(0, mid, w, mid, fill="#1b1f33")
        amp = (bot - top) / 2.0 - 4
        for x, (lo, hi) in enumerate(peaks):
            y0 = mid - hi * amp
            y1 = mid - lo * amp
            if abs(y1 - y0) < 1:
                y1 = y0 + 1
            cv.create_line(x, y0, x, y1, fill=WAVE_IN if inside[x] else WAVE)

        # Nummern als kleine Plaketten oben links im Clip.
        for x0, nr, sel in labels:
            txt = str(nr)
            bw = 10 + 7 * len(txt)
            cv.create_rectangle(x0 + 4, top + 4, x0 + 4 + bw, top + 20,
                                fill=ACC if sel else "#2c2566", outline="")
            cv.create_text(x0 + 4 + bw / 2, top + 12, text=txt,
                           fill="#ffffff", font=(UI_FONT_SB, 8))

        step = self._nice_step(span)
        tt = (int(self.view_a / step)) * step
        while tt <= self.view_b:
            x = self._t2x(tt)
            cv.create_line(x, h - 18, x, h - 12, fill=EDGE)
            cv.create_text(x + 4, h - 9, anchor="w", fill=MUTED,
                           text=pc.fmt_time(tt)[:-2], font=(MONO_FONT, 8))
            tt += step

        if self.duration > span:
            self._syncing = True
            try:
                self.hscroll.set(self.view_a / max(1e-6, self.duration - span))
            finally:
                self._syncing = False

    @staticmethod
    def _nice_step(span):
        for s in (0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600):
            if span / s <= 12:
                return s
        return 900

    # ------------------------------------------------- Maus auf der Wellenform
    def _canvas_down(self, event):
        if self.busy:
            return
        self._caption_save()
        if not len(self.wave_data):
            return
        tt = self._x2t(event.x)
        tol = (self.view_b - self.view_a) / max(1, self.canvas.winfo_width()) * 6
        for i, c in enumerate(self.clips):
            if abs(tt - c["start"]) <= tol:
                self.selected = i
                self._drag = ("start", i)
                self.refresh_list()
                return
            if abs(tt - c["end"]) <= tol:
                self.selected = i
                self._drag = ("end", i)
                self.refresh_list()
                return
        for i, c in enumerate(self.clips):
            if c["start"] <= tt <= c["end"]:
                self.selected = i
                self._drag = None
                self.refresh_list()
                self.draw_wave()
                return
        self._drag = ("new", tt)
        self.draw_wave()

    def _canvas_move(self, event):
        if self.busy:
            return
        if not self._drag:
            return
        tt = max(0.0, min(self.duration, self._x2t(event.x)))
        kind, ref = self._drag
        if kind == "start":
            c = self.clips[ref]
            c["start"] = min(tt, c["end"] - 0.05)
        elif kind == "end":
            c = self.clips[ref]
            c["end"] = max(tt, c["start"] + 0.05)
        else:
            self.canvas.delete("newsel")
            x0, x1 = self._t2x(ref), event.x
            self.canvas.create_rectangle(x0, 10, x1, self.canvas.winfo_height() - 22,
                                         outline=ACC2, width=2, dash=(4, 3),
                                         tags="newsel")
            return
        self.draw_wave()

    def _canvas_up(self, event):
        if self.busy:
            return
        if not self._drag:
            return
        kind, ref = self._drag
        self._drag = None
        self.canvas.delete("newsel")
        if kind == "new":
            tt = max(0.0, min(self.duration, self._x2t(event.x)))
            a, b = min(ref, tt), max(ref, tt)
            if b - a >= 0.15:
                self.clips.append({"start": a, "end": b, "caption": "",
                                   "name": "clip%02d" % (len(self.clips) + 1)})
                self.clips.sort(key=lambda c: c["start"])
                self.selected = next(i for i, c in enumerate(self.clips)
                                     if abs(c["start"] - a) < 1e-9)
        self._remap_captions()
        self.refresh_list()
        self.draw_wave()

    # -------------------------------------------------------------- BAUEN
    def start_build(self):
        if self.busy:
            return
        self._caption_save()
        if not self.clips:
            messagebox.showinfo(t("dlg_noclips_t"), t("dlg_noclips"))
            return
        name = pc.safe_name(self.pack_name.get(), "Mein_Pack")
        self.pack_name.set(name)
        self._save_cfg()
        clips = sorted([dict(c) for c in self.clips], key=lambda c: c["start"])
        self._bg(lambda: self._do_build(name, clips), on_done=self._after_build)

    def _do_build(self, name, clips):
        if self.fmt.get() == "cv":
            return self._do_build_cv(name, clips)
        captions = {}
        os.makedirs(OUT_DIR, exist_ok=True)
        dest = os.path.join(OUT_DIR, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        dub = bool(self.is_dub.get())
        src_audio = self.vocals_path or self.audio_path

        lines = [t("ts_head", name)]

        total = len(clips)
        for i, c in enumerate(clips, 1):
            fn = pc.clip_filename(i, c["name"], c["start"], dub=dub)
            self._set_status(t("st_clip", i, total), 5 + 60 * i / max(1, total))
            pc.export_clip(src_audio, c["start"], c["end"],
                           os.path.join(dest, fn))
            cap = (c.get("caption") or "").strip()
            if cap:
                captions[fn] = cap
            lines.append("%-44s %10.3f   %5.2fs%s"
                         % (fn, c["start"], c["end"] - c["start"],
                            "   | " + cap if cap else ""))
            self._log("  %s   @ %.3f s%s" % (fn, c["start"],
                                             "   | " + cap if cap else ""))

        if captions:
            pc.write_captions(dest, captions)
            self._log("  %s (%d)" % (pc.CAPTION_FILE, len(captions)))

        if dub and self.transcript is not None:
            tr.write_outputs(dest, tr.subtitle_outputs(self.transcript))

        if dub and self.backing_path and os.path.isfile(self.backing_path):
            self._set_status(t("st_backing"), 68)
            pc.export_backing_track(self.backing_path,
                                    os.path.join(dest, "_backing_track.wav"),
                                    log=self._log)
            self._log("  _backing_track.wav")

        if dub:
            self._set_status(t("st_ogv"), 72)
            pc.convert_video(self.video_path,
                             os.path.join(dest, "dub_video.mp4"),
                             max_height=int(self.vheight.get()), log=self._log)
            self._log("  dub_video.mp4")
            with open(os.path.join(dest, "_TIMESTAMPS.txt"), "w",
                      encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        with open(os.path.join(dest, "_README.txt"), "w", encoding="utf-8") as f:
            f.write(t("readme", name,
                      t("type_dub") if dub else t("type_voice"), len(clips)))
            if dub:
                f.write(t("readme_dub"))

        self.built_path = dest
        self._set_status(t("st_built", dest), 100)

    def _do_build_cv(self, name, clips):
        """Pack im Choicer-Voicer-Format schreiben."""
        os.makedirs(OUT_DIR, exist_ok=True)
        dest = os.path.join(OUT_DIR, name)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        dub = bool(self.is_dub.get())
        src_audio = self.vocals_path or self.audio_path

        # Ein Bild je Figur - genau so machen es echte Packs.
        images = {}
        for who, path in sorted(self.char_images.items()):
            if who and os.path.isfile(path):
                fn = pc.safe_name(who, "figur") + ".png"
                shutil.copy2(path, os.path.join(dest, fn))
                images[who] = fn
                self._log("  " + fn)

        total = len(clips)
        for n, ((nr, who), c) in enumerate(zip(pc.cv_numbering(clips), clips), 1):
            base = "%02d_%s" % (nr, pc.safe_name(who, "clip"))
            self._set_status(t("st_clip", n, total), 5 + 60 * n / max(1, total))
            pc.export_clip(src_audio, c["start"], c["end"],
                           os.path.join(dest, base + ".wav"))
            pc.write_cv_meta(
                os.path.join(dest, base + pc.CV_META_EXT),
                caption=c.get("caption", ""),
                image=images.get(who, ""),
                timestamps=[c["start"]],
                characters=[who] if who else [])
            self._log("  %s.wav + %s%s   @ %.3f s"
                      % (base, base, pc.CV_META_EXT, c["start"]))

        # Pack-Beschreibung
        icon = ""
        if self.pack_icon and os.path.isfile(self.pack_icon):
            icon = "_icon.png"
            shutil.copy2(self.pack_icon, os.path.join(dest, icon))
            self._log("  " + icon)
        authors = [a.strip() for a in self.pack_authors.get().split(",")
                   if a.strip()]
        pc.write_pack_info(os.path.join(dest, pc.CV_PACK_INFO),
                           title=self.pack_title.get().strip() or name,
                           icon=icon, authors=authors,
                           readme=self.pack_readme.get().strip(),
                           characters=self._characters())
        self._log("  " + pc.CV_PACK_INFO)

        if dub and self.backing_path and os.path.isfile(self.backing_path):
            self._set_status(t("st_backing"), 68)
            pc.export_backing_track(self.backing_path,
                                    os.path.join(dest, "_backing_track.wav"),
                                    log=self._log)
            self._log("  _backing_track.wav")

        if dub:
            # Godot kann nur OGV - ohne dub_video.ogv laedt der Pack nicht.
            self._set_status(t("st_ogv"), 72)
            pc.convert_video(self.video_path,
                             os.path.join(dest, "dub_video.ogv"),
                             max_height=int(self.vheight.get()), log=self._log)
            self._log("  dub_video.ogv")

        self.built_path = dest
        self._set_status(t("st_built", dest), 100)

    def _after_build(self):
        path = self.built_path
        if path:
            if messagebox.askyesno(t("dlg_done_t"), t("dlg_done", path)):
                self.install()
            else:
                self._open_folder(path)

    def install(self):
        path = self.built_path
        if not path or not os.path.isdir(path):
            messagebox.showinfo(t("dlg_nobuild_t"), t("dlg_nobuild"))
            return
        target = self.target_dir.get().strip()
        if not target or not os.path.isdir(target):
            self._pick_target()
            target = self.target_dir.get().strip()
        if not target or not os.path.isdir(target):
            messagebox.showerror(t("dlg_notgt_t"), t("dlg_notgt"))
            return
        try:
            dest = pc.copy_pack(path, target)
        except Exception as ex:
            messagebox.showerror(t("dlg_copyfail"), str(ex))
            return
        self._save_cfg()
        self._log(t("log_copied", dest))
        if messagebox.askyesno(t("dlg_copied_t"), t("dlg_copied", dest)):
            self._open_folder(dest)

    # -------------------------------------------------------------- Schluss
    def _save_cfg(self):
        self.cfg.update({
            "lang": LANG,
            "asr_language": self.asr_language.get().strip().lower(),
            "asr_model": self.asr_model.get(),
            "asr_device": self.asr_device.get(),
            "src_mode": self.src_mode.get(),
            "last_url": self.url_var.get(),
            "t_start": self.t_start.get(),
            "t_end": self.t_end.get(),
            "separate": self.sep_var.get(),
            "sens": float(self.sens.get()),
            "maxlen": float(self.maxlen.get()),
            "pack_name": self.pack_name.get(),
            "is_dub": self.is_dub.get(),
            "vheight": self.vheight.get(),
            "target_dir": self.target_dir.get(),
            "fmt": self.fmt.get(),
            "pack_title": self.pack_title.get(),
            "pack_authors": self.pack_authors.get(),
            "pack_readme": self.pack_readme.get(),
        })
        save_cfg(self.cfg)

    def _on_close(self):
        # Aufraeumen darf das Beenden nicht verhindern: beim Update wartet
        # ein Skript darauf, dass dieser Prozess wirklich verschwindet.
        for step in (self._save_cfg, self._stop_play,
                     lambda: shutil.rmtree(self.work, ignore_errors=True)):
            try:
                step()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    appwin.set_app_id("DubForge")
    App().mainloop()
