# -*- coding: utf-8 -*-
"""
DubForge - Dub-Packs aus Videos bauen.
DubForge - build dub packs from video.

Ablauf / flow:
  Quelle -> Analysieren -> Clips auf Spuren verteilen -> Pack bauen.
  Source -> Analyse -> Arrange clips on tracks -> Build pack.

Spuren / tracks:
  Jede Spur ist ein Sprecher. Der Spurname landet im Dateinamen des Clips
  (03_Snake_5-460.wav) - genau daraus liest DisDubs die Rollen, DubStage
  liest ihn als Beschriftung. Das Pack-Format bleibt unveraendert.
  Each track is a speaker. The track name goes into the clip file name
  (03_Snake_5-460.wav) - which is exactly what DisDubs casts parts from,
  and what DubStage shows as the label. The pack format is unchanged.
"""

import os
import sys
import json
import time
import queue
import shutil
import threading
import traceback
import tempfile
import subprocess

import atexit
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dubforge_core as pc
import updater as upd

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(APP_DIR, "packs")
CFG_PATH = os.path.join(APP_DIR, "dubforge_settings.json")
LOG_PATH = os.path.join(APP_DIR, "dubforge.log")     # letzte Sitzung / last session
HELP_URL = "https://github.com/Tann2019/dubstage-DisDubs#readme"

# ---- Farben / colours ------------------------------------------------------
BG = "#1e1f26"        # Fenster / window
BG2 = "#272935"       # Felder, Karten / fields, cards
BG3 = "#15161c"       # Zeitleiste, Log / timeline, log
FG = "#e7e7ef"
DIM = "#9aa0b5"
LINE = "#3a3d4d"
ACC = "#7c5cff"       # Markenfarbe / brand
ACC2 = "#43d69a"      # "los" / go
WARN = "#ffb454"
WAVE = "#6f7ba8"
SEL_ROW = "#363a55"   # Zeilenauswahl in der Liste / list selection
BAN = "#332e5e"       # Update-Banner / update banner
BAN_TXT = "#241f47"

# Spurfarben - jede Spur ist ein Sprecher / track colours - one per speaker
TRACK_COLORS = ["#7c5cff", "#43d69a", "#ff8a5c", "#5cc8ff",
                "#ffd166", "#ff6b9d", "#9be36a", "#c58cff"]
MAX_TRACKS = len(TRACK_COLORS)

# Zeitleisten-Geometrie / timeline geometry (px)
GUTTER = 128          # linke Spalte mit Spurnamen / left column with track names
RULER_H = 20
WAVE_H = 64
LANE_H = 34
ADD_H = 24
EDGE_PX = 6           # Griffbreite an Cliprändern / edge grab width
PLAY_FPS = 10         # Bildrate der bewegten Vorschau / preview frame rate

FONT = "Segoe UI"
MONO = "Consolas"


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
    "title":        ("DubForge  -  Dub-Packs aus Videos bauen",
                     "DubForge  -  build dub packs from video"),
    "tagline":      ("Packs fuer DubStage und DisDubs",
                     "packs for DubStage and DisDubs"),
    "lang_label":   ("Sprache:", "Language:"),

    # --- Schritt 1
    "s1":           (" 1. Quelle ", " 1. Source "),
    "src_url":      ("YouTube-Link", "YouTube link"),
    "src_file":     ("Datei auf der Platte", "File on disk"),
    "pick_file":    ("Datei waehlen ...", "Choose file ..."),
    "open_pack":    ("Pack weiterbearbeiten ...", "Reopen a pack ..."),
    "from":         ("Von:", "From:"),
    "to":           ("Bis:", "To:"),
    "time_hint":    ("(z.B. 1:30  oder  0:02:15.5  -  leer = alles)",
                     "(e.g. 1:30  or  0:02:15.5  -  empty = everything)"),
    "sep_voc":      ("Stimmen von Musik trennen (Demucs)",
                     "Separate vocals from music (Demucs)"),
    "analyze":      ("Laden und analysieren", "Load and analyse"),
    "upd_ytdlp":    ("yt-dlp aktualisieren", "Update yt-dlp"),
    "ytdlp_ver":    ("yt-dlp %s (%d Tage alt)", "yt-dlp %s (%d days old)"),
    "ytdlp_old":    ("yt-dlp ist %d Tage alt. YouTube aendert staendig etwas - "
                     "bei Download-Problemen zuerst aktualisieren.",
                     "yt-dlp is %d days old. YouTube keeps changing things - "
                     "update it first if downloads fail."),
    "st_upd":       ("Aktualisiere yt-dlp ...", "Updating yt-dlp ..."),
    "upd_done":     ("Jetzt: yt-dlp %s", "Now: yt-dlp %s"),
    "upd_fail":     ("Aktualisierung hat nichts geaendert. Im Terminal:\n"
                     "py -m pip install --upgrade yt-dlp",
                     "The update changed nothing. In a terminal:\n"
                     "py -m pip install --upgrade yt-dlp"),
    "upd_same":     ("Die Version ist unveraendert: %s\n\n"
                     "Meist liegt eine aeltere yt-dlp.exe im PATH und hat "
                     "Vorrang vor der Installation, die pip erneuert hat. "
                     "Welche Datei benutzt wird, steht im Protokoll - diese "
                     "Datei entfernen oder direkt erneuern.",
                     "The version has not changed: %s\n\n"
                     "Usually an older yt-dlp.exe sits in PATH and takes "
                     "precedence over the installation pip just updated. "
                     "The log shows which file is in use - remove or update "
                     "that file."),
    "dl_hint":      ("Der Download ist fehlgeschlagen. yt-dlp ist %d Tage alt - "
                     "das koennte die Ursache sein, wenn oben ein Fehler beim "
                     "Auslesen der Seite steht.",
                     "The download failed. yt-dlp is %d days old - that may be "
                     "the cause if the log shows an error while reading the "
                     "page."),
    "demucs_hint":  ("Erster Lauf mit Demucs dauert laenger (Modell wird geladen).",
                     "The first Demucs run takes longer (the model is downloaded)."),

    # --- Schritt 2
    "s2":           (" 2. Clips und Spuren ", " 2. Clips and tracks "),
    "canvas_empty": ("Noch nichts geladen  -  oben eine Quelle waehlen und "
                     "'Laden und analysieren' klicken, oder einen Pack "
                     "weiterbearbeiten.",
                     "Nothing loaded yet  -  choose a source above and click "
                     "'Load and analyse', or reopen a pack."),
    "zoom_in":      ("Zoom +", "Zoom +"),
    "zoom_out":     ("Zoom -", "Zoom -"),
    "zoom_all":     ("Alles zeigen", "Fit all"),
    "zoom_sel":     ("Auf Clip zoomen", "Zoom to clip"),
    "mouse_hint":   ("Ziehen in einer Spur = neuer Clip   |   Clip ziehen = "
                     "verschieben (auch in andere Spur)   |   Rand = trimmen   |   "
                     "Strg+Rad = Zoom",
                     "Drag in a track = new clip   |   drag a clip = move (also "
                     "across tracks)   |   edge = trim   |   Ctrl+wheel = zoom"),
    "add_track":    ("+ Spur", "+ Track"),
    "add_track_row": ("+  Spur hinzufuegen  -  eine je Sprecher",
                      "+  Add a track  -  one per speaker"),
    "track_default": ("Stimme", "Voice"),
    "track_new":    ("Sprecher %d", "Speaker %d"),
    "tracks_hint":  ("Spuren nach dem Sprecher benennen - DisDubs verteilt "
                     "danach die Rollen (hoechstens halb so viele Sprecher wie "
                     "Clips).",
                     "Name tracks after who speaks - DisDubs casts parts from "
                     "them (at most half as many speakers as clips)."),
    "col_nr":       ("#", "#"),
    "col_track":    ("Sprecher", "Speaker"),
    "col_start":    ("Start", "Start"),
    "col_end":      ("Ende", "End"),
    "col_len":      ("Laenge", "Length"),
    "col_caption":  ("Untertitel", "Subtitle"),
    "insp_title":   ("Clip %d von %d", "Clip %d of %d"),
    "insp_none":    ("Kein Clip gewaehlt", "No clip selected"),
    "insp_track":   ("Sprecher / Spur:", "Speaker / track:"),
    "insp_start":   ("Start:", "Start:"),
    "insp_end":     ("Ende:", "End:"),
    "caption":      ("Untertitel:", "Subtitle:"),
    "caption_hint": ("Enter = speichern und zum naechsten Clip   ·   "
                     "Esc = zurueck zur Zeitleiste   ·   Strg+Leertaste = anhoeren",
                     "Enter = save and go to the next clip   ·   "
                     "Esc = back to the timeline   ·   Ctrl+Space = play"),
    "keys_hint":    ("Leertaste = anhoeren  ·  S = teilen  ·  Strg+D = duplizieren  ·  "
                     "Entf = loeschen  ·  Pfeile = schieben / Spur wechseln  ·  "
                     "Strg+Z/Y = rueckgaengig/wiederholen",
                     "Space = play  ·  S = split  ·  Ctrl+D = duplicate  ·  "
                     "Del = delete  ·  arrows = nudge / change track  ·  "
                     "Ctrl+Z/Y = undo/redo"),
    "help":         ("Hilfe", "Help"),
    "cancel":       ("Abbrechen", "Cancel"),
    "st_cancelled": ("Abgebrochen.", "Cancelled."),
    "dlg_abort_t":  ("Es laeuft noch etwas", "Something is still running"),
    "dlg_abort":    ("Ein Vorgang laeuft noch (%s).\n\nAbbrechen und schliessen?",
                     "A job is still running (%s).\n\nAbort it and close?"),
    "warn_tools":   ("Fehlt: %s  -  bitte Setup.bat ausfuehren.",
                     "Missing: %s  -  please run Setup.bat."),
    "warn_demucs":  ("(nicht installiert - Setup.bat)", "(not installed - Setup.bat)"),
    "ff_ready":     ("ffmpeg bereit (H.264: %s, AAC: %s)",
                     "ffmpeg ready (H.264: %s, AAC: %s)"),
    "dlg_exists_t": ("Pack existiert", "Pack exists"),
    "dlg_exists":   ("Es gibt schon einen Pack '%s'.\n\n"
                     "Ja = ueberschreiben\nNein = als '%s' speichern",
                     "There is already a pack '%s'.\n\n"
                     "Yes = overwrite\nNo = save as '%s'"),
    "dlg_check_t":  ("Vor dem Bauen", "Before building"),
    "dlg_check":    ("Das faellt an dem Pack auf:\n\n%s\n\nTrotzdem bauen?",
                     "Things worth knowing about this pack:\n\n%s\n\nBuild anyway?"),
    "dlg_built_t":  ("Pack gebaut", "Pack built"),
    "dlg_built":    ("%s\n\n%d Clips, %d Sprecher%s",
                     "%s\n\n%d clips, %d speakers%s"),
    "dlg_built_parts": ("  ·  DisDubs: %d Rolle(n)", "  ·  DisDubs: %d part(s)"),
    "btn_zip_now":  ("Als ZIP fuer DisDubs", "Zip for DisDubs"),
    "btn_open_folder": ("Ordner oeffnen", "Open folder"),
    "btn_close":    ("Schliessen", "Close"),
    "dlg_rebuild_t": ("Clips geaendert", "Clips changed"),
    "dlg_rebuild":  ("Die Clips wurden seit dem letzten Bauen geaendert.\n\n"
                     "Erst neu bauen?",
                     "The clips changed since the last build.\n\nRebuild first?"),
    "dlg_voice_zip": ("Das ist ein Clip-Pack ohne Video - DisDubs nimmt nur "
                      "Packs mit Video an.\n'Mit Video' anhaken und neu bauen.",
                      "This is a clip pack without video - DisDubs only accepts "
                      "packs with video.\nTick 'With video' and rebuild."),
    "dlg_long_t":   ("Lange Zeitspanne", "Long time span"),
    "dlg_long":     ("Der Ausschnitt ist %s lang und die Stimmen-Trennung ist an. "
                     "Demucs braucht dafuer auf der CPU leicht 10-20 Minuten.\n\n"
                     "Trotzdem starten?",
                     "The span is %s long and vocal separation is on. On the CPU "
                     "Demucs can easily take 10-20 minutes for that.\n\n"
                     "Start anyway?"),
    "dlg_yt_t":     ("Download fehlgeschlagen", "Download failed"),
    "dlg_yt_upd":   ("\n\nJetzt yt-dlp aktualisieren?", "\n\nUpdate yt-dlp now?"),
    "built_at":     ("gebaut %s  ·  %d Clips", "built %s  ·  %d clips"),
    "stats_parts":  ("DisDubs: %d Rolle(n)", "DisDubs: %d part(s)"),
    "preview_none": ("kein Videobild", "no video frame"),
    "preview_pick": ("Clip waehlen", "select a clip"),
    "st_voc_fail":  ("Stimmen-Trennung fehlgeschlagen - Originalton wird benutzt.",
                     "Vocal separation failed - using the original audio."),
    "st_novideo":   ("Quelle ohne Bild - es wird ein Standbild-Video gebaut.",
                     "Source has no picture - building a still-image video."),
    "st_still":     ("Baue Standbild-Video (Cover oder Karte) ...",
                     "Building still-image video (cover art or card) ..."),
    "dlg_src_t":    ("Quelle waehlen", "Choose the source"),
    "dlg_src_for":  ("Dieser Pack hat kein Video. Bitte die urspruengliche "
                     "Quelle (Video oder Audio) waehlen, aus der er gebaut wurde.",
                     "This pack has no video. Please choose the original source "
                     "(video or audio) it was built from."),
    "st_check":     ("Pruefe Werkzeuge ...", "Checking tools ..."),
    "crash_t":      ("DubForge ist auf einen Fehler gestossen",
                     "DubForge ran into an error"),
    "crash":        ("%s\n\nDetails stehen in dubforge.log neben dem Programm.",
                     "%s\n\nDetails are in dubforge.log next to the program."),
    "btn_play":     ("Anhoeren", "Play"),
    "btn_stop":     ("Stopp", "Stop"),
    "btn_split":    ("Teilen", "Split"),
    "btn_dup":      ("Duplizieren", "Duplicate"),
    "btn_delete":   ("Loeschen", "Delete"),
    "btn_undo":     ("Rueckgaengig", "Undo"),
    "btn_redo":     ("Wiederholen", "Redo"),
    "detect_menu":  ("Erkennung ▾", "Detect ▾"),
    "sep_now":      ("Stimmen jetzt von Musik trennen (Demucs)",
                     "Separate vocals from music now (Demucs)"),
    "dlg_sep_t":    ("Kein Backing-Track", "No backing track"),
    "dlg_sep_ask":  ("Dieser Pack hat keinen _backing_track (Musik ohne Stimmen). "
                     "Ohne ihn laeuft in DubStage und DisDubs kein Ton unter der "
                     "Aufnahme.\n\nJetzt die Stimmen mit Demucs trennen? "
                     "(dauert je nach Laenge einige Minuten)",
                     "This pack has no _backing_track (music without vocals). "
                     "Without it DubStage and DisDubs play no sound under the "
                     "recording.\n\nSeparate the vocals with Demucs now? "
                     "(takes a few minutes depending on length)"),
    "dlg_sep_missing": ("Demucs ist nicht installiert - Setup.bat ausfuehren und "
                        "die Stimmen-Trennung mit installieren.",
                        "Demucs is not installed - run Setup.bat and install "
                        "vocal separation."),
    "st_sep_done":  ("Stimmen getrennt - Backing-Track vorhanden.",
                     "Vocals separated - backing track ready."),
    "sensitivity":  ("Empfindlichkeit", "Sensitivity"),
    "sens_low":     ("niedrig (weniger Clips)", "low (fewer clips)"),
    "sens_norm":    ("normal", "normal"),
    "sens_high":    ("hoch", "high"),
    "sens_vhigh":   ("sehr hoch (mehr Clips)", "very high (more clips)"),
    "maxlen":       ("Max. Cliplaenge", "Max. clip length"),
    "redetect":     ("Jetzt neu erkennen", "Detect again now"),
    "dlg_redetect": ("Neu erkennen ersetzt alle Clips (Untertitel und "
                     "Spurzuordnung gehen verloren - Rueckgaengig geht).\n\n"
                     "Fortfahren?",
                     "Detecting again replaces all clips (subtitles and track "
                     "assignment are lost - Undo works).\n\nContinue?"),
    "subs_menu":    ("Untertitel ▾", "Subtitles ▾"),
    "subs_file":    ("Aus SRT/VTT-Datei uebernehmen ...",
                     "Import from SRT/VTT file ..."),
    "subs_yt":      ("Von YouTube holen (%s)", "Fetch from YouTube (%s)"),
    "subs_clear":   ("Alle Untertitel loeschen", "Clear all subtitles"),
    "subs_over_t":  ("Untertitel", "Subtitles"),
    "subs_over":    ("%d Cues gefunden.\n\nAuch Clips ueberschreiben, die "
                     "schon einen Untertitel haben?\n(Nein = nur leere fuellen)",
                     "Found %d cues.\n\nAlso overwrite clips that already have "
                     "a subtitle?\n(No = fill empty ones only)"),
    "subs_done":    ("Untertitel: %d Clips befuellt.", "Subtitles: %d clips filled."),
    "subs_none":    ("Keine Untertitel gefunden.", "No subtitles found."),
    "subs_notyt":   ("Dafuer muss die Quelle ein YouTube-Link sein.",
                     "The source has to be a YouTube link for that."),
    "st_subs":      ("Hole Untertitel ...", "Fetching subtitles ..."),
    "dlg_sub_t":    ("Untertitel-Datei waehlen", "Choose a subtitle file"),
    "dlg_sub_filter": ("Untertitel", "Subtitles"),
    "menu_rename":  ("Spur umbenennen ...", "Rename track ..."),
    "menu_color":   ("Farbe wechseln", "Change colour"),
    "menu_up":      ("Nach oben", "Move up"),
    "menu_down":    ("Nach unten", "Move down"),
    "menu_del":     ("Spur loeschen", "Delete track"),
    "menu_sel_all": ("Alle Clips dieser Spur anhoeren", "Play this track"),
    "dlg_track_t":  ("Spur", "Track"),
    "dlg_track_name": ("Name des Sprechers:", "Speaker name:"),
    "dlg_track_del": ("Spur '%s' mit %d Clips loeschen?",
                      "Delete track '%s' and its %d clips?"),
    "dlg_track_max": ("Mehr als %d Spuren gibt es nicht.",
                      "There is a limit of %d tracks."),
    "stats":        ("%d Clips  ·  %d Spuren  ·  %d ohne Untertitel  ·  %s gesprochen",
                     "%d clips  ·  %d tracks  ·  %d without subtitle  ·  %s spoken"),
    "overlap_note": ("%d Ueberschneidungen in derselben Spur",
                     "%d overlaps within the same track"),

    # --- Schritt 3
    "s3":           (" 3. Pack bauen ", " 3. Build the pack "),
    "pack_name":    ("Pack-Name:", "Pack name:"),
    "author":       ("Autor:", "Author:"),
    "is_dub":       ("Mit Video (fuer DubStage / DisDubs)",
                     "With video (for DubStage / DisDubs)"),
    "vheight":      ("Video-Hoehe:", "Video height:"),
    "target_dir":   ("Zielordner:", "Target folder:"),
    "browse":       ("Waehlen", "Browse"),
    "build":        ("Pack bauen", "Build pack"),
    "zip":          ("Als ZIP fuer DisDubs", "Zip for DisDubs"),
    "install":      ("In Zielordner kopieren", "Copy to target folder"),
    "open_out":     ("Pack-Ordner oeffnen", "Open pack folder"),
    "log_show":     ("Protokoll ▸", "Log ▸"),
    "log_hide":     ("Protokoll ▾", "Log ▾"),

    # --- Status / Log
    "ready":        ("Bereit.", "Ready."),
    "missing":      ("FEHLT: %s  ->  bitte Setup.bat ausfuehren.",
                     "MISSING: %s  ->  please run Setup.bat."),
    "yes":          ("ja", "yes"),
    "no_caps":      ("NEIN", "NO"),

    "st_download":  ("Lade Video ...", "Downloading video ..."),
    "st_trim":      ("Schneide Zeitspanne ...", "Cutting the time span ..."),
    "st_open":      ("Oeffne Pack ...", "Opening pack ..."),
    "st_audio":     ("Ton extrahieren ...", "Extracting audio ..."),
    "st_demucs":    ("Trenne Stimmen von Musik (Demucs, dauert) ...",
                     "Separating vocals from music (Demucs, takes a while) ..."),
    "st_wave":      ("Analysiere Wellenform ...", "Analysing waveform ..."),
    "st_detect":    ("Suche Clips ...", "Looking for clips ..."),
    "st_done_an":   ("Fertig analysiert.", "Analysis finished."),
    "st_opened":    ("Pack geoeffnet: %d Clips auf %d Spuren.",
                     "Pack opened: %d clips on %d tracks."),
    "st_clip":      ("Exportiere Clip %d/%d ...", "Exporting clip %d/%d ..."),
    "st_backing":   ("Schreibe _backing_track ...", "Writing _backing_track ..."),
    "st_video":     ("Konvertiere Video (dauert am laengsten) ...",
                     "Converting the video (this takes the longest) ..."),
    "st_video_copy": ("Uebernehme Video aus dem Pack ...",
                      "Reusing the video from the pack ..."),
    "st_zip":       ("Packe ZIP ...", "Zipping ..."),
    "st_built":     ("Pack gebaut: %s", "Pack built: %s"),
    "st_zipped":    ("ZIP geschrieben: %s", "ZIP written: %s"),
    "log_len":      ("Laenge: %.2f s", "Length: %.2f s"),
    "log_voc_ok":   ("Vocals getrennt.", "Vocals separated."),
    "log_voc_fail": ("Demucs fehlgeschlagen (%s) - nutze den Originalton.",
                     "Demucs failed (%s) - falling back to the original audio."),
    "log_found":    ("%d Clips gefunden.", "Found %d clips."),
    "log_redet":    ("Neu erkannt: %d Clips.", "Detected again: %d clips."),
    "log_copied":   ("Kopiert nach: %s", "Copied to: %s"),
    "log_noplay":   ("Wiedergabe nicht moeglich: %s", "Playback not possible: %s"),
    "log_backend":  ("Wiedergabe ueber %s.", "Playback via %s."),
    "st_playing":   ("Spiele %.1f s ...", "Playing %.1f s ..."),
    "log_novoc":    ("Hinweis: der wieder geoeffnete Pack enthaelt keine "
                     "getrennten Vocals - Vorschau und Erkennung nutzen den "
                     "Originalton.",
                     "Note: a reopened pack carries no separated vocals - "
                     "preview and detection use the original audio."),
    "log_nobacking": ("Kein _backing_track im Pack.", "No _backing_track in the pack."),

    # --- Dialoge
    "dlg_busy_t":   ("Moment", "One moment"),
    "dlg_busy":     ("Es laeuft gerade schon etwas.",
                     "Something is already running."),
    "dlg_err":      ("Fehler", "Error"),
    "dlg_missing_t": ("Fehlt", "Missing"),
    "dlg_no_src":   ("Bitte einen Link oder eine Datei angeben.",
                     "Please provide a link or a file."),
    "dlg_time_t":   ("Zeitangabe", "Time value"),
    "dlg_time_order": ("'Bis' muss groesser als 'Von' sein.",
                       "'To' must be greater than 'From'."),
    "dlg_first_t":  ("Erst analysieren", "Analyse first"),
    "dlg_first":    ("Bitte zuerst eine Quelle laden und analysieren.",
                     "Please load and analyse a source first."),
    "dlg_noclips_t": ("Keine Clips", "No clips"),
    "dlg_noclips":  ("Es gibt noch keine Clips.", "There are no clips yet."),
    "dlg_done_t":   ("Fertig", "Finished"),
    "dlg_done":     ("Pack liegt in:\n%s\n\nJetzt in den Zielordner kopieren?",
                     "Pack is located at:\n%s\n\nCopy it to the target folder now?"),
    "dlg_zip_done": ("ZIP fuer DisDubs:\n%s\n\nOrdner oeffnen?",
                     "ZIP for DisDubs:\n%s\n\nOpen the folder?"),
    "dlg_nobuild_t": ("Noch nichts da", "Nothing there yet"),
    "dlg_nobuild":  ("Bitte zuerst 'Pack bauen'.", "Please use 'Build pack' first."),
    "dlg_notgt_t":  ("Zielordner fehlt", "Target folder missing"),
    "dlg_notgt":    ("Es ist kein Zielordner gesetzt.\n\n"
                     "Oben einen Ordner waehlen, in den der fertige Pack "
                     "kopiert werden soll.",
                     "No target folder is set.\n\n"
                     "Choose a folder above to copy the finished pack into."),
    "dlg_copyfail": ("Kopieren fehlgeschlagen", "Copying failed"),
    "dlg_copied_t": ("Kopiert", "Copied"),
    "dlg_copied":   ("Kopiert nach:\n%s\n\nOrdner oeffnen?",
                     "Copied to:\n%s\n\nOpen the folder?"),
    "dlg_video_t":  ("Video oder Audio waehlen", "Choose video or audio"),
    "dlg_filter":   ("Video/Audio", "Video/audio"),
    "dlg_allfiles": ("Alle Dateien", "All files"),
    "dlg_target_t": ("Zielordner waehlen", "Choose the target folder"),
    "dlg_pack_t":   ("Pack-Ordner waehlen", "Choose a pack folder"),
    "dlg_unsaved_t": ("Ungebaute Aenderungen", "Unbuilt changes"),
    "dlg_unsaved":  ("Die Clips wurden seit dem letzten Bauen geaendert.\n"
                     "Trotzdem schliessen?",
                     "The clips changed since the last build.\nClose anyway?"),
    "dlg_replace_t": ("Neu laden", "Load again"),
    "dlg_replace":  ("Es sind schon Clips da. Neu laden ersetzt sie.\n\n"
                     "Fortfahren?",
                     "There are clips already. Loading again replaces them.\n\n"
                     "Continue?"),

    # --- Dateien im Pack
    "ts_head":      ("# %s\n# Uebersicht der Clips\n#\n"
                     "# Datei | Startzeit im Video (Sekunden) | Laenge | "
                     "Sprecher | Untertitel\n",
                     "# %s\n# Overview of the clips\n#\n"
                     "# File | start time in the video (seconds) | length | "
                     "speaker | subtitle\n"),
    "readme":       ("Pack: %s\nTyp: %s\nClips: %d\nSprecher: %s\n\n"
                     "Mit DubStage oeffnen und die Szene selbst einsprechen,\n"
                     "oder als ZIP in DisDubs hochladen.\n",
                     "Pack: %s\nType: %s\nClips: %d\nSpeakers: %s\n\n"
                     "Open it in DubStage and dub the scene yourself,\n"
                     "or upload it to DisDubs as a ZIP.\n"),
    "readme_dub":   ("\nDie Startzeit jedes Clips steht im Dateinamen\n"
                     "(z.B. 07_Snake_44-048 = Sprecher Snake, 44.048 Sekunden)\n"
                     "und in _TIMESTAMPS.txt. Untertitel liegen in _captions.json.\n"
                     "_dubforge.json ist das Projekt - damit laesst sich der Pack\n"
                     "in DubForge weiterbearbeiten.\n",
                     "\nEach clip's start time is in its file name\n"
                     "(e.g. 07_Snake_44-048 = speaker Snake, 44.048 seconds)\n"
                     "and in _TIMESTAMPS.txt. Subtitles live in _captions.json.\n"
                     "_dubforge.json is the project - reopen the pack in\n"
                     "DubForge to keep editing it.\n"),
    "type_dub":     ("Dub-Pack", "Dub pack"),
    "type_voice":   ("Clip-Pack", "Clip pack"),

    # --- Update
    "upd_head":     ("Version %s ist da", "Version %s is out"),
    "upd_sub":      ("Du hast %s", "You have %s"),
    "upd_more":     ("Was ist neu", "What's new"),
    "upd_less":     ("Zuklappen", "Collapse"),
    "upd_now":      ("Jetzt aktualisieren", "Update now"),
    "upd_later":    ("Spaeter", "Later"),
    "upd_page":     ("Auf GitHub", "On GitHub"),
    "upd_nonotes":  ("Zu dieser Version wurde kein Text hinterlegt.",
                     "No description was published for this version."),
    "upd_ask_t":    ("Update einspielen?", "Install update?"),
    "upd_ask":      ("DubForge und DubStage werden auf %s aktualisiert.\n\n"
                     "Die App schliesst sich, die Dateien werden getauscht "
                     "und die App startet neu.\n"
                     "Packs, Aufnahmen und Einstellungen bleiben unberuehrt.\n\n"
                     "Fortfahren?",
                     "DubForge and DubStage will be updated to %s.\n\n"
                     "The app closes, the files are replaced and the app "
                     "starts again.\n"
                     "Packs, recordings and settings are left untouched.\n\n"
                     "Continue?"),
    "upd_dl":       ("Lade %s ... %d%%", "Downloading %s ... %d%%"),
    "upd_check":    ("Pruefe das Archiv ...", "Checking the archive ..."),
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


def _is_text_widget(w):
    return isinstance(w, (tk.Entry, ttk.Entry, tk.Text, ttk.Spinbox,
                          ttk.Combobox, tk.Spinbox))


# ==========================================================================
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.cfg = load_cfg()
        set_lang(self.cfg.get("lang", "de"))

        # Fensterhoehe an den Bildschirm anpassen; darunter scrollt die Seite.
        # Fit the window to the screen; below that the page scrolls.
        sh = self.winfo_screenheight()
        self.geometry(self.cfg.get("geometry",
                                   "1260x%d" % min(920, max(560, sh - 130))))
        self.minsize(1040, 520)
        self.configure(bg=BG)

        self.msgq = queue.Queue()
        self.busy = False
        self.busy_what = ""
        self.player = None
        self._logfile = None
        try:
            self._logfile = open(LOG_PATH, "w", encoding="utf-8")
            self._logfile.write("DubForge %s  -  %s\n" % (upd.VERSION, time.ctime()))
        except Exception:
            self._logfile = None
        self.report_callback_exception = self._tk_exception

        pc.sweep_temp("dubforge_", max_age_h=24)
        self.work = tempfile.mkdtemp(prefix="dubforge_")
        atexit.register(lambda: shutil.rmtree(self.work, ignore_errors=True))
        self.have_ffmpeg = True
        self.have_demucs = True
        self.have_ytdlp = True
        self.built_dub = True
        self.built_info = None       # (time, clips) / letzter Bau
        self._auto_detect_ok = False # Regler duerfen frisch erkennen
        self.video_path = None
        self.video_has_stream = False
        self.video_from_pack = False   # dub_video aus einem Pack: kopieren statt neu kodieren
        self.audio_path = None       # kompletter Ton / full audio
        self.vocals_path = None      # nur Stimmen / vocals only
        self.backing_path = None     # alles ausser Stimmen / everything else
        self.wave_data = []
        self.wave_sr = 8000
        self.duration = 0.0
        self.src_offset = 0.0        # Start des Ausschnitts im Original / offset in the source
        self.source_url = ""

        # Spuren und Clips / tracks and clips
        # track: {'name': str, 'color': str}
        # clip:  {'start': float, 'end': float, 'track': int, 'caption': str}
        self.tracks = []
        self.clips = []
        self.selected = None
        self._caption_for = None
        self._ytdlp_age = None
        self.built_path = None
        self.dirty = False

        self._undo = []
        self._redo = []

        self.upd_info = None        # gefundenes Release / found release
        self.upd_open = False       # Changelog aufgeklappt?
        self.upd_busy = False
        self.upd_dismissed = False

        self.view_a = 0.0
        self.view_b = 1.0
        self._drag = None
        self._peak_cache = (None, None)
        self._syncing = False
        self._play = None            # (wall_t0, start, end)
        self._play_token = 0
        self._pending_play = None
        self._play_frames = None
        self._play_frame_idx = -1
        self.playhead = None
        self._preview_job = None
        self._preview_img = None
        self._preview_key = None
        self._preview_cache = {}

        self._build_style()
        self._init_vars()
        self._build_ui()
        self.title(t("title") + "   ·   v" + upd.VERSION)
        # Mausrad global: die Seite scrollt, ausser ueber Widgets, die
        # selbst scrollen (siehe _wheel). / page scroll, see _wheel
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Button-4>", self._wheel)
        self.bind("<Button-5>", self._wheel)
        self._pump_id = self.after(80, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Key>", self._on_key)
        self.after(50, self._check_tools_async)
        self._upd_id = self.after(1200, self._check_update)

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
        self.author = tk.StringVar(value=c.get("author", ""))
        self.is_dub = tk.BooleanVar(value=c.get("is_dub", True))
        self.vheight = tk.StringVar(value=c.get("vheight", "720"))
        self.target_dir = tk.StringVar(value=c.get("target_dir", ""))
        self.caption_var = tk.StringVar(value="")
        self.track_var = tk.StringVar(value="")
        self.start_var = tk.StringVar(value="")
        self.end_var = tk.StringVar(value="")
        # Auf niedrigen Bildschirmen startet das Protokoll eingeklappt.
        # On short screens the log starts collapsed.
        self.log_open = bool(c.get("log_open", self.winfo_screenheight() >= 900))

    # ------------------------------------------------------------------ UI
    def _build_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(".", background=BG, foreground=FG, fieldbackground=BG2,
                    bordercolor=LINE, lightcolor=BG2, darkcolor=BG2,
                    font=(FONT, 10))
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=BG2)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("Card.TLabel", background=BG2, foreground=FG)
        s.configure("Head.TLabel", background=BG, foreground=ACC2,
                    font=(FONT + " Semibold", 13))
        s.configure("Tag.TLabel", background=BG, foreground=DIM,
                    font=(FONT, 10))
        s.configure("Dim.TLabel", background=BG, foreground=DIM)
        s.configure("Insp.TLabel", background=BG, foreground=FG,
                    font=(FONT + " Semibold", 10))
        s.configure("Warn.TLabel", background="#3a2f1e", foreground=WARN,
                    padding=(10, 5), font=(FONT + " Semibold", 10))
        s.configure("TButton", background="#3a3d4d", foreground=FG, padding=6,
                    borderwidth=0, focuscolor=BG)
        s.map("TButton", background=[("active", "#4a4e63"),
                                     ("disabled", "#2c2e3a")],
              foreground=[("disabled", "#6c718a")])
        s.configure("Small.TButton", padding=(6, 3))
        s.configure("Accent.TButton", background=ACC, foreground="#ffffff",
                    padding=8, font=(FONT + " Semibold", 10))
        s.map("Accent.TButton", background=[("active", "#9078ff"),
                                            ("disabled", "#463a7a")])
        s.configure("Go.TButton", background=ACC2, foreground="#0d2b20",
                    padding=8, font=(FONT + " Semibold", 10))
        s.map("Go.TButton", background=[("active", "#5ee7ae"),
                                        ("disabled", "#2b5c48")])
        s.configure("TMenubutton", background="#3a3d4d", foreground=FG,
                    padding=6, borderwidth=0, arrowcolor=FG)
        s.map("TMenubutton", background=[("active", "#4a4e63")])
        s.configure("TEntry", fieldbackground=BG2, foreground=FG,
                    insertcolor=FG, padding=4)
        s.configure("TSpinbox", fieldbackground=BG2, foreground=FG,
                    insertcolor=FG, arrowcolor=FG, padding=3)
        s.map("TSpinbox", fieldbackground=[("readonly", BG2)])
        s.configure("TCombobox", fieldbackground=BG2, background=BG2,
                    foreground=FG, arrowcolor=FG, bordercolor=LINE,
                    lightcolor=BG2, darkcolor=BG2, padding=4,
                    selectbackground=BG2, selectforeground=FG)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG2), ("disabled", BG)],
              background=[("readonly", BG2), ("active", BG2)],
              foreground=[("readonly", FG), ("disabled", "#7a7f96")],
              selectbackground=[("readonly", BG2), ("focus", BG2)],
              selectforeground=[("readonly", FG), ("focus", FG)],
              arrowcolor=[("readonly", FG), ("disabled", "#7a7f96")])
        self.option_add("*TCombobox*Listbox.background", BG2)
        self.option_add("*TCombobox*Listbox.foreground", FG)
        self.option_add("*TCombobox*Listbox.selectBackground", ACC)
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.option_add("*TCombobox*Listbox.borderWidth", 0)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TRadiobutton", background=BG, foreground=FG)
        s.configure("Treeview", background=BG2, fieldbackground=BG2,
                    foreground=FG, rowheight=24, borderwidth=0)
        s.configure("Treeview.Heading", background="#343747", foreground=FG,
                    font=(FONT + " Semibold", 9))
        # Neutrale Auswahlfarbe, damit die Sprecherfarben lesbar bleiben.
        # Neutral selection so the per-speaker text colours stay readable.
        s.map("Treeview", background=[("selected", SEL_ROW)],
              foreground=[("selected", FG)])
        s.configure("TProgressbar", background=ACC2, troughcolor=BG2,
                    borderwidth=0)
        s.configure("Ban.TFrame", background=BAN)
        s.configure("Ban.TLabel", background=BAN, foreground=FG)
        s.configure("BanHead.TLabel", background=BAN, foreground="#ffffff",
                    font=(FONT + " Semibold", 11))
        s.configure("BanDim.TLabel", background=BAN, foreground="#b6b1dc")
        s.configure("Ban.TButton", background="#4b4590", foreground=FG,
                    padding=6, borderwidth=0)
        s.map("Ban.TButton", background=[("active", "#5d56ad")])
        s.configure("Vertical.TScrollbar", background="#3a3d4d",
                    troughcolor=BG2, bordercolor=BG2, arrowcolor=FG,
                    darkcolor=BG2, lightcolor=BG2, borderwidth=0)
        s.map("Vertical.TScrollbar", background=[("active", "#4a4e63")])
        s.configure("Horizontal.TScrollbar", background="#3a3d4d",
                    troughcolor=BG2, bordercolor=BG2, arrowcolor=FG,
                    darkcolor=BG2, lightcolor=BG2, borderwidth=0)
        s.map("Horizontal.TScrollbar", background=[("active", "#4a4e63")])
        s.configure("TLabelframe", background=BG, foreground=ACC2)
        s.configure("TLabelframe.Label", background=BG, foreground=ACC2,
                    font=(FONT + " Semibold", 10))
        s.configure("TScale", background=BG, troughcolor=BG2)
        s.configure("TSeparator", background=LINE)
        s.configure("TPanedwindow", background=BG)

    def _menu(self, parent):
        return tk.Menu(parent, tearoff=0, bg=BG2, fg=FG, activebackground=ACC,
                       activeforeground="#ffffff", relief="flat", bd=0)

    def _build_ui(self):
        self.title(t("title"))

        # Der Inhalt liegt in einem Canvas mit Scrollbalken: passt er nicht
        # ins Fenster, scrollt die Seite statt unten abgeschnitten zu werden.
        # The content sits in a scrolling canvas: too small a window scrolls
        # instead of cutting off the bottom.
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)
        self.ui_root = outer

        # Update-Banner ausserhalb des Scrollbereichs / banner outside scroll
        self.banner = ttk.Frame(outer, style="Ban.TFrame")
        self.upd_text = None
        self.upd_status = None

        host = ttk.Frame(outer)
        host.pack(fill="both", expand=True)
        self.scroll_host = host
        self.vcanvas = tk.Canvas(host, bg=BG, highlightthickness=0, takefocus=0,
                                 yscrollincrement=20)
        self.vcanvas.pack(side="left", fill="both", expand=True)
        vbar = ttk.Scrollbar(host, orient="vertical", command=self.vcanvas.yview)
        vbar.pack(side="right", fill="y")
        self.vcanvas.configure(yscrollcommand=vbar.set)

        root = ttk.Frame(self.vcanvas, padding=(10, 8, 10, 8))
        self._root_win = self.vcanvas.create_window((0, 0), window=root,
                                                    anchor="nw")
        self.root_frame = root
        root.bind("<Configure>", self._scroll_geom)
        self.vcanvas.bind("<Configure>", self._scroll_geom)

        # ---------------- Kopfzeile / header
        top = ttk.Frame(root)
        top.pack(fill="x")
        ttk.Label(top, text="DubForge", style="Head.TLabel").pack(side="left")
        ttk.Label(top, text="   " + t("tagline"),
                  style="Tag.TLabel").pack(side="left", pady=(3, 0))
        self.lang_box = ttk.Combobox(top, textvariable=self.lang_var, width=10,
                                     state="readonly",
                                     values=("Deutsch", "English"))
        self.lang_box.pack(side="right")
        self.lang_box.bind("<<ComboboxSelected>>", self._change_lang)
        ttk.Label(top, text=t("lang_label"),
                  style="Dim.TLabel").pack(side="right", padx=(0, 6))
        ttk.Button(top, text=t("help"), style="Small.TButton",
                   command=lambda: webbrowser.open(HELP_URL)).pack(side="right",
                                                                   padx=(0, 12))
        # Warnzeile fuer fehlende Werkzeuge / warning row for missing tools
        self.warn_lbl = ttk.Label(root, text="", style="Warn.TLabel")
        self._apply_tool_state()

        # ---------------- Schritt 1: Quelle / source
        step1 = ttk.LabelFrame(root, text=t("s1"), padding=(10, 6, 10, 8))
        step1.pack(fill="x", pady=(6, 0))

        r1 = ttk.Frame(step1)
        r1.pack(fill="x")
        ttk.Radiobutton(r1, text=t("src_url"), value="url",
                        variable=self.src_mode,
                        command=self._sync_src).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(r1, text=t("src_file"), value="file",
                        variable=self.src_mode,
                        command=self._sync_src).pack(side="left", padx=(0, 12))
        self.url_entry = ttk.Entry(r1, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.file_btn = ttk.Button(r1, text=t("pick_file"), command=self._pick_file)
        self.file_btn.pack(side="left", padx=(8, 0))
        ttk.Button(r1, text=t("open_pack"),
                   command=self.open_pack).pack(side="left", padx=(8, 0))

        r2 = ttk.Frame(step1)
        r2.pack(fill="x", pady=(8, 0))
        ttk.Label(r2, text=t("from")).pack(side="left")
        ttk.Entry(r2, textvariable=self.t_start, width=11).pack(side="left", padx=6)
        ttk.Label(r2, text=t("to")).pack(side="left")
        ttk.Entry(r2, textvariable=self.t_end, width=11).pack(side="left", padx=6)
        ttk.Label(r2, text=t("time_hint"),
                  style="Dim.TLabel").pack(side="left", padx=(4, 16))
        self.sep_chk = ttk.Checkbutton(r2, text=t("sep_voc"),
                                       variable=self.sep_var)
        self.sep_chk.pack(side="left")
        self.upd_btn = ttk.Button(r2, text=t("upd_ytdlp"), style="Small.TButton",
                                  command=self.update_ytdlp)
        self.upd_btn.pack(side="right")
        self.analyze_btn = ttk.Button(r2, text=t("analyze"),
                                      style="Accent.TButton",
                                      command=self.start_analyze)
        self.analyze_btn.pack(side="right", padx=(0, 10))

        # ---------------- Schritt 2: Clips und Spuren / clips and tracks
        step2 = ttk.LabelFrame(root, text=t("s2"), padding=(10, 6, 10, 8))
        step2.pack(fill="both", expand=True, pady=(8, 0))

        bar = ttk.Frame(step2)
        bar.pack(fill="x")
        self.play_btn = ttk.Button(bar, text="▶  " + t("btn_play"), width=12,
                                   command=self._play_selected)
        self.play_btn.pack(side="left")
        ttk.Button(bar, text="■", width=3,
                   command=self._stop_play).pack(side="left", padx=(2, 10))
        ttk.Button(bar, text=t("zoom_in"), width=8, style="Small.TButton",
                   command=lambda: self._zoom(0.6)).pack(side="left")
        ttk.Button(bar, text=t("zoom_out"), width=8, style="Small.TButton",
                   command=lambda: self._zoom(1.7)).pack(side="left", padx=2)
        ttk.Button(bar, text=t("zoom_all"), width=12, style="Small.TButton",
                   command=self._zoom_all).pack(side="left")
        ttk.Button(bar, text=t("zoom_sel"), width=14, style="Small.TButton",
                   command=self._zoom_selected).pack(side="left", padx=2)
        self.hscroll = ttk.Scale(bar, from_=0.0, to=1.0, orient="horizontal",
                                 command=self._scroll_to)
        self.hscroll.pack(side="left", fill="x", expand=True, padx=10)

        self.subs_mb = ttk.Menubutton(bar, text=t("subs_menu"))
        sm = self._menu(self.subs_mb)
        sm.add_command(label=t("subs_file"), command=self.import_subs_file)
        sm.add_command(label=t("subs_yt", self._sub_lang_label()),
                       command=self.fetch_subs_youtube)
        sm.add_separator()
        sm.add_command(label=t("subs_clear"), command=self.clear_captions)
        self.subs_mb.configure(menu=sm)
        self.subs_mb.pack(side="right")

        self.det_mb = ttk.Menubutton(bar, text=t("detect_menu"))
        dm = self._menu(self.det_mb)
        dm.add_command(label=t("redetect"), command=self.redetect)
        dm.add_command(label=t("sep_now"), command=self.separate_now)
        dm.add_separator()
        sub1 = self._menu(dm)
        for key, val in (("sens_low", 0.6), ("sens_norm", 1.0),
                         ("sens_high", 1.5), ("sens_vhigh", 2.2)):
            sub1.add_radiobutton(label=t(key), variable=self.sens, value=val,
                                 command=self._detect_setting_changed)
        dm.add_cascade(label=t("sensitivity"), menu=sub1)
        sub2 = self._menu(dm)
        for val in (3.0, 4.0, 6.0, 8.0, 12.0, 20.0):
            sub2.add_radiobutton(label="%g s" % val, variable=self.maxlen, value=val,
                                 command=self._detect_setting_changed)
        dm.add_cascade(label=t("maxlen"), menu=sub2)
        self.det_mb.configure(menu=dm)
        self.det_mb.pack(side="right", padx=(0, 6))
        ttk.Button(bar, text=t("add_track"), width=9, style="Small.TButton",
                   command=self.add_track).pack(side="right", padx=(0, 6))
        self.redo_btn = ttk.Button(bar, text="↷", width=3, style="Small.TButton",
                                   command=self.redo)
        self.redo_btn.pack(side="right", padx=(0, 10))
        self.undo_btn = ttk.Button(bar, text="↶", width=3, style="Small.TButton",
                                   command=self.undo)
        self.undo_btn.pack(side="right", padx=(0, 2))

        self.canvas = tk.Canvas(step2, height=RULER_H + WAVE_H + LANE_H + ADD_H,
                                bg=BG3, highlightthickness=1,
                                highlightbackground=LINE)
        self.canvas.pack(fill="x", pady=(6, 0))
        self.canvas.bind("<Configure>", lambda e: self.draw_wave())
        self.canvas.bind("<ButtonPress-1>", self._canvas_down)
        self.canvas.bind("<B1-Motion>", self._canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self._canvas_up)
        self.canvas.bind("<Motion>", self._canvas_hover)
        self.canvas.bind("<MouseWheel>", self._canvas_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._canvas_wheel)
        self.canvas.bind("<Control-MouseWheel>", self._canvas_wheel)
        self.canvas.bind("<Double-Button-1>", self._canvas_double)
        self.canvas.bind("<Button-3>", self._canvas_right)

        hint = ttk.Frame(step2)
        hint.pack(fill="x", pady=(3, 0))
        self.stats_lbl = ttk.Label(hint, text="", style="Dim.TLabel")
        self.stats_lbl.pack(side="left")
        ttk.Label(hint, text=t("mouse_hint"), style="Dim.TLabel").pack(side="right")

        # ---- Clip-Streifen: Bild links, Felder rechts / clip strip
        strip = ttk.Frame(step2)
        strip.pack(fill="x", pady=(6, 0))
        self.preview = tk.Canvas(strip, width=224, height=126, bg="#000000",
                                 highlightthickness=1, highlightbackground=LINE)
        self.preview.pack(side="left")
        fields = ttk.Frame(strip, padding=(10, 0, 0, 0))
        fields.pack(side="left", fill="both", expand=True)

        f1 = ttk.Frame(fields)
        f1.pack(fill="x")
        self.insp_title = ttk.Label(f1, text=t("insp_none"), style="Insp.TLabel",
                                    width=16)
        self.insp_title.pack(side="left")
        ttk.Label(f1, text=t("insp_track")).pack(side="left", padx=(8, 4))
        self.track_box = ttk.Combobox(f1, textvariable=self.track_var, width=16,
                                      state="readonly")
        self.track_box.pack(side="left")
        self.track_box.bind("<<ComboboxSelected>>", self._insp_track_changed)
        ttk.Label(f1, text=t("insp_start")).pack(side="left", padx=(14, 4))
        e1 = ttk.Entry(f1, textvariable=self.start_var, width=9, font=(MONO, 10))
        e1.pack(side="left")
        e1.bind("<Return>", lambda e: self._insp_time_apply())
        e1.bind("<FocusOut>", lambda e: self._insp_time_apply())
        ttk.Label(f1, text=t("insp_end")).pack(side="left", padx=(8, 4))
        e2 = ttk.Entry(f1, textvariable=self.end_var, width=9, font=(MONO, 10))
        e2.pack(side="left")
        e2.bind("<Return>", lambda e: self._insp_time_apply())
        e2.bind("<FocusOut>", lambda e: self._insp_time_apply())
        for key, cmd in (("btn_delete", self._delete_selected),
                         ("btn_dup", self._duplicate_selected),
                         ("btn_split", self._split_selected)):
            ttk.Button(f1, text=t(key), style="Small.TButton",
                       command=cmd).pack(side="right", padx=(4, 0))

        f2 = ttk.Frame(fields)
        f2.pack(fill="x", pady=(10, 0))
        ttk.Label(f2, text=t("caption")).pack(side="left")
        self.caption_entry = ttk.Entry(f2, textvariable=self.caption_var,
                                       font=(FONT, 11))
        self.caption_entry.pack(side="left", fill="x", expand=True, padx=(6, 0),
                                ipady=3)
        self.caption_entry.bind("<Return>", self._caption_next)
        self.caption_entry.bind("<FocusOut>", lambda e: self._caption_save())
        self.caption_entry.bind("<Escape>", lambda e: self.canvas.focus_set())
        self.caption_entry.bind("<Control-space>",
                                lambda e: (self._play_selected(), "break")[1])
        f3 = ttk.Frame(fields)
        f3.pack(fill="x", pady=(3, 0))
        ttk.Label(f3, text=t("caption_hint"), style="Dim.TLabel").pack(side="left")
        f4 = ttk.Frame(fields)
        f4.pack(fill="x", pady=(1, 0))
        ttk.Label(f4, text=t("keys_hint"), style="Dim.TLabel").pack(side="left")
        f5 = ttk.Frame(fields)
        f5.pack(fill="x", pady=(1, 0))
        ttk.Label(f5, text=t("tracks_hint"), style="Dim.TLabel").pack(side="left")

        # ---- Liste / list
        mid = ttk.Frame(step2)
        mid.pack(fill="both", expand=True, pady=(8, 0))
        cols = ("nr", "track", "start", "end", "len", "caption")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=3)
        for c, key, w in (("nr", "col_nr", 36), ("track", "col_track", 130),
                          ("start", "col_start", 80), ("end", "col_end", 80),
                          ("len", "col_len", 64), ("caption", "col_caption", 320)):
            self.tree.heading(c, text=t(key))
            self.tree.column(c, width=w, minwidth=w,
                             anchor="w" if c in ("track", "caption") else "center",
                             stretch=(c == "caption"))
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        sb.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._tree_select)
        self.tree.bind("<Double-Button-1>", lambda e: self._focus_caption())
        for i, col in enumerate(TRACK_COLORS):
            self.tree.tag_configure("t%d" % i, foreground=col)

        # ---------------- Schritt 3: Bauen / build
        step3 = ttk.LabelFrame(root, text=t("s3"), padding=(10, 6, 10, 8))
        step3.pack(fill="x", pady=(8, 0))

        g = ttk.Frame(step3)
        g.pack(fill="x")
        ttk.Label(g, text=t("pack_name")).pack(side="left")
        ttk.Entry(g, textvariable=self.pack_name, width=26).pack(side="left", padx=6)
        ttk.Label(g, text=t("author")).pack(side="left", padx=(8, 0))
        ttk.Entry(g, textvariable=self.author, width=22).pack(side="left", padx=6)
        ttk.Checkbutton(g, text=t("is_dub"), variable=self.is_dub).pack(
            side="left", padx=(16, 6))
        ttk.Combobox(g, textvariable=self.vheight, width=7, state="readonly",
                     values=("1080", "720", "540", "480", "360")).pack(side="right")
        ttk.Label(g, text=t("vheight")).pack(side="right", padx=(10, 4))

        act = ttk.Frame(step3)
        act.pack(fill="x", pady=(8, 0))
        self.build_btn = ttk.Button(act, text=t("build"),
                                    style="Accent.TButton", command=self.start_build)
        self.build_btn.pack(side="left")
        self.zip_btn = ttk.Button(act, text=t("zip"), style="Go.TButton",
                                  command=self.zip_pack)
        self.zip_btn.pack(side="left", padx=8)
        ttk.Button(act, text=t("open_out"),
                   command=self._open_out).pack(side="left")
        self.install_btn = ttk.Button(act, text=t("install"), command=self.install)
        self.install_btn.pack(side="left", padx=(16, 0))
        ttk.Button(act, text=t("browse"), width=9,
                   command=self._pick_target).pack(side="left", padx=(6, 0))
        ttk.Entry(act, textvariable=self.target_dir).pack(
            side="left", fill="x", expand=True, padx=(4, 0))
        self.log_btn = ttk.Button(act, text="", style="Small.TButton",
                                  command=self._toggle_log)
        self.log_btn.pack(side="right", padx=(10, 0))

        foot = ttk.Frame(root)
        foot.pack(fill="x", pady=(8, 0))
        self.status = ttk.Label(foot, text=t("ready"), style="Dim.TLabel")
        self.status.pack(side="left", fill="x", expand=True)
        self.cancel_btn = ttk.Button(foot, text=t("cancel"), style="Small.TButton",
                                     command=self.cancel_job, state="disabled")
        self.cancel_btn.pack(side="right", padx=(8, 0))
        self.prog = ttk.Progressbar(foot, mode="determinate", maximum=100,
                                    length=260)
        self.prog.pack(side="right")
        self.built_lbl = ttk.Label(foot, text="", style="Dim.TLabel")
        self.built_lbl.pack(side="right", padx=(0, 14))
        self._url_span_guard()

        self.logf = ttk.Frame(root)
        self.log = tk.Text(self.logf, height=5, bg=BG3, fg="#93a0c0",
                           insertbackground=FG, relief="flat",
                           font=(MONO, 9), wrap="none")
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(self.logf, orient="vertical", command=self.log.yview)
        lsb.pack(side="left", fill="y")
        self.log.configure(yscrollcommand=lsb.set)
        self._apply_log_state()

        self._sync_src()
        self._refresh_track_box()
        self._update_undo_buttons()
        self.after_idle(self._scroll_geom)
        if self.upd_info:
            self._show_banner()

    # ------------------------------------------------------------- Scrollen
    def _scroll_geom(self, _e=None):
        """Inhaltsbreite ans Fenster koppeln, Hoehe mitwachsen lassen."""
        try:
            c, f = self.vcanvas, self.root_frame
            w = max(1, c.winfo_width())
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
        for _ in range(30):
            if w is None or w is self:
                break
            if w is getattr(self, "canvas", None):
                return                           # Zeitleiste scrollt/zoomt selbst
            try:
                if w.winfo_class() in ("TSpinbox", "Spinbox", "TCombobox",
                                       "TScale"):
                    return
            except Exception:
                pass
            if w in (getattr(self, "tree", None), getattr(self, "log", None),
                     getattr(self, "upd_text", None)) and w is not None:
                first, last = w.yview()
                if (step < 0 and first > 0.0) or (step > 0 and last < 1.0):
                    return                       # hat noch Weg / still room
                break
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
        """Beim Start nachsehen, ob es etwas Neues gibt / check on start."""
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
                          highlightthickness=0, font=(FONT, 9))
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
        keep = self.log.get("1.0", "end-1c")
        set_lang(code)
        self.cfg["lang"] = code
        save_cfg(self.cfg)
        self.ui_root.destroy()
        self._build_ui()
        if keep.strip():
            self.log.insert("end", keep + "\n")
            self.log.see("end")
        self.refresh_list()
        self.draw_wave()
        self._set_busy(self.busy)

    def _sub_lang_label(self):
        return "en, de" if LANG == "en" else "de, en"

    def _sub_langs(self):
        return ("en", "de") if LANG == "en" else ("de", "en")

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

    def _toggle_log(self):
        self.log_open = not self.log_open
        self.cfg["log_open"] = self.log_open
        self._apply_log_state()

    def _apply_log_state(self):
        if self.log_open:
            self.logf.pack(fill="both", expand=False, pady=(4, 0))
            self.log_btn.configure(text=t("log_hide"))
        else:
            self.logf.pack_forget()
            self.log_btn.configure(text=t("log_show"))

    def _check_tools_async(self):
        """Werkzeuge im Hintergrund pruefen - der Start soll nicht haengen."""
        self._set_status(t("st_check"))

        def work():
            res = {"ffmpeg": bool(pc.find_tool("ffmpeg") and pc.find_tool("ffprobe")),
                   "ytdlp": bool(pc.ytdlp()),
                   "demucs": pc.has_demucs()}
            enc = None
            if res["ffmpeg"]:
                try:
                    enc = pc.check_encoders()
                except Exception:
                    enc = None
            ver, age = (None, None)
            if res["ytdlp"]:
                try:
                    ver, age = pc.ytdlp_version()
                except Exception:
                    pass
            self.msgq.put(("tools", (res, enc, ver, age)))
        threading.Thread(target=work, daemon=True).start()

    def _on_tools(self, res, enc, ver, age):
        self.have_ffmpeg = res["ffmpeg"]
        self.have_ytdlp = res["ytdlp"]
        self.have_demucs = res["demucs"]
        missing = [n for n, ok in (("ffmpeg", res["ffmpeg"]),
                                   ("yt-dlp", res["ytdlp"])) if not ok]
        if missing:
            self._log(t("missing", ", ".join(missing)))
        elif enc:
            self._log(t("ff_ready", t("yes") if enc[0] else t("no_caps"),
                        t("yes") if enc[1] else t("no_caps")))
        self._ytdlp_age = age
        if ver and age is not None:
            yt = pc.ytdlp() or []
            where = yt[0] if len(yt) == 1 else os.path.dirname(sys.executable)
            self._log(t("ytdlp_ver", ver, age) + "   -   " + str(where))
            if age > 60:
                self._log(t("ytdlp_old", age))
        if not self.busy:
            self.status.configure(text=t("ready"))
        self._apply_tool_state()

    def _apply_tool_state(self):
        """Warnzeile, Knoepfe und Demucs-Haken nach den gefundenen Werkzeugen."""
        missing = []
        if not self.have_ffmpeg:
            missing.append("ffmpeg")
        if not self.have_ytdlp:
            missing.append("yt-dlp")
        try:
            if missing:
                self.warn_lbl.configure(text="⚠  " + t("warn_tools", ", ".join(missing)))
                self.warn_lbl.pack(fill="x", pady=(6, 0), after=self.warn_lbl.master
                                   .winfo_children()[0])
            else:
                self.warn_lbl.pack_forget()
            if not self.busy:
                self.analyze_btn.configure(
                    state="normal" if self.have_ffmpeg else "disabled")
                self.build_btn.configure(
                    state="normal" if self.have_ffmpeg else "disabled")
            if self.have_demucs:
                self.sep_chk.configure(text=t("sep_voc"), state="normal")
            else:
                self.sep_var.set(False)
                self.sep_chk.configure(text=t("sep_voc") + "  " + t("warn_demucs"),
                                       state="disabled")
        except Exception:
            pass

    def update_ytdlp(self):
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
                # Gleiche Version - fast immer eine aeltere Datei im PATH.
                self._log(t("upd_same", ver))
                messagebox.showwarning(t("title"), t("upd_same", ver))
            else:
                messagebox.showwarning(t("title"), t("upd_fail"))
        self._bg(work, on_done=done)

    # -------------------------------------------------- Thread-Kommunikation
    def _log(self, text):
        text = str(text)
        self.msgq.put(("log", text))
        f = self._logfile
        if f:
            try:
                f.write(text + "\n")
                f.flush()
            except Exception:
                pass

    def _set_status(self, text, pct=None):
        self.msgq.put(("status", (text, pct)))

    def _set_progress(self, frac):
        """0..1 aus einem Arbeitsschritt / from a worker step."""
        self.msgq.put(("progress", frac))

    def _tk_exception(self, exc, val, tb):
        """Unerwartete Fehler in Tk-Callbacks: loggen und zeigen statt schlucken."""
        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            self._log(text)
        except Exception:
            pass
        try:
            messagebox.showerror(t("crash_t"), t("crash", str(val)[:300]))
        except Exception:
            pass

    def _pump(self):
        try:
            while True:
                kind, payload = self.msgq.get_nowait()
                try:
                    self._dispatch(kind, payload)
                except Exception:
                    # Ein kaputter Callback darf die Pumpe nicht toeten.
                    # A broken callback must not kill the pump.
                    self._log(traceback.format_exc())
        except queue.Empty:
            pass
        finally:
            self._pump_id = self.after(80, self._pump)

    def _dispatch(self, kind, payload):
        if kind == "log":
            self.log.insert("end", payload + "\n")
            self.log.see("end")
            if int(self.log.index("end-1c").split(".")[0]) > 600:
                self.log.delete("1.0", "200.0")
        elif kind == "status":
            text, pct = payload
            self.status.configure(text=text)
            self._bar(pct)
        elif kind == "progress":
            self._bar_frac(payload)
        elif kind == "done":
            self._set_busy(False)
            payload()
        elif kind == "cancelled":
            pc.reset_cancel()
            self._set_busy(False)
            self.status.configure(text=t("st_cancelled"))
            self._log(t("st_cancelled"))
            if payload:
                payload()
        elif kind == "error":
            self._set_busy(False)
            self.status.configure(text=t("dlg_err"))
            self._show_error(payload)
        elif kind == "tools":
            self._on_tools(*payload)
        elif kind == "preview":
            self._show_preview(*payload)
        elif kind == "play_start":
            self._on_play_start(*payload)
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
            self.dirty = False
            self.after(700, self._on_close)
        elif kind == "upd_error":
            self.upd_busy = False
            try:
                self.upd_go.configure(state="normal")
            except Exception:
                pass
            self._upd_say("")
            messagebox.showerror(t("upd_fail_t"), t("upd_fail", payload))

    def _show_error(self, payload):
        """payload: str oder (text, 'ytdlp') fuer den Update-Vorschlag."""
        if isinstance(payload, tuple):
            text, kind = payload
            if kind == "ytdlp":
                if messagebox.askyesno(t("dlg_yt_t"), text + t("dlg_yt_upd")):
                    self.update_ytdlp()
                return
            payload = text
        messagebox.showerror(t("dlg_err"), payload)

    # ---- Fortschrittsbalken / progress bar
    def _bar(self, pct):
        """Prozent bekannt -> bestimmt; None -> unbestimmt (laeuft)."""
        try:
            if pct is None:
                if self.busy and str(self.prog.cget("mode")) != "indeterminate":
                    self.prog.configure(mode="indeterminate")
                    self.prog.start(12)
                return
            if str(self.prog.cget("mode")) == "indeterminate":
                self.prog.stop()
                self.prog.configure(mode="determinate")
            self.prog.configure(value=max(0, min(100, pct)))
        except Exception:
            pass

    def _bar_frac(self, frac):
        lo, hi = getattr(self, "_bar_span", (0, 100))
        self._bar(lo + (hi - lo) * max(0.0, min(1.0, float(frac))))

    def _phase(self, text, lo, hi):
        """Ein Arbeitsschritt, der von lo bis hi Prozent laeuft."""
        self._bar_span = (lo, hi)
        self._set_status(text, lo)

    def _set_busy(self, flag, what=""):
        self.busy = flag
        self.busy_what = what if flag else ""
        state = "disabled" if flag else "normal"
        for b in (self.analyze_btn, self.build_btn, self.install_btn,
                  self.zip_btn, self.upd_btn):
            b.configure(state=state)
        try:
            self.cancel_btn.configure(state="normal" if flag else "disabled")
        except Exception:
            pass
        if not flag:
            try:
                self.prog.stop()
                self.prog.configure(mode="determinate", value=0)
            except Exception:
                pass
            self._apply_tool_state()

    def _bg(self, fn, on_done=None, on_cancel=None, what=""):
        if self.busy:
            messagebox.showinfo(t("dlg_busy_t"), t("dlg_busy"))
            return
        self._set_busy(True, what)
        self._bar_span = (0, 100)
        pc.reset_cancel()

        def wrapper():
            try:
                fn()
                self.msgq.put(("done", on_done or (lambda: None)))
            except pc.Cancelled:
                self.msgq.put(("cancelled", on_cancel))
            except Exception as ex:
                if pc.cancelled():
                    self.msgq.put(("cancelled", on_cancel))
                    return
                self._log(traceback.format_exc())
                self.msgq.put(("error", self._friendly_error(ex)))
        threading.Thread(target=wrapper, daemon=True).start()

    def cancel_job(self):
        if not self.busy:
            return
        pc.cancel()
        self.status.configure(text=t("st_cancelled") + " ...")

    def _friendly_error(self, ex):
        """yt-dlp-Ausgaben in verstaendliche Meldungen uebersetzen."""
        text = str(ex)
        key, upd_helps = pc.classify_ytdlp_error(text)
        if key:
            msg = pc.M(key)
            age = getattr(self, "_ytdlp_age", None)
            if upd_helps:
                if age is not None:
                    msg += "\n\n" + t("ytdlp_ver", "", age).replace("yt-dlp  ", "yt-dlp ")
                return (msg, "ytdlp")
            return msg
        return text

    # ------------------------------------------------------ Undo / Redo
    def _state_json(self):
        return json.dumps({"tracks": self.tracks, "clips": self.clips})

    def _snapshot(self):
        """Vor jeder Aenderung aufrufen / call before every change."""
        self._undo.append(self._state_json())
        if len(self._undo) > 200:
            self._undo.pop(0)
        self._redo.clear()
        self.dirty = True
        self._update_undo_buttons()

    def _restore(self, blob):
        data = json.loads(blob)
        self.tracks = data["tracks"]
        self.clips = data["clips"]
        if self.selected is not None and self.selected >= len(self.clips):
            self.selected = len(self.clips) - 1 if self.clips else None
        self.dirty = True
        self._refresh_track_box()
        self.refresh_list()
        self.draw_wave()
        self._update_undo_buttons()

    def undo(self):
        if not self._undo:
            return
        self._caption_save()
        self._redo.append(self._state_json())
        self._restore(self._undo.pop())

    def redo(self):
        if not self._redo:
            return
        self._undo.append(self._state_json())
        self._restore(self._redo.pop())

    def _update_undo_buttons(self):
        try:
            self.undo_btn.configure(state="normal" if self._undo else "disabled")
            self.redo_btn.configure(state="normal" if self._redo else "disabled")
        except Exception:
            pass

    # ------------------------------------------------------------ Tastatur
    def _on_key(self, event):
        w = self.focus_get()
        if _is_text_widget(w):
            return
        ks = event.keysym
        if ks in ("space", "Return") and isinstance(w, (ttk.Button, ttk.Menubutton,
                                                        ttk.Checkbutton,
                                                        ttk.Radiobutton)):
            return      # der Knopf selbst reagiert / the button handles it
        if isinstance(w, (ttk.Treeview, ttk.Scale, ttk.Scrollbar)) and \
                ks in ("Up", "Down", "Left", "Right", "Home", "End",
                       "Prior", "Next"):
            return      # Liste und Regler steuern sich selbst / they navigate themselves
        ctrl = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)
        if ctrl and ks.lower() == "z":
            self.undo()
        elif ctrl and ks.lower() == "y":
            self.redo()
        elif ctrl and ks.lower() == "d":
            self._duplicate_selected()
        elif ks == "space":
            if self._play:
                self._stop_play()
            else:
                self._play_selected()
            return "break"
        elif ks == "Delete":
            self._delete_selected()
        elif ks in ("Left", "Right"):
            step = 0.5 if ctrl else (0.01 if shift else 0.05)
            self._nudge(-step if ks == "Left" else step)
        elif ks in ("Up", "Down"):
            self._move_selected_track(-1 if ks == "Up" else 1)
        elif ks == "Return":
            self._focus_caption()
        elif ks == "s" and not ctrl:
            self._split_selected()
        elif ks == "Home":
            self.view_b = self.view_b - self.view_a
            self.view_a = 0.0
            self.draw_wave()
        elif ks == "End":
            span = self.view_b - self.view_a
            self.view_b = self.duration
            self.view_a = max(0.0, self.duration - span)
            self.draw_wave()

    def _nudge(self, dt):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        length = c["end"] - c["start"]
        a = max(0.0, min(self.duration - length, c["start"] + dt))
        if abs(a - c["start"]) < 1e-9:
            return
        self._snapshot()
        c["start"], c["end"] = a, a + length
        # Reihenfolge kann sich aendern - dann voll auffrischen, sonst nur
        # die eine Zeile / full refresh only if the order changed
        order = sorted(range(len(self.clips)),
                       key=lambda i: (self.clips[i]["start"], self.clips[i]["track"]))
        if order != list(range(len(self.clips))):
            self._after_edit()
            return
        try:
            i = self.selected
            self.tree.set(str(i), "start", "%.3f" % c["start"])
            self.tree.set(str(i), "end", "%.3f" % c["end"])
        except Exception:
            pass
        self.start_var.set("%.3f" % c["start"])
        self.end_var.set("%.3f" % c["end"])
        self.draw_wave()

    # ------------------------------------------------------------ ANALYSE
    def start_analyze(self):
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
        if self.clips and self.dirty:
            if not messagebox.askyesno(t("dlg_replace_t"), t("dlg_replace")):
                return
        sep = bool(self.sep_var.get()) and self.have_demucs
        span = None
        if t1 is not None:
            span = t1 - (t0 or 0.0)
        elif self.src_mode.get() == "file" and os.path.isfile(src):
            try:
                span = pc.probe_duration(src) - (t0 or 0.0)
            except Exception:
                span = None
        if sep and span and span > 240:
            if not messagebox.askyesno(t("dlg_long_t"),
                                       t("dlg_long", pc.fmt_time(span)[:-4])):
                return
        self._save_cfg()
        self._stop_play()
        mode = self.src_mode.get()
        opts = {"maxlen": float(self.maxlen.get()), "sens": float(self.sens.get())}
        self._bg(lambda: self._do_analyze(src, mode, t0, t1, sep, opts),
                 on_done=self._after_analyze, what=t("analyze"))

    def _new_session(self):
        """Frischer Arbeitsordner; die alte Sitzung bleibt bis zum Erfolg."""
        work = tempfile.mkdtemp(prefix="dubforge_")
        return {"work": work, "video_path": None, "audio_path": None,
                "vocals_path": None, "backing_path": None,
                "video_has_stream": False, "video_from_pack": False,
                "wave_data": [], "wave_sr": 8000, "duration": 0.0,
                "src_offset": 0.0, "source_url": "", "tracks": [], "clips": [],
                "meta": None}

    def _commit_session(self, sess):
        """Hauptthread: neue Sitzung uebernehmen, alte wegraeumen."""
        old = self.work
        self.work = sess["work"]
        for k in ("video_path", "audio_path", "vocals_path", "backing_path",
                  "video_has_stream", "video_from_pack", "wave_data", "wave_sr",
                  "duration", "src_offset", "source_url"):
            setattr(self, k, sess[k])
        self.clips = []
        self.tracks = sess["tracks"]
        self.clips = sess["clips"]
        self._preview_cache = {}
        self._preview_key = None
        self._peak_cache = (None, None)
        self.playhead = None
        if old and old != self.work:
            shutil.rmtree(old, ignore_errors=True)

    def _do_analyze(self, src, mode, t0, t1, separate, opts):
        sess = self._new_session()
        work = sess["work"]
        try:
            sess["src_offset"] = float(t0 or 0.0)
            sess["source_url"] = src if mode == "url" else ""

            if mode == "url":
                self._phase(t("st_download"), 2, 22)
                try:
                    sess["video_path"] = pc.download_youtube(
                        src, t0, t1, work, log=self._log,
                        progress=self._set_progress)
                except pc.Cancelled:
                    raise
                except Exception:
                    age = getattr(self, "_ytdlp_age", None)
                    if age is not None and age > 30:
                        self._log(t("dl_hint", age))
                    raise
            else:
                if not os.path.isfile(src):
                    raise RuntimeError(pc.M("file_missing", src))
                self._phase(t("st_trim"), 2, 22)
                sess["video_path"] = pc.trim_local(src, t0, t1, work, log=self._log)

            self._phase(t("st_audio"), 22, 28)
            sess["audio_path"] = os.path.join(work, "audio.wav")
            pc.extract_audio(sess["video_path"], sess["audio_path"], log=self._log)
            sess["duration"] = pc.probe_duration(sess["audio_path"])
            self._log(t("log_len", sess["duration"]))
            try:
                sess["video_has_stream"] = pc.has_video_stream(sess["video_path"])
            except Exception:
                sess["video_has_stream"] = False

            cut_source = sess["audio_path"]
            if separate:
                self._phase(t("st_demucs"), 28, 78)
                self._set_status(t("st_demucs"), None)
                try:
                    voc, nov = pc.separate_vocals(sess["audio_path"], work,
                                                  log=self._log,
                                                  progress=self._set_progress)
                    sess["vocals_path"] = voc
                    sess["backing_path"] = nov
                    cut_source = voc
                    self._log(t("log_voc_ok"))
                except pc.Cancelled:
                    raise
                except Exception as ex:
                    self._log(t("log_voc_fail", str(ex).splitlines()[0][:70]))
                    self._voc_failed = True

            self._phase(t("st_wave"), 78, 88)
            sess["wave_data"], sess["wave_sr"] = pc.load_mono(cut_source)

            self._phase(t("st_detect"), 88, 98)
            found = pc.detect_clips(sess["wave_data"], sess["wave_sr"],
                                    max_clip=opts["maxlen"],
                                    sensitivity=opts["sens"])
            sess["tracks"] = [{"name": t("track_default"), "color": TRACK_COLORS[0]}]
            sess["clips"] = [{"start": a, "end": b, "track": 0, "caption": ""}
                             for (a, b) in found]
            self._log(t("log_found", len(sess["clips"])))
            self._pending_session = sess
            self._set_status(t("st_done_an"), 100)
        except BaseException:
            shutil.rmtree(work, ignore_errors=True)
            raise

    def _after_analyze(self):
        sess = getattr(self, "_pending_session", None)
        if sess is not None:
            self._pending_session = None
            self._commit_session(sess)
        self._undo.clear()
        self._redo.clear()
        self.dirty = False
        self.built_path = None
        self.built_info = None
        self._auto_detect_ok = True
        self.selected = 0 if self.clips else None
        self._refresh_track_box()
        self._zoom_all()
        self.refresh_list()
        self._update_undo_buttons()
        self._update_built_label()
        if getattr(self, "_voc_failed", False):
            self._voc_failed = False
            self.status.configure(text=t("st_voc_fail"))
        elif not self.video_has_stream and self.audio_path:
            self.status.configure(text=t("st_novideo"))

    # ------------------------------------------------ Pack weiterbearbeiten
    def open_pack(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        folder = filedialog.askdirectory(title=t("dlg_pack_t"), initialdir=OUT_DIR)
        if not folder:
            return
        if self.clips and self.dirty:
            if not messagebox.askyesno(t("dlg_replace_t"), t("dlg_replace")):
                return
        try:
            info = pc.read_pack_for_edit(folder)
        except Exception as ex:
            messagebox.showerror(t("dlg_err"), str(ex))
            return
        source = None
        if not info["video"]:
            messagebox.showinfo(t("dlg_src_t"), t("dlg_src_for"))
            source = filedialog.askopenfilename(
                title=t("dlg_src_t"),
                filetypes=[(t("dlg_filter"), "*.mp4 *.mkv *.mov *.avi *.webm *.m4v "
                                             "*.wav *.mp3 *.ogg *.m4a *.flac"),
                           (t("dlg_allfiles"), "*.*")])
            if not source:
                return
        self._stop_play()
        self._bg(lambda: self._do_open_pack(folder, source),
                 on_done=self._after_open, what=t("open_pack"))

    def _do_open_pack(self, folder, source=None):
        self._phase(t("st_open"), 2, 10)
        info = pc.read_pack_for_edit(folder)      # prueft, bevor etwas passiert
        if not info["video"] and source:
            info["video"] = source
        if not info["video"]:
            raise RuntimeError(pc.M("no_pack", folder))
        sess = self._new_session()
        work = sess["work"]
        try:
            # Quelle sichern - beim Neubauen in denselben Ordner wuerde sie
            # sonst geloescht. / copy sources out first
            ext = os.path.splitext(info["video"])[1]
            sess["video_path"] = os.path.join(work, "source" + ext)
            shutil.copy2(info["video"], sess["video_path"])
            sess["video_from_pack"] = (ext.lower() == ".mp4" and not source)
            if info["backing"]:
                sess["backing_path"] = os.path.join(work, "backing.wav")
                shutil.copy2(info["backing"], sess["backing_path"])
            else:
                self._log(t("log_nobacking"))

            self._phase(t("st_audio"), 10, 50)
            sess["audio_path"] = os.path.join(work, "audio.wav")
            pc.extract_audio(sess["video_path"], sess["audio_path"], log=self._log)
            sess["duration"] = pc.probe_duration(sess["audio_path"])
            try:
                sess["video_has_stream"] = pc.has_video_stream(sess["video_path"])
            except Exception:
                sess["video_has_stream"] = False
            self._log(t("log_novoc"))

            self._phase(t("st_wave"), 50, 90)
            sess["wave_data"], sess["wave_sr"] = pc.load_mono(sess["audio_path"])

            tracks = []
            used = set()
            for i, tr in enumerate(info["tracks"][:MAX_TRACKS]):
                col = tr.get("color")
                if col not in TRACK_COLORS or col in used:
                    free = [c for c in TRACK_COLORS if c not in used]
                    col = free[0] if free else TRACK_COLORS[i % MAX_TRACKS]
                used.add(col)
                tracks.append({"name": str(tr.get("name") or t("track_new", i + 1)),
                               "color": col})
            if not tracks:
                tracks = [{"name": t("track_default"), "color": TRACK_COLORS[0]}]
            clips = []
            dur = sess["duration"]
            for c in info["clips"]:
                c["track"] = min(c["track"], len(tracks) - 1)
                c["end"] = min(c["end"], dur) if dur else c["end"]
                if c["end"] - c["start"] >= 0.05:
                    clips.append(c)
            sess["tracks"], sess["clips"] = tracks, clips
            meta = info.get("meta") or {}
            sess["meta"] = {"name": os.path.basename(folder),
                            "author": meta.get("author", ""),
                            "url": meta.get("source_url", ""),
                            "offset": float(meta.get("offset", 0.0) or 0.0),
                            "vheight": str(meta.get("vheight", "") or ""),
                            "folder": folder}
            sess["src_offset"] = sess["meta"]["offset"]
            sess["source_url"] = sess["meta"]["url"]
            self._pending_session = sess
            self._set_status(t("st_opened", len(clips), len(tracks)), 100)
        except BaseException:
            shutil.rmtree(work, ignore_errors=True)
            raise

    def _after_open(self):
        sess = getattr(self, "_pending_session", None)
        m = (sess or {}).get("meta") or {}
        self._opened_meta = m
        self.pack_name.set(m.get("name") or self.pack_name.get())
        if m.get("author"):
            self.author.set(m["author"])
        if m.get("url"):
            self._span_url = m["url"]
            self.url_var.set(m["url"])
            self.src_mode.set("url")
            self._sync_src()
        if m.get("vheight") in ("1080", "720", "540", "480", "360"):
            self.vheight.set(m["vheight"])
        self._after_analyze()
        self._auto_detect_ok = False      # geladene Clips nicht ueberschreiben
        if not self.backing_path and self.audio_path:
            if self.have_demucs:
                if messagebox.askyesno(t("dlg_sep_t"), t("dlg_sep_ask")):
                    self.separate_now()
            else:
                self._log(t("dlg_sep_missing"))

    # ------------------------------------------ Stimmen nachtraeglich trennen
    def separate_now(self):
        """Demucs auf die laufende Sitzung anwenden - z.B. nach 'Pack
        weiterbearbeiten'. Clips bleiben, die Wellenform zeigt danach die
        Stimmen. / run Demucs on the current session, keep the clips."""
        if not self.audio_path:
            messagebox.showinfo(t("dlg_first_t"), t("dlg_first"))
            return
        if not self.have_demucs:
            messagebox.showinfo(t("dlg_sep_t"), t("dlg_sep_missing"))
            return
        self._stop_play()
        audio, work = self.audio_path, self.work

        def job():
            self._phase(t("st_demucs"), 2, 90)
            self._set_status(t("st_demucs"), None)
            voc, nov = pc.separate_vocals(audio, work, log=self._log,
                                          progress=self._set_progress)
            self._phase(t("st_wave"), 90, 100)
            data, sr = pc.load_mono(voc)
            self._sep_result = (voc, nov, data, sr)

        def done():
            voc, nov, data, sr = self._sep_result
            self._sep_result = None
            self.vocals_path, self.backing_path = voc, nov
            self.wave_data, self.wave_sr = data, sr
            self._peak_cache = (None, None)
            self._log(t("log_voc_ok"))
            self.status.configure(text=t("st_sep_done"))
            self.draw_wave()
        self._bg(job, on_done=done, what=t("sep_now"))

    # ---------------------------------------------------------- Erkennung
    def redetect(self, quiet=False):
        if not len(self.wave_data):
            if not quiet:
                messagebox.showinfo(t("dlg_first_t"), t("dlg_first"))
            return
        if not quiet and self.clips and (len(self.tracks) > 1 or
                                         any(c.get("caption") for c in self.clips)):
            if not messagebox.askyesno(t("dlg_track_t"), t("dlg_redetect")):
                return
        found = pc.detect_clips(self.wave_data, self.wave_sr,
                                max_clip=float(self.maxlen.get()),
                                sensitivity=float(self.sens.get()))
        old = list(self.clips)
        self._snapshot()
        new = []
        for a, b in found:
            best, best_ov = None, 0.0
            for c in old:
                ov = min(b, c["end"]) - max(a, c["start"])
                if ov > best_ov:
                    best, best_ov = c, ov
            # Spur und Untertitel vom Clip mit der groessten Ueberlappung
            # uebernehmen / carry track + caption from the best overlap
            new.append({"start": a, "end": b,
                        "track": best["track"] if best else 0,
                        "caption": best.get("caption", "") if best else ""})
        self.clips = new
        self.selected = 0 if self.clips else None
        self._log(t("log_redet", len(self.clips)))
        self.refresh_list()
        self.draw_wave()

    def _detect_setting_changed(self):
        """Regler im Erkennungs-Menue: solange nichts von Hand geaendert
        wurde, gleich neu erkennen. / auto re-run while nothing is edited."""
        if self._auto_detect_ok and not self.dirty and len(self.wave_data):
            self.redetect(quiet=True)
            self.dirty = False
            self._undo.clear()
            self._update_undo_buttons()

    # -------------------------------------------------------------- Spuren
    def _new_track(self, name, idx=None, color=None):
        used = {tr.get("color") for tr in self.tracks}
        if color not in TRACK_COLORS:
            color = None
        if color is None:
            if idx is not None and TRACK_COLORS[idx % MAX_TRACKS] not in used:
                color = TRACK_COLORS[idx % MAX_TRACKS]
            else:
                free = [c for c in TRACK_COLORS if c not in used]
                color = free[0] if free else TRACK_COLORS[len(self.tracks) % MAX_TRACKS]
        return {"name": name, "color": color}

    def _track_tag(self, track_idx):
        col = self.tracks[track_idx]["color"] if 0 <= track_idx < len(self.tracks) \
            else TRACK_COLORS[0]
        return "t%d" % TRACK_COLORS.index(col)

    def add_track(self, name=None):
        if not self.tracks and not len(self.wave_data):
            messagebox.showinfo(t("dlg_first_t"), t("dlg_first"))
            return None
        if len(self.tracks) >= MAX_TRACKS:
            messagebox.showinfo(t("dlg_track_t"), t("dlg_track_max", MAX_TRACKS))
            return None
        if name is None:
            name = simpledialog.askstring(
                t("dlg_track_t"), t("dlg_track_name"),
                initialvalue=t("track_new", len(self.tracks) + 1), parent=self)
            if not name:
                return None
        self._snapshot()
        self.tracks.append(self._new_track(name.strip()))
        self._refresh_track_box()
        self.refresh_list()
        self.draw_wave()
        return len(self.tracks) - 1

    def rename_track(self, i):
        if not (0 <= i < len(self.tracks)):
            return
        new = simpledialog.askstring(t("dlg_track_t"), t("dlg_track_name"),
                                     initialvalue=self.tracks[i]["name"],
                                     parent=self)
        if new and new.strip() and new.strip() != self.tracks[i]["name"]:
            self._snapshot()
            self.tracks[i]["name"] = new.strip()
            self._refresh_track_box()
            self.refresh_list()
            self.draw_wave()

    def recolor_track(self, i):
        used = {tr["color"] for tr in self.tracks}
        cur = TRACK_COLORS.index(self.tracks[i]["color"])
        for k in range(1, MAX_TRACKS + 1):
            cand = TRACK_COLORS[(cur + k) % MAX_TRACKS]
            if cand not in used or cand == self.tracks[i]["color"]:
                self._snapshot()
                self.tracks[i]["color"] = cand
                break
        self.refresh_list()
        self.draw_wave()

    def move_track(self, i, delta):
        j = i + delta
        if not (0 <= i < len(self.tracks)) or not (0 <= j < len(self.tracks)):
            return
        self._snapshot()
        self.tracks[i], self.tracks[j] = self.tracks[j], self.tracks[i]
        for c in self.clips:
            if c["track"] == i:
                c["track"] = j
            elif c["track"] == j:
                c["track"] = i
        self._refresh_track_box()
        self.refresh_list()
        self.draw_wave()

    def delete_track(self, i):
        if len(self.tracks) <= 1 or not (0 <= i < len(self.tracks)):
            return
        n = sum(1 for c in self.clips if c["track"] == i)
        if n and not messagebox.askyesno(t("dlg_track_t"),
                                         t("dlg_track_del", self.tracks[i]["name"], n)):
            return
        self._snapshot()
        sel = self.clips[self.selected] if self.selected is not None else None
        del self.tracks[i]
        self.clips = [c for c in self.clips if c["track"] != i]
        for c in self.clips:
            if c["track"] > i:
                c["track"] -= 1
        self.selected = self._index_of(sel)
        self._refresh_track_box()
        self.refresh_list()
        self.draw_wave()

    def _refresh_track_box(self):
        try:
            self.track_box.configure(values=[tr["name"] for tr in self.tracks])
        except Exception:
            pass

    def _move_selected_track(self, delta):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        j = c["track"] + delta
        if not (0 <= j < len(self.tracks)):
            return
        self._snapshot()
        c["track"] = j
        self._after_edit()

    def _insp_track_changed(self, _e=None):
        if self.selected is None:
            return
        name = self.track_var.get()
        for i, tr in enumerate(self.tracks):
            if tr["name"] == name:
                if self.clips[self.selected]["track"] != i:
                    self._snapshot()
                    self.clips[self.selected]["track"] = i
                    self._after_edit()
                break
        self.canvas.focus_set()

    # ---------------------------------------------------------- Clip-Liste
    def _index_of(self, clip):
        if clip is None:
            return None
        for i, c in enumerate(self.clips):
            if c is clip:
                return i
        return None

    def _normalize(self):
        """Sortiert die Clips nach Start und haelt die Auswahl fest."""
        sel = self.clips[self.selected] if self.selected is not None and \
            0 <= self.selected < len(self.clips) else None
        self.clips.sort(key=lambda c: (c["start"], c["track"]))
        self.selected = self._index_of(sel)

    def _after_edit(self):
        self._normalize()
        self.refresh_list()
        self.draw_wave()

    def refresh_list(self):
        self._normalize()
        self.tree.delete(*self.tree.get_children())
        for i, c in enumerate(self.clips):
            tr = self.tracks[c["track"]] if 0 <= c["track"] < len(self.tracks) \
                else {"name": "?"}
            self.tree.insert("", "end", iid=str(i), values=(
                i + 1, tr["name"], "%.3f" % c["start"], "%.3f" % c["end"],
                "%.2f" % (c["end"] - c["start"]), c.get("caption", "")),
                tags=(self._track_tag(c["track"]),))
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            self._syncing = True
            try:
                self.tree.selection_set(str(self.selected))
                self.tree.see(str(self.selected))
            finally:
                self._syncing = False
        else:
            self.tree.selection_remove(self.tree.selection())
        self._load_inspector()
        self._update_stats()

    def _update_stats(self):
        if not self.clips:
            self.stats_lbl.configure(text="")
            return
        spoken = sum(c["end"] - c["start"] for c in self.clips)
        nocap = sum(1 for c in self.clips if not c.get("caption"))
        txt = t("stats", len(self.clips), len(self.tracks), nocap,
                pc.fmt_time(spoken)[:-2])
        ov = 0
        by = {}
        for c in self.clips:
            by.setdefault(c["track"], []).append(c)
        for lst in by.values():
            lst.sort(key=lambda c: c["start"])
            for a, b in zip(lst, lst[1:]):
                if b["start"] < a["end"] - 1e-6:
                    ov += 1
        if ov:
            txt += "  ·  " + t("overlap_note", ov)
        if len(self.tracks) > 1:
            txt += "  ·  " + t("stats_parts", pc.disdubs_parts(self.tracks, self.clips))
        self.stats_lbl.configure(text=txt)

    def _tree_select(self, _e=None):
        if self._syncing:
            return
        sel = self.tree.selection()
        if sel:
            self._caption_save()
            self.selected = int(sel[0])
            self._load_inspector()
            self.draw_wave()

    # ------------------------------------------------------------ Inspektor
    def _load_inspector(self):
        self._caption_for = self.selected
        c = None
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            c = self.clips[self.selected]
        if c is None:
            self.insp_title.configure(text=t("insp_none"))
            self.caption_var.set("")
            self.track_var.set("")
            self.start_var.set("")
            self.end_var.set("")
            self._preview_placeholder("preview_pick")
            self._preview_key = None
            return
        self.insp_title.configure(text=t("insp_title", self.selected + 1,
                                         len(self.clips)))
        self.caption_var.set(c.get("caption", ""))
        self.track_var.set(self.tracks[c["track"]]["name"])
        self.start_var.set("%.3f" % c["start"])
        self.end_var.set("%.3f" % c["end"])
        self._schedule_preview(c)

    def _insp_time_apply(self):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        try:
            a = pc.parse_time(self.start_var.get())
            b = pc.parse_time(self.end_var.get())
        except ValueError:
            return
        if a is None or b is None:
            return
        a = max(0.0, min(self.duration, a))
        b = max(0.0, min(self.duration, b))
        if b - a < 0.05:
            return
        if abs(a - c["start"]) < 1e-4 and abs(b - c["end"]) < 1e-4:
            return
        self._snapshot()
        c["start"], c["end"] = a, b
        self._after_edit()

    def _caption_save(self):
        i = self._caption_for
        if i is None or not (0 <= i < len(self.clips)):
            return
        new = self.caption_var.get().strip()
        if self.clips[i].get("caption", "") != new:
            self._snapshot()
            self.clips[i]["caption"] = new
            try:
                self.tree.set(str(i), "caption", new)
            except Exception:
                pass
            self._update_stats()
            self.draw_wave()

    def _caption_next(self, _e=None):
        self._caption_save()
        if self.selected is not None and self.selected < len(self.clips) - 1:
            self.selected += 1
            self._syncing = True
            try:
                self.tree.selection_set(str(self.selected))
                self.tree.see(str(self.selected))
            finally:
                self._syncing = False
            self._load_inspector()
            self.draw_wave()
            self.caption_entry.focus_set()
            self.caption_entry.selection_range(0, "end")
        return "break"

    def _focus_caption(self):
        if self.selected is None:
            return
        self.caption_entry.focus_set()
        self.caption_entry.selection_range(0, "end")

    # ---- Standbild / frame preview
    def _preview_placeholder(self, key):
        self.preview.delete("all")
        w = int(self.preview.cget("width"))
        h = int(self.preview.cget("height"))
        self.preview.create_text(w // 2, h // 2, text=t(key), fill="#4a5070",
                                 font=(FONT, 9))

    def _schedule_preview(self, clip):
        if not (self.video_path and self.video_has_stream):
            self._preview_placeholder("preview_none")
            return
        tt = clip["start"] + min(0.4, (clip["end"] - clip["start"]) / 2.0)
        key = int(round(tt * 5))
        if key == self._preview_key:
            return                  # steht schon oder ist unterwegs / shown or pending
        if self._preview_job:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        self._preview_key = key
        if key in self._preview_cache:
            self._show_preview(key, self._preview_cache[key])
            return
        self._preview_job = self.after(220, lambda: self._start_preview(key, tt))

    def _start_preview(self, key, tt):
        self._preview_job = None
        video = self.video_path
        out = os.path.join(self.work, "prev_%d.png" % key)

        def work():
            try:
                pc.extract_frame(video, tt, out, width=224)
                self.msgq.put(("preview", (key, out)))
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _show_preview(self, key, path):
        if not os.path.isfile(path):
            return
        self._preview_cache[key] = path
        if key != self._preview_key:
            return
        try:
            img = tk.PhotoImage(file=path)
        except Exception:
            return
        self._preview_img = img
        self.preview.delete("all")
        w = int(self.preview.cget("width"))
        h = int(self.preview.cget("height"))
        self.preview.create_image(w // 2, h // 2, image=img, anchor="center")
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            c = self.clips[self.selected]
            col = self.tracks[c["track"]]["color"]
            self.preview.create_rectangle(0, h - 5, w, h, fill=col, outline="")

    # ------------------------------------------------------- Clip-Aktionen
    def _delete_selected(self):
        if self.selected is None:
            return
        self._snapshot()
        del self.clips[self.selected]
        self.selected = min(self.selected, len(self.clips) - 1)
        if self.selected < 0:
            self.selected = None
        self.refresh_list()
        self.draw_wave()

    def _split_selected(self):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        # Am Playhead teilen, wenn er im Clip steht, sonst in der Mitte.
        # Split at the playhead if it sits inside the clip, else in the middle.
        mid = (c["start"] + c["end"]) / 2.0
        if self.playhead is not None and c["start"] < self.playhead < c["end"]:
            mid = self.playhead
        if mid - c["start"] < 0.1 or c["end"] - mid < 0.1:
            return
        self._snapshot()
        new = {"start": mid, "end": c["end"], "track": c["track"],
               "caption": ""}
        c["end"] = mid
        self.clips.insert(self.selected + 1, new)
        self._after_edit()

    def _duplicate_selected(self):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        self._snapshot()
        new = dict(c)
        # In die naechste Spur, wenn es eine gibt - dafuer sind Spuren da.
        # Into the next track if there is one - that is what tracks are for.
        if c["track"] + 1 < len(self.tracks):
            new["track"] = c["track"] + 1
        self.clips.append(new)
        self.selected = len(self.clips) - 1
        self._after_edit()

    # ------------------------------------------------------------ Wiedergabe
    def _play_selected(self):
        if self.selected is None or not self.audio_path:
            return
        c = self.clips[self.selected]
        self._play_range(c["start"], c["end"])

    def _play_track(self, i):
        lst = sorted((c for c in self.clips if c["track"] == i),
                     key=lambda c: c["start"])
        if lst:
            a = lst[0]["start"]
            self._play_range(a, min(lst[-1]["end"], a + 90.0))

    def _play_range(self, a, b):
        """
        Spielt [a, b] ab. Ton: sounddevice (wie DubStage), sonst ffplay,
        sonst winsound. Bild: eine PNG-Folge des Ausschnitts laeuft in der
        Vorschau mit. Beides wird im Hintergrund vorbereitet; sobald der Ton
        steht, startet die Uhr.
        Plays [a, b]: sounddevice first, then ffplay, then winsound; the
        preview animates a PNG sequence of the span in sync.
        """
        self._stop_play()
        src = self.vocals_path or self.audio_path
        if not src or b - a <= 0.02:
            return
        self._play_token += 1
        token = self._play_token
        old_dir = os.path.join(self.work, "play_%d" % (token - 1))
        shutil.rmtree(old_dir, ignore_errors=True)
        self._play_frames = None
        self._play_frame_idx = -1
        self.play_btn.configure(text="■  " + t("btn_stop"))
        self._set_status(t("st_playing", b - a))

        video = self.video_path if (self.video_has_stream and b - a <= 25) else None
        work = self.work

        def audio_work():
            data, err = None, None
            try:
                data = pc.decode_pcm(src, a, b)
            except Exception as ex:
                err = str(ex).splitlines()[-1][:120] if str(ex) else "?"
            self.msgq.put(("play_start", (token, data, err)))

        def frames_work():
            outdir = os.path.join(work, "play_%d" % token)
            try:
                pc.extract_frames_range(video, a, b, outdir, fps=PLAY_FPS, width=224)
            except Exception:
                pass

        threading.Thread(target=audio_work, daemon=True).start()
        if video:
            self._play_frames = os.path.join(work, "play_%d" % token)
            threading.Thread(target=frames_work, daemon=True).start()
        self._pending_play = (token, a, b)

    def _on_play_start(self, token, data, err):
        """Hauptthread: Ton anwerfen und die Uhr starten / start the clock."""
        if self._pending_play is None or self._pending_play[0] != token:
            return
        _tok, a, b = self._pending_play
        self._pending_play = None
        if err:
            self._log(t("log_noplay", err))
        backend = self._start_audio(data, a, b)
        if not backend:
            self._stop_play()
            return
        if backend != getattr(self, "_last_backend", None):
            self._last_backend = backend
            self._log(t("log_backend", backend))
        self._play = (time.time(), a, b)
        self._tick_playhead()

    def _start_audio(self, data, a, b):
        """Versucht die Backends der Reihe nach / tries the backends in turn."""
        src = self.vocals_path or self.audio_path
        sd = pc.sounddevice()
        if sd is not None and data is not None:
            try:
                sd.stop()
                sd.play(data, 44100)
                return "sounddevice"
            except Exception as ex:
                self._log(t("log_noplay", "sounddevice: %s" % ex))
        fp = pc.ffplay()
        if fp:
            try:
                self.player = subprocess.Popen(
                    [fp, "-nodisp", "-autoexit", "-loglevel", "quiet",
                     "-ss", "%.3f" % a, "-t", "%.3f" % (b - a), src],
                    creationflags=pc._NOWINDOW)
                return "ffplay"
            except Exception as ex:
                self._log(t("log_noplay", "ffplay: %s" % ex))
        if os.name == "nt":
            try:
                import winsound
                tmp = os.path.join(self.work, "_preview.wav")
                if data is not None:
                    pc.write_pcm_wav(tmp, data, 44100)
                else:
                    pc.run([pc.ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                            "-ss", "%.3f" % a, "-i", src, "-t", "%.3f" % (b - a),
                            "-c:a", "pcm_s16le", tmp])
                winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return "winsound"
            except Exception as ex:
                self._log(t("log_noplay", "winsound: %s" % ex))
        return None

    def _tick_playhead(self):
        if not self._play:
            return
        t0, a, b = self._play
        pos = a + (time.time() - t0)
        if pos >= b or (self.player and self.player.poll() is not None
                        and pos > a + 0.3):
            self._stop_play()
            return
        self.playhead = pos
        self._draw_playhead()
        self._show_play_frame(pos - a)
        self.after(40, self._tick_playhead)

    def _show_play_frame(self, rel):
        d = self._play_frames
        if not d:
            return
        idx = int(rel * PLAY_FPS) + 1
        if idx == self._play_frame_idx:
            return
        path = os.path.join(d, "f%03d.png" % idx)
        if not os.path.isfile(path):
            return
        try:
            img = tk.PhotoImage(file=path)
        except Exception:
            return
        self._play_frame_idx = idx
        self._preview_img = img
        self.preview.delete("all")
        w = int(self.preview.cget("width"))
        h = int(self.preview.cget("height"))
        self.preview.create_image(w // 2, h // 2, image=img, anchor="center")

    def _stop_play(self):
        self._pending_play = None
        sd = pc.sounddevice()
        if sd is not None:
            try:
                sd.stop()
            except Exception:
                pass
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
        was_playing = self._play is not None
        self._play = None
        try:
            self.play_btn.configure(text="▶  " + t("btn_play"))
        except Exception:
            pass
        self._draw_playhead()
        if was_playing:
            self._set_status(t("ready"))
            # zurueck zum Startbild des Clips / back to the clip's still
            self._preview_key = None
            if self.selected is not None and 0 <= self.selected < len(self.clips):
                self._schedule_preview(self.clips[self.selected])

    def _draw_playhead(self):
        cv = self.canvas
        cv.delete("playhead")
        if self.playhead is None or not len(self.wave_data):
            return
        if not (self.view_a <= self.playhead <= self.view_b):
            return
        x = self._t2x(self.playhead)
        h = cv.winfo_height()
        cv.create_line(x, 0, x, h, fill="#ffffff", width=1, tags="playhead")
        cv.create_polygon(x - 5, 0, x + 5, 0, x, 7, fill="#ffffff",
                          outline="", tags="playhead")

    # ------------------------------------------------------------ Wellenform
    def _zoom_all(self):
        self.view_a, self.view_b = 0.0, max(0.5, self.duration)
        self.draw_wave()

    def _zoom_selected(self):
        if self.selected is None:
            return
        c = self.clips[self.selected]
        pad = max(0.3, (c["end"] - c["start"]) * 0.6)
        self.view_a = max(0.0, c["start"] - pad)
        self.view_b = min(self.duration, c["end"] + pad)
        self.draw_wave()

    def _zoom(self, factor, anchor=None):
        if self.duration <= 0:
            return
        span_old = self.view_b - self.view_a
        centre = (self.view_a + self.view_b) / 2.0 if anchor is None else anchor
        span = max(0.3, min(self.duration, span_old * factor))
        # Anker bleibt unter der Maus / keep the anchor under the mouse
        rel = 0.5 if anchor is None else (anchor - self.view_a) / max(1e-6, span_old)
        self.view_a = max(0.0, centre - rel * span)
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

    def _scroll_by(self, dt):
        span = self.view_b - self.view_a
        if span >= self.duration:
            return
        a = max(0.0, min(self.duration - span, self.view_a + dt))
        self.view_a, self.view_b = a, a + span
        self.draw_wave()

    def _canvas_wheel(self, event):
        if not len(self.wave_data):
            return
        if event.state & 0x4:      # Strg / Ctrl = Zoom an der Maus
            self._zoom(0.8 if event.delta > 0 else 1.25, anchor=self._x2t(event.x))
        else:
            span = self.view_b - self.view_a
            self._scroll_by(-span * 0.12 if event.delta > 0 else span * 0.12)

    def _tl_width(self):
        return max(1, self.canvas.winfo_width() - GUTTER)

    def _x2t(self, x):
        return self.view_a + ((x - GUTTER) / self._tl_width()) * (self.view_b - self.view_a)

    def _t2x(self, tt):
        span = max(1e-6, self.view_b - self.view_a)
        return GUTTER + (tt - self.view_a) / span * self._tl_width()

    def _lane_top(self, i):
        return RULER_H + WAVE_H + i * LANE_H

    def _lane_at(self, y):
        i = int((y - RULER_H - WAVE_H) // LANE_H)
        if 0 <= i < len(self.tracks):
            return i
        return None

    def _canvas_height(self):
        return RULER_H + WAVE_H + max(1, len(self.tracks)) * LANE_H + ADD_H

    def draw_wave(self):
        cv = self.canvas
        want_h = self._canvas_height()
        if int(cv.cget("height")) != want_h:
            cv.configure(height=want_h)
        cv.delete("all")
        w = max(1, cv.winfo_width())
        h = max(1, cv.winfo_height())

        if not len(self.wave_data) or self.duration <= 0:
            cv.create_text(w / 2, h / 2, fill="#5a6180", text=t("canvas_empty"),
                           font=(FONT, 11), width=w - 40, justify="center")
            return

        span = max(1e-6, self.view_b - self.view_a)
        tw = self._tl_width()
        n = len(self.wave_data)
        a = int(self.view_a / self.duration * n)
        b = int(self.view_b / self.duration * n)
        b = max(a + 2, min(n, b))
        key = (a, b, tw)
        if self._peak_cache[0] == key:
            peaks = self._peak_cache[1]
        else:
            peaks = pc.waveform_peaks(self.wave_data[a:b], tw)
            self._peak_cache = (key, peaks)

        # ---- Rinne links / gutter
        cv.create_rectangle(0, 0, GUTTER, h, fill="#1a1b22", outline="")
        cv.create_line(GUTTER, 0, GUTTER, h, fill=LINE)

        # ---- Lineal / ruler
        cv.create_rectangle(GUTTER, 0, w, RULER_H, fill="#1a1b22", outline="")
        step = self._nice_step(span)
        tt = (int(self.view_a / step)) * step
        while tt <= self.view_b:
            x = self._t2x(tt)
            if x >= GUTTER:
                cv.create_line(x, RULER_H - 6, x, RULER_H, fill="#4a4e63")
                cv.create_line(x, RULER_H, x, h, fill="#20222b")
                cv.create_text(x + 3, RULER_H / 2, anchor="w", fill="#7d84a0",
                               text=pc.fmt_time(tt)[:-2], font=(MONO, 8))
            tt += step
        cv.create_line(GUTTER, RULER_H, w, RULER_H, fill=LINE)

        # ---- Wellenform / waveform, mit Clipspannen in Sprecherfarbe
        top, bot = RULER_H, RULER_H + WAVE_H
        mid = (top + bot) / 2.0
        amp = (WAVE_H / 2.0) - 6
        for i, c in enumerate(self.clips):
            if c["end"] < self.view_a or c["start"] > self.view_b:
                continue
            x0, x1 = self._t2x(c["start"]), self._t2x(c["end"])
            col = self.tracks[c["track"]]["color"]
            cv.create_rectangle(x0, top + 1, x1, bot - 1, fill=col, outline="",
                                stipple="gray25" if i != self.selected else "gray50")
        for x, (lo, hi) in enumerate(peaks):
            y0 = mid - hi * amp
            y1 = mid - lo * amp
            if abs(y1 - y0) < 1:
                y1 = y0 + 1
            cv.create_line(GUTTER + x, y0, GUTTER + x, y1, fill=WAVE)
        cv.create_line(GUTTER, mid, w, mid, fill=LINE)
        cv.create_line(GUTTER, bot, w, bot, fill=LINE)
        cv.create_text(8, mid, anchor="w", fill="#5a6180", font=(FONT, 9),
                       text=("Vocals" if self.vocals_path else "Audio"))

        # ---- Spuren / lanes
        for i, tr in enumerate(self.tracks):
            y0 = self._lane_top(i)
            y1 = y0 + LANE_H
            col = tr["color"]
            if i % 2:
                cv.create_rectangle(GUTTER, y0, w, y1, fill="#17181e", outline="")
            cv.create_line(GUTTER, y1, w, y1, fill=LINE)
            # Rinne: Farbstreifen + Name / gutter: colour bar + name
            cv.create_rectangle(0, y0, 5, y1, fill=col, outline="")
            cv.create_text(14, (y0 + y1) / 2, anchor="w", fill=FG,
                           text=self._ellipsize(tr["name"], 16),
                           font=(FONT + " Semibold", 10), tags=("lane%d" % i,))
            cv.create_line(0, y1, GUTTER, y1, fill=LINE)

        for i, c in enumerate(self.clips):
            if c["end"] < self.view_a or c["start"] > self.view_b:
                continue
            x0, x1 = self._t2x(c["start"]), self._t2x(c["end"])
            x0, x1 = max(GUTTER, x0), max(GUTTER, x1)
            y0 = self._lane_top(c["track"]) + 4
            y1 = y0 + LANE_H - 8
            col = self.tracks[c["track"]]["color"]
            sel = (i == self.selected)
            cv.create_rectangle(x0, y0, x1, y1, fill=col, outline="#ffffff" if sel else col,
                                width=2 if sel else 1,
                                stipple="" if sel else "gray75")
            if x1 - x0 > 26:
                label = "%d" % (i + 1)
                cap = c.get("caption", "")
                if cap and x1 - x0 > 60:
                    label += "  " + self._ellipsize(cap, int((x1 - x0 - 24) / 6.5))
                cv.create_text(x0 + 6, (y0 + y1) / 2, anchor="w",
                               fill="#0d0e14" if sel else "#0f1017",
                               text=label, font=(FONT + " Semibold", 9))

        # ---- Spur hinzufuegen / add-track row
        y0 = self._lane_top(len(self.tracks))
        cv.create_text(14, y0 + ADD_H / 2, anchor="w", fill="#6f76a0",
                       text=t("add_track_row"), font=(FONT, 9), tags=("addtrack",))

        self._draw_playhead()

        if self.duration > span:
            self._syncing = True
            try:
                self.hscroll.set(self.view_a / max(1e-6, self.duration - span))
            finally:
                self._syncing = False

    @staticmethod
    def _ellipsize(text, n):
        text = str(text)
        if n < 2:
            return ""
        return text if len(text) <= n else text[:max(1, n - 1)] + "…"

    @staticmethod
    def _nice_step(span):
        for s in (0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600):
            if span / s <= 12:
                return s
        return 900

    # ------------------------------------------------- Maus auf der Zeitleiste
    def _hit(self, x, y):
        """
        Was liegt unter der Maus? -> ('edge_start'|'edge_end'|'body', i)
        oder ('lane', track) oder ('wave', None) oder ('gutter', track) ...
        """
        if not len(self.wave_data):
            return (None, None)
        if x < GUTTER:
            lane = self._lane_at(y)
            if lane is not None:
                return ("gutter", lane)
            if y >= self._lane_top(len(self.tracks)):
                return ("add", None)
            return (None, None)
        if y < RULER_H:
            return ("ruler", None)
        if y < RULER_H + WAVE_H:
            return ("wave", None)
        lane = self._lane_at(y)
        if lane is None:
            if y >= self._lane_top(len(self.tracks)):
                return ("add", None)
            return (None, None)
        tt = self._x2t(x)
        tol = (self.view_b - self.view_a) / self._tl_width() * EDGE_PX
        # zuerst der gewaehlte Clip, dann die anderen / selected first
        order = list(range(len(self.clips)))
        if self.selected is not None and 0 <= self.selected < len(self.clips):
            order.remove(self.selected)
            order.insert(0, self.selected)
        for i in order:
            c = self.clips[i]
            if c["track"] != lane:
                continue
            if abs(tt - c["end"]) <= tol and c["end"] - c["start"] > 3 * tol:
                return ("edge_end", i)
            if abs(tt - c["start"]) <= tol and c["end"] - c["start"] > 3 * tol:
                return ("edge_start", i)
        for i in order:
            c = self.clips[i]
            if c["track"] == lane and c["start"] <= tt <= c["end"]:
                return ("body", i)
        return ("lane", lane)

    def _canvas_hover(self, event):
        kind, _ref = self._hit(event.x, event.y)
        cur = ""
        if kind in ("edge_start", "edge_end"):
            cur = "sb_h_double_arrow"
        elif kind == "body":
            cur = "fleur"
        elif kind == "lane":
            cur = "crosshair"
        elif kind in ("gutter", "add", "ruler"):
            cur = "hand2"
        self.canvas.configure(cursor=cur)

    def _canvas_down(self, event):
        self.canvas.focus_set()
        kind, ref = self._hit(event.x, event.y)
        if kind is None:
            return
        self._caption_save()
        if kind == "add":
            self.add_track()
            return
        if kind == "gutter":
            self._drag = None
            return
        if kind in ("ruler", "wave"):
            self.playhead = max(0.0, min(self.duration, self._x2t(event.x)))
            self._drag = ("scrub", None)
            self._draw_playhead()
            return
        tt = self._x2t(event.x)
        if kind == "edge_start":
            self.selected = ref
            self._drag = ("start", ref, False)
        elif kind == "edge_end":
            self.selected = ref
            self._drag = ("end", ref, False)
        elif kind == "body":
            self.selected = ref
            c = self.clips[ref]
            self._drag = ("move", ref, False, tt - c["start"], c["track"], event.y)
        else:  # lane -> neuer Clip / new clip
            self.selected = None
            self._drag = ("new", tt, ref)
        self.refresh_list()
        self.draw_wave()

    def _canvas_move(self, event):
        if not self._drag:
            return
        kind = self._drag[0]
        tt = max(0.0, min(self.duration, self._x2t(event.x)))
        if kind == "scrub":
            self.playhead = tt
            self._draw_playhead()
            return
        if kind == "new":
            _k, t0, lane = self._drag
            self.canvas.delete("newsel")
            y0 = self._lane_top(lane) + 4
            self.canvas.create_rectangle(self._t2x(t0), y0, self._t2x(tt),
                                         y0 + LANE_H - 8, outline=ACC2, width=2,
                                         tags="newsel")
            return
        # trimmen oder verschieben / trim or move: erst beim ersten Ruck
        # ein Undo-Punkt / first real motion pushes the undo point
        ref = self._drag[1]
        c = self.clips[ref]
        if not self._drag[2]:
            self._snapshot()
            self._drag = (self._drag[0], ref, True) + tuple(self._drag[3:])
        if kind == "start":
            c["start"] = max(0.0, min(tt, c["end"] - 0.05))
        elif kind == "end":
            c["end"] = min(self.duration, max(tt, c["start"] + 0.05))
        elif kind == "move":
            _k, _r, _s, grab, lane0, y_start = self._drag
            length = c["end"] - c["start"]
            a = max(0.0, min(self.duration - length, tt - grab))
            c["start"], c["end"] = a, a + length
            lane = self._lane_at(event.y)
            if lane is not None:
                c["track"] = lane
        self.draw_wave()
        # Inspektor live / live inspector
        self.start_var.set("%.3f" % c["start"])
        self.end_var.set("%.3f" % c["end"])
        self.track_var.set(self.tracks[c["track"]]["name"])

    def _canvas_up(self, event):
        if not self._drag:
            return
        drag = self._drag
        self._drag = None
        self.canvas.delete("newsel")
        kind = drag[0]
        if kind == "scrub":
            return
        if kind == "new":
            _k, t0, lane = drag
            tt = max(0.0, min(self.duration, self._x2t(event.x)))
            a, b = min(t0, tt), max(t0, tt)
            if b - a >= 0.15:
                self._snapshot()
                new = {"start": a, "end": b, "track": lane, "caption": ""}
                self.clips.append(new)
                self.selected = len(self.clips) - 1
                self._after_edit()
                return
        self._after_edit()

    def _canvas_double(self, event):
        kind, ref = self._hit(event.x, event.y)
        if kind == "gutter":
            self.rename_track(ref)
        elif kind == "body":
            self.selected = ref
            self.refresh_list()
            self._play_selected()
        elif kind in ("wave", "ruler"):
            # ab hier 8 Sekunden anhoeren / listen from here for 8 seconds
            a = max(0.0, min(self.duration, self._x2t(event.x)))
            self._play_range(a, min(self.duration, a + 8.0))

    def _canvas_right(self, event):
        self._caption_save()
        kind, ref = self._hit(event.x, event.y)
        if kind == "gutter" or (kind in ("lane", "body", "edge_start", "edge_end")
                                and self.tracks):
            if kind != "gutter":
                if kind == "lane":
                    lane = ref
                else:
                    lane = self.clips[ref]["track"]
                    self.selected = ref
                    self.refresh_list()
                    self.draw_wave()
            else:
                lane = ref
            m = self._menu(self)
            m.add_command(label=t("menu_rename"), command=lambda: self.rename_track(lane))
            m.add_command(label=t("menu_color"), command=lambda: self.recolor_track(lane))
            m.add_command(label=t("menu_sel_all"), command=lambda: self._play_track(lane))
            m.add_separator()
            m.add_command(label=t("menu_up"), command=lambda: self.move_track(lane, -1),
                          state="normal" if lane > 0 else "disabled")
            m.add_command(label=t("menu_down"), command=lambda: self.move_track(lane, 1),
                          state="normal" if lane < len(self.tracks) - 1 else "disabled")
            m.add_separator()
            m.add_command(label=t("menu_del"), command=lambda: self.delete_track(lane),
                          state="normal" if len(self.tracks) > 1 else "disabled")
            if kind in ("body", "edge_start", "edge_end"):
                m.add_separator()
                m.add_command(label=t("btn_split"), command=self._split_selected)
                m.add_command(label=t("btn_dup"), command=self._duplicate_selected)
                m.add_command(label=t("btn_delete"), command=self._delete_selected)
            try:
                m.tk_popup(event.x_root, event.y_root)
            finally:
                m.grab_release()

    # ------------------------------------------------------------ Untertitel
    def import_subs_file(self):
        if not self.clips:
            messagebox.showinfo(t("dlg_noclips_t"), t("dlg_noclips"))
            return
        p = filedialog.askopenfilename(
            title=t("dlg_sub_t"),
            filetypes=[(t("dlg_sub_filter"), "*.srt *.vtt"),
                       (t("dlg_allfiles"), "*.*")])
        if not p:
            return
        try:
            cues = pc.read_subtitle_file(p)
        except Exception as ex:
            messagebox.showerror(t("dlg_err"), str(ex))
            return
        self._apply_cues(cues, self.src_offset)

    def fetch_subs_youtube(self):
        if not self.clips:
            messagebox.showinfo(t("dlg_noclips_t"), t("dlg_noclips"))
            return
        url = self.source_url or (self.url_var.get().strip()
                                  if self.src_mode.get() == "url" else "")
        if not url or not url.lower().startswith(("http://", "https://")):
            messagebox.showinfo(t("subs_over_t"), t("subs_notyt"))
            return
        offset = self.src_offset

        def work():
            self._set_status(t("st_subs"), 20)
            path = pc.fetch_youtube_subs(url, self.work, langs=self._sub_langs(),
                                         log=self._log)
            self._fetched_cues = pc.read_subtitle_file(path) if path else []
            self._set_status(t("st_subs"), 100)

        def done():
            cues = getattr(self, "_fetched_cues", [])
            self._apply_cues(cues, offset)
        self._bg(work, on_done=done)

    def _apply_cues(self, cues, offset):
        if not cues:
            messagebox.showinfo(t("subs_over_t"), t("subs_none"))
            return
        overwrite = messagebox.askyesno(t("subs_over_t"), t("subs_over", len(cues)))
        self._caption_save()
        self._snapshot()
        n = pc.assign_captions(self.clips, cues, offset=offset, overwrite=overwrite)
        self._log(t("subs_done", n))
        self.refresh_list()
        self.draw_wave()

    def clear_captions(self):
        if not any(c.get("caption") for c in self.clips):
            return
        self._snapshot()
        for c in self.clips:
            c["caption"] = ""
        self.refresh_list()
        self.draw_wave()

    # -------------------------------------------------------------- BAUEN
    def start_build(self, then=None):
        self._caption_save()
        if not self.clips:
            messagebox.showinfo(t("dlg_noclips_t"), t("dlg_noclips"))
            return
        name = pc.safe_name(self.pack_name.get(), "Mein_Pack")
        self.pack_name.set(name)
        dub = bool(self.is_dub.get())

        # --- Vorabpruefung / pre-flight (DisDubs + DubStage)
        default_names = (t("track_default"), "Voice", "Stimme") + \
            tuple(t("track_new", i) for i in range(1, MAX_TRACKS + 1))
        warns = pc.disdubs_check(
            self.tracks, self.clips, duration=self.duration, dub=dub,
            has_backing=bool(self.backing_path), has_video=self.video_has_stream,
            default_names=default_names)
        if warns:
            body = "\n".join("• " + w for w in warns[:8])
            if not messagebox.askyesno(t("dlg_check_t"), t("dlg_check", body)):
                return

        # --- vorhandener Pack / existing pack
        os.makedirs(OUT_DIR, exist_ok=True)
        dest = os.path.join(OUT_DIR, name)
        opened = (getattr(self, "_opened_meta", None) or {}).get("folder")
        same_as_opened = opened and os.path.normcase(os.path.abspath(opened)) == \
            os.path.normcase(os.path.abspath(dest))
        if os.path.exists(dest) and dest != self.built_path and not same_as_opened:
            alt = name
            k = 2
            while os.path.exists(os.path.join(OUT_DIR, alt)):
                alt = "%s_%d" % (name, k)
                k += 1
            if not messagebox.askyesno(t("dlg_exists_t"), t("dlg_exists", name, alt)):
                name = alt
                self.pack_name.set(name)

        self._save_cfg()
        clips = sorted([dict(c) for c in self.clips],
                       key=lambda c: (c["start"], c["track"]))
        tracks = [dict(tr) for tr in self.tracks]
        opts = {"dub": dub, "author": self.author.get().strip(),
                "vheight": int(self.vheight.get()),
                "has_video": self.video_has_stream}
        self._build_then = then
        self.built_path = None
        self._bg(lambda: self._do_build(name, clips, tracks, opts),
                 on_done=self._after_build, what=t("build"))

    def _do_build(self, name, clips, tracks, opts):
        captions = {}
        os.makedirs(OUT_DIR, exist_ok=True)
        final = os.path.join(OUT_DIR, name)
        # Erst in einen Nebenordner bauen, dann tauschen: ein Abbruch laesst
        # den alten Pack heil. / build beside, swap on success
        dest = final + ".building"
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        dub = opts["dub"]
        src_audio = self.vocals_path or self.audio_path
        author = opts["author"]
        try:
            lines = [t("ts_head", name)]
            total = len(clips)
            for i, c in enumerate(clips, 1):
                speaker = tracks[c["track"]]["name"] if 0 <= c["track"] < len(tracks) \
                    else "Voice"
                fn = pc.clip_filename(i, speaker, c["start"], dub=dub)
                c["file"] = fn
                self._set_status(t("st_clip", i, total), 3 + 45 * i / max(1, total))
                pc.export_clip(src_audio, c["start"], c["end"],
                               os.path.join(dest, fn))
                cap = (c.get("caption") or "").strip()
                if cap:
                    captions[fn] = cap
                lines.append("%-44s %10.3f   %5.2fs   %-16s%s"
                             % (fn, c["start"], c["end"] - c["start"], speaker,
                                "   | " + cap if cap else ""))
                self._log("  %s   @ %.3f s%s" % (fn, c["start"],
                                                 "   | " + cap if cap else ""))

            if captions:
                pc.write_captions(dest, captions)
                self._log("  %s (%d)" % (pc.CAPTION_FILE, len(captions)))

            if dub and self.backing_path and os.path.isfile(self.backing_path):
                self._phase(t("st_backing"), 48, 55)
                pc.export_backing_track(self.backing_path,
                                        os.path.join(dest, "_backing_track.wav"),
                                        log=self._log)
                self._log("  _backing_track.wav")

            if dub and opts["has_video"]:
                out_video = os.path.join(dest, "dub_video.mp4")
                if self.video_from_pack:
                    self._phase(t("st_video_copy"), 55, 95)
                    shutil.copy2(self.video_path, out_video)
                else:
                    self._phase(t("st_video"), 55, 95)
                    pc.convert_video(self.video_path, out_video,
                                     max_height=opts["vheight"], log=self._log,
                                     progress=self._set_progress)
                self._log("  dub_video.mp4")
            elif dub:
                # Quelle ohne Bild: Standbild-Video aus Cover oder dunkler
                # Karte, damit der Pack abspielbar bleibt. / still video
                self._phase(t("st_still"), 55, 95)
                self._log(t("st_novideo"))
                cover = pc.extract_cover(self.video_path,
                                         os.path.join(self.work, "cover.png"))
                pc.make_still_video(self.audio_path,
                                    os.path.join(dest, "dub_video.mp4"),
                                    image=cover, max_height=opts["vheight"],
                                    log=self._log, progress=self._set_progress)
                self._log("  dub_video.mp4 (%s)" % ("cover" if cover else "card"))
            if dub:
                with open(os.path.join(dest, "_TIMESTAMPS.txt"), "w",
                          encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

            speakers = ", ".join(tr["name"] for tr in tracks)
            pc.write_pack_info(dest, name.replace("_", " "),
                               [author] if author else None)
            pc.write_project(dest, {
                "version": 1,
                "app": "DubForge",
                "dubforge_version": upd.VERSION,
                "tracks": tracks,
                "clips": [{"start": round(c["start"], 3), "end": round(c["end"], 3),
                           "track": c["track"], "caption": c.get("caption", ""),
                           "file": c.get("file", "")} for c in clips],
                "meta": {"author": author, "source_url": self.source_url,
                         "offset": self.src_offset, "vheight": str(opts["vheight"]),
                         "dub": dub},
            })
            with open(os.path.join(dest, "_README.txt"), "w", encoding="utf-8") as f:
                f.write(t("readme", name,
                          t("type_dub") if dub else t("type_voice"), len(clips),
                          speakers))
                if dub:
                    f.write(t("readme_dub"))

            # tauschen / swap
            self._set_status(t("st_built", final), 98)
            if os.path.exists(final):
                shutil.rmtree(final)
            os.replace(dest, final)
        except BaseException:
            shutil.rmtree(dest, ignore_errors=True)
            raise
        self._built_result = (final, dub, len(clips), len(tracks))
        self._set_status(t("st_built", final), 100)

    def _after_build(self):
        res = getattr(self, "_built_result", None)
        if not res:
            return
        self._built_result = None
        path, dub, n_clips, n_tracks = res
        self.built_path = path
        self.built_dub = dub
        self.built_info = (time.strftime("%H:%M"), n_clips)
        self.dirty = False
        self._update_built_label()
        then = getattr(self, "_build_then", None)
        self._build_then = None
        if then:
            then()
            return
        self._built_dialog(path, dub, n_clips, n_tracks)

    def _update_built_label(self):
        try:
            if self.built_info and self.built_path:
                self.built_lbl.configure(text=t("built_at", *self.built_info))
            else:
                self.built_lbl.configure(text="")
        except Exception:
            pass

    def _built_dialog(self, path, dub, n_clips, n_tracks):
        """Drei Wege nach dem Bauen: ZIP fuer DisDubs, Ordner, Schliessen."""
        parts = t("dlg_built_parts", pc.disdubs_parts(self.tracks, self.clips)) \
            if dub and n_tracks > 1 else ""
        dlg = tk.Toplevel(self)
        dlg.title(t("dlg_built_t"))
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=t("dlg_built", path, n_clips, n_tracks, parts),
                  wraplength=520, justify="left").pack(anchor="w")
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=(14, 0))

        def close():
            dlg.destroy()

        def do_zip():
            close()
            self.zip_pack()

        def do_open():
            close()
            self._open_folder(path)
        if dub:
            ttk.Button(row, text=t("btn_zip_now"), style="Go.TButton",
                       command=do_zip).pack(side="left")
        ttk.Button(row, text=t("btn_open_folder"),
                   command=do_open).pack(side="left", padx=8)
        ttk.Button(row, text=t("install"), command=lambda: (close(), self.install())
                   ).pack(side="left")
        ttk.Button(row, text=t("btn_close"), command=close).pack(side="right")
        dlg.bind("<Escape>", lambda e: close())
        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 3
        dlg.geometry("+%d+%d" % (max(0, x), max(0, y)))
        dlg.grab_set()
        dlg.focus_set()

    def _ensure_built(self, then):
        """Zip/Copy: gebaut und aktuell? Sonst anbieten, erst zu bauen."""
        path = self.built_path
        if not path or not os.path.isdir(path):
            if self.clips:
                if messagebox.askyesno(t("dlg_nobuild_t"), t("dlg_rebuild")):
                    self.start_build(then=then)
            else:
                messagebox.showinfo(t("dlg_nobuild_t"), t("dlg_nobuild"))
            return False
        if self.dirty:
            if messagebox.askyesno(t("dlg_rebuild_t"), t("dlg_rebuild")):
                self.start_build(then=then)
                return False
        return True

    def zip_pack(self):
        if not self._ensure_built(self.zip_pack):
            return
        path = self.built_path
        if not self.built_dub:
            messagebox.showinfo(t("zip"), t("dlg_voice_zip"))
            return

        def work():
            self._set_status(t("st_zip"), None)
            self._zip_path = pc.zip_pack(path)
            self._set_status(t("st_zipped", self._zip_path), 100)

        def done():
            z = getattr(self, "_zip_path", None)
            if z:
                self._log(t("st_zipped", z))
                if messagebox.askyesno(t("dlg_done_t"), t("dlg_zip_done", z)):
                    self._open_folder(os.path.dirname(z))
        self._bg(work, on_done=done, what=t("zip"))

    def install(self):
        if not self._ensure_built(self.install):
            return
        path = self.built_path
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
            "src_mode": self.src_mode.get(),
            "last_url": self.url_var.get(),
            "t_start": self.t_start.get(),
            "t_end": self.t_end.get(),
            "separate": self.sep_var.get(),
            "sens": float(self.sens.get()),
            "maxlen": float(self.maxlen.get()),
            "pack_name": self.pack_name.get(),
            "author": self.author.get(),
            "is_dub": self.is_dub.get(),
            "vheight": self.vheight.get(),
            "target_dir": self.target_dir.get(),
            "log_open": self.log_open,
        })
        try:
            if self.state() == "normal":
                self.cfg["geometry"] = self.geometry()
        except Exception:
            pass
        save_cfg(self.cfg)

    def destroy(self):
        for attr in ("_pump_id", "_upd_id"):
            try:
                if getattr(self, attr, None):
                    self.after_cancel(getattr(self, attr))
            except Exception:
                pass
        self._pump_id = None
        super().destroy()

    def _on_close(self):
        if self.busy:
            if not messagebox.askyesno(t("dlg_abort_t"),
                                       t("dlg_abort", self.busy_what or "?")):
                return
            pc.cancel()
        elif self.clips and self.dirty:
            if not messagebox.askyesno(t("dlg_unsaved_t"), t("dlg_unsaved")):
                return
        self._save_cfg()
        self._stop_play()
        pc.cancel()
        shutil.rmtree(self.work, ignore_errors=True)
        try:
            if self._logfile:
                self._logfile.close()
        except Exception:
            pass
        self.destroy()

    # ---- Von/Bis leeren, wenn ein anderer Link kommt / clear span on new URL
    def _url_span_guard(self):
        self._span_url = self.url_var.get().strip()

        def changed(*_a):
            cur = self.url_var.get().strip()
            if cur == self._span_url:
                return
            if self.src_mode.get() == "url" and self._span_url and \
                    (self.t_start.get().strip() or self.t_end.get().strip()):
                self.t_start.set("")
                self.t_end.set("")
            self._span_url = cur
        try:
            self.url_var.trace_add("write", changed)
        except Exception:
            pass


def _main():
    try:
        app = App()
    except Exception:
        # Schon der Start ging schief: wenigstens sagen, warum.
        # Even the start failed: at least say why.
        err = traceback.format_exc()
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("DubForge", err[-1500:])
        except Exception:
            pass
        raise
    app.mainloop()


if __name__ == "__main__":
    _main()
