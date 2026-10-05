"""
RLHF batch 3 - two goals:
  1. DETERMINISM: re-generate seed 736123 on the SAME text as b2/T3 and compare bytes.
     If identical -> a fixed seed pool is bulletproof (same seed => same audio).
  2. SCREENING: try NEW random seeds on one short text to find more robust candidates.
     The b1 screen found ~2/8 good; we need ~4 robust seeds, so screen a wider batch.
"""
import os
import sys
import json
import random
import hashlib
import subprocess
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

from phonetic_respell import respell, normalize_numbers
from tts_engine import TTSEngine
from voice_config import get_named_voice

# Same text as b2/T3 (for the determinism check)
T3 = "I'm Junior. I'll be here with you right through the night. Let's keep the music going."
SCREEN_TEXT = "Experiment FM, 105.9. That was a lovely one, and I hope it found you tonight."

GOLD_SEED = 736123
N_NEW = 12


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    voice = get_named_voice("jr")
    outdir = os.path.join("tts_cache", "rlhf")
    os.makedirs(outdir, exist_ok=True)
    eng = TTSEngine(model="F5-TTS", main_dj_gender=voice.get("gender", "male"))
    result = {"determinism": None, "screening": []}

    # --- 1. Determinism: regenerate gold seed on T3 ---
    prep_t3 = normalize_numbers(respell(T3)).replace('!', '.').replace('...', ',')
    det_wav = os.path.join(outdir, "det_jr_T3_s736123.wav")
    eng.generate(prep_t3, language="english", voice_name="jr",
                 output_path=det_wav, seed=GOLD_SEED)
    # existing b2 file for comparison
    b2_wav = os.path.join(outdir, "jr_b2_T3_s736123.wav")
    det = {"new_md5": md5(det_wav), "existing_md5": md5(b2_wav) if os.path.exists(b2_wav) else None}
    det["identical"] = det["new_md5"] == det["existing_md5"]
    result["determinism"] = det
    print(f"DETERMINISM: identical={det['identical']} "
          f"({det['new_md5'][:8]} vs {str(det['existing_md5'])[:8]})", flush=True)

    # --- 2. Screening new seeds on one text ---
    prep = normalize_numbers(respell(SCREEN_TEXT)).replace('!', '.').replace('...', ',')
    seeds = random.sample(range(1, 999999), N_NEW)
    for i, seed in enumerate(seeds, 1):
        base = f"jr_b3_{i:02d}_s{seed}"
        wav = os.path.join(outdir, base + ".wav")
        mp3 = os.path.join(outdir, base + ".mp3")
        try:
            eng.generate(prep, language="english", voice_name="jr",
                         output_path=wav, seed=seed)
            subprocess.run(["ffmpeg", "-y", "-i", wav, mp3], capture_output=True, check=True)
            result["screening"].append({"idx": i, "seed": seed, "mp3": mp3})
            print(f"[{i}/{N_NEW}] seed={seed} -> {mp3}", flush=True)
        except Exception as e:
            print(f"[{i}/{N_NEW}] seed={seed} FAILED: {e}", flush=True)

    with open(os.path.join(outdir, "jr_b3.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
