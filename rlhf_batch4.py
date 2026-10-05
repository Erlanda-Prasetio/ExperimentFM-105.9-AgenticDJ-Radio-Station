"""
RLHF batch 4 - cross-text robustness verification.

The b1->b2 lesson: a seed that looks good on ONE text can be fragile on another
(456112 looked great in b1, then broke on 2 of 3 texts in b2). So a seed only enters
the pool after it stays clean across MULTIPLE texts.

Here: 6 candidates from b3 x 3 different texts = 18 takes.
Texts deliberately include the station number (the classic artefact spot) and a soft line.
"""
import os
import sys
import json
import subprocess
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

from phonetic_respell import respell, normalize_numbers
from tts_engine import TTSEngine
from voice_config import get_named_voice

CANDIDATES = [903725, 528278, 233578, 135530, 565081, 241630]

TEXTS = {
    "A": "Experiment FM, 105.9. You're with me through the night, and the music keeps going.",
    "B": "That was for everyone driving home late, headlights on empty roads. This next one is for you.",
    "C": "I'm Junior. Take a breath, let the day go, and stay right here with me a little longer.",
}


def main():
    voice = get_named_voice("jr")
    outdir = os.path.join("tts_cache", "rlhf")
    os.makedirs(outdir, exist_ok=True)
    eng = TTSEngine(model="F5-TTS", main_dj_gender=voice.get("gender", "male"))

    takes = []
    total = len(CANDIDATES) * len(TEXTS)
    i = 0
    for tkey, raw in TEXTS.items():
        prep = normalize_numbers(respell(raw)).replace('!', '.').replace('...', ',')
        for seed in CANDIDATES:
            i += 1
            base = f"jr_b4_{tkey}_s{seed}"
            wav = os.path.join(outdir, base + ".wav")
            mp3 = os.path.join(outdir, base + ".mp3")
            try:
                eng.generate(prep, language="english", voice_name="jr",
                             output_path=wav, seed=seed)
                subprocess.run(["ffmpeg", "-y", "-i", wav, mp3], capture_output=True, check=True)
                takes.append({"text": tkey, "seed": seed, "mp3": mp3})
                print(f"[{i}/{total}] {tkey} seed={seed} -> {base}.mp3", flush=True)
            except Exception as e:
                print(f"[{i}/{total}] {tkey} seed={seed} FAILED: {e}", flush=True)

    with open(os.path.join(outdir, "jr_b4.json"), "w", encoding="utf-8") as f:
        json.dump({"voice": "jr", "batch": "b4", "candidates": CANDIDATES,
                   "created": datetime.now().isoformat(), "takes": takes}, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
