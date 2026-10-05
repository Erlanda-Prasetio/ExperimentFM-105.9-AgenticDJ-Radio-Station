"""
Test Kokoro TTS for DJ voice
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from kokoro import KPipeline

# Initialize American English pipeline
print("Loading Kokoro pipeline...")
pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')

text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"Generating with Kokoro (am_adam voice)...")
print(f"Text: {text}\n")

# Generate - returns generator of Result objects
results = list(pipeline(text, voice='am_adam', speed=1.0))
# Concatenate all audio chunks
import numpy as np
audio = np.concatenate([r.audio.cpu().numpy() for r in results])
sr = 24000  # Kokoro sample rate

# Save
import scipy.io.wavfile as wavfile
wavfile.write("test_kokoro_adam.wav", sr, audio)
print("✓ test_kokoro_adam.wav")
