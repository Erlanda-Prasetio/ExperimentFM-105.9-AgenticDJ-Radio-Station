"""
Test: Bruce feature timeline math (v2 design).

Two modes:
  BRUCE  : short voice over a real intro. Song enters at `entry = max(0, voice_len-intro)`
           so the song's BODY lands exactly on the DJ's last word. Only the INTRO rides
           under the voice (never the vocals).
  NORMAL : same delay so the body lands on the DJ's last word (no talk over vocals).

Key invariant: song_body_time == voice_end_time  (body lands on the last word).
"""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import audio_engine as AE

def entry_time(voice_len, intro):
    """Song start offset so its body lands on the DJ's last word."""
    return max(0.0, voice_len - intro)

checks = []
cases = [
    (15.0, 12.0),  # short voice + real intro -> small ride gap (Bruce-worthy)
    (12.0, 10.0),
    (18.0, 10.0),
    (30.0, 6.0),   # long voice, short intro -> big delay (normal mode)
    (40.0, 0.3),   # almost no intro -> big delay
    (10.0, 25.0),  # intro longer than voice -> entry 0 (song from top, body after voice)
    (12.0, 12.0),  # exactly equal -> entry 0
]
for voice_len, intro in cases:
    entry = entry_time(voice_len, intro)
    voice_end = voice_len                       # voice starts at 0
    body = entry + intro                        # song starts at entry, body after its intro
    # Body lands on the last word (entry>0), OR - when the intro is longer than the
    # voice - the song plays out from the top and the body simply arrives after
    # the DJ (entry==0, unavoidable). Either way the body NEVER arrives early.
    aligned = abs(body - voice_end) < 1e-6 or (entry == 0.0 and body >= voice_end - 1e-6)
    no_neg = entry >= 0
    never_early = body >= voice_end - 1e-6
    checks.append((f"voice={voice_len}s intro={intro}s -> entry={entry:.1f}s, "
                   f"body@{body:.1f}s vs voice_end@{voice_end:.1f}s",
                   aligned and no_neg and never_early))

# --- Mode dispatch (mirror of the controller) ---
def dispatch(want_post, voice_len, intro,
             max_voice=18.0, min_intro=10.0, max_gap=4.0, lead=2.5):
    """Return 'ride' | 'talkup' | 'normal' - exactly the controller's logic."""
    entry = max(0.0, voice_len - intro)
    ride = (want_post and voice_len <= max_voice
            and intro >= min_intro and entry <= max_gap)
    talkup = want_post and not ride and voice_len >= lead + 1.5
    if ride:
        return "ride"
    if talkup:
        return "talkup"
    return "normal"

gate_cases = [
    # want, voice, intro, expect
    (True,  15.0, 12.0, "ride"),     # short script + real intro + tight gap
    (True,  18.0, 14.0, "ride"),     # entry 4 exactly
    (True,  25.0, 12.0, "talkup"),   # script too long for a ride -> talk-up
    (True,  15.0,  5.0, "talkup"),   # intro too short to ride -> talk-up
    (True,  18.0, 13.0, "talkup"),   # ride gap 5 > 4 -> talk-up
    (True,  40.0,  4.0, "talkup"),   # long script, short intro -> talk-up
    (False, 15.0, 12.0, "normal"),   # LLM said no
    (False, 40.0, 12.0, "normal"),
    (True,   3.0,  5.0, "normal"),   # script too short to ride OR talk-up (intro short too)
]
for want, vl, it, expect in gate_cases:
    got = dispatch(want, vl, it)
    e = entry_time(vl, it)
    checks.append((f"dispatch(want={want},voice={vl},intro={it}) entry={e:.1f} -> {got} (expect {expect})",
                   got == expect))

# --- helpers still intact ---
sr = 44100
voiced = np.concatenate([np.random.randn(sr*2, 2).astype(np.float32)*0.1,
                         np.zeros((sr*3, 2), dtype=np.float32)])
checks.append(("trim silence 5.0s -> 2.05s",
               abs(AE.trim_trailing_silence(voiced, sr).shape[0]/sr - 2.05) < 0.1))
p = AE.prepend_silence(np.ones((sr, 2), dtype=np.float32), 1.5, sr)
checks.append(("prepend 1.5s -> 2.5s", abs(p.shape[0]/sr - 2.5) < 0.01))

print("=== BRUCE TIMELINE TEST (v2) ===")
ok = 0
for name, passed in checks:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok += passed
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
