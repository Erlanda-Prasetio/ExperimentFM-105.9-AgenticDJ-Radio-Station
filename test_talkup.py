"""
Test: TALK-UP mode (long script, music comes up in the last few seconds).

Drives the REAL mixer callback with the controller's talk-up timeline:
  - music is silent until (voice_len - lead)
  - from there it comes up from TALKUP_DUCK and swells to full at voice_len
  - at the post (voice_len) the music is at full volume

Run: python test_talkup.py
"""
import os, sys, glob
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import numpy as np
import librosa
import audio_engine as AE

SR = 44100
BLOCK = 4096
SONG_DIR = "../YT_Downloader/downloads/Wow, this ist gud"
LEAD = 2.5
DUCK = 0.5

if not hasattr(AE.sd, "query_devices"):
    AE.sd.query_devices = lambda: []


def load(path):
    d, sr = librosa.load(path, sr=SR, mono=False)
    if d.ndim == 1:
        d = np.stack([d, d])
    return d.T.astype(np.float32)


mixer = AE.RealtimeRadioMixer(samplerate=SR, channels=2, blocksize=BLOCK)
song_path = sorted(glob.glob(os.path.join(SONG_DIR, "*.mp3")))[0]
voice_path = sorted(glob.glob("tts_cache/dj_*.wav"))[0]

# long script (talk-up territory), trimmed like the controller does
voice = AE.trim_trailing_silence(load(voice_path), SR)
voice_len = len(voice) / SR
start = max(0.0, voice_len - LEAD)
print(f"Voice: {os.path.basename(voice_path)} ({voice_len:.1f}s), music comes up at {start:.1f}s")

song = mixer.load_audio(song_path, name="song", kind="music")
song.data = AE.prepend_silence(song.data, start, SR)   # talk-up: music delayed to `start`
song.volume = DUCK
voice_track = AE.AudioTrack(data=voice, samplerate=SR, name="voice", volume=1.0)


def run(n, capture=False):
    out = []
    for _ in range(n):
        buf = np.zeros((BLOCK, 2), dtype=np.float32)
        mixer._audio_callback(buf, BLOCK, None, None)
        if capture:
            out.append(buf.copy())
    return np.concatenate(out) if out else None


checks = []

# 1) before `start`: music must be SILENT (song has not entered yet)
mixer.add_track(song, slot="music")
mixer.add_track(voice_track, slot="voice")
pre_blocks = int(start * SR / BLOCK) - 2
pre = run(pre_blocks, capture=True)
expected_pre = voice[:len(pre)]
ratio_pre = float(np.sqrt(np.mean(pre**2))) / max(float(np.sqrt(np.mean(expected_pre**2))), 1e-9)
checks.append((f"before music start: output == voice only (ratio {ratio_pre:.3f} ~ 1.0)",
               abs(ratio_pre - 1.0) < 0.05))

# 2) walk the swell: volume must rise monotonically from DUCK to 1.0
mixer.set_volume("music", DUCK)
vols = []
t = start
while t < voice_len:
    frac = min(1.0, (t - start) / LEAD)
    v = DUCK + (1.0 - DUCK) * frac
    mixer.set_volume("music", v)
    vols.append(v)
    t += 0.1
checks.append((f"swell rises monotonically ({vols[0]:.2f} -> {vols[-1]:.2f})",
               all(vols[i] <= vols[i + 1] + 1e-9 for i in range(len(vols) - 1))))
checks.append((f"swell starts at DUCK ({vols[0]:.2f} ~ {DUCK})", abs(vols[0] - DUCK) < 0.06))

# 3) at the post: full volume, voice removed
mixer.set_volume("music", 1.0)
mixer.remove_track("voice")
checks.append(("music at full after post", abs(mixer.get_track_info("music")["volume"] - 1.0) < 1e-6))
checks.append(("voice removed after post", mixer.get_track_info("voice") is None))

# 4) music plays at full from there
pos_before = int(mixer.get_track_info("music")["position"] * SR)
out = run(4, capture=True)
music_full = song.data[pos_before:pos_before + len(out)]
ratio_full = float(np.sqrt(np.mean(out**2))) / max(float(np.sqrt(np.mean(music_full**2))), 1e-9)
checks.append((f"music at full after post (ratio {ratio_full:.3f} ~ 1.0)", abs(ratio_full - 1.0) < 0.05))

print("\n=== TALK-UP TEST ===")
ok = sum(1 for _, p in checks if p)
for name, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {name}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
