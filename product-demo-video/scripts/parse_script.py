#!/usr/bin/env python3
"""Turn a plain-text narration script into a manifest skeleton and map its scenes to screenshots.

    python parse_script.py --script script.txt --screens screenshots/ --out manifest.json [--product "Acme"]

Script format (everything optional except the narration):
    Title: Acme - Getting started          <- header lines (Title / Product / Voice) at the top
    # Overview                               <- '# ' starts a chapter (name it "Step ..." or anything; Overview/Intro/Next steps are un-numbered)
    ## Scene: The dashboard                  <- '## ' starts a scene (the text after it is just a label); without '##', each blank-line-separated paragraph is a scene
    This is the Acme dashboard. Everything you need is one click away.
    [img: 01-dashboard.png]                  <- pin a screenshot (otherwise scenes map to screenshots in order)
    [zoom: Everything you need]              <- zoom to the element named at that phrase (coordinates are filled in afterwards, by looking at the screenshot)
    [click: one click]                       <- same, with a cursor click
    [chip: Settings > Integrations]          <- breadcrumb / key-claim pill
    [blur: 0,0,0.16,1]                       <- privacy blur box (x,y,w,h as fractions)
    [transition: push|crossfade|none]  [seconds: 4]  [clip: demo.mp4 0-5]

One sentence = one voice chunk (keep them under ~25 words); paragraphs are split into sentences automatically.
Prints a mapping table - CHECK IT: when the scene count and screenshot count differ, mapping falls back to order and says so.
"""
from __future__ import annotations

import argparse
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import IMG_EXT, natural_key, save_json, split_sentences  # noqa: E402

DIRECTIVE = re.compile(r"\[(img|zoom|click|chip|blur|transition|seconds|clip)\s*:\s*([^\]]*)\]", re.I)
UNNUMBERED = re.compile(r"^(overview|intro|introduction|what'?s next|next steps?|summary|recap|wrap[- ]?up|conclusion)", re.I)


def sid(scene_no, k):
    return f"s{scene_no:02d}{string.ascii_lowercase[k]}" if k < 26 else f"s{scene_no:02d}x{k}"


def parse(text):
    meta, chapters, blocks = {}, [], []
    cur_chapter = None
    cur = None
    lines = text.splitlines()
    i = 0
    while i < len(lines) and re.match(r"^(title|product|voice)\s*:", lines[i], re.I):
        k, v = lines[i].split(":", 1)
        meta[k.strip().lower()] = v.strip()
        i += 1
    explicit = any(l.startswith("## ") for l in lines)

    def flush():
        nonlocal cur
        if cur and (cur["text"].strip() or cur["dir"]):
            blocks.append(cur)
        cur = None

    def start(label=""):
        nonlocal cur
        flush()
        cur = {"label": label, "text": "", "dir": [], "chapter": cur_chapter}

    for line in lines[i:]:
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            flush()
            title = s[2:].strip()
            cur_chapter = f"c{len(chapters) + 1}"
            chapters.append({"id": cur_chapter, "title": re.sub(r"^step\s*\d+\s*[:.\-]\s*", "", title, flags=re.I), "raw": title})
            continue
        if s.startswith("## "):
            start(s[3:].strip())
            continue
        if not s:
            if not explicit:
                flush()
            continue
        if cur is None:
            start()
        for m in DIRECTIVE.finditer(s):
            cur["dir"].append((m.group(1).lower(), m.group(2).strip()))
        body = DIRECTIVE.sub("", s).strip()
        if body:
            cur["text"] += (" " if cur["text"] else "") + body
    flush()
    return meta, chapters, blocks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", required=True)
    ap.add_argument("--screens", required=True)
    ap.add_argument("--out", default="manifest.json")
    ap.add_argument("--product", default="")
    ap.add_argument("--voice", default="Sofia")
    a = ap.parse_args()

    meta, chapters, blocks = parse(Path(a.script).read_text(encoding="utf-8"))
    shots = sorted([f.name for f in Path(a.screens).iterdir() if f.suffix.lower() in IMG_EXT], key=natural_key)
    if not blocks:
        sys.exit("no scenes found in the script")

    step = 0
    for c in chapters:
        if UNNUMBERED.match(c["raw"]):
            c["step"] = None
        else:
            step += 1
            c["step"] = step
        c.pop("raw")

    pinned = {n for b in blocks for k, v in b["dir"] if k == "img" for n in [v]}
    free = [s for s in shots if s not in pinned]
    notes, scenes = [], []
    order_pos = 0
    for n, b in enumerate(blocks, 1):
        img = next((v for k, v in b["dir"] if k == "img"), None)
        clip = next((v for k, v in b["dir"] if k == "clip"), None)
        if img and img not in shots:
            notes.append(f"scene {n}: [img: {img}] is not in {a.screens}")
        if not img and not clip:
            if order_pos < len(free):
                img = free[order_pos]
                order_pos += 1
            else:
                notes.append(f"scene {n}: no screenshot left for this scene")
        sc = {"id": f"s{n:02d}"}
        if clip:
            parts = clip.split()
            c = {"src": parts[0]}
            if len(parts) > 1 and re.match(r"^[\d.]+-[\d.]+$", parts[1]):
                c["from"], c["to"] = (float(x) for x in parts[1].split("-"))
            sc["clip"] = c
        else:
            sc["image"] = img
        if b["chapter"]:
            sc["chapter"] = b["chapter"]
        sc["sentences"] = [{"id": sid(n, k), "caption": t} for k, t in enumerate(split_sentences(b["text"]))]
        focus = []
        for k, v in b["dir"]:
            if k in ("zoom", "click"):
                f = {"on": v, "zoom": 1.6, "_todo": "set x,y,w,h (fractions) by looking at the screenshot"}
                if k == "click":
                    f["click"] = True
                focus.append(f)
            elif k == "chip":
                sc["chip"] = v
            elif k == "blur":
                x, y, w, h = (float(t) for t in v.split(","))
                sc.setdefault("blur", []).append({"x": x, "y": y, "w": w, "h": h})
            elif k == "transition":
                sc["transition"] = v
            elif k == "seconds":
                sc["seconds"] = float(v)
        if focus:
            sc["focus"] = focus
        if not sc["sentences"]:
            sc.pop("sentences")
        scenes.append(sc)

    unused = [s for s in free[order_pos:]]
    if len(blocks) != len(shots):
        notes.append(f"{len(blocks)} scenes vs {len(shots)} screenshots: mapped by order. REVIEW the table below and fix any scene with an [img: ...] pin.")
    if unused:
        notes.append("screenshots not used: " + ", ".join(unused))

    manifest = {
        "title": meta.get("title", Path(a.script).stem),
        "product": meta.get("product", a.product),
        "voice": meta.get("voice", a.voice),
        "fps": 30,
        "stageLabel": "Product tour",
        "chapters": [{"id": c["id"], "step": c["step"], "title": c["title"]} for c in chapters],
        "scenes": scenes,
    }
    if not chapters:
        manifest.pop("chapters")
    if notes:
        manifest["_notes"] = notes
    save_json(a.out, manifest)

    print(f"{'scene':6} {'screenshot':34} sentences  text")
    for sc in scenes:
        t = " ".join(s["caption"] for s in sc.get("sentences", []))
        print(f"{sc['id']:6} {(sc.get('image') or str(sc.get('clip'))):34} {len(sc.get('sentences', [])):^9}  {t[:70]}")
    for n in notes:
        print("NOTE:", n)
    todo = sum(1 for sc in scenes for f in sc.get("focus", []) if "_todo" in f)
    if todo:
        print(f"{todo} zoom/click directive(s) still need coordinates (look at inspect_screens.py grid images).")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
