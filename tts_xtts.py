"""
XTTS-Hindi TTS Engine for RadioExperiment
Uses Coqui XTTS v2 Hindi fine-tuned model for native Hindi pronunciation
"""
import os
import sys
import hashlib
from pathlib import Path

# Add TTS venv to path
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")

try:
    from TTS.api import TTS
    import torch
except ImportError as e:
    raise RuntimeError(f"TTS library not installed. Run: pip install TTS==0.22.0\n{e}")


class XTTSHindiEngine:
    """
    XTTS-Hindi TTS Engine with voice cloning
    
    Features:
    - Native Hindi pronunciation (fine-tuned model)
    - Voice cloning from reference audio
    - Multi-speaker support
    """
    
    def __init__(self, model_path: str = "C:/sourceCode/TTS/xtts-hindi-model", speed: float = 1.0):
        self.model_path = model_path
        self.speed = speed
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.tts = None
        
        print(f"[XTTS-Hindi] Initializing from: {model_path}")
        self._load_model()
    
    def _load_model(self):
        """Load XTTS-Hindi model"""
        try:
            config_path = os.path.join(self.model_path, "config.json")
            
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config not found: {config_path}")
            
            # Load XTTS model
            self.tts = TTS(
                model_path=self.model_path,
                config_path=config_path,
                progress_bar=False,
                gpu=torch.cuda.is_available()
            )
            
            print(f"[XTTS-Hindi] ✓ Model loaded (GPU: {torch.cuda.is_available()})")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load XTTS-Hindi model: {e}")
    
    def generate(self, text: str, speaker_wav: str, language: str = "hi", output_path: str = None) -> str:
        """
        Generate speech from text with Hindi pronunciation
        
        Args:
            text: Text to speak (Hindi/English)
            speaker_wav: Path to speaker reference audio (6-10s)
            language: Language code ('hi' for Hindi, 'en' for English)
            output_path: Output file path (auto-generated if None)
        
        Returns:
            Path to generated audio file (WAV)
        """
        if output_path is None:
            # Auto-generate filename
            text_hash = hashlib.md5(f"{text}{speaker_wav}{language}".encode()).hexdigest()[:8]
            output_path = str(self.cache_dir / f"xtts_{text_hash}.wav")
        
        # Check cache
        if os.path.exists(output_path):
            print(f"[XTTS-Hindi] Using cached: {output_path}")
            return output_path
        
        print(f"[XTTS-Hindi] Generating: '{text[:50]}...' (lang: {language})")
        
        try:
            # Generate with XTTS
            self.tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=speaker_wav,
                language=language,
                speed=self.speed
            )
            
            # Get duration (approximate from file size)
            file_size = os.path.getsize(output_path)
            approx_duration = file_size / 176400  # 44.1kHz * 2 bytes * 2 channels
            
            print(f"[XTTS-Hindi] Generated: {output_path} (~{approx_duration:.1f}s)")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"XTTS-Hindi generation failed: {e}")
    
    def generate_multilingual(self, segments: list, speaker_wav: str, output_path: str = None) -> str:
        """
        Generate speech from mixed language segments
        
        Args:
            segments: List of (text, language) tuples
            speaker_wav: Speaker reference audio
            output_path: Output file path
        
        Returns:
            Path to spliced audio file
        """
        from pydub import AudioSegment
        
        combined = AudioSegment.empty()
        
        for i, (text, language) in enumerate(segments):
            print(f"[XTTS-Hindi] Segment {i+1}/{len(segments)}: {text[:30]}... ({language})")
            
            # Generate segment
            segment_path = self.generate(text, speaker_wav, language)
            
            # Load and append
            audio = AudioSegment.from_wav(segment_path)
            combined += audio
        
        # Save combined audio
        if output_path is None:
            output_path = str(self.cache_dir / f"xtts_multilingual_{hashlib.md5(str(segments).encode()).hexdigest()[:8]}.wav")
        
        combined.export(output_path, format="wav")
        
        duration = len(combined) / 1000
        print(f"[XTTS-Hindi] ✓ Spliced: {output_path} ({duration:.1f}s)")
        
        return output_path


if __name__ == "__main__":
    # Test XTTS-Hindi
    engine = XTTSHindiEngine()
    
    # Test Hindi
    output = engine.generate(
        text="Namaste doston, aap sun rahe hain Experiment FM. That was Kabhi Khushi Kabhie Gham from Rab Ne Bana Di Jodi.",
        speaker_wav="voice_references/experiment_fm_intro_naksh.wav",
        language="hi"
    )
    
    print(f"\n✓ Test audio: {output}")
    print("Play it to check pronunciation quality!")
