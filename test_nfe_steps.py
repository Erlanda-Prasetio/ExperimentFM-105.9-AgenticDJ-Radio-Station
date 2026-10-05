"""Test different nfe_step values"""
import sys
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")

from f5_tts.api import F5TTS

tts = F5TTS()

test_steps = [32, 64, 96, 128, 192]

for steps in test_steps:
    try:
        print(f"\n=== Testing nfe_step={steps} ===")
        wav, sr, spec = tts.infer(
            ref_file="voice_references/radio_intro_sirius.mp3.wav",
            ref_text="Hey, welcome to Experiment FM one-oh-five point nine.",
            gen_text="Testing steps.",
            file_wave=f"test_nfe_{steps}.wav",
            nfe_step=steps,
            cfg_strength=2.0,
            sway_sampling_coef=-1.0
        )
        print(f"✓ nfe_step={steps} WORKS ({len(wav)/sr:.1f}s)")
    except Exception as e:
        print(f"✗ nfe_step={steps} FAILED: {e}")
