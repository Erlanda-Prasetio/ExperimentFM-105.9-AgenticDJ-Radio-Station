"""
Integration test: drive the REAL RealtimeRadioMixer callback offline.

This exercises the exact production mixing code path (audio_engine._audio_callback),
not just the timeline math. It simulates the Bruce feature by feeding blocks and
checking:
  1. while the voice plays, music stays ducked (mixed RMS stays low-ish)
  2. after we lift music to 1.0, the SAME music window is ~1/duck louder
  3. the voice track is removed and the song keeps playing to the end
"""
import os, sys, glob, types
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import librosa
import audio_engine as AE
from song_intro import detect_intro

SR = 44100
BLOCK = 4096
SONG_DIR = "../YT_Downloader/downloads/Wow, this ist gud"
DUCK = 0.22

# --- monkeypatch sounddevice so the mixer can be constructed without hardware ---
if not hasattr(AE.sd, "query_devices"):
    AE.sd.query_devices = lambda: []


def load(path):
    d, sr = librosa.load(path, sr=SR, mono=False)
    if d.ndim == 1:
        d = np.stack([d, d])
    return d.T.astype(np.float32)


mixer = AE.RealtimeRadioMixer(samplerate=SR, channels=2, blocksize=BLOCK)

# pick real files
song_path = next(f for f in sorted(glob.glob(os.path.join(SONG_DIR, "*.mp3")))
                 if detect_intro(f) > 2.0)
voice_path = sorted(glob.glob("tts_cache/dj_*.wav"))[0]
intro = detect_intro(song_path)
print(f"Song: {os.path.basename(song_path)} (intro {intro:.2f}s)")
print(f"Voice: {os.path.basename(voice_path)}")

song = mixer.load_audio(song_path, name="song", kind="music")
voice = mixer.load_audio(voice_path, name="voice", kind="voice")
voice.data = AE.trim_trailing_silence(voice.data, voice.samplerate)
voice_len = voice.duration
post = max(voice_len, intro)
print(f"voice_len={voice_len:.2f}s  post={post:.2f}s")


def run_blocks(n, capture=None):
    """Feed n audio blocks through the real callback; optionally capture output."""
    out = []
    for i in range(n):
        buf = np.zeros((BLOCK, 2), dtype=np.float32)
        mixer._audio_callback(buf, BLOCK, None, None)
        if capture is not None:
            out.append(buf.copy())
    return np.concatenate(out) if out else None


checks = []

# --- 1) Bruce timeline: song from top (ducked) + voice, both at t=0 ---
song.volume = DUCK
mixer.add_track(song, slot="music")
mixer.add_track(voice, slot="voice")

# play up to just before the post (music should be ducked the whole time)
blocks_to_post = int(post * SR / BLOCK) - 2
pre = run_blocks(blocks_to_post, capture=True)
# expected mix = voice (full) + music (ducked); compare actual mixer output to it
n_pre = len(pre)
expected_pre = (voice.data[:n_pre] + song.data[:n_pre] * DUCK).astype(np.float32)
ratio_pre = float(np.sqrt(np.mean(pre**2))) / max(float(np.sqrt(np.mean(expected_pre**2))), 1e-9)

# --- 2) lift music, remove voice (what the controller does at the post) ---
mixer.set_volume("music", 1.0)
mixer.remove_track("voice")

# capture the SAME window of music, now at full
song_window = song.data[len(pre):len(pre) + BLOCK * 4]
post_blocks = run_blocks(4, capture=True)
music_full = song_window * 1.0
ratio_post = float(np.sqrt(np.mean(post_blocks**2))) / max(float(np.sqrt(np.mean(music_full**2))), 1e-9)

checks.append(("voice removed after post", mixer.get_track_info("voice") is None))
checks.append(("music slot still present", mixer.get_track_info("music") is not None))
checks.append(("music volume = 1.0 after post", abs(mixer.get_track_info("music")["volume"] - 1.0) < 1e-6))
checks.append((f"before post: mixer == voice + ducked music (ratio {ratio_pre:.3f} ~ 1.0)",
               abs(ratio_pre - 1.0) < 0.05))
checks.append((f"after post: mixed~full music (ratio {ratio_post:.2f} ~ 1.0)",
               ratio_post > 0.6))

# --- 3) song keeps playing to the end (no premature cut) ---
pos_before = mixer.get_track_info("music")["position"]
run_blocks(50)
pos_after = mixer.get_track_info("music")["position"]
checks.append((f"song advances (pos {pos_before:.1f}s -> {pos_after:.1f}s)", pos_after > pos_before))

print("\n=== BRUCE MIXER INTEGRATION TEST ===")
ok = sum(1 for _, p in checks if p)
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
