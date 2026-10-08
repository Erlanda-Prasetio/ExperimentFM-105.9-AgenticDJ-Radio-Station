"""
Real-time audio mixing engine for Experiment FM 105.9
Handles multiple audio streams with crossfading
"""
import os
import json
import numpy as np
import sounddevice as sd
import librosa
from threading import Thread, Lock, Event
from queue import Queue
from dataclasses import dataclass
from typing import Optional
import time


# --- Music loudness normalization (songs only; DJ voice is already -16 LUFS) ---
# Songs come in at wildly different levels (-10 to -15 dB). Without this, the DJ
# sounds quiet next to loud tracks and every song change jumps in volume. We measure
# each song once and cache the gain, so repeat plays are instant.
MUSIC_LUFS = float(os.getenv("MUSIC_LUFS", "-16.0"))     # target integrated loudness (matches DJ voice @ -16 LUFS)
MUSIC_MAX_GAIN_DB = float(os.getenv("MUSIC_MAX_GAIN_DB", "8.0"))  # don't boost a quiet track to death
_LOUDNESS_CACHE_FILE = os.path.join("tts_cache", "loudness_cache.json")
_loudness_cache = None


def _load_loudness_cache() -> dict:
    global _loudness_cache
    if _loudness_cache is None:
        try:
            with open(_LOUDNESS_CACHE_FILE, "r", encoding="utf-8") as f:
                _loudness_cache = json.load(f)
        except Exception:
            _loudness_cache = {}
    return _loudness_cache


def _save_loudness_cache():
    if _loudness_cache is None:
        return
    try:
        os.makedirs(os.path.dirname(_LOUDNESS_CACHE_FILE), exist_ok=True)
        with open(_LOUDNESS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_loudness_cache, f, indent=0)
    except Exception:
        pass


def _file_sig(filepath: str) -> str:
    """Cache key: path + size + mtime, so a changed file re-measures."""
    try:
        st = os.stat(filepath)
        return f"{filepath}|{st.st_size}|{int(st.st_mtime)}"
    except Exception:
        return filepath


def trim_trailing_silence(data: np.ndarray, sr: int, threshold: float = 0.005) -> np.ndarray:
    """Trim trailing near-silence from a (samples, channels) array.

    Used on DJ voice so the 'post' lands on the last WORD, not on the tail silence
    F5-TTS leaves after it. Returns a shorter array (never empty).
    """
    if data is None or data.size == 0:
        return data
    mono = np.abs(data).max(axis=1) if data.ndim > 1 else np.abs(data)
    nz = np.where(mono > threshold)[0]
    if nz.size == 0:
        return data
    end = int(nz[-1]) + int(0.05 * sr)   # keep 50ms tail so it doesn't clip the word
    end = min(end, len(data))
    return data[:end]


def prepend_silence(data: np.ndarray, seconds: float, sr: int) -> np.ndarray:
    """Prepend `seconds` of silence to a (samples, channels) array.

    Used to start a song LATE so its intro rides under the DJ voice and the post
    lands exactly when the voice stops.
    """
    if data is None or seconds <= 0:
        return data
    pad = int(seconds * sr)
    if data.ndim > 1:
        silence = np.zeros((pad, data.shape[1]), dtype=data.dtype)
    else:
        silence = np.zeros(pad, dtype=data.dtype)
    return np.concatenate([silence, data], axis=0)


def measure_gain(filepath: str, data: np.ndarray, sr: int) -> float:
    """Return a linear gain to bring this track to MUSIC_LUFS (cached, capped, peak-safe)."""
    key = _file_sig(filepath)
    cache = _load_loudness_cache()
    if key in cache:
        return float(cache[key])

    gain = 1.0
    try:
        import pyloudnorm as pyln
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(data)  # data = (samples, channels)
        if np.isfinite(loudness):
            gain_db = MUSIC_LUFS - loudness
            gain_db = max(-MUSIC_MAX_GAIN_DB, min(MUSIC_MAX_GAIN_DB, gain_db))
            gain = float(10 ** (gain_db / 20.0))
    except Exception as e:
        print(f"[Loudness] Measure failed ({e}) - leaving gain at 1.0")
        gain = 1.0

    # Peak safety: never let the boosted signal clip.
    try:
        peak = float(np.max(np.abs(data * gain))) if data.size else 0.0
        if peak > 0.99:
            gain *= (0.99 / peak)
    except Exception:
        pass

    cache[key] = round(gain, 6)
    _save_loudness_cache()
    return gain


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

        # Optional session recorder (captures the final on-air mix to MP3).
        # Set via attach_recorder(); push() is a cheap queue append, safe for
        # the real-time callback.
        self.recorder = None

        print(f"[Mixer] Initialized: {samplerate}Hz, {channels}ch, blocksize={blocksize}")

    def attach_recorder(self, recorder):
        """Attach a SessionRecorder to capture the final on-air mix."""
        self.recorder = recorder
        print("[Mixer] Recorder attached")
    
    def load_audio(self, filepath: str, name: str, kind: str = "music") -> AudioTrack:
        """Load audio file and convert to mixer format.

        kind='music' -> apply loudness normalization (songs vary -10..-15 dB).
        kind='voice' -> no gain (DJ voice is already mastered to -16 LUFS).
        """
        print(f"[Mixer] Loading: {filepath}")
        
        # Load with librosa (handles MP3, WAV, etc.)
        data, sr = librosa.load(filepath, sr=self.samplerate, mono=False)
        
        # Ensure stereo
        if data.ndim == 1:
            data = np.stack([data, data])  # Mono to stereo
        
        # Transpose to (samples, channels) format
        data = data.T

        # Music loudness normalization (DJ voice is left untouched)
        if kind == "music":
            try:
                g = measure_gain(filepath, data, sr)
                if abs(g - 1.0) > 0.01:
                    data = data * g
                    print(f"[Loudness] {name}: gain x{g:.3f} ({20*np.log10(g):+.1f} dB) -> {MUSIC_LUFS} LUFS")
            except Exception as e:
                print(f"[Loudness] Skip for {name}: {e}")
        
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

        # Capture the final on-air mix (queue append only; never blocks here)
        if self.recorder is not None:
            self.recorder.push(mixed)

        # Write to output
        outdata[:] = mixed
    
    def _resolve_output_devices(self):
        """Resolve output_device to an ORDERED list of sounddevice indices to try.

        output_device may be a single name substring or a '|'-separated priority
        chain, e.g. "Headphones (NeraBox|Headphones (Realtek". Each needle is
        matched case-insensitively; the first chain entry that yields a working
        device wins, later entries are fallbacks. A trailing None (Windows
        default) is always appended as the last resort.
        Prefers A2DP (btha2dp) over HFP (Hands-Free) for Bluetooth devices."""
        if not self.output_device:
            return [None]  # Windows default
        try:
            devs = sd.query_devices()
        except Exception as e:
            print(f"[Mixer] Device query failed: {e} - using default")
            return [None]

        def score(item):
            i, d = item
            n = d['name'].lower()
            hfp = ('hands-free' in n or 'headset' in n or 'hfp' in n) and 'btha2dp' not in n
            return (0 if not hfp else 1, -d['max_output_channels'])

        chain = [c.strip() for c in str(self.output_device).split('|') if c.strip()]
        candidates = []
        seen = set()
        for needle in chain:
            needle_l = needle.lower()
            matches = [(i, d) for i, d in enumerate(devs)
                       if d['max_output_channels'] > 0 and needle_l in d['name'].lower()]
            if not matches:
                print(f"[Mixer] Output device '{needle}' not found - skipping")
                continue
            matches.sort(key=score)
            i, d = matches[0]
            if i not in seen:
                seen.add(i)
                candidates.append(i)
                print(f"[Mixer] Candidate -> [{i}] {d['name']} ({d['max_output_channels']}ch)")
        # Always keep Windows default as the final safety net.
        candidates.append(None)
        return candidates

    def _resolve_output_device(self):
        """Back-compat: return the first (highest-priority) candidate index."""
        return self._resolve_output_devices()[0]

    def start(self):
        """Start the mixer stream.

        Walks the resolved device priority chain and opens the FIRST device that
        actually works. A device that enumerates but fails to open (e.g. a
        Bluetooth headset that just disconnected) is skipped automatically, so a
        dead NeraBox silently falls back to Realtek / Windows default without a
        code change or a restart."""
        if self.running:
            print("[Mixer] Already running")
            return

        candidates = self._resolve_output_devices()
        last_err = None
        for device in candidates:
            name = "Windows default" if device is None else sd.query_devices(device)['name']
            try:
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
                print(f"[Mixer] Stream started -> {name}")
                return
            except Exception as e:
                last_err = e
                print(f"[Mixer] Could not open '{name}': {e} - trying next")
                try:
                    if self.stream:
                        self.stream.close()
                except Exception:
                    pass
                self.stream = None
        raise RuntimeError(f"[Mixer] No working output device (last error: {last_err})")
    
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
