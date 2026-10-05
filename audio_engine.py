"""
Real-time audio mixing engine for Experiment FM 105.9
Handles multiple audio streams with crossfading
"""
import numpy as np
import sounddevice as sd
import librosa
from threading import Thread, Lock, Event
from queue import Queue
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class AudioTrack:
    """Represents an audio track with playback state"""
    data: np.ndarray  # Audio samples (stereo)
    samplerate: int
    name: str
    volume: float = 1.0
    position: int = 0
    
    @property
    def duration(self) -> float:
        """Duration in seconds"""
        return len(self.data) / self.samplerate
    
    @property
    def remaining(self) -> float:
        """Remaining time in seconds"""
        return (len(self.data) - self.position) / self.samplerate
    
    def is_finished(self) -> bool:
        """Check if track has finished playing"""
        return self.position >= len(self.data)


class RealtimeRadioMixer:
    """
    Real-time audio mixer with DJ capabilities:
    - Multiple simultaneous tracks (song, DJ voice, etc.)
    - Real-time volume control for crossfading
    - Low-latency streaming output
    """
    
    def __init__(self, samplerate: int = 44100, channels: int = 2, blocksize: int = 4096, output_device: str = None):
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.output_device = output_device  # None = Windows default; else substring match by name
        
        # Active tracks (playing simultaneously)
        self.tracks: dict[str, AudioTrack] = {}
        self.tracks_lock = Lock()
        
        # Control
        self.running = False
        self.stream: Optional[sd.OutputStream] = None
        
        print(f"[Mixer] Initialized: {samplerate}Hz, {channels}ch, blocksize={blocksize}")
    
    def load_audio(self, filepath: str, name: str) -> AudioTrack:
        """Load audio file and convert to mixer format"""
        print(f"[Mixer] Loading: {filepath}")
        
        # Load with librosa (handles MP3, WAV, etc.)
        data, sr = librosa.load(filepath, sr=self.samplerate, mono=False)
        
        # Ensure stereo
        if data.ndim == 1:
            data = np.stack([data, data])  # Mono to stereo
        
        # Transpose to (samples, channels) format
        data = data.T
        
        track = AudioTrack(
            data=data,
            samplerate=sr,
            name=name
        )
        
        print(f"[Mixer] Loaded: {name} ({track.duration:.1f}s)")
        return track
    
    def add_track(self, track: AudioTrack, slot: str = "main"):
        """Add track to mixer (starts playing immediately)"""
        with self.tracks_lock:
            self.tracks[slot] = track
        print(f"[Mixer] Added track '{track.name}' to slot '{slot}'")
    
    def remove_track(self, slot: str):
        """Remove track from mixer"""
        with self.tracks_lock:
            if slot in self.tracks:
                del self.tracks[slot]
                print(f"[Mixer] Removed slot '{slot}'")
    
    def set_volume(self, slot: str, volume: float):
        """Set track volume (0.0 to 1.0)"""
        with self.tracks_lock:
            if slot in self.tracks:
                self.tracks[slot].volume = max(0.0, min(1.0, volume))
    
    def get_track_info(self, slot: str) -> Optional[dict]:
        """Get track playback info"""
        with self.tracks_lock:
            if slot in self.tracks:
                track = self.tracks[slot]
                return {
                    "name": track.name,
                    "position": track.position / track.samplerate,
                    "duration": track.duration,
                    "remaining": track.remaining,
                    "volume": track.volume
                }
        return None
    
    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        Called by sounddevice for each audio block
        This is the heart of the mixer - runs in real-time
        """
        if status:
            print(f"[Mixer] Status: {status}")
        
        # Start with silence
        mixed = np.zeros((frames, self.channels), dtype=np.float32)
        
        with self.tracks_lock:
            finished_slots = []
            
            for slot, track in self.tracks.items():
                if track.is_finished():
                    finished_slots.append(slot)
                    continue
                
                # Get next chunk from this track
                end_pos = track.position + frames
                chunk = track.data[track.position:end_pos]
                
                # Handle end of track (pad with zeros if needed)
                if len(chunk) < frames:
                    chunk = np.pad(chunk, ((0, frames - len(chunk)), (0, 0)))
                
                # Mix in this track (with volume control)
                mixed += chunk * track.volume
                
                # Advance position
                track.position += frames
            
            # Remove finished tracks
            for slot in finished_slots:
                print(f"[Mixer] Track finished: {self.tracks[slot].name}")
                del self.tracks[slot]
        
        # Clip to prevent distortion
        mixed = np.clip(mixed, -1.0, 1.0)
        
        # Write to output
        outdata[:] = mixed
    
    def _resolve_output_device(self):
        """Resolve output_device (a name substring) to a sounddevice index.
        Prefers A2DP (btha2dp) over HFP (Hands-Free) for Bluetooth devices."""
        if not self.output_device:
            return None  # Windows default
        try:
            devs = sd.query_devices()
        except Exception as e:
            print(f"[Mixer] Device query failed: {e} - using default")
            return None
        needle = self.output_device.lower()
        matches = []
        for i, d in enumerate(devs):
            if d['max_output_channels'] > 0 and needle in d['name'].lower():
                matches.append((i, d))
        if not matches:
            print(f"[Mixer] Output device '{self.output_device}' not found - using Windows default")
            return None
        # Prefer non-hands-free (A2DP/stereo), then most channels
        def score(item):
            i, d = item
            n = d['name'].lower()
            hfp = ('hands-free' in n or 'headset' in n or 'hfp' in n) and 'btha2dp' not in n
            return (0 if not hfp else 1, -d['max_output_channels'])
        matches.sort(key=score)
        chosen_i, chosen = matches[0]
        print(f"[Mixer] Output device -> [{chosen_i}] {chosen['name']} ({chosen['max_output_channels']}ch)")
        return chosen_i

    def start(self):
        """Start the mixer stream"""
        if self.running:
            print("[Mixer] Already running")
            return
        
        device = self._resolve_output_device()
        
        self.stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            blocksize=self.blocksize,
            device=device,
            callback=self._audio_callback,
            dtype=np.float32,
            latency='high'  # Higher latency = more stable, no underruns
        )
        
        self.stream.start()
        self.running = True
        dev_name = "Windows default" if device is None else sd.query_devices(device)['name']
        print(f"[Mixer] Stream started -> {dev_name}")
    
    def stop(self):
        """Stop the mixer stream"""
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        print("[Mixer] Stream stopped")
    
    def crossfade(self, from_slot: str, to_slot: str, duration: float = 5.0):
        """
        Crossfade between two tracks over duration seconds
        Runs in background thread (non-blocking)
        """
        def _fade():
            steps = int(duration * 10)  # 100ms per step
            for i in range(steps + 1):
                progress = i / steps
                
                # Fade out old track
                self.set_volume(from_slot, 1.0 - progress)
                
                # Fade in new track
                self.set_volume(to_slot, progress)
                
                time.sleep(duration / steps)
            
            # Remove old track
            self.remove_track(from_slot)
            print(f"[Mixer] Crossfade complete: {from_slot} → {to_slot}")
        
        Thread(target=_fade, daemon=True).start()
        print(f"[Mixer] Starting crossfade: {from_slot} → {to_slot} ({duration}s)")
