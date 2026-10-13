"""Word timing for captions. The spoken text is already known, so speech recognition (faster-whisper, optional) is only used to
anchor word times; everything else is interpolated. Without faster-whisper, words are spread over the clip by character count."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

import numpy as np

_MODEL = {}


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def distribute(words, t0, t1):
    """Spread words over [t0, t1] proportionally to their length (+1 for the gap)."""
    weights = np.array([len(w) + 1 for w in words], dtype=float)
    edges = np.concatenate([[0], np.cumsum(weights)]) / weights.sum()
    return [(t0 + (t1 - t0) * edges[i], t0 + (t1 - t0) * edges[i + 1]) for i in range(len(words))]


def whisper_words(a, sr, prompt="", model_name="small.en"):
    """Returns [(word, start, end)] or None if faster-whisper is not installed / fails."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    try:
        if model_name not in _MODEL:
            _MODEL[model_name] = WhisperModel(model_name, device="cpu", compute_type="int8")
        x = a.astype("float32") / 32768.0
        if sr != 16000:  # float32 numpy input avoids the av/metadata crash seen when passing a path
            n = int(len(x) * 16000 / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype("float32")
        segs, _ = _MODEL[model_name].transcribe(
            x, language="en", word_timestamps=True, initial_prompt=prompt or None, beam_size=5, condition_on_previous_text=False
        )
        return [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in s.words]
    except Exception as e:  # noqa: BLE001
        print("  (whisper failed, using character timing):", e)
        return None


def align(target, heard, t0, t1):
    """Time every word in `target` using anchors from `heard` [(word,start,end)] and linear interpolation in between."""
    if not target:
        return []
    if not heard:
        return distribute(target, t0, t1)
    tn = [norm(w) for w in target]
    hn = [norm(h[0]) for h in heard]
    times = [None] * len(target)
    for blk in SequenceMatcher(None, tn, hn, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (heard[blk.b + k][1], heard[blk.b + k][2])
    i = 0
    while i < len(target):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(target) and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i > 0 else t0
        hi = times[j][0] if j < len(target) else t1
        if hi <= lo:
            hi = lo + 0.12 * (j - i)
        for k, tt in zip(range(i, j), distribute(target[i:j], lo, hi)):
            times[k] = tt
        i = j
    # enforce monotonic, non-overlapping times
    out, prev_end = [], t0
    for s, e in times:
        s = max(s, prev_end)
        e = max(e, s + 0.05)
        out.append((s, e))
        prev_end = e
    return out
