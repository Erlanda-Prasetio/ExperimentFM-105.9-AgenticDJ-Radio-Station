"""
Quick test of XTTS-Hindi fine-tuned model
"""
import sys
sys.path.insert(0, "C:/sourceCode/TTS")

from TTS.api import TTS
import torch

print("Loading XTTS-Hindi model...")
tts = TTS(
    model_path="C:/sourceCode/TTS/xtts-hindi-model",
    config_path="C:/sourceCode/TTS/xtts-hindi-model/config.json",
    progress_bar=True,
    gpu=torch.cuda.is_available()
)

print("\nTesting Hindi pronunciation with Naksh voice...")

# Test text with Hindi
test_text = "That was Kabhi Khushi Kabhie Gham from Rab Ne Bana Di Jodi. Up next, keeping the romance alive."

# Use Naksh voice reference
speaker_wav = "voice_references/experiment_fm_intro_naksh.wav"

print(f"\nGenerating: {test_text}")
print(f"Reference: {speaker_wav}")

tts.tts_to_file(
    text=test_text,
    file_path="test_xtts_hindi_output.wav",
    speaker_wav=speaker_wav,
    language="hi"  # Hindi
)

print("\n✓ Generated: test_xtts_hindi_output.wav")
print("Play it to check Hindi pronunciation quality!")
