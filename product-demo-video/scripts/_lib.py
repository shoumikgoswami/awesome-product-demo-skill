"""Shared helpers for the product-demo-video scripts. Needs only the standard library + numpy + Pillow."""
from __future__ import annotations

import colorsys
import json
import re
import wave
from pathlib import Path

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]


def load_json(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------- colour -------------
def hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def hsv_hex(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0, min(1, s)), max(0, min(1, v)))
    return rgb_to_hex((r * 255, g * 255, b * 255))


def hex_hsv(h: str):
    r, g, b = (c / 255 for c in hex_to_rgb(h))
    return colorsys.rgb_to_hsv(r, g, b)


def luminance(hexcol: str) -> float:
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (f(c) for c in hex_to_rgb(hexcol))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- audio --------------
def read_wav(path):
    """Returns (sample_rate, numpy int16 mono array)."""
    import numpy as np

    with wave.open(str(path), "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: only 16-bit PCM wav is supported (got {sw * 8}-bit)")
    a = np.frombuffer(raw, dtype="<i2")
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1).astype("int16")
    return sr, a


def write_wav(path, sr, a):
    import numpy as np

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.asarray(a, dtype="<i2").tobytes())


def speech_bounds(a, sr, thresh=0.012):
    """First/last sample index (seconds) where the clip is louder than thresh * full scale. Used to ignore padding."""
    import numpy as np

    x = np.abs(a.astype("float32")) / 32768.0
    win = max(1, int(sr * 0.01))
    n = len(x) // win
    if n == 0:
        return 0.0, len(a) / sr
    env = x[: n * win].reshape(n, win).max(axis=1)
    idx = np.where(env > thresh)[0]
    if len(idx) == 0:
        return 0.0, len(a) / sr
    return idx[0] * win / sr, (idx[-1] + 1) * win / sr


# ---------------------------------------------------------------- text ---------------
_ABBR = {"e.g", "i.e", "vs", "etc", "dr", "mr", "mrs", "ms", "inc", "ltd", "no", "approx"}


def split_sentences(text: str):
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    parts, buf = [], ""
    for tok in text.split(" "):
        buf = (buf + " " + tok).strip()
        if re.search(r"[.!?][\"')\]]*$", tok):
            bare = tok.rstrip(".!?\"')]").lower()
            if bare in _ABBR or re.fullmatch(r"[a-z]", bare) or re.fullmatch(r"\d+", bare) and tok.endswith("."):
                continue
            parts.append(buf)
            buf = ""
    if buf:
        parts.append(buf)
    return parts


def chunk_words(words, max_chars=66, min_chars=18):
    """Split a list of words (strings) into caption chunks of <= max_chars, preferring breaks after commas and before conjunctions."""
    text = " ".join(words)
    if len(text) <= max_chars:
        return [list(range(len(words)))]
    n = -(-len(text) // max_chars)
    target = len(text) / n
    chunks, cur, curlen = [], [], 0
    for i, w in enumerate(words):
        cur.append(i)
        curlen += len(w) + 1
        nxt = words[i + 1] if i + 1 < len(words) else ""
        remaining_chunks = n - len(chunks) - 1
        good_break = w.endswith((",", ";", ":")) or nxt.lower() in {"and", "but", "so", "that", "which", "to", "for", "with", "you", "then"}
        if remaining_chunks > 0 and (curlen >= target * 1.05 or (curlen >= target * 0.8 and good_break)) and curlen >= min_chars:
            chunks.append(cur)
            cur, curlen = [], 0
    if cur:
        if chunks and sum(len(words[j]) + 1 for j in cur) < min_chars:
            chunks[-1].extend(cur)
        else:
            chunks.append(cur)
    return chunks


GENERIC_PRONUNCIATIONS = {
    "API": "A P I",
    "APIs": "A P Is",
    "SSO": "S S O",
    "SaaS": "sass",
    "UI": "U I",
    "UX": "U X",
    "URL": "U R L",
    "PDF": "P D F",
    "CSV": "C S V",
    "MCP": "M C P",
    "SDK": "S D K",
    "CRM": "C R M",
    "KPI": "K P I",
    "KPIs": "K P Is",
    "AI": "A I",
    "ChatGPT": "Chat G P T",
}


def apply_pronunciations(text: str, table: dict) -> str:
    """Whole-word, longest-first replacement. `table` maps written form -> spoken form."""
    for src in sorted(table, key=len, reverse=True):
        text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(src) + r"(?![A-Za-z0-9])", table[src], text)
    return text
