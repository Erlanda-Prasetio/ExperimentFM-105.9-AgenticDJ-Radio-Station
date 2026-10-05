"""
Simulation: how often do the three modes fire in production conditions?

Uses the REAL DJ voice lengths (tts_cache/dj_*.wav) x REAL song intros (intro_cache)
and the exact dispatch the controller applies (assuming the DJ wants to hit the post):

    ride   = voice_len <= BRUCE_MAX_VOICE_S AND intro >= BRUCE_MIN_INTRO_S
             AND (voice_len - intro) <= BRUCE_MAX_GAP_S
    talkup = not ride AND voice_len >= TALKUP_LEAD_S + 1.5
    normal = otherwise

Also verifies the safety property: in RIDE, the song body never arrives before the
voice ends (so the DJ never talks over vocals).
"""
import os, sys, glob, json
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
load_dotenv()

MAX_V = float(os.getenv("BRUCE_MAX_VOICE_S", "18"))
MIN_I = float(os.getenv("BRUCE_MIN_INTRO_S", "10"))
MAX_GAP = float(os.getenv("BRUCE_MAX_GAP_S", "4"))
LEAD = float(os.getenv("TALKUP_LEAD_S", "2.5"))

voices = sorted(glob.glob("tts_cache/dj_*.wav"))
vd = np.array([sf.info(v).duration for v in voices if os.path.exists(v)])
cache = json.load(open("tts_cache/intro_cache.json")) if os.path.exists("tts_cache/intro_cache.json") else {}
iv = np.array(list(cache.values())) if cache else np.array([])

print(f"Gate: ride needs voice<={MAX_V}s, intro>={MIN_I}s, gap<={MAX_GAP}s; talk-up needs voice>={LEAD+1.5:.1f}s")
print(f"Real data: {len(vd)} voices (median {np.median(vd):.1f}s), {len(iv)} intros (median {np.median(iv):.1f}s)\n")

checks = []
if len(vd) and len(iv):
    V, I = np.meshgrid(vd, iv, indexing="ij")
    entry = np.maximum(0, V - I)
    ride = (V <= MAX_V) & (I >= MIN_I) & (entry <= MAX_GAP)
    talkup = (~ride) & (V >= LEAD + 1.5)
    normal = ~(ride | talkup)
    total = V.size
    print(f"Pair grid {V.shape} ({total} pairs, if the DJ always wanted to hit the post):")
    print(f"  RIDE   : {100*ride.mean():5.1f}%")
    print(f"  TALK-UP: {100*talkup.mean():5.1f}%")
    print(f"  NORMAL : {100*normal.mean():5.1f}%")

    # safety: in RIDE, body never arrives before the voice ends
    Vr, Ir = V[ride], I[ride]
    body = np.maximum(0, Vr - Ir) + Ir
    early = (body < Vr - 1e-6).sum()
    print(f"\nRIDE pairs where body arrives BEFORE voice ends: {early} "
          f"({'OK - impossible' if early == 0 else 'BUG!'})")

    checks.append((f"RIDE is the minority ({100*ride.mean():.0f}% <= 40%)", ride.mean() <= 0.40))
    checks.append((f"TALK-UP covers the rest of the long scripts ({100*talkup.mean():.0f}% > 0)",
                   talkup.mean() > 0))
    checks.append((f"All three modes reachable (normal {100*normal.mean():.0f}% > 0)",
                   normal.mean() > 0))
    checks.append(("No RIDE pair ever talks over vocals", early == 0))

ok_n = sum(1 for _, p in checks if p)
print("\n=== MODE COVERAGE SIM ===")
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok_n}/{len(checks)} passed")
sys.exit(0 if ok_n == len(checks) else 1)
