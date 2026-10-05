"""Test multi-voice TTS system"""
from tts_engine import TTSEngine
from voice_config import VOICES
import time

print("=== Testing Multi-Voice TTS System ===\n")

# Initialize TTS
tts = TTSEngine(main_dj_gender="male")

# Test each language
tests = [
    ("english", "male", "Hey, this is your English male DJ speaking."),
    ("english", "female", "And here's your English female DJ."),
    ("indonesian", "male", "Halo, ini DJ Indonesia pria."),
    ("indonesian", "female", "Halo, ini DJ Indonesia wanita."),
    ("spanish", "male", "Hola, soy tu DJ español masculino."),
    ("spanish", "female", "Hola, soy tu DJ español femenino."),
    ("hindi", "male", "Namaste, main aapka Hindi male DJ hoon."),
    ("hindi", "female", "Namaste, main aapki Hindi female DJ hoon.")
]

print("Generating test samples...\n")

for lang, gender, text in tests:
    print(f"Testing: {lang.upper()} {gender}")
    try:
        output = tts.generate(
            text=text,
            language=lang,
            gender=gender,
            output_path=f"test_{lang}_{gender}.wav"
        )
        print(f"  ✓ Generated: {output}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    print()
    time.sleep(1)  # Small delay between generations

print("=== Test Complete ===")
print("\nCheck the generated test_*.wav files to verify voice quality!")
