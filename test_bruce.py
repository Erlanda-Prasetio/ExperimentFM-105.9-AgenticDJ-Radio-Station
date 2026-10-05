"""
Test: Bruce feature timeline math ("hitting the post").

Design: the song plays from the TOP, ducked, under the DJ voice (no dead air).
The music lifts to full at the "post" = max(voice_len, intro):
  - if the DJ talks longer than the intro -> lift lands on the DJ's last word
  - if the intro is longer than the DJ  -> lift lands on the song's drop
"""
import os
import sys
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import audio_engine as AE

def post_time(voice_len, intro):
    """Same math as the controller's Bruce branch."""
    return max(voice_len, intro)

checks = []
cases = [
    (25.0, 6.0),   # DJ longer than intro -> lift on last word
    (20.0, 6.4),   # INDUSTRY BABY-like
    (30.0, 21.5),  # long intro, DJ still longer
    (15.0, 21.5),  # intro LONGER than voice -> lift on the drop
    (12.0, 12.0),  # exactly equal
    (40.0, 0.3),   # almost no intro -> lift on last word
]
for voice_len, intro in cases:
    post = post_time(voice_len, intro)
    # The lift must never come before the voice ends (no talking over full music)
    not_before_voice = post >= voice_len - 1e-9
    # The lift must never come before the song body (that would be a fake drop)
    not_before_body = post >= intro - 1e-9
    # And it must be exactly one of the two, never some third value
    is_exact = abs(post - voice_len) < 1e-9 or abs(post - intro) < 1e-9
    checks.append((f"voice={voice_len}s intro={intro}s -> post@{post:.1f}s "
                   f"(>=voice:{not_before_voice}, >=body:{not_before_body}, exact:{is_exact})",
                   not_before_voice and not_before_body and is_exact))

# --- trim_trailing_silence ---
sr = 44100
voiced = np.concatenate([np.random.randn(sr*2, 2).astype(np.float32)*0.1,
                         np.zeros((sr*3, 2), dtype=np.float32)])  # 2s audio + 3s silence
trimmed = AE.trim_trailing_silence(voiced, sr)
checks.append((f"trim silence: 5.0s -> {trimmed.shape[0]/sr:.2f}s", abs(trimmed.shape[0]/sr - 2.05) < 0.1))

# --- prepend_silence (still used by the mixer helpers) ---
p = AE.prepend_silence(np.ones((sr, 2), dtype=np.float32), 1.5, sr)
checks.append((f"prepend 1.5s: 1.0s -> {p.shape[0]/sr:.2f}s", abs(p.shape[0]/sr - 2.5) < 0.01))
checks.append(("prepend keeps channels", p.shape[1] == 2))
checks.append(("prepend 0s = unchanged", AE.prepend_silence(np.ones((100,2),dtype=np.float32), 0, sr).shape[0] == 100))

print("=== BRUCE FEATURE TIMELINE TEST ===")
ok = 0
for name, passed in checks:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok += passed
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
