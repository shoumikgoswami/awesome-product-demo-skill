#!/usr/bin/env python3
"""Talk to the local voice server (assets/tts/voice_server.py) through its shared folder. Standard library only.

    voice_job.py lint    --manifest M [--pron P]                     # list words the TTS is likely to mispronounce
    voice_job.py submit  --manifest M --root VOICE_DIR --job NAME [--voice Sofia] [--only s01a,s02b] [--pron P]
    voice_job.py wait    --root VOICE_DIR --job NAME [--timeout 170]  # exit 0 done, 2 error, 3 not finished / server not running
    voice_job.py collect --root VOICE_DIR --job NAME --audio-dir DIR [--manifest M]   # copy wavs -> DIR/<sentence id>.wav

VOICE_DIR is the folder start_voice_server.py serves (it contains jobs/ and results/).
Rules the server imposes: job names and chunk ids match ^[A-Za-z0-9_.-]+$, and a chunk whose wav already exists in
results/<job>/ is SKIPPED - so a corrected line must always go in a NEW job name (`--job myvideo_fix01`).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import GENERIC_PRONUNCIATIONS, apply_pronunciations, load_json  # noqa: E402

SAFE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def pron_table(path, manifest, manifest_path=None):
    """generic table < manifest.pronunciations < <video>/pronunciations.json (auto-detected) < --pron file"""
    t = dict(GENERIC_PRONUNCIATIONS)
    t.update(manifest.get("pronunciations", {}))
    if manifest_path:
        t.update(load_json(Path(manifest_path).parent / "pronunciations.json", {}) or {})
    if path:
        t.update(load_json(path, {}) or {})
    return t


def sentences(manifest):
    for sc in manifest["scenes"]:
        for s in sc.get("sentences", []):
            yield sc, s


def say_text(s, table):
    if s.get("say"):
        return s["say"]
    return apply_pronunciations(s["caption"], table)


def cmd_lint(a):
    m = load_json(a.manifest)
    table = pron_table(a.pron, m, a.manifest)
    seen = {}
    for sc, s in sentences(m):
        txt = say_text(s, table)
        n = len(txt.split())
        if n > 28:
            print(f"LONG  {s['id']}: {n} words - split it (keep one sentence per chunk, <= ~25 words)")
        for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\.\+/]*", txt):
            if tok.isupper() and len(tok) > 1 and not tok.isdigit():
                seen.setdefault(tok, s["id"])
            elif re.search(r"[a-z][A-Z]", tok) or re.search(r"\d", tok) or "/" in tok or "." in tok.strip("."):
                seen.setdefault(tok, s["id"])
        if re.search(r"[()\[\]{}<>_*#@&%$=+~|\\]", txt):
            print(f"SYMBOL {s['id']}: contains symbols the voice may read oddly -> {txt!r}")
    if seen:
        print("\nTokens to check (add a spoken form to pronunciations.json if they sound wrong; letter-by-letter acronyms need spaces: 'A P I'):")
        for tok, sid in seen.items():
            print(f"  {tok:24s} first used in {sid}")
    else:
        print("no risky tokens found")


def cmd_submit(a):
    m = load_json(a.manifest)
    root = Path(a.root)
    if not SAFE.match(a.job):
        sys.exit("job name must match ^[A-Za-z0-9_.-]+$")
    if (root / "results" / a.job).exists() or (root / "jobs" / "done" / f"{a.job}.json").exists():
        sys.exit(f"job '{a.job}' already exists. Use a NEW name - the server skips chunks whose wav already exists.")
    table = pron_table(a.pron, m, a.manifest)
    only = set(a.only.split(",")) if a.only else None
    chunks = []
    for _, s in sentences(m):
        if only is not None and s["id"] not in only:
            continue
        if not SAFE.match(s["id"]):
            sys.exit(f"sentence id {s['id']!r} must match ^[A-Za-z0-9_.-]+$")
        chunks.append({"id": s["id"], "text": say_text(s, table)})
    if not chunks:
        sys.exit("nothing to voice (check --only)")
    jobs = root / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    tmp = jobs / f".{a.job}.tmp"
    tmp.write_text(json.dumps({"job": a.job, "voice": a.voice or m.get("voice", "Sofia"), "chunks": chunks}, indent=1), encoding="utf-8")
    os.replace(tmp, jobs / f"{a.job}.json")
    words = sum(len(c["text"].split()) for c in chunks)
    print(f"submitted {a.job}: {len(chunks)} chunks, ~{words} words (expect roughly {words / 2.4 * 1.35:.0f}s of GPU time on first run)")


def cmd_wait(a):
    st = Path(a.root) / "results" / a.job / "status.json"
    t0 = time.time()
    started = False
    while time.time() - t0 < a.timeout:
        if st.exists():
            try:
                s = json.loads(st.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                time.sleep(1)
                continue
            started = True
            if s["state"] == "done":
                print(f"done: {s['done']}/{s['total']} chunks")
                return 0
            if s["state"] == "error":
                print("ERROR from voice server:\n" + s.get("error", "?"))
                return 2
            print(f"running {s['done']}/{s['total']}", flush=True)
        elif time.time() - t0 > 30 and not started:
            print("No status after 30 s - the voice server is probably not running. Ask the user to start start_voice_server.bat (Windows) or start_voice_server.sh (Linux) and leave the window open.")
            return 3
        time.sleep(4)
    print("not finished yet (timeout) - call wait again")
    return 3


def cmd_collect(a):
    res = Path(a.root) / "results" / a.job
    if not (res / "durations.json").exists():
        sys.exit("job not finished (no durations.json)")
    out = Path(a.audio_dir)
    out.mkdir(parents=True, exist_ok=True)
    durs = json.loads((res / "durations.json").read_text(encoding="utf-8"))
    n = 0
    for sid in durs:
        shutil.copyfile(res / f"{sid}.wav", out / f"{sid}.wav")
        n += 1
    cur = load_json(out / "durations.json", {}) or {}
    cur.update(durs)
    (out / "durations.json").write_text(json.dumps(cur, indent=1), encoding="utf-8")
    print(f"copied {n} wavs to {out}; durations.json now has {len(cur)} entries")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("lint")
    p.add_argument("--manifest", required=True)
    p.add_argument("--pron")
    p.set_defaults(fn=cmd_lint)
    p = sp.add_parser("submit")
    p.add_argument("--manifest", required=True)
    p.add_argument("--root", required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--voice")
    p.add_argument("--only")
    p.add_argument("--pron")
    p.set_defaults(fn=cmd_submit)
    p = sp.add_parser("wait")
    p.add_argument("--root", required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--timeout", type=int, default=170)
    p.set_defaults(fn=cmd_wait)
    p = sp.add_parser("collect")
    p.add_argument("--root", required=True)
    p.add_argument("--job", required=True)
    p.add_argument("--audio-dir", required=True)
    p.add_argument("--manifest")
    p.set_defaults(fn=cmd_collect)
    a = ap.parse_args()
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
