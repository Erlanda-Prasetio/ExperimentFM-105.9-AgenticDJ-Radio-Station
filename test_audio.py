"""Test sounddevice setup"""
import sounddevice as sd
import numpy as np

# List audio devices
print("Available audio devices:")
print(sd.query_devices())

# Generate a simple 440Hz tone (A note)
duration = 2  # seconds
samplerate = 44100
t = np.linspace(0, duration, int(samplerate * duration))
audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 0.3 volume

print("\nPlaying 440Hz test tone for 2 seconds...")
sd.play(audio, samplerate)
sd.wait()
print("Done!")
