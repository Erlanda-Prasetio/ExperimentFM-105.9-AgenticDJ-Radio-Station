"""Test F5-TTS with full Hindi script using Naksh voice"""
import sys
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")

from f5_tts.api import F5TTS

tts = F5TTS()

# Hindi test text (song title + simple phrase)
hindi_text = "चूड़ी बजी है। यह गाना बहुत सुंदर है।"
print(f"Testing Hindi: {hindi_text}\n")

# Use Naksh (Hindi male) voice
wav, sr, spec = tts.infer(
    ref_file="voice_references/hindi_radio_naksh.mp3.wav",
    ref_text="Namaste doston, aap sun rahe hain Experiment FM. Aaj raat humne aapke liye Bollywood se lekar indie music tak, sabhi kuch taiyar kiya hai. Toh chaliye, music ke saath enjoy karte hain.",
    gen_text=hindi_text,
    file_wave="test_hindi_naksh.wav",
    nfe_step=64,
    cfg_strength=2.0,
    sway_sampling_coef=-1.0
)

print(f"\n✓ Generated: test_hindi_naksh.wav ({len(wav)/sr:.1f}s)")
print("Play to check if Naksh pronounces pure Hindi!")
