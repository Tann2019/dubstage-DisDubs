# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

Nothing yet.

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

[Unreleased]: https://github.com/xmrius/dubstage/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/xmrius/dubstage/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/xmrius/dubstage/releases/tag/v1.0.0
