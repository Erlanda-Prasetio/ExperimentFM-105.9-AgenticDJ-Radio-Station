"""Generate station ident: music bed + TTS voice"""
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import sys
import os

# Add TTS project to path
sys.path.insert(0, "C:/sourceCode/TTS")

def generate_music_bed(duration=8.0, samplerate=44100):
    """Generate atmospheric synth pad"""
    t = np.linspace(0, duration, int(samplerate * duration))
    
    # Chord: A minor (A, C, E)
    freq_a = 220.0  # A3
    freq_c = 261.63  # C4
    freq_e = 329.63  # E4
    
    # Generate harmonics with envelope
    envelope = np.exp(-t * 0.3)  # Slow decay
    
    wave_a = 0.3 * np.sin(2 * np.pi * freq_a * t) * envelope
    wave_c = 0.25 * np.sin(2 * np.pi * freq_c * t) * envelope
    wave_e = 0.2 * np.sin(2 * np.pi * freq_e * t) * envelope
    
    # Mix
    mixed = wave_a + wave_c + wave_e
    
    # Add some reverb-like effect (simple delay)
    delay_samples = int(0.1 * samplerate)
    delayed = np.pad(mixed, (delay_samples, 0))[:-delay_samples] * 0.3
    mixed = mixed + delayed
    
    # Normalize
    mixed = mixed / np.max(np.abs(mixed)) * 0.4
    
    # Stereo
    stereo = np.stack([mixed, mixed]).T
    
    return stereo, samplerate

# Generate music bed
print("Generating music bed...")
music, sr = generate_music_bed(duration=8.0)
sf.write("ident_music.wav", music, sr)
print("✓ Music bed created: ident_music.wav")

# Generate voice with F5-TTS
print("\nGenerating voice with F5-TTS...")

# Use F5-TTS API
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")
from f5_tts.api import F5TTS

tts = F5TTS()
wav, sr, spec = tts.infer(
    ref_file="C:/sourceCode/TTS/carina_7s.wav",
    ref_text="I am Anna. The tension breaks. He stops. He hears the raw plea in my voice and he pulls back immediately.",
    gen_text="You're listening to Experiment FM, one oh five point nine.",
    file_wave="ident_voice.wav"
)

print(f"✓ Voice created: ident_voice.wav ({len(wav)/sr:.1f}s)")

# Mix them together with pydub
print("\nMixing music + voice...")
music_audio = AudioSegment.from_wav("ident_music.wav")
voice_audio = AudioSegment.from_wav("ident_voice.wav")

# Start voice at 1 second
voice_start_ms = 1000

# Lower music volume when voice plays
music_quiet = music_audio - 8  # -8dB when voice plays

# Overlay voice
final = music_quiet.overlay(voice_audio, position=voice_start_ms)

# Fade out at end
final = final.fade_out(1000)

# Export
final.export("station_ident.wav", format="wav")
print("✓ Station ident created: station_ident.wav")

print("\n✓ Done! Duration:", len(final) / 1000, "seconds")

# Clean up temp files
os.remove("ident_music.wav")
os.remove("ident_voice.wav")
