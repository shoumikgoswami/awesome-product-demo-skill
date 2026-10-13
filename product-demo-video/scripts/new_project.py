#!/usr/bin/env python3
"""Start a demo-video project folder from screenshots (and optionally a script and a logo).

    python new_project.py --name my-demo --screens path/to/screenshots [--script script.txt] [--logo logo.png] [--product "Acme"] [--root .]

Creates <root>/<name>/ with screenshots/ (copies - your originals are never touched), audio/, optional script.txt and logo, theme.json
(brand colours extracted automatically), inspect/ (contact sheet + gridded copies) and a manifest.json skeleton.
With --script the skeleton already contains the narration, split into sentences and mapped to screenshots.
Without it, scenes are created from the screenshots in order with empty narration, ready for the script to be written.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _lib import IMG_EXT, natural_key, save_json  # noqa: E402


def run(script, *args):
    r = subprocess.run([sys.executable, str(HERE / script), *map(str, args)], text=True, capture_output=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip(), file=sys.stderr)
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--screens", required=True, nargs="+", help="a folder, or several image files")
    ap.add_argument("--script")
    ap.add_argument("--logo")
    ap.add_argument("--product", default="")
    ap.add_argument("--root", default=".")
    ap.add_argument("--mode", default="auto", choices=["auto", "dark", "light"])
    ap.add_argument("--font", default="inter")
    a = ap.parse_args()

    V = Path(a.root) / a.name
    (V / "screenshots").mkdir(parents=True, exist_ok=True)
    (V / "audio").mkdir(exist_ok=True)
    srcs = []
    for s in a.screens:
        p = Path(s)
        srcs += [f for f in p.iterdir() if f.suffix.lower() in IMG_EXT] if p.is_dir() else [p]
    srcs = sorted(srcs, key=lambda f: natural_key(f.name))
    if not srcs:
        sys.exit("no screenshots found")
    for f in srcs:
        shutil.copyfile(f, V / "screenshots" / f.name)
    logo_name = None
    if a.logo:
        shutil.copyfile(a.logo, V / Path(a.logo).name)
        logo_name = Path(a.logo).name
    print(f"project: {V}  ({len(srcs)} screenshots)\n")

    run("inspect_screens.py", "--screens", V / "screenshots", "--out", V / "inspect")
    print()
    brand_args = ["--screens", V / "screenshots", "--product", a.product, "--mode", a.mode, "--font", a.font, "--out", V / "theme.json"]
    if logo_name:
        brand_args += ["--logo", V / logo_name]
    run("extract_brand.py", *brand_args)
    print()

    if a.script:
        shutil.copyfile(a.script, V / "script.txt")
        run("parse_script.py", "--script", V / "script.txt", "--screens", V / "screenshots", "--out", V / "manifest.json", "--product", a.product)
    else:
        scenes = [{"id": f"s{i:02d}", "image": f.name, "sentences": []} for i, f in enumerate(srcs, 1)]
        save_json(V / "manifest.json", {
            "title": a.name, "product": a.product, "voice": "Sofia", "fps": 30, "stageLabel": "Product tour",
            "_notes": ["No script yet: write the narration into each scene's sentences (id + caption), one sentence per entry."],
            "scenes": scenes,
        })
        print("wrote manifest.json with empty narration (no --script given)")
    if logo_name:
        m = __import__("json").loads((V / "manifest.json").read_text(encoding="utf-8"))
        m["logo"] = logo_name
        save_json(V / "manifest.json", m)
    print(f"\nnext: look at {V / 'inspect' / 'contact-sheet.png'} and {V / 'brand-swatches.png'}, then edit {V / 'manifest.json'}")


if __name__ == "__main__":
    main()
