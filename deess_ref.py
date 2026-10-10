"""De-ess a voice reference clip BEFORE cloning.

Why: if the source reference is sibilant, the TTS model (F5 / Qwen) learns and
reproduces that sibilance. Cleaning the reference attacks the problem at the
source instead of only patching the output. This is how `cara_ref_deessed.wav`
was produced from "[DJ CARA (GTA V)] Hey.mp3".

Usage:
    python deess_ref.py <in.wav|in.mp3> <out.wav> [--sr 24000]

Then point the voice's "file" in voice_config.py at <out.wav> and give the voice
a "de_ess" spec (see NAMED_VOICES["ara"]).
"""
import argparse
import os
import numpy as np
import soundfile as sf
import librosa


def de_ess_stft(y, sr, bands, n_fft=1024, hop=256):
    """Phase-consistent STFT de-esser (relative thresholds, per band)."""
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
        thr = np.percentile(env_db, 90) + thr_below
        over = env_db - thr
        gr_db = np.minimum(0.0, np.maximum(-over, maxred))
        mag[b, :] *= (10 ** (gr_db / 20.0))[None, :]
    S2 = mag * np.exp(1j * phase)
    return librosa.istft(S2, hop_length=hop, length=len(y)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--sr", type=int, default=24000)
    ap.add_argument("--band", action="append", default=None,
                    help="lo,hi,thr_below,max_red,release_ms (repeatable)")
    args = ap.parse_args()

    sr_target = args.sr
    y, sr = sf.read(args.src)
    if y.ndim > 1:
        y = y.mean(1)
    if sr != sr_target:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(sr), int(sr_target))
        y = resample_poly(y, sr_target // g, sr // g)
    y = y.astype(np.float32)
    print(f"[deess-ref] in: {len(y)/sr_target:.1f}s @ {sr_target}Hz")

    if args.band:
        bands = [tuple(float(x) for x in b.split(",")) for b in args.band]
    else:
        # Female-voice defaults (Cara): 'sh/ch' at 3-6k, 's' at 6-10k.
        bands = [
            (3000, 6000, -10.0, -8.0, 50.0),
            (6000, 10000, -10.0, -12.0, 50.0),
        ]

    y2 = de_ess_stft(y, sr_target, bands)
    pk = np.max(np.abs(y2)) + 1e-12
    if pk > 0.99:
        y2 = y2 / pk * 0.99
    sf.write(args.dst, y2, sr_target)
    print(f"[deess-ref] out: {args.dst}")

    def bands_e(sig):
        S = np.abs(librosa.stft(sig, n_fft=1024, hop_length=256)) ** 2
        fr = librosa.fft_frequencies(sr=sr_target, n_fft=1024)
        g = lambda lo, hi: S[(fr >= lo) & (fr < hi)].sum()
        return g(300, 3000), g(3000, 6000), g(6000, 10000)
    b1, s1, e1 = bands_e(y)
    b2, s2, e2 = bands_e(y2)
    print(f"  sh/body: {s1/b1:.4f} -> {s2/b2:.4f}")
    print(f"  s/body : {e1/b1:.4f} -> {e2/b2:.4f}")


if __name__ == "__main__":
    main()
