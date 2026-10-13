#!/usr/bin/env python3
"""Turn manifest.json (+ theme.json + voice wavs) into everything the Remotion template renders.

    python build_timeline.py --video-dir my-video --template renderer [--name my-video] [--silent] [--no-whisper]

Reads   <video-dir>/manifest.json, theme.json (optional), screenshots/, audio/<sentence id>.wav + audio/durations.json
Writes  <template>/public/<name>/{timeline.json, props.json, narration.wav, images/*, logo.*, ...}
Timing:  scene = lead + clips (+ gap between sentences) + tail; the narration track is assembled sample-accurately from the clips.
Then:    npx remotion still ProductDemo out/x.png --props=public/<name>/props.json --frame=N      (or render.py)
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import align as al  # noqa: E402
from _lib import IMG_EXT, chunk_words, load_json, read_wav, save_json, speech_bounds, write_wav  # noqa: E402

DEFAULT_COLORS = {
    "bgDeep": "#101522", "bg": "#1a2236", "bgLight": "#27324d", "accent": "#3b82f6", "accent2": "#93c5fd",
    "text": "#ffffff", "textMuted": "#c3cad8", "onAccent": "#ffffff", "card": "#ffffff",
}
warnings: list[str] = []


def warn(msg):
    warnings.append(msg)
    print("WARNING:", msg)


def find_file(video_dir: Path, ref: str, *subdirs):
    p = Path(ref)
    cands = [p] if p.is_absolute() else []
    for sd in ("",) + subdirs:
        cands.append(video_dir / sd / ref)
    for c in cands:
        if c.exists():
            return c
    return None


def logo_plate(path, bg, mode):
    """Plate colour when a big share of the logo's opaque pixels has too little contrast with the video background, else None."""
    from _lib import contrast, rgb_to_hex

    im = Image.open(path).convert("RGBA")
    im.thumbnail((120, 120))
    px = [p for p in im.convert("RGBA").resize(im.size).tobytes() and list(zip(*[iter(im.tobytes())] * 4)) if p[3] > 128]
    if not px:
        return None
    low = sum(1 for p in px if contrast(rgb_to_hex(p[:3]), bg) < 2.0)
    if low / len(px) < 0.3:
        return None
    return "#ffffff" if mode == "dark" else "#111827"


def est_duration(text):
    return max(1.6, 0.4 * len(text.split()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video-dir", required=True)
    ap.add_argument("--template", required=True, help="the Remotion project folder (from setup_renderer.py)")
    ap.add_argument("--name", help="public/<name> folder (default: video-dir name)")
    ap.add_argument("--silent", action="store_true", help="no voiceover: estimate durations from word count, captions only")
    ap.add_argument("--no-whisper", action="store_true", help="never use faster-whisper; time captions by character count")
    a = ap.parse_args()

    V = Path(a.video_dir).resolve()
    name = a.name or V.name
    pub = Path(a.template).resolve() / "public" / name
    if pub.exists():
        for sub in ("images", "clips"):
            shutil.rmtree(pub / sub, ignore_errors=True)
    (pub / "images").mkdir(parents=True, exist_ok=True)

    m = load_json(V / "manifest.json")
    if not m:
        sys.exit(f"{V / 'manifest.json'} not found")
    fps = int(m.get("fps", 30))
    pace = {"lead": 0.35, "gap": 0.25, "tail": 0.5, "firstLead": 0.6, "lastTail": 1.0, "hold": 3.0}
    pace.update(m.get("pacing", {}))

    # ---------------------------------------------------------------- theme -----------------------------
    theme_json = load_json(V / "theme.json", {}) or {}
    colors = {**DEFAULT_COLORS, **theme_json.get("colors", {}), **m.get("theme", {}).get("colors", {})}
    theme = {
        "product": m.get("product") or theme_json.get("product") or m.get("title", "Product"),
        "mode": m.get("theme", {}).get("mode") or theme_json.get("mode", "dark"),
        "font": m.get("theme", {}).get("font") or theme_json.get("font", "inter"),
        "logo": None,
        "logoPlate": m.get("theme", {}).get("logoPlate"),
        "colors": colors,
    }
    logo_ref = m.get("logo") or theme_json.get("logo")
    if logo_ref:
        lp = find_file(V, logo_ref)
        if lp:
            shutil.copyfile(lp, pub / f"logo{lp.suffix.lower()}")
            theme["logo"] = f"logo{lp.suffix.lower()}"
            if "logoPlate" not in m.get("theme", {}):
                theme["logoPlate"] = logo_plate(lp, colors["bg"], theme["mode"])
            if theme["logoPlate"] and "logoPlate" not in m.get("theme", {}):
                print(f"note: the logo would not read on the {theme['mode']} background, so it sits on a {theme['logoPlate']} plate (set theme.logoPlate to null in manifest to disable)")
        else:
            warn(f"logo '{logo_ref}' not found - the product name is used as a wordmark")

    # ---------------------------------------------------------------- scenes: files + sentence timing ----
    scenes_in = m["scenes"]
    audio_dir = V / "audio"
    durs = load_json(audio_dir / "durations.json", {}) or {}
    clips = {}  # sentence id -> (sr, samples)
    missing = []
    sent_dur = {}
    for sc in scenes_in:
        for s in sc.get("sentences", []):
            wav = audio_dir / f"{s['id']}.wav"
            if a.silent:
                sent_dur[s["id"]] = est_duration(s["caption"])
            elif wav.exists():
                clips[s["id"]] = read_wav(wav)
                sr_, arr_ = clips[s["id"]]
                sent_dur[s["id"]] = len(arr_) / sr_
            else:
                missing.append(s["id"])
    if missing:
        sys.exit(f"missing voice clips for: {', '.join(missing)}\nRun voice_job.py (submit/wait/collect) or tts_edge.py first, or pass --silent.")

    n = len(scenes_in)
    t = 0.0  # stage seconds (float), converted to frames with cumulative rounding
    scenes, plan = [], []
    for i, sc in enumerate(scenes_in):
        lead = pace["firstLead"] if i == 0 else pace["lead"]
        tail = pace["lastTail"] if i == n - 1 else pace["tail"]
        sents = sc.get("sentences", [])
        if sents:
            body = sum(sent_dur[s["id"]] for s in sents) + pace["gap"] * (len(sents) - 1)
            dur = lead + body + tail
        else:
            c_ = sc.get("clip") or {}
            clip_len = (c_["to"] - c_.get("from", 0)) if "to" in c_ else None
            dur = float(sc.get("seconds", clip_len if clip_len else pace["hold"]))
            lead = 0.0
        offsets, o = [], lead
        for s in sents:
            offsets.append(o)
            o += sent_dur[s["id"]] + pace["gap"]
        plan.append({"t0": t, "dur": dur, "lead": lead, "tail": tail, "offsets": offsets})
        t += dur
    starts = [round(p["t0"] * fps) for p in plan] + [round(t * fps)]
    stage_frames = starts[-1]

    # ---------------------------------------------------------------- narration track --------------------
    SR = next((sr for sr, _ in clips.values()), 22050)
    narr_file = None
    if clips and not a.silent:
        total = np.zeros(int(stage_frames / fps * SR) + SR, dtype="float32")
        for i, sc in enumerate(scenes_in):
            for s, off in zip(sc.get("sentences", []), plan[i]["offsets"]):
                sr_, arr = clips[s["id"]]
                if sr_ != SR:
                    sys.exit(f"{s['id']}: sample rate {sr_} differs from {SR}; re-voice with one engine")
                x = arr.astype("float32")
                fade = int(0.012 * SR)
                if len(x) > 2 * fade:
                    x[:fade] *= np.linspace(0, 1, fade)
                    x[-fade:] *= np.linspace(1, 0, fade)
                start = int(round((starts[i] / fps + off) * SR))
                total[start : start + len(x)] += x
        raw = pub / "narration_raw.wav"
        write_wav(raw, SR, np.clip(total, -32768, 32767).astype("int16"))
        outw = pub / "narration.wav"
        if shutil.which("ffmpeg"):
            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", "48000", "-ac", "1", str(outw)],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                warn("ffmpeg loudnorm failed (" + r.stderr[-200:] + "); using the un-normalised narration")
                shutil.move(raw, outw)
            else:
                raw.unlink()
        else:
            warn("ffmpeg not found: narration is not loudness-normalised")
            shutil.move(raw, outw)
        narr_file = "narration.wav"

    # ---------------------------------------------------------------- per scene build ---------------------
    vocab = m.get("vocabulary", "")
    use_whisper = not a.no_whisper and not a.silent
    captions, chapters_in = [], m.get("chapters", [])
    if not chapters_in:
        chapters_in = [{"id": "c0", "step": None, "title": m.get("title", "Overview")}]
    chap_ids = [c["id"] for c in chapters_in]
    cap_words_by_scene = []
    prev_chapter, prev_cursor = chap_ids[0], None
    chapter_start = {}
    sizes_seen = set()
    for i, sc in enumerate(scenes_in):
        sf = starts[i]
        dur_f = starts[i + 1] - sf
        chap = sc.get("chapter", prev_chapter)
        if chap not in chap_ids:
            warn(f"scene {sc['id']}: unknown chapter '{chap}' - using '{prev_chapter}'")
            chap = prev_chapter
        chapter_start.setdefault(chap, sf)
        # ---- media
        entry = {"id": sc["id"], "chapter": chap, "start": sf, "duration": dur_f, "focus": [], "chips": [], "blur": [], "type": [], "callouts": []}
        if sc.get("clip"):
            c = sc["clip"]
            cp = find_file(V, c["src"], "clips")
            if not cp:
                sys.exit(f"clip not found: {c['src']}")
            (pub / "clips").mkdir(exist_ok=True)
            shutil.copyfile(cp, pub / "clips" / cp.name)
            entry.update(kind="clip", clip={"src": f"clips/{cp.name}", "fromFrame": round(c.get("from", 0) * fps), "toFrame": round(c.get("to", c.get("from", 0) + plan[i]["dur"]) * fps)})
            entry["imageSize"] = {"w": c.get("width", 1920), "h": c.get("height", 1080)}
        else:
            ip = find_file(V, sc["image"], "screenshots")
            if not ip:
                sys.exit(f"screenshot not found: {sc['image']} (looked in {V} and {V / 'screenshots'})")
            dst = pub / "images" / ip.name
            shutil.copyfile(ip, dst)
            with Image.open(ip) as im:
                size = {"w": im.width, "h": im.height}
            sizes_seen.add((size["w"] // 10, size["h"] // 10))
            entry.update(kind="image", image=f"images/{ip.name}", imageSize=size)

        # ---- sentences -> caption words (global stage frames)
        words_scene = []  # (word text, start_s, end_s) scene-relative seconds
        for s, off in zip(sc.get("sentences", []), plan[i]["offsets"]):
            cw = s["caption"].split()
            d = sent_dur[s["id"]]
            if a.silent:
                times = al.distribute(cw, 0.0, d)
            else:
                sr_, arr = clips[s["id"]]
                sp0, sp1 = speech_bounds(arr, sr_)
                heard = al.whisper_words(arr, sr_, vocab) if use_whisper else None
                if use_whisper and heard is None and not getattr(main, "_warned", False):
                    warn("faster-whisper not available - captions are timed by character count (fine for short sentences; `pip install faster-whisper` for tighter sync)")
                    main._warned = True
                times = al.align(cw, heard, sp0, sp1)
            wl = []
            for w, (ws, we) in zip(cw, times):
                ws_f = starts[i] + round((off + ws) * fps)
                we_f = starts[i] + round((off + min(we, ws + 0.5)) * fps)
                wl.append({"text": w, "start": ws_f, "end": max(we_f, ws_f + 1)})
                words_scene.append((w, off + ws, off + we))
            sent_end = starts[i] + round((off + d) * fps)
            chunks = chunk_words(cw)
            for ci, idxs in enumerate(chunks):
                ws_ = [wl[j] for j in idxs]
                nxt = wl[chunks[ci + 1][0]]["start"] if ci + 1 < len(chunks) else sent_end + round(0.25 * fps)
                end = min(ws_[-1]["end"] + round(0.25 * fps), max(nxt - 1, ws_[-1]["end"]))
                captions.append({"start": ws_[0]["start"], "end": end, "words": ws_})
        cap_words_by_scene.append(words_scene)

        # ---- focus
        for fo in sc.get("focus", []):
            if "on" in fo:
                target = [al.norm(x) for x in fo["on"].split() if al.norm(x)]
                hit = None
                wn = [al.norm(w[0]) for w in words_scene]
                for k in range(len(wn) - len(target) + 1):
                    if wn[k : k + len(target)] == target:
                        hit = words_scene[k][1]
                        break
                if hit is None:
                    for k, w in enumerate(wn):
                        if target and target[0] and target[0] in w:
                            hit = words_scene[k][1]
                            break
                if hit is None:
                    warn(f"scene {sc['id']}: focus 'on': '{fo['on']}' not found in the caption text - using the scene start")
                    ts = plan[i]["lead"]
                else:
                    ts = max(0.0, hit - 0.45)
            else:
                ts = float(fo.get("t", plan[i]["lead"]))
            if "x" not in fo or "y" not in fo:
                warn(f"scene {sc['id']}: focus '{fo.get('on', fo.get('t', '?'))}' has no x/y coordinates yet - skipped (read them off inspect/grid/ images)")
                continue
            x, y, w_, h_ = (float(fo.get(k, 0)) for k in ("x", "y", "w", "h"))
            for k, v in (("x", x), ("y", y), ("w", w_), ("h", h_)):
                if not 0 <= v <= 1:
                    warn(f"scene {sc['id']}: focus {k}={v} is outside 0-1 (coordinates are fractions of the screenshot)")
            if x + w_ > 1.001 or y + h_ > 1.001:
                warn(f"scene {sc['id']}: focus box extends past the screenshot edge")
            entry["focus"].append({
                "frame": round(ts * fps), "x": x, "y": y, "w": w_, "h": h_, "zoom": float(fo.get("zoom", 1.6)),
                "hold": round(float(fo.get("hold", 2.4)) * fps), "click": bool(fo.get("click", False)),
                "cursor": bool(fo.get("cursor", False)), "highlight": bool(fo.get("highlight", w_ > 0 and h_ > 0)),
            })
        entry["focus"].sort(key=lambda f_: f_["frame"])
        for f_ in entry["focus"]:
            if f_["frame"] + round(0.7 * fps) > dur_f:
                warn(f"scene {sc['id']}: a focus move starts at {f_['frame'] / fps:.1f}s but the scene is only {dur_f / fps:.1f}s long")

        # ---- chips / blur / callouts / type
        if sc.get("chip"):
            entry["chips"].append({"text": sc["chip"], "start": round(0.45 * fps), "end": dur_f - round(0.3 * fps)})
        for c in sc.get("chips", []):
            entry["chips"].append({"text": c["text"], "start": round(c.get("t0", 0.45) * fps), "end": round(c.get("t1", dur_f / fps - 0.3) * fps)})
        for b in sc.get("blur", []):
            entry["blur"].append({k: float(b[k]) for k in ("x", "y", "w", "h")})
        for co in sc.get("callouts", []):
            entry["callouts"].append({"frame": round(co.get("t", 1.0) * fps), "hold": round(co.get("hold", 2.0) * fps), "scale": float(co.get("scale", 1.12)),
                                      **{k: float(co[k]) for k in ("x", "y", "w", "h")}})
        for ty in sc.get("type", []):
            entry["type"].append({"frame": round(ty.get("t", 1.0) * fps), "text": ty["text"], "fill": ty.get("fill", "#ffffff"), "color": ty.get("color", "#111827"),
                                  "size": int(ty.get("size", 26)), **{k: float(ty[k]) for k in ("x", "y", "w", "h")}})

        # ---- transition
        tr = sc.get("transition", "auto")
        if i == 0:
            tr = "none"
        elif tr == "auto":
            tr = "push" if chap != prev_chapter else "crossfade"
        tfr = 0 if tr == "none" else round((0.35 if tr == "push" else 0.3) * fps)
        if i > 0:
            prev_tail = round(plan[i - 1]["tail"] * fps)
            if tfr > prev_tail - 1:
                tfr = max(0, prev_tail - 1)
                if tfr == 0:
                    tr = "none"
        entry.update(transition=tr, transitionFrames=tfr)

        # ---- cursor continuity
        cf = [f_ for f_ in entry["focus"] if f_["click"] or f_["cursor"]]
        entry["cursorStart"] = prev_cursor if cf else None
        if cf:
            last = cf[-1]
            prev_cursor = {"x": last["x"] + last["w"] * 0.58, "y": last["y"] + last["h"] * 0.66}  # same point as clickPoint() in SceneView.tsx
        scenes.append(entry)
        prev_chapter = chap

    if len(sizes_seen) > 1:
        print("note: screenshots have different sizes - the card follows the most common aspect ratio; others are letterboxed over a blurred copy")

    chapters = []
    for c in chapters_in:
        chapters.append({"id": c["id"], "step": c.get("step"), "title": c["title"], "start": chapter_start.get(c["id"], 0)})
        if c["id"] not in chapter_start:
            warn(f"chapter '{c['id']}' has no scenes")

    # ---------------------------------------------------------------- intro / outro / music ----------------
    intro = m.get("intro") or None
    outro = m.get("outro") or None
    intro_frames = round((intro or {}).get("seconds", 5.0) * fps) if intro else 0
    outro_frames = round((outro or {}).get("seconds", 5.0) * fps) if outro else 0
    if intro and "headline" not in intro:
        sys.exit("intro needs a headline")
    if outro and "headline" not in outro:
        sys.exit("outro needs a headline")
    if intro and intro.get("hero"):
        hp = find_file(V, intro["hero"], "screenshots")
        if hp:
            shutil.copyfile(hp, pub / "images" / hp.name)
            intro = {**intro, "hero": f"images/{hp.name}"}
    elif intro:
        intro = {**intro, "hero": None}

    music, mvol = None, float(m.get("music", {}).get("volume", 0.12)) if isinstance(m.get("music"), dict) else 0.12
    if m.get("music"):
        mf = m["music"]["file"] if isinstance(m["music"], dict) else m["music"]
        mp = find_file(V, mf)
        if mp:
            shutil.copyfile(mp, pub / f"music{mp.suffix.lower()}")
            music = f"music{mp.suffix.lower()}"
        else:
            warn(f"music file '{mf}' not found - continuing without music")

    total = intro_frames + stage_frames + outro_frames
    timeline = {
        "fps": fps, "width": 1920, "height": 1080, "totalFrames": total, "introFrames": intro_frames, "stageFrames": stage_frames, "outroFrames": outro_frames,
        "theme": theme, "stageLabel": m.get("stageLabel", "Product tour"), "intro": intro, "outro": outro,
        "scenes": scenes, "chapters": chapters, "captions": captions,
        "audio": {"narration": narr_file, "music": music, "musicVolume": mvol},
    }
    save_json(pub / "timeline.json", timeline)
    save_json(pub / "props.json", {"dir": name})
    print(f"\nbuilt {pub}")
    print(f"  {len(scenes)} scenes, {len(captions)} captions, {total} frames = {total / fps:.1f}s @ {fps}fps (intro {intro_frames / fps:.1f}s, tour {stage_frames / fps:.1f}s, outro {outro_frames / fps:.1f}s)")
    print(f"  render props file: public/{name}/props.json")
    if warnings:
        print(f"  {len(warnings)} warning(s) above")


if __name__ == "__main__":
    main()
