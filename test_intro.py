"""Test the song-intro detector on real library songs."""
import os
import sys
sys.path.insert(0, ".")
import song_intro

LIB = "C:/sourceCode/YT_Downloader/downloads/Wow, this ist gud"
PICKS = ["As It Was", "INDUSTRY BABY", "All of Me", "BIRDS OF A FEATHER",
         "Hymn for the Weekend", "Masih Ada", "Blinding Lights", "Save Your Tears"]

def find(sub):
    for root, _, fs in os.walk(LIB):
        for f in fs:
            if sub.lower() in f.lower() and f.lower().endswith(".mp3"):
                return os.path.join(root, f)
    return None

print("=== intro detection (seconds until main body) ===\n")
found = 0
for sub in PICKS:
    fp = find(sub)
    if not fp:
        print(f"  {sub:26} (not found)")
        continue
    found += 1
    t = song_intro.detect_intro(fp)
    print(f"  {sub:26} intro ~ {t:5.1f}s")
print(f"\n  detected {found} songs")

# cache check
fp = find(PICKS[0])
if fp:
    import time
    t0 = time.time(); a = song_intro.detect_intro(fp); t1 = time.time()
    b = song_intro.detect_intro(fp); t2 = time.time()
    print(f"\n  cache: 1st={t1-t0:.2f}s  2nd={t2-t1:.4f}s  same={a==b}")
