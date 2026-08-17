# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **Listening to a clip plays a little around it.** Half a second before and
  half a second after, so you hear whether the line is cut off at either
  edge instead of a blip that starts and ends mid-word. The switch
  **Run-up ±0.5 s** next to the play button turns it off, and then playback
  starts where the cursor stands: inside the clip it runs to the clip's end,
  outside it plays eight seconds from there. The setting is remembered.
- **Space in the subtitle field plays the clip** as long as nothing has been
  typed - which is exactly the state right after Enter jumped to the next
  clip. Pressing it again stops playback. As soon as there is text in the
  field it is an ordinary space again, so the run through a scene is Enter,
  Space to listen, type, Enter. It also protects the caption you just
  jumped to: it was fully selected, so a space used to wipe it.

### Fixed

- **The test run could stop and wait for a click.** Reopening a pack without
  a backing track asks whether to separate the vocals, and with Demucs
  installed that dialog appeared in the middle of the automated run - who
  saw it depended on whether the Demucs probe had finished yet. The GUI
  tests now replace `messagebox`, `filedialog` and `simpledialog` with stubs
  that answer at once and record what was asked, and the full run checks
  that this very question is asked.

## [1.2.3] - 2026-08-16

### Changed

- **The setup and the starters speak one language, not both.** They ask
  Windows which language it is set to (`Control Panel\International`), and a
  language already chosen in DubForge or DubStage beats that - so the window
  you watch during the install is either German or English, never every line
  twice. The starter hands its answer over to `Setup.bat`, so the two agree.
  Anything other than a German system reads as English.
- **DubForge and DubStage open in the system language** on the very first
  start instead of always in German. As soon as a language is picked in the
  window, that choice is remembered and wins from then on.

## [1.2.2] - 2026-08-16

### Changed

- **Setting up is no longer a separate step.** `Start DubForge.bat` and
  `Start DubStage.bat` check before they launch: no Python, missing packages
  or no ffmpeg and they run `Setup.bat` themselves, then start the tool. A
  marker in `tools\.setup-done` means an installed copy still starts
  instantly - the check only runs while that marker is missing, and `tools`
  survives an update. Running out of ideas is now said in one line ("run
  Setup.bat, then start again") instead of a dead end, and the setup is never
  run twice in a row.

### Added

- **Desktop shortcuts.** At the end of `Setup.bat`, one question puts
  DubForge and DubStage on the desktop.

## [1.2.1] - 2026-08-16

### Fixed

- **Building from an MP3 (or any audio-only source) failed** with
  "Could not find tag for codec h264": ffprobe reported the file's embedded
  cover art as a video stream, and ffmpeg then tried to encode that one JPEG
  as the scene. Cover art and other still-image "streams" are no longer
  counted as video. Instead, an audio-only source now gets a **still-image
  video** built for it - the cover art if there is one, otherwise a dark card
  - so the pack still plays in DubStage and DisDubs.
- **"Separate vocals now"** (Detect menu) runs Demucs on the current session
  - clips stay, the waveform switches to the vocals, and the pack gets its
  `_backing_track`. Offered automatically after reopening a pack that has no
  backing track.
- **"Reopen a pack" accepts packs without a video** (clip packs built with
  "With video" unticked): it asks for the original source file and rebuilds
  the session from it, so a project saved that way is not lost.

## [1.2.0] - 2026-08-16

The fixes from a five-lens product review (UX, correctness, DisDubs
compatibility, robustness, onboarding) - 48 verified findings, worked
through top to bottom before the first external test. Pack format
unchanged.

### Added

- **Cancel.** Every background job (download, Demucs, build, zip) can be
  aborted from a Cancel button next to the progress bar; the child processes
  are killed including their children (`taskkill /T`), and closing the window
  during a job asks first instead of orphaning ffmpeg. The bar shows real
  percentages from yt-dlp, ffmpeg (`time=` against the known duration) and
  Demucs' tqdm output, and turns indeterminate while nothing is known.
- **DisDubs pre-flight check** before building: the half rule
  (`speakers × 2 > clips` -> DisDubs casts a single part), names over 40
  characters, symbol-only names, two tracks that collide after
  file-name cleaning, tracks still carrying a default name, no
  `_backing_track`, no picture, scenes over 3:00 (free-server limit), clips
  ending less than 1 s into the next (DisDubs trims those), sub-0.3 s clips,
  no subtitles at all. One dialog, only when something is flagged. The stats
  line shows live how many parts DisDubs would cast.
- **Startup tool probe** off the main thread: a warning row names missing
  ffmpeg/yt-dlp and points at Setup.bat, Analyse/Build are disabled without
  ffmpeg, the Demucs checkbox is off and disabled with "(not installed)" when
  Demucs is not importable, and a failed separation is said in the status
  line, not just the log. The ffmpeg line now reports H.264/AAC (what the
  pack actually uses) instead of Theora/Vorbis.
- **Post-build dialog** with three ways on: Zip for DisDubs, open the folder,
  copy to the target folder. Zip/Copy with unbuilt changes offer to rebuild
  first; a "built 12:03 · 8 clips" label sits by the progress bar. Voice
  packs (no video) are refused by "Zip for DisDubs" with an explanation.
- **Friendly yt-dlp errors**: "Sign in to confirm", unavailable/private,
  HTTP 403, extractor failures and network errors get a plain-language
  message; where an update usually helps, the dialog offers "Update yt-dlp
  now?".
- **Crash safety**: the message pump survives a failing callback (and logs
  it), unexpected Tk exceptions show a dialog instead of vanishing under
  pythonw, a start-up failure is shown too, and every session is teed to
  `dubforge.log` next to the program. The window title carries the version,
  `_dubforge.json` records `dubforge_version`.
- Keyboard: Esc and Ctrl+Space hints in the subtitle field, a one-line
  shortcut cheat sheet under it, Ctrl+Space plays while typing. A **Help**
  button opens the README. Preview shows "no video frame" / "select a clip"
  instead of black.
- Detection presets re-run detection immediately as long as nothing was
  edited by hand; "Detect again" now **keeps track and subtitle** of the
  clip that overlaps most, instead of dropping everything to track 1.
- From/To are cleared when a different link is pasted; a span over four
  minutes with Demucs on asks first (CPU Demucs takes 10-20 minutes for that).
- Setup.bat and the Start scripts weed out the Microsoft Store `python`
  stub, the Demucs prompt accepts Y as well as J, and error lines are echoed
  in English too.
- Tests: pre-flight rules, progress parsing, error classification, i18n
  placeholder parity across both string tables, missing-tools UI state,
  pump survival, redetect carry-over, URL span guard, cancel of a running
  job, failed analyse leaving the session intact (36 tests).

### Fixed

- **Building never destroys a pack it did not mean to.** A pack of the same
  name asks overwrite / save as `Name_2`; the build goes into `Name.building`
  and is swapped in only on success, so a failed or cancelled build leaves
  the previous pack untouched and never leaves `built_path` pointing at a
  half-written folder.
- **A failed analyse or reopen no longer leaves a half-alive session**: the
  new session is staged in its own work dir and committed on the main thread
  only on success; on failure the old clips, waveform and audio stay usable.
- Worker threads no longer mutate the clip list, tracks or duration
  directly; Tk variables are read on the main thread before a job starts.
- `trim_local` failed on audio-only sources with a time span (`-map 0:v:0`
  is now optional); `convert_video` produced an odd height that libx264
  refuses (`scale` now rounds to even).
- Right-click on the timeline saves a pending subtitle first; nudging a clip
  updates its list row in place instead of rebuilding the list; the previous
  playback frame folder is removed on the next Play; whole-track playback is
  capped at 90 s; stale `%TEMP%\dubforge_*` folders older than a day are
  swept at start and the own one on exit.
- yt-dlp lookup and version are cached, so the app starts faster and
  "Update yt-dlp" invalidates the cache.

## [1.1.0] - 2026-08-15

DubForge overhaul. The pack format is unchanged: everything DubStage and
DisDubs read is written exactly as before, and the two new files start with
`_`, which both readers skip.

### Added

- **Tracks - one per speaker.** The waveform now sits above a lane per
  speaker; clips are dragged between lanes, so overlapping lines (someone
  interrupting, two people at once) no longer fight for space on one strip.
  The track name becomes the clip's label in the file name
  (`03_Snake_5-460.wav`) - which is exactly what DisDubs' `speakersFrom` casts
  parts from, and what DubStage shows as the line's label. Rename, recolour,
  reorder and delete tracks from a right-click menu on the lane name.
- **Editing.** Drag a clip to move it (in time and across tracks), trim its
  edges, nudge with the arrow keys, split at the playhead, duplicate, delete;
  undo/redo (Ctrl+Z / Ctrl+Y) across every change; hover cursors say what a
  drag will do; the selected clip is drawn on the waveform too. Ctrl+wheel
  zooms at the mouse, the wheel alone scrolls, Home/End jump.
- **Playhead and preview.** Playback draws a moving playhead; double-clicking
  the waveform plays eight seconds from there. A frame preview next to the
  subtitle field shows who is on screen at the clip's start, and **plays the
  video while a clip plays** (a PNG sequence of the span, 10 fps, extracted
  in the background; Tk's own PNG support, no Pillow needed).
- **Playback no longer depends on ffplay.** The span is decoded to PCM in
  memory and played through `sounddevice` - the same backend DubStage uses,
  so it works wherever DubStage does. ffplay and, on Windows, `winsound` are
  fallbacks. The backend in use and any playback error are written to the
  log instead of failing silently.
- **Tests.** `tests/test_core.py` (parsing, file names, pack files, ffmpeg
  helpers) and `tests/test_app.py` (UI smoke tests plus a full run: analyse ->
  tracks -> playback -> build -> DubStage loads it -> zip -> reopen ->
  rebuild). `python -m unittest discover tests -v`; ffmpeg- and
  display-dependent tests skip themselves when those are missing.
- **Subtitle import.** From an SRT/VTT file, or fetched from YouTube with
  yt-dlp (manual subtitles preferred, automatic ones as a fallback - the
  rolling auto-caption format is collapsed to one line per cue). Cues are
  matched to clips by overlap; existing subtitles are only overwritten on
  request. The chosen "From" offset is honoured.
- **Reopen a pack.** Loads a built pack - video, backing track, clips, tracks,
  subtitles, author - for further editing. Packs from earlier DubForge
  versions open too: clips come from the file names, ends from the clip
  lengths, speakers from the labels. Rebuilding into the same folder is safe
  (the sources are copied out first) and reuses the pack's `dub_video.mp4`
  instead of re-encoding it.
- **Zip for DisDubs.** Writes `<name>.zip` with the pack folder at the top
  level, the layout the DisDubs uploader expects.
- **`_pack_info.ini`** (title, authors - the Choicer convention DisDubs reads)
  and **`_dubforge.json`** (the project: tracks, exact clip bounds, subtitles,
  source URL) are written into every pack. Both start with `_` and are
  ignored by DubStage and DisDubs.
- **Author field**, clip statistics line (count, tracks, missing subtitles,
  spoken time, same-track overlaps), a collapsible log, window geometry
  remembered, a warning before closing or reloading over unbuilt changes.

### Fixed

- The frame preview could get stuck on black: re-selecting the same clip
  cancelled the pending extraction and then returned early. Analysis and
  pack-opening threads no longer touch Tk widgets (stopping playback moved to
  the main thread).

### Changed

- **Layout.** Detection settings moved from a permanent side panel into a
  "Detect" menu; the clip inspector became a horizontal strip (frame preview,
  speaker, start/end, a wide subtitle field) above a full-width list, so the
  whole window fits a 1080p display at 125 % scaling with the log open.
- Clips no longer carry an individual name; the speaker (track) name is the
  label. `_TIMESTAMPS.txt` gained a speaker column.
- The list selection is a neutral slate instead of the accent colour, so the
  per-speaker text colours stay legible on the selected row.

### Added (merged from upstream xmrius/dubstage 1.1.0)

- **Update notice inside both tools.** (In this fork the updater checks
  `Tann2019/dubstage-DisDubs` releases, never upstream, so an update can
  never replace the fork's DubForge with the original.) On start they ask GitHub once whether a
  newer release exists — at most every six hours, and the answer is remembered
  so the banner also appears when no request is made. The banner names the new
  version, expands to show that release's changelog, and updates the tools on
  one click: the archive is downloaded, checked, the app closes, the files are
  replaced and the app starts again.
- `packs/`, `dubs/`, `tools/` and the settings files are never touched by an
  update. Only known project files are replaced, everything else in the archive
  is discarded before the swap, and the previous `.pyw`, `.py`, `.bat` and `.md`
  files are copied to a backup folder in `%TEMP%` first. A log of every step
  lands next to it.
- Guard rails on the way in: HTTPS only, GitHub hosts only, this repository
  only, a size limit on the download, no archive paths pointing outside the
  target folder, and every `.py`/`.pyw` from the archive is compiled before
  anything is replaced — a truncated download cannot leave a broken install.
- The check can be switched off by setting `"check_updates": false` in
  `dubforge_settings.json` or `dubstage_settings.json`. Nothing but the release
  information is ever requested, and nothing is sent.

### Fixed (merged from upstream xmrius/dubstage 1.1.0)

- **YouTube downloads failed with HTTP 403 on newer ffmpeg builds.** With
  `--download-sections`, yt-dlp hands the video URL to ffmpeg and lets it fetch
  the data; that request does not carry what the URL was signed for, and Google
  refuses it. DubForge now falls back to downloading the whole video with
  yt-dlp's own downloader and cutting it locally with the existing trim path —
  slower, but it works regardless of the ffmpeg build. The fast section
  download is still tried first.

- **"Update yt-dlp" updated a different yt-dlp than the one that runs.** The
  button always went through `pip` for the interpreter running DubForge, while
  the version shown — and the binary actually used for downloads — comes from
  `shutil.which`, which finds any `yt-dlp.exe` in `PATH` first. With both
  present, pip reported success and nothing changed. The button now updates
  whatever `ytdlp()` resolves to: a standalone build updates itself with `-U`,
  a pip launcher falls back to pip from *its own* installation. The startup log
  and the yt-dlp line now name the file in use, and if the version is unchanged
  after an update the dialog says so and explains why instead of claiming
  success.

- **DubForge was unusable in a non-maximised window.** The three steps were
  packed straight into the window, so anything past the bottom edge — step 3,
  "Build pack", the progress bar and the log — was simply gone, with no way to
  reach it. The content now sits in a scrollable canvas. It is stretched to the
  window as long as there is room, so a maximised window looks exactly as
  before; below that it scrolls.
- The mouse wheel scrolls the page, except over widgets that scroll or count on
  their own: the waveform still zooms, the clip list and the log scroll
  themselves and hand the wheel back to the page once they hit their end, and
  the spinbox keeps counting.
- Minimum window size lowered from 980×740 to 900×480, and both tools now open
  no taller than the screen allows. At 1180×880 DubForge did not fit on a 1080p
  display once the taskbar and title bar were subtracted — which is how the
  problem arose in the first place.
- Scrollbars were unstyled and showed up pale grey against the dark interface.


## [1.0.1] - 2026-08-11

### Added

- **yt-dlp maintenance.** DubForge reports the installed yt-dlp version and its
  age at startup, warns beyond 60 days, and offers a one-click update. The
  updater detects how yt-dlp was installed: a standalone binary in `tools/`
  updates itself with `-U`, a pip installation goes through pip. If a download
  fails and the version is older than 30 days, the log points at it as the
  likely cause — YouTube changes its delivery constantly and a stale yt-dlp is
  by far the most common reason for failures.
- **Logo** in light and dark variants (`docs/logo.png`, `docs/logo-dark.png`),
  switched automatically via `<picture>` and `prefers-color-scheme`. The dark
  variant lifts the wordmark to a light tone and the wave from `#4b24ed` to
  `#7c5cff`; on GitHub's dark background the original values reach only 1.10
  and 2.50 contrast, below the 3.0 minimum for graphics.
- **Screenshots** in the README.
- **`.gitattributes`** — LF inside the repository, CRLF on checkout for `.bat`
  and `.cmd`. Keeps `LICENSE` from showing up as fully rewritten whenever line
  endings differ between systems.

### Fixed

- **Read-only dropdowns were unreadable.** Their colours come from a ttk state
  table that `configure()` does not reach, so the light default background
  survived. Now set through `map()` with an explicit `readonly` entry, in both
  tools. The popup list is a plain Tk widget that ttk does not style at all and
  is now coloured via `option_add` — it would have stayed white.
- **Batch files had LF-only line endings.** cmd.exe handles those unreliably,
  particularly around labels and `goto`. All `.bat` files converted to CRLF and
  pinned via `.gitattributes`.
- Status text announced "converting to OGV" although MP4 has been written since
  the format switch; two dialogs still spoke of copying "into the game".

### Removed

- `Push to GitHub.bat` is no longer part of the repository. It is a maintenance
  helper, not part of the project. The push script now untracks anything that
  matches `.gitignore` but is still tracked, so the file stays on disk while
  disappearing from GitHub.

## [1.0.0] - 2026-08-10

First public release. Two Windows desktop tools, German and English interface,
switchable at runtime.

### DubForge — building packs

- Source from a YouTube link or a local file, limited to a chosen time span.
  The stream-copy cut is verified against the expected duration and re-encoded
  when it lands off target, because keyframe seeking is frequently inaccurate.
- Optional vocal separation with Demucs; falls back to the original audio when
  it is unavailable, losing only the backing track.
- Automatic clip detection from the loudness envelope, with adjustable
  sensitivity and maximum clip length. Long segments are split at their
  quietest point.
- Waveform editor: drag edges to trim, drag empty space for a new clip, split,
  rename, delete, listen. Mouse wheel zooms.
- Subtitles per clip. Enter saves and moves to the next clip, so a whole pack
  can be captioned without touching the mouse.
- Clips exported at −1 dBFS peak so that loudness does not distort the
  comparison later.
- Video written as MP4/H.264. Roughly four times faster to encode than the
  previous Theora path and about 40 % smaller.

### DubStage — recording

- Line-by-line workflow: hear the original, record over it, play your own take
  back, as often as you like. Any line can be left empty and keeps the original
  voice.
- **Comparison strip** — the original as a silhouette with your take drawn over
  it on a shared time axis, live while recording. Both curves are normalised to
  their own peak, so what you judge is timing and rhythm rather than level.
- Subtitles shown below the video, and running along as real subtitles during
  the final playback.
- Finale plays the whole scene with your recordings mixed over the backing
  track; export as MP4.
- Microphone test with level readout and playback.
- Video is split into JPEG frames once and cached instead of being decoded
  during playback, at 25 fps and 960 px. Playback timing derives each frame
  deadline from the start time rather than adding a fixed delay, which is the
  difference between a nominal 25 fps and 19 effective.

### Packs

- A pack is a plain folder. Each clip carries its start time in the file name
  (`07_MyLine_44-048.wav` = 44.048 s), subtitles live in `_captions.json`.
  No database and no binary index, so packs stay readable and hand-editable.

### Robustness

- Recording can never leave the interface stuck: button states are set before
  any drawing happens, the frame loop tolerates drawing errors, a watchdog ends
  the recording even if the loop stalls, and every phase carries a deadline
  after which the interface is released.
- Array lengths are aligned before mixing a take with the backing track.
  `int(len(x) / sr * sr)` does not reliably return `len(x)`; for roughly 8 % of
  clip lengths it lands one sample short, which previously raised mid-playback
  and froze the interface.

[Unreleased]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.2.3...HEAD
[1.2.3]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Tann2019/dubstage-DisDubs/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/xmrius/dubstage/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/xmrius/dubstage/releases/tag/v1.0.0
