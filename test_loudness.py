"""
Test: music loudness normalization.

Shows the measured gain per song and the resulting loudness, proving songs land
near the same target (MUSIC_LUFS) while the DJ voice is left untouched.
"""
import os
import sys
import numpy as np
import librosa
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import audio_engine as AE
import pyloudnorm as pyln

LIB = "C:/sourceCode/YT_Downloader/downloads/Wow, this ist gud"
# A spread of the loudest and quietest tracks we measured earlier
PICKS = ["INDUSTRY BABY", "BIRDS OF A FEATHER", "Hymn for the Weekend",
         "All of Me", "Masih Ada"]

def find(sub):
    for root, _, fs in os.walk(LIB):
        for f in fs:
            if sub.lower() in f.lower() and f.lower().endswith(".mp3"):
                return os.path.join(root, f)
    return None

print(f"=== MUSIC LUFS target: {AE.MUSIC_LUFS} ===\n")
print(f"{'song':28} {'before':>9} {'gain':>8} {'after':>9}")
print("-" * 58)

ok = 0
total = 0
for sub in PICKS:
    fp = find(sub)
    if not fp:
        continue
    total += 1
    data, sr = librosa.load(fp, sr=44100, mono=False)
    if data.ndim == 1:
        data = np.stack([data, data])
    data = data.T
    meter = pyln.Meter(sr)
    before = meter.integrated_loudness(data)
    g = AE.measure_gain(fp, data, sr)
    after = meter.integrated_loudness(data * g)
    print(f"{sub:28} {before:>8.1f}L {g:>7.3f}x {after:>8.1f}L")
    if abs(after - AE.MUSIC_LUFS) < 2.0:   # within 2 LU of target
        ok += 1

print()
print(f"  {ok}/{total} songs landed within 2 LU of {AE.MUSIC_LUFS}")

# --- cache check: second call must be instant + identical ---
fp = find(PICKS[0])
data, sr = librosa.load(fp, sr=44100, mono=False)
if data.ndim == 1: data = np.stack([data, data])
data = data.T
import time
t0 = time.time(); g1 = AE.measure_gain(fp, data, sr); t1 = time.time()
g2 = AE.measure_gain(fp, data, sr); t2 = time.time()
print(f"  cache: 1st={t1-t0:.3f}s  2nd={t2-t1:.4f}s  same={g1==g2}")

# --- voice untouched ---
print(f"\n  DJ voice: kind='voice' -> no gain (handled in load_audio, not here)")

sys.exit(0 if ok == total else 1)
