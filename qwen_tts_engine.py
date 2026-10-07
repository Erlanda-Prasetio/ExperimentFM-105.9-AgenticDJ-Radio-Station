"""Qwen3-TTS engine - drop-in replacement for tts_engine.TTSEngine.

Same public surface as TTSEngine.generate(...) so the controller and the offline
renderer can use it unchanged. Uses the Qwen3-TTS 0.6B Base voice clone instead
of F5-TTS.

Why a separate engine: F5 lives in C:/sourceCode/TTS/.venv; Qwen lives in
C:/sourceCode/Qwen3-TTS/.venv. The offline renderer runs under the Qwen venv
with the radio venv's site-packages appended, so only Qwen is importable here.

The radio processing chain (radio_processing + per-voice EQ + pitch-preserving
tempo) is IDENTICAL to the F5 path, so a Qwen voice sounds like it went through
the same broadcast chain.
"""
import os
import hashlib
import subprocess
from pathlib import Path

import numpy as np

from voice_config import get_named_voice, get_main_dj_voice, get_voice

QWEN_MODEL_DIR = os.getenv("QWEN_MODEL_DIR",
                           "C:/sourceCode/Qwen3-TTS/models/Qwen3-TTS-12Hz-0.6B-Base")
QWEN_LANGUAGE = os.getenv("QWEN_LANGUAGE", "English")


class QwenTTSEngine:
    """Qwen3-TTS 0.6B Base voice-clone engine (3s reference -> speech)."""

    def __init__(self, main_dj_gender: str = "male", model: str = "Qwen3-TTS"):
        self.model = model
        self.main_dj_gender = main_dj_gender
        main_voice = get_main_dj_voice(main_dj_gender)
        self.default_voice = main_voice['file']
        self.default_text = main_voice['transcript']
        # Optional override: a named voice used when no voice_name is passed
        # (single-DJ mode). e.g. QWEN_DEFAULT_VOICE=naksh_thick
        _ov = os.getenv("QWEN_DEFAULT_VOICE")
        if _ov:
            _named = get_named_voice(_ov)
            if _named:
                self.default_voice = _named['file']
                self.default_text = _named['transcript']
                print(f"[QwenTTS] Default voice overridden -> {_ov} ({_named['name']})")
            else:
                print(f"[QwenTTS] ⚠️ QWEN_DEFAULT_VOICE={_ov} not found - using default")
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self._qwen = None
        print(f"[QwenTTS] Initialized: {model}")
        print(f"[QwenTTS] Model dir: {QWEN_MODEL_DIR}")

    # ---- model lifecycle -------------------------------------------------
    def _load(self):
        if self._qwen is None:
            import torch
            from qwen_tts import Qwen3TTSModel
            print("[QwenTTS] Loading Qwen3-TTS 0.6B Base (first call, cached after)...")
            self._qwen = Qwen3TTSModel.from_pretrained(
                QWEN_MODEL_DIR, device_map="cuda:0", dtype=torch.bfloat16)
            print("[QwenTTS] Model loaded")
        return self._qwen

    def preload(self):
        self._load()

    # ---- generate --------------------------------------------------------
    def generate(self, text: str, output_path: str = None, language: str = "english",
                 gender: str = None, skip_processing: bool = False, voice_name: str = None,
                 speed: float = None, cfg_strength: float = None, seed: int = None) -> str:
        named = get_named_voice(voice_name) if voice_name else None
        eq_spec = None
        if named:
            ref_voice = named['file']
            ref_text = named['transcript']
            eq_spec = named.get('eq')
        elif language.lower() == "english" and gender is None:
            ref_voice = self.default_voice
            ref_text = self.default_text
        else:
            v = get_voice(language, gender)
            ref_voice = v['file']
            ref_text = v['transcript']

        # speed: explicit arg > per-voice 'speed' > TTS_SPEED env > 1.0
        if speed is None:
            if named and named.get('speed') is not None:
                speed = float(named['speed'])
            else:
                speed = float(os.getenv("TTS_SPEED", "1.0"))
        speed = float(speed)

        if output_path is None:
            key = f"qwen|{text}|{language}|{gender or 'default'}|{voice_name or 'auto'}|{speed}"
            h = hashlib.md5(key.encode()).hexdigest()[:10]
            output_path = str(self.cache_dir / f"qdj_{h}.wav")

        if os.path.exists(output_path):
            print(f"[QwenTTS] Using cached: {output_path}")
            return output_path

        print(f"[QwenTTS] Generating: '{text[:50]}...' ({language}"
              f"{', voice=' + voice_name if voice_name else ''})")

        import soundfile as sf
        model = self._load()
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=QWEN_LANGUAGE,
            ref_audio=ref_voice,
            ref_text=ref_text,
        )
        wav = np.asarray(wavs[0]).flatten().astype(np.float32)

        raw = output_path.replace('.wav', '_raw.wav')
        sf.write(raw, wav, sr)
        print(f"[QwenTTS] Raw generation: {len(wav)/sr:.1f}s @ {sr}Hz")

        if skip_processing:
            os.replace(raw, output_path)
        else:
            from audio_processing import radio_processing, apply_voice_eq
            radio_processing(raw, output_path, sr=48000)
            try:
                os.remove(raw)
            except OSError:
                pass
            if eq_spec:
                eq_tmp = output_path.replace('.wav', '_eq.wav')
                apply_voice_eq(output_path, eq_tmp, eq_spec, sr=48000)
                os.replace(eq_tmp, output_path)

        # Tempo adjustment while preserving pitch (ffmpeg atempo)
        if abs(speed - 1.0) > 1e-6:
            tmp = output_path.replace('.wav', '_tmp.wav')
            subprocess.run(['ffmpeg', '-i', output_path, '-filter:a', f'atempo={speed}', '-y', tmp],
                           capture_output=True, check=True)
            os.replace(tmp, output_path)
            print(f"[QwenTTS] Tempo {speed:.2f}x (pitch preserved)")

        print(f"[QwenTTS] Generated: {output_path}")
        return output_path

    def clear_cache(self):
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir()
        print("[QwenTTS] Cache cleared")
