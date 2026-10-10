"""
Radio audio processing chain
Professional broadcast sound: compression, EQ, reverb, limiting, LUFS normalization

Sibilance ("sss" / "sh" / "ch" harshness) is handled per-voice via a dynamic
STFT de-esser. See `de_ess_spec` in voice_config.py: voices whose reference clip
is sibilant (e.g. Cara) get a spec; clean voices (e.g. Jerry) get none and are
processed exactly as before.
"""
import numpy as np
from pedalboard import (Pedalboard, HighpassFilter, PeakFilter,
                        HighShelfFilter, Compressor, Reverb, Limiter, Gain)
from pedalboard.io import AudioFile
import pyloudnorm as pyln


# ---------------------------------------------------------------------------
# Sibilance treatment
# ---------------------------------------------------------------------------
def peak_normalize(y: np.ndarray, target_db: float = -6.0) -> np.ndarray:
    """Scale so the absolute peak sits at `target_db` (gain staging)."""
    pk = np.max(np.abs(y)) + 1e-12
    return y * (10 ** (target_db / 20.0) / pk)


def de_esser_stft(y: np.ndarray, sr: int = 48000, bands=None,
                  n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    """Phase-consistent STFT de-esser.

    For each band it measures the per-frame band energy, derives a gain
    reduction that only engages above a threshold, and scales the magnitude of
    the bins in that band. Phase is untouched, so reconstruction is clean (no
    split-band filter artifacts).

    Thresholds are RELATIVE: each band's threshold sits `thr_below` dB under the
    95th percentile of that band's own envelope, so the de-esser engages on
    genuine sibilant spikes rather than every frame (which would just be a
    static EQ cut).

    bands: list of (lo_hz, hi_hz, thr_below_p95_db, max_reduction_db, release_ms)
    """
    import librosa
    if bands is None:
        bands = [
            (3000, 6000, -8.0, -5.0, 60.0),    # 'sh' / 'ch'
            (6000, 10000, -8.0, -7.0, 60.0),   # 's'
        ]
    y = np.asarray(y, dtype=np.float32)
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    mag = np.abs(S)
    phase = np.angle(S)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    for lo, hi, thr_below, maxred, rel_ms in bands:
        b = (freqs >= lo) & (freqs < hi)
        if not b.any():
            continue
        band_mag = mag[b, :].sum(axis=0)
        a_rel = np.exp(-1.0 / (sr / hop * rel_ms / 1000.0))
        env = np.empty_like(band_mag)
        prev = 0.0
        for i in range(len(band_mag)):
            prev = a_rel * prev + (1 - a_rel) * band_mag[i]
            env[i] = prev
        env_db = 20 * np.log10(env + 1e-12)
        thr = np.percentile(env_db, 95) + thr_below
        over = env_db - thr
        gr_db = np.minimum(0.0, np.maximum(-over, maxred))
        mag[b, :] *= (10 ** (gr_db / 20.0))[None, :]

    S2 = mag * np.exp(1j * phase)
    return librosa.istft(S2, hop_length=hop, length=len(y)).astype(np.float32)


def reduce_breaths(y: np.ndarray, sr: int = 48000, win_ms: int = 30,
                   floor_db: float = -40.0, reduction_db: float = -8.0) -> np.ndarray:
    """Pull down breath noise (quiet, non-voiced stretches) without gating."""
    hop = int(sr * win_ms / 1000)
    n = len(y)
    nwin = max(1, n // hop)
    env = np.array([np.sqrt(np.mean(y[i*hop:(i+1)*hop]**2) + 1e-12)
                    for i in range(nwin)])
    env_db = 20 * np.log10(env + 1e-12)
    peak_db = np.percentile(env_db, 98)
    is_breath = (env_db < peak_db + floor_db) & (env_db > -80)
    gain = np.ones(nwin)
    gain[is_breath] = 10 ** (reduction_db / 20.0)
    gain = np.convolve(gain, np.ones(5)/5, mode='same')
    gain_s = np.interp(np.arange(n), np.arange(nwin)*hop, gain, right=1.0)
    return y * gain_s


def _apply_de_ess(audio: np.ndarray, sr: int, spec: dict) -> np.ndarray:
    """Apply the optional sibilance treatment described by `spec` (per voice).

    spec keys (all optional):
        de_ess     : list of (lo, hi, thr_below, max_red, release_ms) bands
        gain_stage : peak target dB for pre-normalization (e.g. -6.0)
        breaths    : bool, pull breaths down
    Operates on (channels, samples); processes each channel identically.
    """
    if not spec:
        return audio
    mono_shape = audio.ndim == 2
    if mono_shape:
        chans = [audio[c] for c in range(audio.shape[0])]
    else:
        chans = [audio]

    out = []
    for ch in chans:
        x = np.asarray(ch, dtype=np.float32)
        if spec.get("gain_stage") is not None:
            x = peak_normalize(x, float(spec["gain_stage"]))
        if spec.get("de_ess"):
            x = de_esser_stft(x, sr=sr, bands=[tuple(b) for b in spec["de_ess"]])
        if spec.get("breaths"):
            x = reduce_breaths(x, sr=sr)
        out.append(x.astype(np.float32))

    return np.stack(out, axis=0) if mono_shape else out[0]


def _broadcast_board(comp_attack_ms: float = 8.0, presence_db: float = 1.5,
                     chsh_cut: bool = False, shelf_db: float = -2.0,
                     shelf_hz: float = 8000):
    """The shared broadcast EQ/comp/reverb/limiter stack.

    Default args reproduce the ORIGINAL chain exactly (presence +1.5 @3.5k,
    shelf -2 @8k, no ch/sh cut). De-essed voices pass gentler values so the
    de-esser isn't fighting a presence boost.
    """
    stages = [
        HighpassFilter(cutoff_frequency_hz=80),
        PeakFilter(cutoff_frequency_hz=300, gain_db=2.5, q=0.8),
        PeakFilter(cutoff_frequency_hz=3500, gain_db=presence_db, q=0.8),
    ]
    if chsh_cut:
        stages.append(PeakFilter(cutoff_frequency_hz=6500, gain_db=-2.0, q=1.1))
    stages += [
        HighShelfFilter(cutoff_frequency_hz=shelf_hz, gain_db=shelf_db),
        Compressor(threshold_db=-18, ratio=3, attack_ms=comp_attack_ms, release_ms=120),
        Gain(gain_db=3),
        Reverb(room_size=0.15, wet_level=0.08, dry_level=0.95),
        Limiter(threshold_db=-1.0),
    ]
    return Pedalboard(stages)


def radio_processing(in_path: str, out_path: str, sr: int = 48000,
                     de_ess_spec: dict = None):
    """
    Apply professional radio processing chain

    Args:
        in_path: Input audio file
        out_path: Output processed file
        sr: Sample rate (default 48kHz for broadcast quality)
        de_ess_spec: optional per-voice sibilance treatment (see _apply_de_ess).
            When None the chain is byte-for-byte the original behaviour.
    """
    # Load and resample
    with AudioFile(in_path).resampled_to(sr) as f:
        audio = f.read(f.frames)  # shape: (channels, samples)

    # Pad so the reverb tail isn't cut off
    audio = np.pad(audio, ((0, 0), (0, int(sr * 0.5))))

    if de_ess_spec:
        # Gain stage + dynamic de-ess BEFORE the EQ, so the de-esser sees the
        # raw sibilance and the presence boost doesn't re-introduce it.
        audio = _apply_de_ess(audio, sr, de_ess_spec)
        # Gentler presence/shelf so we don't undo the de-essing.
        board = _broadcast_board(
            comp_attack_ms=float(de_ess_spec.get("comp_attack_ms", 25.0)),
            presence_db=float(de_ess_spec.get("presence_db", 0.5)),
            chsh_cut=True,
            shelf_db=float(de_ess_spec.get("shelf_db", -2.0)),
            shelf_hz=float(de_ess_spec.get("shelf_hz", 9000)),
        )
    else:
        board = _broadcast_board()   # original chain

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
