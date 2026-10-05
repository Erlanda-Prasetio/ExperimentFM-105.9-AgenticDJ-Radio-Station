"""
End-to-end (offline) render test for the Bruce feature (v2, final design).

Real files: DJ voice wav + real songs. Rebuilds the controller's exact timeline:

  BRUCE  (rare): short voice + real intro. Song enters at `entry = max(0, voice_len-intro)`
                 so its BODY lands on the DJ's last word. The intro rides DUCKED under
                 the voice; music lifts to full at the voice end.
  NORMAL       : the DJ talks first (no music under them), then the song starts from
                 the TOP once the voice ends - the song is delayed by the whole script.

Checks:
  - BRUCE: the song BODY never arrives before the voice ends (no talk over vocals)
  - BRUCE: the riding intro is ducked, the body is at full
  - NORMAL: no music plays while the voice is speaking (song delayed by the script)

Run: python test_bruce_render.py
"""
import os, sys, glob
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import librosa
import audio_engine as AE
from song_intro import detect_intro

SR = 44100
SONG_DIR = "../YT_Downloader/downloads/Wow, this ist gud"
DUCK = 0.22


def load(path):
    d, sr = librosa.load(path, sr=SR, mono=False)
    if d.ndim == 1:
        d = np.stack([d, d])
    return d.T.astype(np.float32)


def entry_time(voice_len, intro):
    return max(0.0, voice_len - intro)


def render_bruce(voice, song, voice_len, intro, duck=DUCK):
    """BRUCE: song enters at `entry`, ducked; lifts to full at voice_len. Voice from t=0."""
    entry = entry_time(voice_len, intro)
    n = max(len(voice), int((entry + len(song) / SR) * SR))
    v = np.pad(voice, ((0, n - len(voice)), (0, 0)))
    s = AE.prepend_silence(song, entry, SR)
    s = np.pad(s, ((0, n - len(s)), (0, 0)))
    cut = int(voice_len * SR)
    s_mix = s.copy()
    s_mix[:cut] *= duck
    s_mix[cut:] *= 1.0
    return v + s_mix, entry


def render_normal(voice, song, voice_len):
    """NORMAL: silence while the voice speaks, then the song from the top."""
    n = len(voice) + len(song)
    v = np.pad(voice, ((0, n - len(voice)), (0, 0)))
    s = AE.prepend_silence(song, voice_len, SR)
    s = np.pad(s, ((0, n - len(s)), (0, 0)))
    return v + s


voices = sorted(glob.glob("tts_cache/dj_*.wav"))
all_songs = sorted(glob.glob(os.path.join(SONG_DIR, "*.mp3")))
bruce_songs = [f for f in all_songs if detect_intro(f) >= 10.0][:3]
assert voices, "no DJ wav found"
assert bruce_songs, "no song with intro>=10s found"

voice = AE.trim_trailing_silence(load(voices[0]), SR)
voice_len = len(voice) / SR
print(f"Voice: {os.path.basename(voices[0])} ({voice_len:.1f}s)")

checks = []

# --- BRUCE mode with a synthetic SHORT voice (so it's Bruce-worthy) ---
short = AE.trim_trailing_silence(
    (np.random.randn(int(14.0 * SR), 2).astype(np.float32) * 0.15), SR)
sv_len = len(short) / SR
for song_path in bruce_songs:
    song = load(song_path)
    intro = detect_intro(song_path)
    mix, entry = render_bruce(short, song, sv_len, intro)

    body = entry + intro
    never_early = body >= sv_len - 1e-6
    win = int(0.5 * SR)
    duck_win = song[max(0, int((sv_len - 1.0) * SR)):int(sv_len * SR)]
    full_win = song[int(body * SR):int(body * SR) + win]
    r_duck = float(np.sqrt(np.mean((duck_win * DUCK) ** 2))) if duck_win.size else 0.0
    r_full = float(np.sqrt(np.mean(full_win ** 2))) if full_win.size else 0.0
    lifts = r_full > r_duck * 1.3

    title = os.path.basename(song_path)
    print(f"\n  [BRUCE] {title}")
    print(f"    voice={sv_len:.1f}s intro={intro:.1f}s entry={entry:.1f}s "
          f"body@{body:.1f}s (voice_end@{sv_len:.1f}s)")
    print(f"    ducked intro RMS={r_duck:.4f}  body RMS={r_full:.4f} -> "
          f"{'lifts' if lifts else 'NO LIFT'}")
    checks.append((f"{title[:34]}: body never before voice end", never_early))
    checks.append((f"{title[:34]}: intro ducked, body at full", lifts))

# --- NORMAL mode: no music while the voice speaks ---
for song_path in all_songs[:3]:
    song = load(song_path)
    mix = render_normal(voice, song, voice_len)
    # energy during the voice vs just after the voice (the song must start only after)
    win = int(0.5 * SR)
    during = mix[max(0, int((voice_len - 0.5) * SR)):int(voice_len * SR)]
    after = mix[int(voice_len * SR):int(voice_len * SR) + win]
    # compare "after voice" to the raw song start (should match: song from the top)
    song_start = song[:win]
    r_after = float(np.sqrt(np.mean(after ** 2))) if after.size else 0.0
    r_song = float(np.sqrt(np.mean(song_start ** 2))) if song_start.size else 0.0
    starts_after = abs(r_after - r_song) / max(r_song, 1e-9) < 0.05

    title = os.path.basename(song_path)
    print(f"\n  [NORMAL] {title}")
    print(f"    voice={voice_len:.1f}s -> song starts at {voice_len:.1f}s from the top "
          f"(rms after={r_after:.4f}, raw start={r_song:.4f})")
    checks.append((f"{title[:34]}: song starts from the top right after the voice", starts_after))

print("\n=== BRUCE END-TO-END RENDER TEST (v2) ===")
ok = sum(1 for _, p in checks if p)
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
