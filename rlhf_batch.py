"""
RLHF-style preference collection for TTS.

Generate a batch of takes with DISTINCT random seeds, save numbered audio + a manifest.
The user listens and labels each take (good/bad). Labels feed a curated SEED POOL that
production rotates - i.e. best-of-N driven by human preference, since no cheap automatic
metric reliably separates a clean take from an artefact-y one.

Usage:
  python rlhf_batch.py --voice jr --n 8 --label b1
"""
import os
import sys
import json
import random
import argparse
import subprocess
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

from phonetic_respell import respell, normalize_numbers
from tts_engine import TTSEngine
from voice_config import get_named_voice

# A representative DJ transition line: has the station number (validates the fix),
# a warm reflective beat and a forward-looking beat (tests expressiveness).
DEFAULT_TEXT = (
    "Experiment FM, 105.9. That was a beautiful one to sit with, and I hope it found "
    "you wherever you are tonight. Coming up next, something a little warmer for the "
    "ride home. Stay with me."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="jr")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--label", default="b1")
    ap.add_argument("--text", default=None)
    ap.add_argument("--seed-min", type=int, default=1)
    ap.add_argument("--seed-max", type=int, default=999999)
    args = ap.parse_args()

    raw = args.text or DEFAULT_TEXT
    prepared = normalize_numbers(respell(raw)).replace('!', '.').replace('...', ',')
    voice = get_named_voice(args.voice)
    cfg = voice.get("cfg") if voice else None
    gender = voice.get("gender", "male") if voice else "male"

    outdir = os.path.join("tts_cache", "rlhf")
    os.makedirs(outdir, exist_ok=True)

    seeds = random.sample(range(args.seed_min, args.seed_max + 1), args.n)
    eng = TTSEngine(model="F5-TTS", main_dj_gender=gender)

    print(f"TEXT: {prepared}", flush=True)
    print(f"VOICE: {args.voice}  cfg={cfg}  takes={args.n}", flush=True)

    takes = []
    for i, seed in enumerate(seeds, 1):
        base = f"{args.voice}_{args.label}_{i:02d}_s{seed}"
        wav = os.path.join(outdir, base + ".wav")
        mp3 = os.path.join(outdir, base + ".mp3")
        try:
            eng.generate(prepared, language="english", voice_name=args.voice,
                         output_path=wav, seed=seed)
            subprocess.run(["ffmpeg", "-y", "-i", wav, mp3],
                           capture_output=True, check=True)
            takes.append({"idx": i, "seed": seed, "file": wav, "mp3": mp3})
            print(f"[{i}/{args.n}] seed={seed} -> {mp3}", flush=True)
        except Exception as e:
            print(f"[{i}/{args.n}] seed={seed} FAILED: {e}", flush=True)

    manifest = {
        "voice": args.voice,
        "cfg": cfg,
        "batch": args.label,
        "text": prepared,
        "created": datetime.now().isoformat(),
        "takes": takes,
    }
    mpath = os.path.join(outdir, f"{args.voice}_{args.label}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("MANIFEST:", mpath, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
