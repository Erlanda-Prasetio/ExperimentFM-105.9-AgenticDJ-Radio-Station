"""
Main radio controller
Orchestrates: playlist → DJ agent → TTS → audio mixer
"""
import time
from threading import Thread, Event
from pathlib import Path
import os
import re
from pydub import AudioSegment

from audio_engine import RealtimeRadioMixer, AudioTrack
from playlist_manager import PlaylistManager, Track
from dj_agent import DJAgent
from tts_engine import TTSEngine


class RadioController:
    """
    Experiment FM 105.9 - AI Radio Station Controller
    
    Manages the full radio flow:
    1. Play song
    2. During song: prepare next transition (LLM + TTS)
    3. Crossfade to DJ voice
    4. Crossfade to next song
    5. Loop
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.stop_event = Event()
        
        # Components
        self.mixer = RealtimeRadioMixer(
            samplerate=config.get('samplerate', 44100),
            channels=2
        )
        
        self.playlist = PlaylistManager(config['music_dir'])
        
        self.dj = DJAgent(
            llm_endpoint=config['llm_endpoint'],
            llm_api_key=config['llm_api_key'],
            llm_model=config['llm_model'],
            station_name=config.get('station_name', 'Experiment FM 105.9')
        )
        
        self.tts = TTSEngine(
            main_dj_gender=config.get('dj_gender', 'male'),
            model=config.get('tts_model', 'F5-TTS')
        )
        
        # Station ident
        ident_path = config.get('station_ident')
        if ident_path:
            # Convert to absolute path if relative
            if not os.path.isabs(ident_path):
                ident_path = os.path.join(os.path.dirname(__file__), ident_path)
            self.station_ident_path = ident_path if os.path.exists(ident_path) else None
            if self.station_ident_path:
                print(f"[Radio] Station ident loaded: {self.station_ident_path}")
            else:
                print(f"[Radio] Station ident not found: {ident_path}")
        else:
            self.station_ident_path = None
        
        # State
        self.current_song: Track = None
        self.next_song: Track = None
        
        print(f"[Radio] Controller initialized")
    
    def start(self):
        """Start the radio station"""
        if self.running:
            print("[Radio] Already running")
            return
        
        print(f"\n{'='*50}")
        print(f"🎵 {self.config.get('station_name', 'Experiment FM')} 🎵")
        print(f"{'='*50}\n")
        
        # Scan music library
        self.playlist.scan_library()
        
        if not self.playlist.library:
            print("[Radio] ERROR: No music found in library")
            return
        
        # Start mixer
        self.mixer.start()
        self.running = True
        
        # Play startup sequence
        self._startup_sequence()
        
        # Main radio loop
        Thread(target=self._radio_loop, daemon=True).start()
        
        print("[Radio] ✓ Radio started - plug in and enjoy!")
    
    def stop(self):
        """Stop the radio station"""
        print("\n[Radio] Stopping...")
        self.running = False
        self.stop_event.set()
        time.sleep(1)
        self.mixer.stop()
        print("[Radio] Stopped")
    
    def _startup_sequence(self):
        """
        Play station ident + opening monologue
        """
        print("[Radio] Generating opening...")
        opening_script = self.dj.generate_opening()
        print(f"[Radio] DJ says: {opening_script}")
        
        opening_audio_path = self.tts.generate(opening_script)
        
        print("[Radio] Playing startup sequence...")
        
        # 1. Station ident (if available)
        if self.station_ident_path and os.path.exists(self.station_ident_path):
            print("[Radio] Playing station ident...")
            ident = self.mixer.load_audio(self.station_ident_path, "Station Ident", kind="voice")
            self.mixer.add_track(ident, slot="ident")
            
            # Wait for ident to finish
            while not ident.is_finished():
                time.sleep(0.1)
            time.sleep(0.5)
        
        # 2. DJ opening (already generated)
        opening_audio = self.mixer.load_audio(opening_audio_path, "DJ Opening", kind="voice")
        
        self.mixer.add_track(opening_audio, slot="dj")
        
        # Wait for opening to finish
        while not opening_audio.is_finished():
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        print("[Radio] Startup complete, starting music...")
    
    def _radio_loop(self):
        """
        Main radio loop
        Runs in background thread
        """
        # Get first song
        self.current_song = self.playlist.get_next()
        self.next_song = self.playlist.peek_next()
        
        while self.running and not self.stop_event.is_set():
            try:
                self._play_song_cycle()
            except Exception as e:
                print(f"[Radio] ERROR in loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)  # Prevent rapid error loop
    
    def _play_song_cycle(self):
        """
        One complete song cycle:
        - Play current song
        - Prepare transition during playback
        - Crossfade to DJ + next song
        """
        if not self.current_song or not self.next_song:
            print("[Radio] No songs available")
            time.sleep(5)
            return
        
        print(f"\n[Radio] ▶ Now playing: {self.current_song}")
        
        # Check if song_next exists from previous crossfade
        existing_track = self.mixer.get_track_info("song_next")
        
        if existing_track:
            # Rename song_next → song_current (from previous crossfade)
            with self.mixer.tracks_lock:
                if "song_next" in self.mixer.tracks:
                    self.mixer.tracks["song_current"] = self.mixer.tracks.pop("song_next")
            song_audio = self.mixer.tracks["song_current"]
            print("[Radio] Continuing from crossfaded track")
        else:
            # First song or error recovery: load fresh
            song_audio = self.mixer.load_audio(self.current_song.filepath, self.current_song.title)
            self.mixer.add_track(song_audio, slot="song_current")
        
        self.dj.increment_song_count()
        
        # Wait 5 seconds, then start preparing transition
        time.sleep(5)
        
        # Prepare transition in background
        print(f"[Radio] Preparing transition to: {self.next_song}")
        
        # 1. DJ decides intent
        intent = self.dj.decide_intent(self.current_song, self.next_song)
        print(f"[Radio] DJ intent: {intent.type} - {intent.reasoning}")
        
        # Handle silence intent
        if intent.type == "silence":
            print("[Radio] DJ: [silence - letting music speak]")
            # Just wait for song to finish, no DJ voice
            while not song_audio.is_finished() and self.running:
                time.sleep(0.5)
            
            # Move to next song
            self.current_song = self.next_song
            self.next_song = self.playlist.get_next()
            return
        
        # 2. Generate script
        script = self.dj.generate_script(intent, self.current_song, self.next_song)
        print(f"[Radio] DJ script: {script}")
        
        # 3. Generate TTS - TEMP: Skip splicing, use full English
        print(f"[Radio] DJ says: {script}")
        dj_audio_path = self.tts.generate(script, language='english')
        
        # TODO: Re-enable splicing when Hindi pronunciation fixed
        # dj_audio_path = self._generate_multilingual_transition(
        #     script, 
        #     self.current_song, 
        #     self.next_song
        # )
        dj_audio = self.mixer.load_audio(dj_audio_path, "DJ Transition", kind="voice")
        
        # 4. Pre-load next song
        next_song_audio = self.mixer.load_audio(self.next_song.filepath, self.next_song.title)
        
        # Wait for current song to reach last 10 seconds
        while song_audio.remaining > 10 and self.running:
            time.sleep(0.5)
        
        # 5. Duck music, play DJ, restore volume
        print("[Radio] Starting transition...")
        
        # Gradually lower music volume for DJ
        current_vol = 0.8
        target_vol = 0.1
        steps = 30
        step_duration = 3.0 / steps
        
        for i in range(steps):
            vol = current_vol - (current_vol - target_vol) * (i / steps)
            self.mixer.set_volume("song_current", vol)
            time.sleep(step_duration)
        
        # Play DJ voice
        self.mixer.add_track(dj_audio, slot="dj")
        
        # Wait for DJ to finish
        while not dj_audio.is_finished() and self.running:
            time.sleep(0.1)
        
        # Gradually restore music volume
        for i in range(steps):
            vol = target_vol + (0.8 - target_vol) * (i / steps)
            self.mixer.set_volume("song_current", vol)
            time.sleep(step_duration / 1.5)  # Faster fade up
        
        # 6. Crossfade to next song
        self.mixer.add_track(next_song_audio, slot="song_next")
        self.mixer.set_volume("song_next", 0.0)
        
        self.mixer.crossfade("song_current", "song_next", duration=3.0)
        
        time.sleep(3.5)  # Wait for crossfade
        
        # IMPORTANT: Remove DJ track
        self.mixer.remove_track("dj")
        
        # Swap slots: song_next becomes song_current for next iteration
        # (crossfade already removed old song_current)
        
        # Move to next song
        self.current_song = self.next_song
        self.next_song = self.playlist.get_next()
    
    def skip_to_end(self):
        """
        Skip current song to last 30 seconds (for testing)
        """
        try:
            # Access track directly from mixer's tracks dict
            if "song_current" in self.mixer.tracks:
                current_track = self.mixer.tracks["song_current"]
                if current_track and not current_track.is_finished():
                    # Set position to 30 seconds before end
                    target_pos = int((current_track.duration - 30.0) * current_track.samplerate)
                    target_pos = max(0, min(target_pos, len(current_track.data)))
                    current_track.position = target_pos
                    print(f"[Radio] ⏩ Skipped to last 30 seconds of {self.current_song.title}")
                else:
                    print("[Radio] Song already finished or not found")
            else:
                print("[Radio] No active song to skip")
        except Exception as e:
            print(f"[Radio] Skip failed: {e}")
    
    def _generate_multilingual_transition(self, script: str, current_song: Track, next_song: Track) -> str:
        """
        Generate DJ transition with audio splicing for song titles, movie names, and artists
        Uses native language voices for non-English content
        """
        import re
        from pydub import AudioSegment
        from pathlib import Path
        
        # Detect patterns:
        # "Song Title" → song title (native voice)
        # *Movie Name* → movie name (native voice)
        # @Artist Name@ → artist name (native voice)
        
        patterns = [
            (r'"([^"]+)"', 'title'),      # "Quoted text" = song title
            (r'\*([^*]+)\*', 'movie'),    # *Asterisk text* = movie name
            (r'@([^@]+)@', 'artist')      # @Symbol text@ = artist name
        ]
        
        # Find all matches with their positions
        matches = []
        for pattern, entity_type in patterns:
            for match in re.finditer(pattern, script):
                matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(1),
                    'type': entity_type,
                    'full_match': match.group(0)
                })
        
        # Sort by position
        matches.sort(key=lambda x: x['start'])
        
        # If no matches, fallback to full English
        if not matches:
            print("[Radio] No multilingual markers detected, using full English TTS")
            return self.tts.generate(script)
        
        print(f"[Radio] Splicing {len(matches)} multilingual segments...")
        
        # Split script into segments
        segments = []
        last_end = 0
        
        for match in matches:
            # English text before this match
            if match['start'] > last_end:
                english_text = script[last_end:match['start']]
                if english_text.strip():
                    segments.append({
                        'type': 'english',
                        'text': english_text
                    })
            
            # Determine language for this entity
            # Use current_song language as default context
            lang = current_song.language if current_song else 'English'
            
            segments.append({
                'type': match['type'],
                'text': match['text'],
                'language': lang
            })
            
            last_end = match['end']
        
        # Remaining English text
        if last_end < len(script):
            remaining = script[last_end:]
            if remaining.strip():
                segments.append({
                    'type': 'english',
                    'text': remaining
                })
        
        print(f"[Radio] Total segments: {len(segments)}")
        
        # Generate audio for each segment
        audio_segments = []
        
        for i, seg in enumerate(segments):
            print(f"  Segment {i+1}: {seg['type']} - {seg['text'][:40]}... [lang: {seg.get('language', 'N/A')}]")
            
            if seg['type'] == 'english':
                # English DJ voice
                audio_path = self.tts.generate(seg['text'], language='english')
            else:
                # Native language voice for title/movie/artist
                lang_map = {
                    'Indonesian': 'indonesian',
                    'Spanish': 'spanish',
                    'Hindi/Telugu': 'hindi',
                    'Hindi': 'hindi',
                    'Telugu': 'hindi',
                    'Tamil': 'hindi',
                    'Punjabi': 'hindi',
                    'Unknown': 'hindi'  # Default for unrecognized Indian languages
                }
                
                detected_lang = seg.get('language', 'Unknown')
                tts_lang = lang_map.get(detected_lang, 'hindi')  # Default to hindi for Indian content
                
                print(f"    → Detected: '{detected_lang}' → TTS: '{tts_lang}'")
                
                # Generate with native voice
                audio_path = self.tts.generate(seg['text'], language=tts_lang, gender='male')
            
            # Load segment
            audio_seg = AudioSegment.from_wav(audio_path)
            audio_segments.append(audio_seg)
        
        # Concatenate all segments without crossfade to avoid cutting
        final_audio = audio_segments[0]
        for seg in audio_segments[1:]:
            # Direct append without crossfade - cleaner for multilingual segments
            final_audio = final_audio + seg
        
        # Export final mixed audio
        output_path = Path(self.tts.cache_dir) / f"spliced_{hash(script) & 0xffffffff:08x}.wav"
        final_audio.export(str(output_path), format='wav')
        
        print(f"[Radio] ✓ Spliced audio: {output_path} ({len(final_audio)/1000:.1f}s)")
        return str(output_path)
