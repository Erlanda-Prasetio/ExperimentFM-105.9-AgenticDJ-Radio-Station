"""
Song-intro detection for the "Bruce feature" (talking over the intro / hitting the post).

Estimates how many seconds pass before a song's main body (beat/vocal) kicks in — i.e.
how long a DJ can ride the intro before the "post". Cached per file; a manual override
map (intro_overrides.json) lets you pin values for songs the detector gets wrong.

Override file format (keyed by filename OR full path):
  { "Some Song.mp3": 8.5, "C:/full/path/Other.mp3": 4.0 }
"""
import os
import json
import numpy as np
import librosa

_CACHE_FILE = os.path.join("tts_cache", "intro_cache.json")
_OVERRIDE_FILE = "intro_overrides.json"
_MAX_INTRO = 25.0     # never report a longer intro than this (don't start a song 40s early)
_cache = None


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _sig(filepath):
    """Cache key: path + size + mtime, so a changed file re-measures."""
    try:
        st = os.stat(filepath)
        return f"{filepath}|{st.st_size}|{int(st.st_mtime)}"
    except Exception:
        return filepath


def detect_intro(filepath):
    """Seconds until the song's main body starts (0.0 if it starts immediately)."""
    global _cache
    if _cache is None:
        _cache = _load_json(_CACHE_FILE, {})

    key = _sig(filepath)
    if key in _cache:
        return float(_cache[key])

    # manual override (filename or full path) wins over detection
    overrides = _load_json(_OVERRIDE_FILE, {})
    base = os.path.basename(filepath)
    if base in overrides or filepath in overrides:
        val = float(overrides.get(base, overrides.get(filepath, 0.0)))
        _cache[key] = val
        _save_cache()
        return val

    intro = _measure(filepath)
    _cache[key] = intro
    _save_cache()
    return intro


def _measure(filepath, sr=22050, max_seconds=30.0):
    """Find the first sustained energy jump = where the main body kicks in."""
    try:
        y, _ = librosa.load(filepath, sr=sr, mono=True, duration=max_seconds)
    except Exception:
        return 0.0
    if y is None or len(y) < sr // 2:
        return 0.0

    hop = 512
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    if rms.size == 0:
        return 0.0

    ref = float(np.percentile(rms, 90))     # level of the "loud" part of the song
    if ref <= 1e-6:
        return 0.0

    thr = 0.5 * ref
    above = rms > thr
    need = max(1, int(0.25 * sr / hop))     # must stay above threshold ~0.25s (avoid clicks)
    run = 0
    for i, a in enumerate(above):
        run = run + 1 if a else 0
        if run >= need:
            t = librosa.frames_to_time(i - need + 1, sr=sr, hop_length=hop)
            return round(min(float(t), _MAX_INTRO), 2)
    return 0.0


def _save_cache():
    if _cache is None:
        return
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=0)
    except Exception:
        pass
