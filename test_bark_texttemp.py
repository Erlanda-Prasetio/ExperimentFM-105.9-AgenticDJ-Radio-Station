"""
Test Bark TTS with higher text_temp for more natural pronunciation
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np

print("Loading Bark models...")
preload_models()

text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"\nGenerating with Bark (text_temp=0.9 for more natural pronunciation)...")
print(f"Text: {text}\n")

# Higher text_temp = more pronunciation variation & naturalness
audio_array = generate_audio(
    text, 
    history_prompt="v2/en_speaker_6",
    text_temp=0.9,       # Higher for more natural variation
    waveform_temp=0.7    # Default audio quality
)

print(f"✓ Generated: {len(audio_array)} samples @ {SAMPLE_RATE}Hz")

# Save
write_wav("test_bark_texttemp09.wav", SAMPLE_RATE, audio_array)
print("✓ test_bark_texttemp09.wav")
