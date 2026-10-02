"""Opt-in real-model smoke check on a NEW copy of an existing pack.

Run from the project root:
  python tests/validate_pack.py packs/Test packs/Test_french_validation --language fr
Models may download on first use. This is deliberately outside unittest discovery.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import caption_pack
import dubstage_core as ds


def media_hashes(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path(folder).iterdir()
            if p.is_file() and p.suffix.lower() in ds.AUDIO_EXT + ds.VIDEO_EXT}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--language", required=True)
    args = parser.parse_args()
    shutil.copytree(args.source, args.destination)  # refuses to overwrite an existing folder
    before = media_hashes(args.destination)
    original = ds.load_pack(str(args.destination))
    started = time.monotonic()
    result = caption_pack.caption_pack(args.destination, args.language, overwrite=True,
                                      progress=lambda text, pct: print(text, flush=True))
    elapsed = round(time.monotonic() - started, 2)
    after = ds.load_pack(str(args.destination))
    assert media_hashes(args.destination) == before, "Media changed during caption generation"
    assert [(line.file, line.start) for line in original.lines] == [
        (line.file, line.start) for line in after.lines], "Clip identities or timestamps changed"
    report = {"language": args.language, "model": "large-v3", "device": "cpu",
              "elapsed_seconds": elapsed, "clips": len(after.lines),
              "captioned_clips": sum(bool(line.caption) for line in after.lines),
              "segments": result["segments"], "unrecognized_clips": result["empty"],
              "media_and_clip_timestamps_unchanged": True,
              "accuracy_review": "Text/timing require human review against the audio."}
    (args.destination / "_caption_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
