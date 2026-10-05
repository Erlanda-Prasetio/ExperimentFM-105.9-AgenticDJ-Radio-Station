"""
Grok TTS Engine for RadioExperiment
Uses xAI's Grok TTS API with Naksh voice (Indian accent, multilingual)
"""
import os
import requests
from pathlib import Path
import hashlib


class GrokTTSEngine:
    """
    Grok TTS Engine using xAI API
    Features:
    - Naksh voice: Indian accent, warm, thoughtful
    - Auto language detection (Hindi + English mixed)
    - Speed control 0.7-1.5x
    - Returns MP3 directly
    """
    
    def __init__(self, api_key: str, voice: str = "naksh", speed: float = 0.85):
        self.api_key = api_key
        self.voice = voice
        self.speed = speed
        self.endpoint = "https://api.x.ai/v1/tts"
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        print(f"[Grok TTS] Initialized: voice={voice}, speed={speed}")
    
    def generate(self, text: str, output_path: str = None) -> str:
        """
        Generate speech from text using Grok TTS
        
        Args:
            text: Text to speak (can mix English + Hindi)
            output_path: Output file path (auto-generated if None)
        
        Returns:
            Path to audio file (MP3)
        """
        if output_path is None:
            # Auto-generate filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output_path = str(self.cache_dir / f"grok_{text_hash}.mp3")
        
        # Check cache
        if os.path.exists(output_path):
            print(f"[Grok TTS] Using cached: {output_path}")
            return output_path
        
        print(f"[Grok TTS] Generating: '{text[:50]}...'")
        
        try:
            # Call Grok TTS API
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice": self.voice,
                    "language": "auto",  # Auto-detect Hindi/English
                    "speed": self.speed
                },
                timeout=30
            )
            
            response.raise_for_status()
            
            # Save MP3
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Get duration (approximate from file size)
            file_size = os.path.getsize(output_path)
            approx_duration = file_size / 16000  # Rough estimate for MP3
            
            print(f"[Grok TTS] Generated: {output_path} (~{approx_duration:.1f}s)")
            return output_path
            
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response else str(e)
            raise RuntimeError(f"Grok TTS API error: {error_msg}")
        except Exception as e:
            raise RuntimeError(f"Grok TTS failed: {e}")
