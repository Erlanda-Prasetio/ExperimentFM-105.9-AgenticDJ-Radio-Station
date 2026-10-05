"""
Integration test: drive the REAL RealtimeRadioMixer callback offline (v2 design).

Exercises the exact production mixing path (audio_engine._audio_callback).
Builds the v2 Bruce timeline and checks:
  1. while the voice plays, the mixer output == voice + ducked music (song delayed by `entry`)
  2. after the lift, the SAME music window is ~1/duck louder
  3. the voice is removed and the song keeps advancing
"""
import os, sys, glob
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

if not hasattr(AE.sd, "query_devices"):
    AE.sd.query_devices = lambda: []


def load(path):
    d, sr = librosa.load(path, sr=SR, mono=False)
    if d.ndim == 1:
        d = np.stack([d, d])
    return d.T.astype(np.float32)


mixer = AE.RealtimeRadioMixer(samplerate=SR, channels=2, blocksize=BLOCK)

song_path = next(f for f in sorted(glob.glob(os.path.join(SONG_DIR, "*.mp3")))
                 if detect_intro(f) >= 10.0)
voice_path = sorted(glob.glob("tts_cache/dj_*.wav"))[0]
intro = detect_intro(song_path)

# short synthetic voice (Bruce-worthy) so entry is small
voice = AE.trim_trailing_silence(
    (np.random.randn(int(14.0 * SR), 2).astype(np.float32) * 0.15), SR)
voice_len = len(voice) / SR
entry = max(0.0, voice_len - intro)
print(f"Song: {os.path.basename(song_path)} (intro {intro:.2f}s)")
print(f"voice_len={voice_len:.2f}s  entry={entry:.2f}s")

song = mixer.load_audio(song_path, name="song", kind="music")
song.data = AE.prepend_silence(song.data, entry, SR)   # v2: delayed entry
song.volume = DUCK
voice_track = AE.AudioTrack(data=voice, samplerate=SR, name="voice", volume=1.0)


def run_blocks(n, capture=False):
    out = []
    for _ in range(n):
        buf = np.zeros((BLOCK, 2), dtype=np.float32)
        mixer._audio_callback(buf, BLOCK, None, None)
        if capture:
            out.append(buf.copy())
    return np.concatenate(out) if out else None


checks = []

# --- 1) ride phase: voice + ducked music, both from t=0 (song already has entry silence) ---
mixer.add_track(song, slot="music")
mixer.add_track(voice_track, slot="voice")

blocks_to_lift = int(voice_len * SR / BLOCK) - 2
pre = run_blocks(blocks_to_lift, capture=True)
n_pre = len(pre)
expected_pre = (voice[:n_pre] + song.data[:n_pre] * DUCK).astype(np.float32)
ratio_pre = float(np.sqrt(np.mean(pre**2))) / max(float(np.sqrt(np.mean(expected_pre**2))), 1e-9)

# --- 2) lift + remove voice ---
mixer.set_volume("music", 1.0)
mixer.remove_track("voice")

pos = len(pre)
music_after = song.data[pos:pos + BLOCK * 4] * 1.0
post_blocks = run_blocks(4, capture=True)
ratio_post = float(np.sqrt(np.mean(post_blocks**2))) / max(float(np.sqrt(np.mean(music_after**2))), 1e-9)

checks.append(("voice removed after lift", mixer.get_track_info("voice") is None))
checks.append(("music slot still present", mixer.get_track_info("music") is not None))
checks.append(("music volume = 1.0 after lift",
               abs(mixer.get_track_info("music")["volume"] - 1.0) < 1e-6))
checks.append((f"ride phase: mixer == voice + ducked music (ratio {ratio_pre:.3f} ~ 1.0)",
               abs(ratio_pre - 1.0) < 0.05))
checks.append((f"after lift: mixer == full music (ratio {ratio_post:.2f} ~ 1.0)",
               ratio_post > 0.6))

# --- 3) NORMAL mode: no music while the voice speaks (song delayed by the script) ---
mixer2 = AE.RealtimeRadioMixer(samplerate=SR, channels=2, blocksize=BLOCK)
song2 = mixer2.load_audio(song_path, name="song", kind="music")
voice2 = AE.AudioTrack(data=voice, samplerate=SR, name="voice", volume=1.0)
mixer2.add_track(voice2, slot="voice")
# run through the whole voice -> music slot must stay empty
n_voice_blocks = int(voice_len * SR / BLOCK) - 1
run2 = []
for _ in range(n_voice_blocks):
    buf = np.zeros((BLOCK, 2), dtype=np.float32)
    mixer2._audio_callback(buf, BLOCK, None, None)
    run2.append(buf.copy())
run2 = np.concatenate(run2)
music_during_voice = mixer2.get_track_info("music")
# expected: output == voice alone (no music), for the duration of the voice
expected_voice_only = voice[:len(run2)]
ratio_voice_only = float(np.sqrt(np.mean(run2**2))) / max(float(np.sqrt(np.mean(expected_voice_only**2))), 1e-9)

checks.append(("NORMAL: no music track while voice speaks", music_during_voice is None))
checks.append((f"NORMAL: output == voice only (ratio {ratio_voice_only:.3f} ~ 1.0)",
               abs(ratio_voice_only - 1.0) < 0.05))

# then the song starts from the top
mixer2.remove_track("voice")
mixer2.add_track(song2, slot="music")
song_start_win = song2.data[:BLOCK * 4]
out3 = []
for _ in range(4):
    buf = np.zeros((BLOCK, 2), dtype=np.float32)
    mixer2._audio_callback(buf, BLOCK, None, None)
    out3.append(buf.copy())
out3 = np.concatenate(out3)
ratio_song = float(np.sqrt(np.mean(out3**2))) / max(float(np.sqrt(np.mean(song_start_win**2))), 1e-9)
checks.append((f"NORMAL: song plays from the top after (ratio {ratio_song:.2f} ~ 1.0)",
               abs(ratio_song - 1.0) < 0.05))

print("\n=== BRUCE MIXER INTEGRATION TEST (v2) ===")
ok = sum(1 for _, p in checks if p)
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
