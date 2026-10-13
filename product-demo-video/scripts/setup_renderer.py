#!/usr/bin/env python3
"""Copy the Remotion template into your workspace and install it (one time).

    python setup_renderer.py [--dest renderer]

Needs Node.js 18+ and ffmpeg on PATH. Creates <dest>/ (package.json, src/, ...), runs `npm install` and copies the bundled fonts
into <dest>/public/fonts so renders never touch the network. Re-running is safe: it only fills in what is missing.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "remotion-template"
SKIP = {"node_modules", "out", ".git"}


def run(cmd, cwd):
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", default="renderer")
    ap.add_argument("--no-install", action="store_true")
    a = ap.parse_args()
    dest = Path(a.dest).resolve()

    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        sys.exit("Node.js 18+ is required (https://nodejs.org). Install it, reopen the terminal, and run this again.")
    ver = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    if int(ver.lstrip("v").split(".")[0]) < 18:
        sys.exit(f"Node {ver} is too old; Remotion needs 18+.")
    if not shutil.which("ffmpeg"):
        print("WARNING: ffmpeg not found on PATH. It is needed for loudness-normalising the narration and for verify_video.py.")

    for src in TEMPLATE.rglob("*"):
        rel = src.relative_to(TEMPLATE)
        if SKIP & set(rel.parts) or (rel.parts and rel.parts[0] == "public" and len(rel.parts) > 1 and rel.parts[1] != "fonts"):
            continue
        dst = dest / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif not dst.exists() or rel.parts[0] == "src" or rel.name in {"package.json", "tsconfig.json", "remotion.config.ts"}:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)  # template code is always refreshed; user content (public/<video>) is never touched
    (dest / "public").mkdir(exist_ok=True)

    if not a.no_install:
        if not (dest / "node_modules").exists():
            run([npm, "install", "--no-audit", "--no-fund"], dest)
        run([node, "scripts/setup-fonts.mjs"], dest)
    print(f"\nrenderer ready at {dest}")


if __name__ == "__main__":
    main()
