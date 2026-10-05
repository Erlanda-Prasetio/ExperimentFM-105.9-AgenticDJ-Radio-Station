"""
Playlist management and music metadata extraction
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import random


@dataclass
class Track:
    """Music track with metadata"""
    filepath: str
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    duration: float = 0.0
    language: str = "English"  # Default, can be detected
    
    def __str__(self):
        return f"{self.artist} - {self.title}"


class PlaylistManager:
    """
    Manages music library and playlist
    """
    
    def __init__(self, music_dir: str):
        self.music_dir = Path(music_dir)
        self.library: List[Track] = []
        self.current_index: int = 0
        
        print(f"[Playlist] Music directory: {music_dir}")
    
    def scan_library(self, extensions: tuple = ('.mp3', '.flac', '.m4a', '.wav')):
        """Scan music directory and extract metadata"""
        print(f"[Playlist] Scanning library...")
        
        if not self.music_dir.exists():
            print(f"[Playlist] ERROR: Directory not found: {self.music_dir}")
            return
        
        for filepath in self.music_dir.rglob('*'):
            if filepath.suffix.lower() in extensions:
                track = self._extract_metadata(str(filepath))
                if track:
                    self.library.append(track)
        
        print(f"[Playlist] Found {len(self.library)} tracks")
        
        # Shuffle library
        random.shuffle(self.library)
    
    def _extract_metadata(self, filepath: str) -> Optional[Track]:
        """Extract metadata from audio file"""
        try:
            audio = mutagen.File(filepath, easy=True)
            
            if audio is None:
                return None
            
            # Get basic info
            title = audio.get('title', [os.path.basename(filepath)])[0]
            artist = audio.get('artist', ['Unknown Artist'])[0]
            album = audio.get('album', [None])[0]
            genre = audio.get('genre', [None])[0]
            
            # Try to get year
            year = None
            if 'date' in audio:
                year = audio['date'][0][:4]  # Extract year
            
            # Duration
            duration = audio.info.length if hasattr(audio.info, 'length') else 0.0
            
            # Detect language (basic heuristic)
            language = self._detect_language(title, artist, genre)
            
            return Track(
                filepath=filepath,
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                year=year,
                duration=duration,
                language=language
            )
            
        except Exception as e:
            print(f"[Playlist] Error reading {filepath}: {e}")
            return None
    
    def _detect_language(self, title: str, artist: str, genre: Optional[str]) -> str:
        """
        Basic language detection from metadata
        Returns: English, Spanish, Hindi, Telugu, Indonesian, etc.
        """
        text = f"{title} {artist} {genre or ''}".lower()
        
        # Genre-based detection
        if genre:
            genre_lower = genre.lower()
            if 'bollywood' in genre_lower or 'tollywood' in genre_lower:
                return 'Hindi/Telugu'
            if 'reggaeton' in genre_lower or 'latin' in genre_lower:
                return 'Spanish'
            if 'k-pop' in genre_lower:
                return 'Korean'
            if 'j-pop' in genre_lower:
                return 'Japanese'
        
        # Default to English
        return 'English'
    
    def get_next(self) -> Optional[Track]:
        """Get next track in playlist"""
        if not self.library:
            return None
        
        track = self.library[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.library)
        
        return track
    
    def peek_next(self, offset: int = 1) -> Optional[Track]:
        """Peek at upcoming track without advancing"""
        if not self.library:
            return None
        
        index = (self.current_index + offset - 1) % len(self.library)
        return self.library[index]
    
    def add_track(self, filepath: str):
        """Manually add a track"""
        track = self._extract_metadata(filepath)
        if track:
            self.library.append(track)
            print(f"[Playlist] Added: {track}")
