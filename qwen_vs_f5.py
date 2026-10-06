"""HEAD-TO-HEAD (Qwen side): Qwen3-TTS 0.6B bf16 voice-clone of Jerry.

RUN TOMORROW WITH RADIO STOPPED (so Qwen gets full VRAM + undistorted timing):
    C:/sourceCode/Qwen3-TTS/.venv/Scripts/python.exe qwen_vs_f5.py

The F5 side ALREADY EXISTS (same text, same Jerry ref, from the nfe test):
    tts_cache/nfe_test/nfe64_swayon.mp3   <- current production (nfe 64, sway on)
    tts_cache/nfe_test/nfe192_swayoff.mp3 <- the 192 take you liked
Compare qwen_jerry.mp3 against those.

Qwen-only on purpose: F5 lives in a DIFFERENT venv (C:/sourceCode/TTS/.venv);
mixing both in one process risks import/version conflicts.
"""
import os, time, subprocess
import numpy as np
import soundfile as sf
import torch

BASE = "C:/sourceCode/Qwen3-TTS/models/Qwen3-TTS-12Hz-0.6B-Base"
REF_AUDIO = "C:/sourceCode/RadioExperiment/voice_references/voice_ref_jerry.wav"
REF_TEXT  = ("Hey, welcome to Experiment FM 105.9. I'm your AI host for tonight, "
             "and we've got an incredible mix of music from around the world.")
GEN_TEXT  = "You're locked in, no ads, no interruptions. Just the music and me, all night long."

OUT = "C:/sourceCode/RadioExperiment/qwen_vs_f5"
os.makedirs(OUT, exist_ok=True)

print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("VRAM used before load:", torch.cuda.memory_allocated()/1e9, "GB", flush=True)

from qwen_tts import Qwen3TTSModel

print("\n=== loading Qwen3-TTS 0.6B Base (bf16) ===", flush=True)
t0 = time.time()
model = Qwen3TTSModel.from_pretrained(
    BASE,
    device_map="cuda:0",
    dtype=torch.bfloat16,
)
print(f"  loaded in {time.time()-t0:.1f}s", flush=True)
if torch.cuda.is_available():
    print(f"  VRAM after load: {torch.cuda.memory_allocated()/1e9:.2f} GB", flush=True)

# Warm-up + timed run
print("\n=== voice clone ===", flush=True)
t0 = time.time()
wavs, sr = model.generate_voice_clone(
    text=GEN_TEXT, language="English",
    ref_audio=REF_AUDIO, ref_text=REF_TEXT,
)
dt = time.time() - t0
audio = np.asarray(wavs[0]).flatten()
out_wav = f"{OUT}/qwen_jerry.wav"
sf.write(out_wav, audio, sr)
subprocess.run(["ffmpeg", "-y", "-i", out_wav, out_wav.replace(".wav", ".mp3"),
                "-loglevel", "error"], capture_output=True)
print(f"  OK  {len(audio)/sr:.2f}s audio in {dt:.2f}s gen  (RTF {dt/(len(audio)/sr):.3f})", flush=True)
if torch.cuda.is_available():
    print(f"  peak VRAM: {torch.cuda.max_memory_allocated()/1e9:.2f} GB", flush=True)

print("\n=== DONE ===", flush=True)
print(f"Qwen take : {OUT}/qwen_jerry.mp3", flush=True)
print("F5 compare: tts_cache/nfe_test/nfe64_swayon.mp3 (prod) / nfe192_swayoff.mp3", flush=True)
