#!/usr/bin/env python3
"""Look at a screenshot set before planning: sizes, aspect-ratio mix, a contact sheet, and gridded copies for reading coordinates.

    python inspect_screens.py --screens screenshots/ --out inspect/

Writes  inspect/contact-sheet.png          all screenshots, numbered
        inspect/grid/<name>.png            each screenshot with a 10% grid and labelled fractions (read focus x/y/w/h off these)
Coordinates in the manifest are FRACTIONS of the screenshot: x,y = top-left of the box, w,h = its size, all 0-1.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from _lib import IMG_EXT, natural_key  # noqa: E402


def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--screens", required=True)
    ap.add_argument("--out", default="inspect")
    ap.add_argument("--grid-width", type=int, default=1400, help="width of the gridded copies")
    a = ap.parse_args()
    files = sorted([f for f in Path(a.screens).iterdir() if f.suffix.lower() in IMG_EXT], key=lambda f: natural_key(f.name))
    if not files:
        sys.exit("no images found")
    out = Path(a.out)
    (out / "grid").mkdir(parents=True, exist_ok=True)
    sizes = {}
    print(f"{'#':>2}  {'file':40s} {'size':>11}  aspect")
    thumbs = []
    for i, f in enumerate(files, 1):
        with Image.open(f) as im:
            im = im.convert("RGB")
            w, h = im.size
            sizes[f.name] = (w, h)
            print(f"{i:>2}  {f.name:40s} {w:>5}x{h:<5}  {w / h:.3f}")
            t = im.copy()
            t.thumbnail((480, 300))
            thumbs.append((i, f.name, t))
            g = im.resize((a.grid_width, int(h * a.grid_width / w)))
            d = ImageDraw.Draw(g)
            fnt = font(max(12, g.width // 90))
            for k in range(1, 10):
                x, y = g.width * k / 10, g.height * k / 10
                d.line([x, 0, x, g.height], fill=(255, 0, 90), width=1)
                d.line([0, y, g.width, y], fill=(255, 0, 90), width=1)
                d.text((x + 3, 2), f"{k / 10:.1f}", fill=(255, 0, 90), font=fnt)
                d.text((3, y + 2), f"{k / 10:.1f}", fill=(255, 0, 90), font=fnt)
            g.save(out / "grid" / f"{f.stem}.png")
    cols = 3
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * 500, rows * 340), (30, 30, 36))
    d = ImageDraw.Draw(sheet)
    for n, (i, name, t) in enumerate(thumbs):
        x, y = (n % cols) * 500 + 10, (n // cols) * 340 + 30
        sheet.paste(t, (x, y))
        d.text((x, y - 22), f"{i}. {name}", fill=(255, 255, 255), font=font(15))
    sheet.save(out / "contact-sheet.png")
    kinds = {round(w / h, 2) for w, h in sizes.values()}
    print()
    if len(kinds) > 1:
        print(f"NOTE: {len(kinds)} different aspect ratios {sorted(kinds)} - the card follows the most common one; others are letterboxed over a blurred copy.")
    if len({s for s in sizes.values()}) > 1:
        print("NOTE: sizes differ. Fine for rendering, but consistent captures look better (same browser window size, same zoom).")
    small = [n for n, (w, h) in sizes.items() if w < 1280]
    if small:
        print(f"WARNING: low resolution (<1280 px wide): {', '.join(small)}. They will look soft when zoomed in; recapture at 1920 px wide or larger if possible.")
    print(f"wrote {out / 'contact-sheet.png'} and {out / 'grid'}/")


if __name__ == "__main__":
    main()
