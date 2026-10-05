"""
Pause injection via segmented generation + silence stitching.

PROBLEM: the calm reference is a continuous 30s radio ad read with no pauses, so the
clone "bablas" (runs on without breathing). cfg/speed cannot fix rhythm.

FIX: split the script into segments, generate each with F5-TTS, then concatenate with
DETERMINISTIC silence gaps. We control the pause length, not the model.

Variants:
  sent        - split on sentence enders, 350ms gaps
  sent_long   - split on sentence enders, 550ms gaps (more breathing)
  sent_comma  - split on sentences AND commas, 350ms / 150ms gaps
"""
import os
import re
import sys
import subprocess

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

from phonetic_respell import respell, normalize_numbers
from tts_engine import TTSEngine
from audio_processing import radio_processing

SEED = 736123
CFG = 2.0
TEXT = "Experiment FM, one oh five point nine. That was a beautiful one to sit with, coming up next, something a little warmer for the ride home. Stay with me."

OUTDIR = os.path.join("tts_cache", "rlhf")


def split_sent(text):
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_comma(text):
    # split on sentence enders OR commas; keep the delimiter for a natural feel
    parts = re.split(r"(?<=[.?!,])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def render(eng, segments, gaps_ms, tag):
    """segments: list[str]; gaps_ms: list of len(segments)-1 gap durations."""
    frames = []
    sr = None
    for i, seg in enumerate(segments):
        raw = os.path.join(OUTDIR, f"_st_{tag}_{i}.wav")
        if os.path.exists(raw):
            os.remove(raw)
        eng.generate(seg, language="english", voice_name="jr", output_path=raw,
                     seed=SEED, cfg_strength=CFG, speed=1.0, skip_processing=True)
        w, s = sf.read(raw)
        if w.ndim > 1:
            w = w.mean(axis=1)
        sr = s
        frames.append(w.astype(np.float32))
        os.remove(raw)
        if i < len(segments) - 1:
            gap = int(sr * gaps_ms[i] / 1000.0)
            frames.append(np.zeros(gap, dtype=np.float32))

    audio = np.concatenate(frames)
    combined = os.path.join(OUTDIR, f"_st_{tag}_comb.wav")
    sf.write(combined, audio, sr)
    final = os.path.join(OUTDIR, f"jr_stitch_{tag}.wav")
    radio_processing(combined, final, sr=48000)
    mp3 = os.path.join(OUTDIR, f"jr_stitch_{tag}.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", final, mp3], capture_output=True, check=True)
    os.remove(combined)
    os.remove(final)
    print(f"[{tag}] {len(segments)} segs, total {len(audio)/sr:.1f}s -> jr_stitch_{tag}.mp3", flush=True)


def main():
    eng = TTSEngine(model="F5-TTS", main_dj_gender="male")
    prep = normalize_numbers(respell(TEXT)).replace("!", ".").replace("...", ",")
    print("prepped:", prep, flush=True)

    sents = split_sent(prep)
    commas = split_comma(prep)

    # sentence split
    render(eng, sents, [350] * (len(sents) - 1), "sent")
    render(eng, sents, [550] * (len(sents) - 1), "sent_long")
    # sentence + comma split
    render(eng, commas, [150 if s.rstrip().endswith(",") else 350 for s in commas[:-1]], "sent_comma")
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
