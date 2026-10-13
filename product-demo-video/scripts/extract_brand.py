#!/usr/bin/env python3
"""Derive a video theme (brand colours, light/dark mode, text colours) from screenshots and an optional logo.

    python extract_brand.py --screens screenshots/ [--logo logo.png] [--mode auto|dark|light] [--primary "#hex"] [--out theme.json]

Writes theme.json (the colours the Remotion template uses) and brand-swatches.png (look at it before trusting the result).
Heuristic, not magic: it finds the most common *vivid* colours in the UI (buttons, links, charts, logo), so always sanity-check
the swatches. Override anything with --primary / --accent2 / --base, or edit theme.json by hand.
"""
from __future__ import annotations

import argparse
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from _lib import IMG_EXT, contrast, hex_hsv, hex_to_rgb, hsv_hex, natural_key, rgb_to_hex, save_json  # noqa: E402


def load_pixels(path: Path, width=200):
    im = Image.open(path)
    has_alpha = im.mode in ("RGBA", "LA", "P") and "A" in im.convert("RGBA").getbands()
    im = im.convert("RGBA")
    w, h = im.size
    im = im.resize((width, max(1, int(h * width / w))), Image.LANCZOS)
    a = np.asarray(im).reshape(-1, 4).astype("float32")
    if has_alpha:
        a = a[a[:, 3] > 200]
    return a[:, :3] / 255.0


def hsv_arr(rgb):
    mx, mn = rgb.max(1), rgb.min(1)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    h = np.zeros_like(mx)
    m = d > 1e-9
    rc = np.where(m & (mx == r), ((g - b) / np.maximum(d, 1e-9)) % 6, 0)
    gc = np.where(m & (mx == g), (b - r) / np.maximum(d, 1e-9) + 2, 0)
    bc = np.where(m & (mx == b), (r - g) / np.maximum(d, 1e-9) + 4, 0)
    h = (rc + gc + bc) / 6.0
    return h % 1.0, s, mx


def top_clusters(rgb, w, k=6, hue_bins=24):
    """Bucket pixels by hue (and coarse saturation/value) and return weighted-mean colours, heaviest first."""
    h, s, v = hsv_arr(rgb)
    key = (np.floor(h * hue_bins).astype(int) * 16 + np.floor(s * 3.99).astype(int) * 4 + np.floor(v * 3.99).astype(int))
    out = {}
    for kk in np.unique(key):
        m = key == kk
        wt = w[m].sum()
        col = (rgb[m] * w[m, None]).sum(0) / wt
        out[int(kk)] = (float(wt), col, float(h[m].mean()))
    items = sorted(out.values(), key=lambda t: -t[0])
    picked = []
    for wt, col, hh in items:
        hexc = rgb_to_hex(col * 255)
        if all(abs(((hh - p[2] + 0.5) % 1) - 0.5) > 0.06 or abs(hex_hsv(hexc)[2] - hex_hsv(p[1])[2]) > 0.3 for p in picked):
            picked.append((wt, hexc, hh))
        if len(picked) >= k:
            break
    return picked


def ensure_contrast(color: str, bg: str, want=3.2):
    """Nudge the colour's value until it reads against bg (keeps hue/saturation)."""
    h, s, v = hex_hsv(color)
    dark_bg = hex_hsv(bg)[2] < 0.5
    for _ in range(40):
        c = hsv_hex(h, s, v)
        if contrast(c, bg) >= want:
            return c
        v = min(1.0, v + 0.03) if dark_bg else max(0.0, v - 0.03)
        if dark_bg and v >= 1.0:
            s = max(0.0, s - 0.04)
    return hsv_hex(h, s, v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--screens", required=True, help="folder with screenshots (or a single image)")
    ap.add_argument("--logo", help="logo image (PNG with transparency is best); weighted heavily")
    ap.add_argument("--mode", default="auto", choices=["auto", "dark", "light"], help="video background mode (auto = dark unless the brand is very light)")
    ap.add_argument("--product", default="", help="product name stored in the theme")
    ap.add_argument("--primary", help="force the accent colour, e.g. '#EE8F26'")
    ap.add_argument("--accent2", help="force the secondary accent")
    ap.add_argument("--base", help="force the base/background hue colour (dark brand colour, e.g. navy)")
    ap.add_argument("--font", default="inter", choices=["inter", "poppins", "manrope", "dm-sans", "plus-jakarta-sans", "space-grotesk"])
    ap.add_argument("--out", default="theme.json")
    a = ap.parse_args()

    p = Path(a.screens)
    files = [p] if p.is_file() else sorted([f for f in p.iterdir() if f.suffix.lower() in IMG_EXT], key=lambda f: natural_key(f.name))
    if not files:
        sys.exit("no screenshots found")

    pix, wts = [], []
    for f in files:
        px = load_pixels(f)
        pix.append(px)
        wts.append(np.ones(len(px), dtype="float32"))
    logo_px = None
    if a.logo:
        logo_px = load_pixels(Path(a.logo), 120)
        # Logo pixels count 6x as much as an average screenshot's whole area share.
        boost = 6.0 * sum(len(x) for x in pix) / max(1, len(logo_px)) / len(files)
        pix.append(logo_px)
        wts.append(np.full(len(logo_px), boost, dtype="float32"))
    rgb = np.concatenate(pix)
    w = np.concatenate(wts)

    h, s, v = hsv_arr(rgb)
    mean_lum = float((rgb @ np.array([0.2126, 0.7152, 0.0722])).mean())

    vivid = (s > 0.38) & (v > 0.38)
    dark_brand = (s > 0.25) & (v < 0.42) & (v > 0.08)
    vivid_clusters = top_clusters(rgb[vivid], w[vivid]) if vivid.sum() > 30 else []
    dark_clusters = top_clusters(rgb[dark_brand], w[dark_brand], k=3) if dark_brand.sum() > 30 else []

    notes, confidence = [], "high"
    if a.primary:
        accent = a.primary
    elif vivid_clusters:
        accent = vivid_clusters[0][1]
    else:
        accent, confidence = "#3b82f6", "low"
        notes.append("No vivid brand colour found in the screenshots (mostly greyscale UI). Defaulted the accent to blue - pass --primary with the real brand colour.")

    ah = hex_hsv(accent)[0]
    accent2 = a.accent2
    if not accent2:
        for wt, c, hh in vivid_clusters[1:]:
            if abs(((hh - ah + 0.5) % 1) - 0.5) > 0.08 and wt > 0.12 * vivid_clusters[0][0]:
                accent2 = c
                break
    if not accent2:
        accent2 = hsv_hex(ah + 0.08, 0.55, 0.95)
        notes.append("Secondary accent derived from the primary (no second brand colour found).")

    base_src = a.base or (dark_clusters[0][1] if dark_clusters and dark_clusters[0][0] > 0.15 * (vivid_clusters[0][0] if vivid_clusters else 1) else None)
    bh = hex_hsv(base_src)[0] if base_src else ah
    bs = min(0.6, max(0.3, hex_hsv(base_src)[1])) if base_src else 0.55

    mode = a.mode
    if mode == "auto":
        mode = "dark"
        if hex_hsv(accent)[2] < 0.4 and contrast(accent, "#101522") < 2.0:
            mode = "light"
    if mode == "dark":
        deep, bg, light = hsv_hex(bh, bs, 0.14), hsv_hex(bh, bs * 0.95, 0.22), hsv_hex(bh, bs * 0.85, 0.32)
        text, muted, card = "#ffffff", "#c3cad8", "#ffffff"
    else:
        deep, bg, light = hsv_hex(bh, 0.05, 0.99), hsv_hex(bh, 0.08, 0.95), hsv_hex(bh, 0.12, 0.90)
        text, muted, card = hsv_hex(bh, 0.55, 0.16), hsv_hex(bh, 0.3, 0.38), "#ffffff"

    accent = ensure_contrast(accent, bg)
    accent2 = ensure_contrast(accent2, bg)
    on_accent = "#ffffff" if contrast("#ffffff", accent) >= contrast("#111827", accent) else "#111827"

    theme = {
        "product": a.product,
        "mode": mode,
        "font": a.font,
        "logo": None,
        "colors": {
            "bgDeep": deep,
            "bg": bg,
            "bgLight": light,
            "accent": accent,
            "accent2": accent2,
            "text": text,
            "textMuted": muted,
            "onAccent": on_accent,
            "card": card,
        },
        "_meta": {
            "confidence": confidence,
            "screens_mean_luminance": round(mean_lum, 3),
            "vivid_candidates": [c for _, c, _ in vivid_clusters],
            "dark_candidates": [c for _, c, _ in dark_clusters],
            "notes": notes,
        },
    }
    save_json(a.out, theme)

    # Swatch preview ------------------------------------------------------------
    cols = [("bgDeep", deep), ("bg", bg), ("bgLight", light), ("accent", accent), ("accent2", accent2), ("text", text), ("onAccent", on_accent)]
    cols += [(f"cand{i}", c) for i, (_, c, _) in enumerate(vivid_clusters[:4])]
    im = Image.new("RGB", (140 * len(cols), 190), bg)
    d = ImageDraw.Draw(im)
    for i, (n, c) in enumerate(cols):
        d.rectangle([i * 140 + 8, 8, i * 140 + 132, 130], fill=c, outline="#888888")
        d.text((i * 140 + 10, 140), f"{n}\n{c}", fill=text)
    sw = Path(a.out).with_name("brand-swatches.png")
    im.save(sw)

    print(f"mode={mode} accent={accent} accent2={accent2} bg={bg} confidence={confidence}")
    for n in notes:
        print("NOTE:", n)
    print(f"wrote {a.out} and {sw}")


if __name__ == "__main__":
    main()
