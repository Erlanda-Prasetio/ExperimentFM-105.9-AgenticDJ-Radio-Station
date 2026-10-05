"""
Bark Voice Cloning - Create custom Naksh voice prompt
"""
import sys
sys.path.insert(0, r'C:\sourceCode\TTS')

from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np

print("Loading Bark models...")
preload_models()

# Naksh's reference transcript
naksh_transcript = "Namaste and welcome to Experiment FM one-oh-five point nine. I'm your host for the evening. We've got an amazing collection of Bollywood hits lined up for you tonight, from the classics to the latest chartbusters. So sit back, relax, and let the music take over."

print(f"\nStep 1: Generating voice prompt from Naksh transcript...")
print(f"Reference text: {naksh_transcript[:80]}...\n")

# Generate with output_full to get voice prompt
voice_prompt, audio_array = generate_audio(
    naksh_transcript,
    history_prompt="v2/en_speaker_6",  # Start from similar voice
    output_full=True
)

print(f"✓ Voice prompt created: {type(voice_prompt)}")

# Save the voice prompt for reuse
if isinstance(voice_prompt, dict):
    np.savez("naksh_bark_voice.npz", **voice_prompt)
elif isinstance(voice_prompt, np.ndarray):
    np.savez("naksh_bark_voice.npz", semantic_prompt=voice_prompt)
else:
    # Save as-is
    np.save("naksh_bark_voice.npy", voice_prompt)
print("✓ Saved as naksh_bark_voice")

# Test with new text
test_text = """Good evening, you're listening to Experiment FM. That was the beautiful Arijit Singh with Tum Hi Ho from Aashiqui 2. Such a soulful track. Coming up next, we've got another romantic classic - Kabhi Khushi Kabhie Gham from the movie Rab Ne Bana Di Jodi. Stay tuned for more of your favorite Bollywood hits."""

print(f"\nStep 2: Generating with cloned Naksh voice...")
print(f"Text: {test_text[:80]}...\n")

audio_cloned = generate_audio(test_text, history_prompt=voice_prompt)

print(f"✓ Generated: {len(audio_cloned)} samples @ {SAMPLE_RATE}Hz")

# Save
write_wav("test_bark_naksh_cloned.wav", SAMPLE_RATE, audio_cloned)
print("✓ test_bark_naksh_cloned.wav")
