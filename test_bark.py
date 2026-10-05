"""
Test Bark TTS for DJ voice
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np

print("Loading Bark models (first time will download ~10GB)...")
preload_models()

text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"\nGenerating with Bark...")
print(f"Text: {text}\n")

# Bark speaker presets:
# v2/en_speaker_0-9: American English voices
# Use speaker_6 (male, clear voice good for radio)
audio_array = generate_audio(text, history_prompt="v2/en_speaker_6")

print(f"✓ Generated audio: {len(audio_array)} samples @ {SAMPLE_RATE}Hz")

# Save
write_wav("test_bark_speaker6.wav", SAMPLE_RATE, audio_array)
print("✓ test_bark_speaker6.wav")
