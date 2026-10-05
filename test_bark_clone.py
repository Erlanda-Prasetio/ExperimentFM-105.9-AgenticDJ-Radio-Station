"""
Bark Voice Cloning - Generate custom voice from Naksh reference
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from bark import SAMPLE_RATE, generate_audio, preload_models
from bark.generation import load_codec_model, generate_text_semantic
from bark.api import semantic_to_waveform
from scipy.io.wavfile import write as write_wav, read as read_wav
import numpy as np
import torch

print("Loading Bark models...")
preload_models()

# Load reference audio
ref_audio_path = r"C:\sourceCode\RadioExperiment\voice_references\experiment_fm_intro_very_thick_indian_naksh.mp3"
print(f"\nLoading reference audio: {ref_audio_path}")

# Convert MP3 to WAV first (Bark needs WAV)
import subprocess
temp_wav = "temp_naksh_ref.wav"
print("Converting MP3 to WAV...")
subprocess.run([
    "ffmpeg", "-y", "-i", ref_audio_path, 
    "-ar", "24000",  # Bark sample rate
    "-ac", "1",      # Mono
    temp_wav
], check=True, capture_output=True)

print("Generating voice prompt from reference...")
# This creates the custom history prompt
from bark.generation import generate_voice_prompt
voice_prompt = generate_voice_prompt(temp_wav)
print(f"✓ Voice prompt generated: {len(voice_prompt)} tokens")

# Save it for reuse
np.savez("naksh_voice_prompt.npz", **voice_prompt)
print("✓ Saved as naksh_voice_prompt.npz")

# Test generation with cloned voice
text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"\nGenerating with cloned Naksh voice...")
print(f"Text: {text}\n")

audio_array = generate_audio(text, history_prompt=voice_prompt)

print(f"✓ Generated: {len(audio_array)} samples @ {SAMPLE_RATE}Hz")

# Save
write_wav("test_bark_naksh_cloned.wav", SAMPLE_RATE, audio_array)
print("✓ test_bark_naksh_cloned.wav")

# Cleanup
import os
os.remove(temp_wav)
