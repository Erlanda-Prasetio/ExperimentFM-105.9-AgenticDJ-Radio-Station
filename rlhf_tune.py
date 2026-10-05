"""
Tuning sweep: fix seed 736123 (gold), vary cfg_strength, speed, and reference segment.

Goal: the calm reference killed artefacts but sounded FLAT and FAST.
- cfg_strength is the expressiveness knob (lower = livelier, higher = flatter/safer).
- speed (atempo) fixes the fast radio-read tempo.
- the intro-chat reference may have a more natural pace/variation than the ad read.
"""
import os
import sys
import subprocess

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

import voice_config
from phonetic_respell import respell, normalize_numbers
from tts_engine import TTSEngine

SEED = 736123
TEXT = "Experiment FM, one oh five point nine. That was a beautiful one to sit with, coming up next, something a little warmer for the ride home. Stay with me."

CALM = ("voice_references/voice_ref_jr.wav",
        "Owning a vehicle is a huge responsibility, right? But you can feel good about your purchase with Castle Rock's Warranty Forever. It gives you real powertrain coverage for as long as you own your vehicle and having that peace of mind is invaluable.")
INTRO = ("voice_references/candidates/voice_ref_jr_INTRO_chat.wav",
         "Alright, so one of the many things that we do in radio, aside from talking in and out of songs, is we actually do live endorsement reads for clients. I'm about to do one for one of mine right now, I got my notes right here, and I wanted to take you behind the board and show you a little bit about what that's like.")

# (tag, ref, cfg, speed)
GRID = [
    ("calm_cfg16_sp100", CALM, 1.6, 1.00),
    ("calm_cfg18_sp100", CALM, 1.8, 1.00),
    ("calm_cfg20_sp100", CALM, 2.0, 1.00),
    ("calm_cfg18_sp090", CALM, 1.8, 0.90),
    ("intro_cfg18_sp100", INTRO, 1.8, 1.00),
    ("intro_cfg18_sp090", INTRO, 1.8, 0.90),
]


def main():
    eng = TTSEngine(model="F5-TTS", main_dj_gender="male")
    prep = normalize_numbers(respell(TEXT)).replace("!", ".").replace("...", ",")
    outdir = os.path.join("tts_cache", "rlhf")
    os.makedirs(outdir, exist_ok=True)

    total = len(GRID)
    for i, (tag, ref, cfg, speed) in enumerate(GRID, 1):
        # swap the jr reference in-process (get_named_voice reads NAMED_VOICES live)
        voice_config.NAMED_VOICES["jr"]["file"] = ref[0]
        voice_config.NAMED_VOICES["jr"]["transcript"] = ref[1]
        wav = os.path.join(outdir, f"jr_tune_{tag}.wav")
        mp3 = os.path.join(outdir, f"jr_tune_{tag}.mp3")
        try:
            eng.generate(prep, language="english", voice_name="jr",
                         output_path=wav, seed=SEED, cfg_strength=cfg, speed=speed)
            subprocess.run(["ffmpeg", "-y", "-i", wav, mp3], capture_output=True, check=True)
            print(f"[{i}/{total}] {tag}  cfg={cfg} speed={speed} ref={os.path.basename(ref[0])}", flush=True)
        except Exception as e:
            print(f"[{i}/{total}] {tag} FAILED: {e}", flush=True)

    # restore calm ref on disk config (in-process only; file untouched)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
