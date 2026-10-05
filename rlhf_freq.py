"""
Focused fix: the frequency phrase "one oh five point nine".

User: "maybe fix the 1 oh 5, and some knob, but that's it"

The token "one oh five" is where artefacts cluster. Test SPELLING variants so the
model renders it cleanly. Hype reference restored, cfg 1.8.

Variants for the frequency phrase:
  v1  one oh five point nine      (current normalize_numbers output)
  v2  one-oh-five point nine      (hyphenated -> single token, fewer seams)
  v3  one o five point nine       ("o" letter name)
  v4  wun oh five point nine      (phonetic 'one')
  v5  one oh five, point nine     (comma breath before point nine)
"""
import os
import sys
import subprocess

from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, ".")

from tts_engine import TTSEngine

SEED = 736123
CFG = 1.8
OUTDIR = os.path.join("tts_cache", "rlhf")

TEMPLATE = "You're listening to {freq}. Stay with me through the night."

VARIANTS = {
    "v1_oh":       "one oh five point nine",
    "v2_hyphen":   "one-oh-five point nine",
    "v3_o":        "one o five point nine",
    "v4_wun":      "wun oh five point nine",
    "v5_comma":    "one oh five, point nine",
}


def main():
    eng = TTSEngine(model="F5-TTS", main_dj_gender="male")
    total = len(VARIANTS)
    for i, (tag, freq) in enumerate(VARIANTS.items(), 1):
        text = TEMPLATE.format(freq=freq)
        wav = os.path.join(OUTDIR, f"jr_freq_{tag}.wav")
        mp3 = os.path.join(OUTDIR, f"jr_freq_{tag}.mp3")
        try:
            eng.generate(text, language="english", voice_name="jr",
                         output_path=wav, seed=SEED, cfg_strength=CFG, speed=1.0)
            subprocess.run(["ffmpeg", "-y", "-i", wav, mp3], capture_output=True, check=True)
            print(f"[{i}/{total}] {tag}: '{freq}' -> jr_freq_{tag}.mp3", flush=True)
        except Exception as e:
            print(f"[{i}/{total}] {tag} FAILED: {e}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
