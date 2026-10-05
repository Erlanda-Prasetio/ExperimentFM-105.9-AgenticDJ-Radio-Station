"""
RLHF batch 2 - seed robustness test.

Question: does a "good" seed stay good across DIFFERENT sentences?
  YES -> a fixed seed pool can guarantee quality (seed dominates)
  NO  -> quality is text-dependent; seed pool alone is not enough

Uses the two seeds the user rated "good" in b1, each across 3 different script types.
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

GOOD_SEEDS = [456112, 736123]

TEXTS = {
    "T1": "Experiment FM, 105.9. Coming up next, something smooth for the ride home.",
    "T2": "That one was for everybody missing somebody tonight. I hope it reached you where you are.",
    "T3": "I'm Junior. I'll be here with you right through the night. Let's keep the music going.",
}


def main():
    voice = get_named_voice("jr")
    outdir = os.path.join("tts_cache", "rlhf")
    os.makedirs(outdir, exist_ok=True)
    eng = TTSEngine(model="F5-TTS", main_dj_gender=voice.get("gender", "male"))

    takes = []
    n = len(GOOD_SEEDS) * len(TEXTS)
    i = 0
    for tkey, raw in TEXTS.items():
        prepared = normalize_numbers(respell(raw)).replace('!', '.').replace('...', ',')
        for seed in GOOD_SEEDS:
            i += 1
            base = f"jr_b2_{tkey}_s{seed}"
            wav = os.path.join(outdir, base + ".wav")
            mp3 = os.path.join(outdir, base + ".mp3")
            try:
                eng.generate(prepared, language="english", voice_name="jr",
                             output_path=wav, seed=seed)
                subprocess.run(["ffmpeg", "-y", "-i", wav, mp3], capture_output=True, check=True)
                takes.append({"text": tkey, "seed": seed, "mp3": mp3, "text_used": prepared})
                print(f"[{i}/{n}] {tkey} seed={seed} -> {mp3}", flush=True)
            except Exception as e:
                print(f"[{i}/{n}] {tkey} seed={seed} FAILED: {e}", flush=True)

    manifest = {"voice": "jr", "cfg": voice.get("cfg"), "batch": "b2",
                "created": datetime.now().isoformat(), "takes": takes}
    with open(os.path.join(outdir, "jr_b2.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
