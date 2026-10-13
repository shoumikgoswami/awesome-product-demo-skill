#!/usr/bin/env python3
"""Fallback voice for machines without an NVIDIA GPU (macOS, Linux, Windows without CUDA): Microsoft Edge neural voices via `edge-tts`.

    pip install edge-tts          (needs internet; also needs ffmpeg on PATH)
    tts_edge.py --manifest M --audio-dir DIR [--voice en-US-AriaNeural] [--pron P] [--only s01a,s02b]

Writes DIR/<sentence id>.wav (22.05 kHz mono PCM16) and DIR/durations.json - the same files `voice_job.py collect` produces, so
build_timeline.py works unchanged. The local Magpie server (assets/tts) sounds more natural and works offline; this is the easy option.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_json  # noqa: E402
from voice_job import pron_table, say_text, sentences  # noqa: E402


async def synth(text, voice, path, rate):
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--audio-dir", required=True)
    ap.add_argument("--voice", default="en-US-AriaNeural")
    ap.add_argument("--rate", default="+0%", help="e.g. -8%% for slower, +10%% for faster")
    ap.add_argument("--pron")
    ap.add_argument("--only")
    a = ap.parse_args()
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        sys.exit("pip install edge-tts first")
    m = load_json(a.manifest)
    table = pron_table(a.pron, m, a.manifest)
    only = set(a.only.split(",")) if a.only else None
    out = Path(a.audio_dir)
    out.mkdir(parents=True, exist_ok=True)
    durs = load_json(out / "durations.json", {}) or {}
    with tempfile.TemporaryDirectory() as td:
        for _, s in sentences(m):
            if only is not None and s["id"] not in only:
                continue
            mp3 = Path(td) / f"{s['id']}.mp3"
            asyncio.run(synth(say_text(s, table), a.voice, mp3, a.rate))
            wav = out / f"{s['id']}.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "22050", "-sample_fmt", "s16", str(wav)], check=True)
            with wave.open(str(wav), "rb") as w:
                durs[s["id"]] = round(w.getnframes() / w.getframerate(), 3)
            print("voiced", s["id"], durs[s["id"]])
    (out / "durations.json").write_text(json.dumps(durs, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
