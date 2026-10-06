"""
TTS integration for DJ voice
Supports F5-TTS for multilingual pronunciation with multi-voice support
"""
import os
import sys
from pathlib import Path
import tempfile
import subprocess
from voice_config import get_voice, get_main_dj_voice, get_named_voice


class TTSEngine:
    """
    Text-to-speech engine for DJ voice
    Uses F5-TTS for natural multilingual speech
    Supports multiple voices for different languages
    """
    
    def __init__(self, main_dj_gender: str = "male", model: str = "F5-TTS"):
        self.model = model
        self.main_dj_gender = main_dj_gender
        
        # Get main DJ voice
        main_voice = get_main_dj_voice(main_dj_gender)
        self.default_voice = main_voice['file']
        self.default_text = main_voice['transcript']
        
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        print(f"[TTS] Initialized: {model}")
        print(f"[TTS] Main DJ: English {main_dj_gender}")
        print(f"[TTS] Multi-language voices: loaded")
    
    def generate(self, text: str, output_path: str = None, language: str = "english", gender: str = None, skip_processing: bool = False, voice_name: str = None, speed: float = None, cfg_strength: float = None, seed: int = None) -> str:
        """
        Generate speech from text
        
        Args:
            text: Text to speak
            output_path: Output file path (auto-generated if None)
            language: Language for voice selection (english/indonesian/spanish/hindi)
            gender: Voice gender (male/female, uses main DJ if None)
            skip_processing: Skip radio processing chain (test raw TTS quality)
            voice_name: Explicit named voice (e.g. "ara", "jr", "naksh") - overrides language/gender
            speed: Playback tempo multiplier (1.0 = normal, pitch preserved). Defaults to TTS_SPEED env var or 1.0.
            cfg_strength: Voice guidance strength. Higher = more faithful to reference (but stiffer/artifacts).
                          None = auto (2.2 for female, 1.6 for male). Overrides env TTS_CFG_STRENGTH.
            seed: Random seed for reproducibility. None = random each call (natural variation). Fixed = identical output.
        
        Returns:
            Path to audio file
        """
        # Resolve cfg_strength: explicit arg > env TTS_CFG_STRENGTH > auto (gender-based)
        if cfg_strength is None:
            env_cfg = os.getenv("TTS_CFG_STRENGTH")
            if env_cfg:
                cfg_strength = float(env_cfg)

        # Get appropriate voice (resolve BEFORE cache key so per-voice speed/cfg land in it)
        named = get_named_voice(voice_name) if voice_name else None
        eq_spec = None
        nfe_step = None
        sway_coef = None
        if named:
            # Explicit named voice (rotating DJ / handoff)
            ref_voice = named['file']
            ref_text = named['transcript']
            eq_spec = named.get('eq')          # optional per-voice corrective EQ
            nfe_step = named.get('nfe_step')   # optional per-voice diffusion steps
            sway_coef = named.get('sway')      # optional per-voice sway sampling coef
            # Per-voice cfg_strength (if not explicitly overridden)
            if cfg_strength is None and named.get('cfg') is not None:
                cfg_strength = named['cfg']
        elif language.lower() == "english" and gender is None:
            # Use main DJ voice
            ref_voice = self.default_voice
            ref_text = self.default_text
        else:
            # Use language-specific voice
            voice = get_voice(language, gender)
            ref_voice = voice['file']
            ref_text = voice['transcript']

        # Resolve speed: explicit arg > per-voice 'speed' > TTS_SPEED env > 1.0 default
        if speed is None:
            if named and named.get('speed') is not None:
                speed = float(named['speed'])
            else:
                speed = float(os.getenv("TTS_SPEED", "1.0"))
        speed = float(speed)

        # Resolve nfe_step: per-voice > default 64
        if nfe_step is None:
            nfe_step = 64
        # Resolve sway: per-voice; if nfe_step is high, sway MUST be off (float16
        # timestep collision in F5-TTS -> "t must be strictly increasing").
        if sway_coef is None:
            sway_coef = -1.0 if nfe_step <= 64 else None

        if output_path is None:
            # Auto-generate filename with language in hash
            import hashlib
            cache_key = f"{text}_{language}_{gender or 'default'}_{voice_name or 'auto'}_{speed}_{cfg_strength}_{seed}_{nfe_step}_{sway_coef}"
            text_hash = hashlib.md5(cache_key.encode()).hexdigest()[:8]
            output_path = str(self.cache_dir / f"dj_{text_hash}.wav")
        
        # Check cache
        if os.path.exists(output_path):
            print(f"[TTS] Using cached: {output_path}")
            return output_path
        
        print(f"[TTS] Generating: '{text[:50]}...' ({language}{', voice=' + voice_name if voice_name else ''})")
        
        if self.model == "F5-TTS":
            self._generate_f5tts(text, output_path, ref_voice, ref_text, language, skip_processing, speed, cfg_strength, seed, eq_spec, nfe_step, sway_coef)
        else:
            raise ValueError(f"Unknown TTS model: {self.model}")
        
        return output_path
    
    def _generate_f5tts(self, text: str, output_path: str, ref_voice: str, ref_text: str, language: str = "english", skip_processing: bool = False, speed: float = 1.0, cfg_strength: float = None, seed: int = None, eq_spec: dict = None, nfe_step: int = 64, sway_coef: float = -1.0):
        """Generate using F5-TTS API"""
        import sys
        sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")
        
        # Validate text
        if not text or not text.strip():
            raise ValueError("Empty text provided to TTS")
        
        from f5_tts.api import F5TTS
        import soundfile as sf
        import numpy as np
        from audio_processing import radio_processing
        
        # Load the model ONCE and reuse (loading costs ~55s + ~1.3GB VRAM per call)
        if getattr(self, "_f5tts", None) is None:
            print("[TTS] Loading F5-TTS model (first call, cached after)...")
            self._f5tts = F5TTS()
        tts = self._f5tts
        
        try:
            # Generate raw TTS
            temp_output = output_path.replace('.wav', '_raw.wav')
            
            # Don't let F5TTS write (it has shape bug), get raw wav instead
            wav, sr, spec = tts.infer(
                gen_text=text,
                ref_text=ref_text,
                ref_file=ref_voice,
                nfe_step=nfe_step,      # Quality/speed balance (per-voice configurable)
                cfg_strength=cfg_strength if cfg_strength is not None else (2.2 if 'CARA' in ref_voice or 'ara' in ref_voice else 1.6),  # Higher for female
                sway_sampling_coef=sway_coef,  # None required for nfe_step > 64
                speed=1.0,
                seed=seed
            )
            
            # Fix shape: ensure 1D array for mono
            if isinstance(wav, np.ndarray):
                wav = wav.flatten()  # Force 1D
            
            # Write raw TTS output
            sf.write(temp_output, wav, sr)
            
            print(f"[TTS] Raw generation: {len(wav)/sr:.1f}s")
            
            # Apply professional radio processing chain
            if not skip_processing:
                print(f"[TTS] Applying radio processing...")
                radio_processing(temp_output, output_path, sr=48000)
                
                # Clean up raw file
                import os
                os.remove(temp_output)

                # Optional per-voice corrective EQ (after the broadcast chain)
                if eq_spec:
                    from audio_processing import apply_voice_eq
                    import os as _os
                    eq_tmp = output_path.replace('.wav', '_eq.wav')
                    apply_voice_eq(output_path, eq_tmp, eq_spec, sr=48000)
                    _os.replace(eq_tmp, output_path)
            else:
                print(f"[TTS] Skipping radio processing (raw output)")
                import os
                os.rename(temp_output, output_path)
            
            print(f"[TTS] Generated: {output_path} ({len(wav)/sr:.1f}s)")
            
            # Tempo adjustment while preserving pitch (ffmpeg atempo)
            import subprocess
            import os
            
            speed = float(speed)
            if abs(speed - 1.0) < 1e-6:
                print(f"[TTS] Tempo 1.00x (unchanged)")
            else:
                temp_output = output_path.replace('.wav', '_temp.wav')
                # atempo >2.0 or <0.5 needs chaining; our range is safe
                subprocess.run([
                    'ffmpeg', '-i', output_path,
                    '-filter:a', f'atempo={speed}',
                    '-y', temp_output
                ], capture_output=True, check=True)
                os.replace(temp_output, output_path)
                print(f"[TTS] Tempo {speed:.2f}x (pitch preserved)")
            
        except Exception as e:
            raise RuntimeError(f"F5-TTS failed: {e}")
    
    def clear_cache(self):
        """Clear TTS cache"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir()
        print("[TTS] Cache cleared")
