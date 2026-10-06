"""
Radio audio processing chain
Professional broadcast sound: compression, EQ, reverb, limiting, LUFS normalization
"""
import numpy as np
from pedalboard import (Pedalboard, HighpassFilter, PeakFilter,
                        HighShelfFilter, Compressor, Reverb, Limiter, Gain)
from pedalboard.io import AudioFile
import pyloudnorm as pyln


def radio_processing(in_path: str, out_path: str, sr: int = 48000):
    """
    Apply professional radio processing chain
    
    Args:
        in_path: Input audio file
        out_path: Output processed file
        sr: Sample rate (default 48kHz for broadcast quality)
    """
    # Load and resample
    with AudioFile(in_path).resampled_to(sr) as f:
        audio = f.read(f.frames)  # shape: (channels, samples)

    # Pad so the reverb tail isn't cut off
    audio = np.pad(audio, ((0, 0), (0, int(sr * 0.5))))

    # Professional radio chain
    board = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=80),                     # Remove rumble
        PeakFilter(cutoff_frequency_hz=300, gain_db=2.5, q=0.8),   # Warmth
        PeakFilter(cutoff_frequency_hz=3500, gain_db=1.5, q=0.8),  # Presence
        HighShelfFilter(cutoff_frequency_hz=8000, gain_db=-2),     # Smooth highs
        Compressor(threshold_db=-18, ratio=3, attack_ms=8, release_ms=120),
        Gain(gain_db=3),                                            # Makeup gain
        Reverb(room_size=0.15, wet_level=0.08, dry_level=0.95),   # Subtle room
        Limiter(threshold_db=-1.0),                                 # Prevent clipping
    ])
    audio = board(audio, sr)

    # Normalize to broadcast standard -16 LUFS
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(audio.T)
    audio = pyln.normalize.loudness(audio.T, lufs, -16.0).T
    audio = np.clip(audio, -0.99, 1.0)

    # Write processed audio
    with AudioFile(out_path, "w", sr, audio.shape[0]) as f:
        f.write(audio)
    
    print(f"[Audio Processing] Applied radio chain: {out_path}")


def apply_voice_eq(in_path: str, out_path: str, eq_spec: dict, sr: int = 48000):
    """
    Apply a per-voice corrective EQ AFTER the broadcast chain.

    Used for individual DJ voices that need extra shaping (e.g. a piercing treble
    that only affects one voice). Leaves all other voices untouched.

    eq_spec shape:
        {"peaks":  [[freq_hz, gain_db, q], ...],
         "shelves":[[freq_hz, gain_db], ...]}

    Re-normalizes to -16 LUFS so loudness is unchanged.
    """
    if not eq_spec:
        return
    stages = []
    for freq, gain, q in eq_spec.get("peaks", []):
        stages.append(PeakFilter(cutoff_frequency_hz=freq, gain_db=gain, q=q))
    for freq, gain in eq_spec.get("shelves", []):
        stages.append(HighShelfFilter(cutoff_frequency_hz=freq, gain_db=gain))
    if not stages:
        return

    board = Pedalboard(stages)
    with AudioFile(in_path).resampled_to(sr) as f:
        audio = f.read(f.frames)
    audio = board(audio, sr)

    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(audio.T)
    audio = pyln.normalize.loudness(audio.T, lufs, -16.0).T
    audio = np.clip(audio, -0.99, 1.0)

    with AudioFile(out_path, "w", sr, audio.shape[0]) as f:
        f.write(audio)

    print(f"[Audio Processing] Applied per-voice EQ: {out_path}")
