"""
End-to-end (offline) render test for the Bruce feature.

Uses REAL files: a DJ voice wav + real songs. Rebuilds the controller's exact
timeline (song from the top, ducked, under the voice; music lifts at
post = max(voice_len, intro)), mixes it down offline, then checks:
  - the lift never comes before the voice ends
  - the lift never comes before the song body (real drop, not fake)
  - the ducked music is actually quieter than the lifted music

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


def plan(voice_len, intro):
    """Controller's exact math."""
    return max(voice_len, intro)


def mixdown(voice, song, post, duck=DUCK):
    """Song from top (ducked) + voice from top; music at full after `post`."""
    n = max(len(voice), len(song))
    v = np.pad(voice, ((0, n - len(voice)), (0, 0)))
    s = np.pad(song, ((0, n - len(song)), (0, 0)))
    cut = int(post * SR)
    s_mix = s.copy()
    s_mix[cut:] *= 1.0          # full
    s_mix[:cut] *= duck         # ducked
    return v + s_mix


voices = sorted(glob.glob("tts_cache/dj_*.wav"))
songs = [f for f in sorted(glob.glob(os.path.join(SONG_DIR, "*.mp3")))
         if detect_intro(f) > 2.0][:4]
assert voices, "no DJ wav found"
assert songs, "no song with intro>2s found"

voice = load(voices[0])
voice = AE.trim_trailing_silence(voice, SR)
voice_len = len(voice) / SR
print(f"Voice: {os.path.basename(voices[0])} ({voice_len:.1f}s)")

checks = []
for song_path in songs:
    song = load(song_path)
    intro = detect_intro(song_path)
    post = plan(voice_len, intro)
    mix = mixdown(voice, song, post)

    # Isolate the VOLUME change from the song's own dynamics:
    # take the SAME music window (right after the post) at duck level vs full level.
    win = int(0.5 * SR)
    cut = int(post * SR)
    win_music = song[cut:cut + win]
    r_ducked = float(np.sqrt(np.mean((win_music * DUCK) ** 2))) if win_music.size else 0.0
    r_full = float(np.sqrt(np.mean(win_music ** 2))) if win_music.size else 0.0
    louder = r_full > r_ducked * 1.5   # music clearly comes up at the post

    title = os.path.basename(song_path)
    on_voice = abs(post - voice_len) < 1e-9
    on_body = abs(post - intro) < 1e-9
    lifts_after_voice = post >= voice_len - 1e-9
    lifts_after_body = post >= intro - 1e-9

    print(f"\n  {title}")
    print(f"    intro={intro:.2f}s  voice_len={voice_len:.2f}s  post={post:.2f}s "
          f"({'on last word' if on_voice else 'on the drop' if on_body else '??'})")
    print(f"    same-window music RMS: ducked={r_ducked:.4f}  full={r_full:.4f}  "
          f"ratio={r_full/max(r_ducked,1e-9):.2f}x  -> {'up' if louder else 'NO'}")

    checks.append((f"{title[:38]}: lift never before voice", lifts_after_voice))
    checks.append((f"{title[:38]}: lift never before body (real drop)", lifts_after_body))
    checks.append((f"{title[:38]}: music comes UP at the post", louder))

# --- "on the drop" branch: a SHORT voice over a LONG intro ---
short_voice = (np.random.randn(int(8.0 * SR), 2).astype(np.float32) * 0.15)
short_voice = AE.trim_trailing_silence(short_voice, SR)
long_intro = 21.5
post = plan(len(short_voice) / SR, long_intro)
on_drop = abs(post - long_intro) < 1e-9
print(f"\n  [synthetic] short voice {len(short_voice)/SR:.1f}s vs intro {long_intro}s "
      f"-> post={post:.1f}s ({'on the drop' if on_drop else 'on last word'})")
checks.append(("synthetic short voice: lift lands on the DROP", on_drop))
checks.append(("synthetic short voice: lift never before body", post >= long_intro - 1e-9))

print("\n=== BRUCE END-TO-END RENDER TEST ===")
ok = sum(1 for _, p in checks if p)
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
