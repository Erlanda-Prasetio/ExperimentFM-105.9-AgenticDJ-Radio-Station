"""
Test Bark TTS with lower waveform_temp for cleaner audio
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np

print("Loading Bark models...")
preload_models()

text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"\nGenerating with Bark (waveform_temp=0.5 for cleaner audio)...")
print(f"Text: {text}\n")

# Lower waveform_temp = less artifacts, cleaner output
audio_array = generate_audio(
    text, 
    history_prompt="v2/en_speaker_6",
    text_temp=0.7,       # Default pronunciation
    waveform_temp=0.5    # Lower for cleaner audio
)

print(f"✓ Generated: {len(audio_array)} samples @ {SAMPLE_RATE}Hz")

# Save
write_wav("test_bark_clean.wav", SAMPLE_RATE, audio_array)
print("✓ test_bark_clean.wav")
