#!/usr/bin/env python3
"""Render test stills or the final video with the Remotion template.

    python render.py stills --template renderer --name my-demo [--out stills] [--frames auto|10,200,640]
    python render.py video  --template renderer --name my-demo --out my-demo.mp4 [--concurrency 2] [--crf 18]

`stills auto` picks the frames worth checking (intro, each scene start/mid, every zoom landing, every transition, outro) and
writes a numbered contact sheet. Browser: set PRODUCT_DEMO_BROWSER=/path/to/chrome-or-headless_shell if Remotion cannot download
its own (restricted networks); /opt/pw-browsers (Playwright) is detected automatically.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_json  # noqa: E402


def browser_args():
    p = os.environ.get("PRODUCT_DEMO_BROWSER")
    if not p:
        hits = sorted(glob.glob("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell")) or sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
        p = hits[-1] if hits else None
    return [f"--browser-executable={p}"] if p else []


def npx():
    p = shutil.which("npx")
    if not p:
        sys.exit("npx not found - install Node.js")
    return p


def auto_frames(t):
    fps, intro, stage = t["fps"], t["introFrames"], t["stageFrames"]
    fr = []
    if intro:
        fr += [("intro-mid", intro // 2), ("intro-end", intro - 12)]
    for s in t["scenes"]:
        base = intro + s["start"]
        fr.append((f"{s['id']}-mid", base + s["duration"] // 2))
        if s["transitionFrames"]:
            fr.append((f"{s['id']}-transition", base - s["transitionFrames"] // 2))
        for k, f in enumerate(s["focus"]):
            fr.append((f"{s['id']}-focus{k + 1}", base + f["frame"] + round(0.7 * fps) + 6))
    if t["outroFrames"]:
        fr += [("outro-mid", intro + stage + t["outroFrames"] - 40), ("outro-end", intro + stage + t["outroFrames"] - 14)]
    return [(n, max(0, min(t["totalFrames"] - 1, f))) for n, f in fr]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("stills", "video"):
        p = sp.add_parser(name)
        p.add_argument("--template", required=True)
        p.add_argument("--name", required=True)
        p.add_argument("--out", default="stills" if name == "stills" else "demo.mp4")
        if name == "stills":
            p.add_argument("--frames", default="auto")
        else:
            p.add_argument("--concurrency", default="2")
            p.add_argument("--crf", default="18")
            p.add_argument("--range", help="render only frames a-b, e.g. 0-299 (for a quick check)")
    a = ap.parse_args()
    T = Path(a.template).resolve()
    tl = load_json(T / "public" / a.name / "timeline.json")
    if not tl:
        sys.exit(f"{T / 'public' / a.name / 'timeline.json'} missing - run build_timeline.py first")
    props = f"--props=public/{a.name}/props.json"
    base = [npx(), "remotion"]

    if a.cmd == "stills":
        out = Path(a.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        frames = auto_frames(tl) if a.frames == "auto" else [(f"f{f}", int(f)) for f in a.frames.split(",")]
        done = []
        for name, f in frames:
            dst = out / f"{name}-{f}.png"
            r = subprocess.run(base + ["still", "ProductDemo", str(dst), props, f"--frame={f}", *browser_args()], cwd=T, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"FAILED {name} frame {f}:\n{(r.stderr or r.stdout)[-600:]}")
                continue
            done.append((name, f, dst))
            print("still", dst.name, flush=True)
        try:
            from PIL import Image, ImageDraw

            cols = 3
            w, h = 640, 360
            sheet = Image.new("RGB", (cols * w, -(-len(done) // cols) * (h + 24)), (20, 20, 24))
            d = ImageDraw.Draw(sheet)
            for i, (name, f, p) in enumerate(done):
                im = Image.open(p).resize((w, h))
                x, y = (i % cols) * w, (i // cols) * (h + 24)
                sheet.paste(im, (x, y + 24))
                d.text((x + 6, y + 6), f"{name}  (frame {f})", fill=(255, 255, 255))
            sheet.save(out / "contact-sheet.png")
            print("wrote", out / "contact-sheet.png")
        except Exception as e:  # noqa: BLE001
            print("contact sheet skipped:", e)
    else:
        out = Path(a.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = base + ["render", "ProductDemo", str(out), props, "--codec=h264", f"--crf={a.crf}", f"--concurrency={a.concurrency}", *browser_args()]
        if a.range:
            cmd.append(f"--frames={a.range}")
        print("rendering", tl["totalFrames"], "frames ->", out, flush=True)
        sys.exit(subprocess.run(cmd, cwd=T).returncode)


if __name__ == "__main__":
    main()
