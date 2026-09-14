"""Add local captions and full-video subtitles to an existing DubStage pack."""

import argparse
import json
import math
from pathlib import Path
import sys

import dubforge_core as pc
import dubstage_core as ds
import transcription as tr


def caption_pack(folder, language, model="large-v3", device="cpu", overwrite=False,
                 progress=None):
    pack = ds.load_pack(str(folder))
    if pack is None:
        raise ValueError("Expected a DubStage pack with dub_video and timestamped audio clips.")
    existing = tr.read_existing_captions(folder)
    clips = []
    for line in pack.lines:
        duration = pc.probe_duration(line.path)
        if not math.isfinite(duration) or duration <= 0 or line.start < 0:
            raise ValueError("Invalid timing or duration: %s" % line.file)
        clips.append({"file": line.file, "start": line.start,
                      "end": line.start + duration, "caption": existing.get(line.file, "")})
    transcript = tr.transcribe(pack.video, language, model, device, progress)
    generated = tr.map_captions(transcript, clips)
    tr.apply_captions(clips, generated, overwrite=overwrite)
    captions = dict(existing)
    for clip in clips:
        if clip["caption"]:
            captions[clip["file"]] = clip["caption"]
        elif overwrite:
            captions.pop(clip["file"], None)
    outputs = tr.subtitle_outputs(transcript)
    # The playback reader also accepts per-clip text sidecars. Explicitly clear
    # a sidecar when overwrite removes a caption, or it would reappear on load.
    if overwrite:
        for clip in clips:
            sidecar = Path(folder) / (Path(clip["file"]).stem + ".txt")
            if not clip["caption"] and sidecar.is_file():
                outputs[sidecar.name] = ""
    outputs["_captions.json"] = json.dumps(captions, ensure_ascii=False, indent=2) + "\n"
    backup = tr.write_outputs(folder, outputs, backup=True)
    empty = [c["file"] for c, text in zip(clips, generated) if not text]
    return {"clips": len(clips), "empty": empty, "backup": backup,
            "segments": len(transcript.segments)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--language", required=True, help="Spoken language code, e.g. fr (French)")
    parser.add_argument("--model", choices=tr.MODELS, default="large-v3")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing clip captions")
    args = parser.parse_args(argv)
    try:
        result = caption_pack(args.pack, args.language, args.model, args.device, args.overwrite,
                              lambda message, pct: print(message, flush=True))
    except Exception as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1
    print("Saved _captions.json, dub_video.srt and dub_video.vtt for %d clips." % result["clips"])
    if result["empty"]:
        print("No recognized speech mapped to: " + ", ".join(result["empty"]))
    if result["backup"]:
        print("Previous files backed up to: %s" % result["backup"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
