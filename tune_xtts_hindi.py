"""
XTTS-Hindi Tuning Script
Test different speed/temperature settings for better pacing
"""
import os
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from TTS.api import TTS

# Load XTTS-Hindi model
print("Loading XTTS-Hindi model...")
tts = TTS(
    model_path=r"C:\sourceCode\TTS\xtts-hindi-model",
    config_path=r"C:\sourceCode\TTS\xtts-hindi-model\config.json",
    gpu=True
)
print()

test_text = "That was Kabhi Khushi Kabhie Gham from Rab Ne Bana Di Jodi. Up next, keeping the romance alive."
ref_audio = "voice_references/experiment_fm_intro_naksh.wav"

# Test different settings
configs = [
    # (name, speed, temperature, repetition_penalty)
    ("default", 1.0, 0.75, 5.0),
    ("faster", 1.2, 0.75, 5.0),
    ("faster_crisp", 1.3, 0.65, 6.0),
    ("fastest", 1.5, 0.65, 7.0),
    ("natural_fast", 1.2, 0.8, 4.0),
]

print(f"Testing: {test_text}\n")

for name, speed, temp, rep_penalty in configs:
    print(f"Generating [{name}] speed={speed}, temp={temp}, rep_penalty={rep_penalty}")
    output = f"test_xtts_hindi_{name}.wav"
    
    try:
        tts.tts_to_file(
            text=test_text,
            file_path=output,
            speaker_wav=ref_audio,
            language="en",
            speed=speed,
            temperature=temp,
            repetition_penalty=rep_penalty,
        )
        print(f"  ✓ {output}\n")
    except Exception as e:
        print(f"  ✗ Error: {e}\n")

print("\n🎵 Listen to all variants and pick the best!")
print("Files: test_xtts_hindi_*.wav")
