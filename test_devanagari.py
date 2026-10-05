"""Test F5-TTS with Devanagari script"""
import sys
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")

from f5_tts.api import F5TTS

tts = F5TTS()

# Test script with Devanagari
test_text = "That was चूड़ी बजी है from Udit Narayan and Alka Yagnik. Up next, Lata Mangeshkar."

print(f"Testing: {test_text}\n")

wav, sr, spec = tts.infer(
    ref_file="voice_references/radio_intro_sirius.mp3.wav",
    ref_text="Hey, welcome to Experiment FM one-oh-five point nine. I'm your AI host for tonight. We've got an incredible mix of music from around the world, so sit back, relax, and let's get into it.",
    gen_text=test_text,
    file_wave="test_devanagari.wav",
    nfe_step=64,
    cfg_strength=2.0,
    sway_sampling_coef=-1.0
)

print(f"\n✓ Generated: test_devanagari.wav ({len(wav)/sr:.1f}s)")
print("Play it to check pronunciation!")
