#!/usr/bin/env python3
"""Check a rendered demo video against its timeline before you send it.

    python verify_video.py --video demo.mp4 --template renderer --name my-demo [--manifest manifest.json] [--out DIR] [--transcribe]

Checks  duration == timeline frames / fps | 1920x1080 | audio stream present | first speech lands where the timeline says
        (silencedetect) | optional: re-transcribes the audio with faster-whisper and compares each scene with its spoken text.
Writes  <video folder>/verify/contact-sheet.png: frames from the intro, the middle of every scene and the outro - LOOK at it (clipped text, personal
        data, wrong crop, cursor off target).
Exit code 1 if a hard check fails.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_json  # noqa: E402


def probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffprobe failed: " + r.stderr[-300:])
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--out", help="output folder (default: <video folder>/verify)")
    ap.add_argument("--transcribe", action="store_true", help="re-transcribe the audio with faster-whisper (pip install faster-whisper)")
    a = ap.parse_args()
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        sys.exit("ffmpeg/ffprobe are required")
    tl = load_json(Path(a.template) / "public" / a.name / "timeline.json")
    if not tl:
        sys.exit("timeline.json not found")
    out = Path(a.out) if a.out else Path(a.video).resolve().parent / "verify"
    out.mkdir(parents=True, exist_ok=True)
    fps = tl["fps"]
    fails, notes = [], []

    info = probe(a.video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    exp = tl["totalFrames"] / fps
    ok = abs(dur - exp) < 0.15
    print(f"[{'PASS' if ok else 'FAIL'}] duration {dur:.2f}s (expected {exp:.2f}s)")
    if not ok:
        fails.append("duration")
    ok = bool(v) and v["width"] == tl["width"] and v["height"] == tl["height"]
    print(f"[{'PASS' if ok else 'FAIL'}] resolution {v['width']}x{v['height']}" if v else "[FAIL] no video stream")
    if not ok:
        fails.append("resolution")
    want_audio = bool(tl["audio"]["narration"] or tl["audio"]["music"])
    ok = bool(au) or not want_audio
    print(f"[{'PASS' if ok else 'FAIL'}] audio stream {'present (' + au['codec_name'] + ')' if au else 'absent'}")
    if not ok:
        fails.append("audio")

    if au and tl["audio"]["narration"]:
        r = subprocess.run(["ffmpeg", "-i", str(a.video), "-vn", "-af", "silencedetect=noise=-35dB:d=0.5", "-f", "null", "-"], capture_output=True, text=True)
        ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
        starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
        first_scene = tl["scenes"][0]
        first_sent = next((c for c in tl["captions"]), None)
        if first_sent:
            expect = (tl["introFrames"] + first_sent["words"][0]["start"]) / fps
            # first speech = first silence_end after the intro (or t=0 if audio starts with sound after the intro)
            cand = [e for e in ends if e >= tl["introFrames"] / fps - 0.2]
            got = cand[0] if cand else None
            if got is None:
                notes.append("could not find the start of speech with silencedetect")
            else:
                ok = abs(got - expect) < 0.25
                print(f"[{'PASS' if ok else 'WARN'}] first speech at {got:.2f}s (timeline says ~{expect:.2f}s)")
                if not ok:
                    notes.append("first-speech offset > 0.25 s: check audio/intro alignment")
        _ = (starts, first_scene)

    # contact sheet ---------------------------------------------------------------
    stamps = []
    if tl["introFrames"]:
        stamps.append(("intro", tl["introFrames"] * 0.55 / fps))
    for s in tl["scenes"]:
        stamps.append((s["id"], (tl["introFrames"] + s["start"] + s["duration"] * 0.6) / fps))
    if tl["outroFrames"]:
        stamps.append(("outro", (tl["totalFrames"] - tl["outroFrames"] * 0.35) / fps))
    from PIL import Image, ImageDraw

    thumbs = []
    for name, t in stamps:
        p = out / f"{name}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(a.video), "-frames:v", "1", "-vf", "scale=640:-1", str(p)], check=False)
        if p.exists():
            thumbs.append((name, t, Image.open(p)))
    cols = 3
    sheet = Image.new("RGB", (cols * 640, -(-len(thumbs) // cols) * 384), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, (name, t, im) in enumerate(thumbs):
        x, y = (i % cols) * 640, (i // cols) * 384
        sheet.paste(im, (x, y + 24))
        d.text((x + 6, y + 6), f"{name} @ {t:.1f}s", fill=(255, 255, 255))
    sheet.save(out / "contact-sheet.png")
    print("wrote", out / "contact-sheet.png", "- look at it")

    if a.transcribe and au:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            notes.append("faster-whisper not installed: skipped the transcript check")
        else:
            wav = out / "audio.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a.video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
            import numpy as np
            import wave

            with wave.open(str(wav)) as w:
                x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768
            segs, _ = WhisperModel("small.en", device="cpu", compute_type="int8").transcribe(x, language="en", word_timestamps=True, condition_on_previous_text=False)
            words = [(w.word.strip(), w.start) for s in segs for w in s.words]
            say = {}
            if a.manifest:
                m = load_json(a.manifest)
                for sc in m["scenes"]:
                    say[sc["id"]] = " ".join(s.get("say") or s["caption"] for s in sc.get("sentences", []))
            norm = lambda t: re.sub(r"[^a-z0-9 ]", "", t.lower())  # noqa: E731
            for s in tl["scenes"]:
                t0 = (tl["introFrames"] + s["start"]) / fps
                t1 = t0 + s["duration"] / fps
                heard = norm(" ".join(w for w, t in words if t0 - 0.2 <= t < t1))
                if s["id"] in say:
                    ratio = SequenceMatcher(None, norm(say[s["id"]]), heard).ratio()
                    flag = "ok  " if ratio > 0.8 else "CHECK"
                    print(f"[{flag}] {s['id']}: transcript similarity {ratio:.2f}  heard: {heard[:90]}")
                else:
                    print(f"       {s['id']}: heard: {heard[:90]}")
            print("Brand terms and acronyms are the usual mismatches - a low score there can be a whisper mishearing, not a bad voice line. Ask the user to listen to flagged scenes.")

    for n in notes:
        print("NOTE:", n)
    print("\nRESULT:", "FAIL (" + ", ".join(fails) + ")" if fails else "all hard checks passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
