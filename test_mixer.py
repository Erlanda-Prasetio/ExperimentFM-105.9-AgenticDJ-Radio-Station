"""Test the real-time mixer with generated audio"""
import numpy as np
import soundfile as sf
from audio_engine import RealtimeRadioMixer, AudioTrack
import time

def generate_tone(frequency: float, duration: float, samplerate: int = 44100) -> np.ndarray:
    """Generate a sine wave tone (stereo)"""
    t = np.linspace(0, duration, int(samplerate * duration))
    mono = 0.3 * np.sin(2 * np.pi * frequency * t)
    stereo = np.stack([mono, mono]).T  # (samples, 2)
    return stereo

# Create test audio files
print("Generating test audio files...")
tone_440 = generate_tone(440, 5.0)  # A note, 5 seconds
tone_880 = generate_tone(880, 5.0)  # A note octave higher, 5 seconds

sf.write("test_tone_a.wav", tone_440, 44100)
sf.write("test_tone_b.wav", tone_880, 44100)
print("Test files created: test_tone_a.wav, test_tone_b.wav")

# Test the mixer
print("\n=== Testing Mixer ===")
mixer = RealtimeRadioMixer()

# Load tracks
track_a = mixer.load_audio("test_tone_a.wav", "Track A (440Hz)")
track_b = mixer.load_audio("test_tone_b.wav", "Track B (880Hz)")

# Start mixer
mixer.start()

# Play first track
print("\n[Test] Playing Track A for 3 seconds...")
mixer.add_track(track_a, slot="deck_a")
time.sleep(3)

# Crossfade to second track
print("\n[Test] Crossfading to Track B (5 second fade)...")
track_b.position = 0  # Reset position
mixer.add_track(track_b, slot="deck_b")
mixer.set_volume("deck_b", 0.0)  # Start silent
mixer.crossfade("deck_a", "deck_b", duration=5.0)

time.sleep(6)  # Wait for crossfade + 1 sec

# Play Track B to completion
print("\n[Test] Playing Track B to completion...")
time.sleep(2)

# Stop
print("\n[Test] Stopping mixer...")
mixer.stop()

print("\n✓ Mixer test complete!")
