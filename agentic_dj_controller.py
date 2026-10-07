"""
Agentic Radio Controller - Full LLM Autonomy
DJ decides song selection + script generation in single call
"""
import os
import re
import time
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict

from playlist_manager import PlaylistManager, Track
from tts_engine import TTSEngine
from audio_engine import RealtimeRadioMixer, AudioTrack, trim_trailing_silence, prepend_silence
from phonetic_respell import respell, normalize_numbers
from listener_llm import (ListenerLLM, load_seeds, pick_seed,
                          time_profile, generate_session)
from song_intro import detect_intro


@dataclass
class AgenticDecision:
    """LLM's autonomous decision"""
    reasoning: str
    intent: str  # trivia, weather, vibe-check, energetic, chill, surprise
    next_song_id: str
    script: str
    repeat_reason: Optional[str] = None  # strong reason if replaying a song
    vibe_notes: Optional[str] = None
    dj_name: Optional[str] = None        # who is speaking this break
    dj_voice: Optional[str] = None       # voice id for TTS (ara/jr/naksh)
    is_handoff: Optional[bool] = False   # True if this is a goodbye/hello handoff break
    is_for_you_zone: Optional[bool] = False   # True if this break reads listener messages
    listener: Optional[list] = None      # listener messages read this break (list of dicts)
    messages_read: Optional[int] = None  # how many listener messages the DJ actually read this break (resolved from the DJ's reported numbers)
    talk_over_intro: Optional[bool] = False  # Bruce feature: ride the song intro, land the post on the DJ's last word


class AgenticRadioController:
    """
    Fully autonomous AI radio controller
    LLM has complete control over programming
    """
    
    def __init__(self, music_dir: str, station_name: str, llm_endpoint: str, 
                 llm_api_key: str, llm_model: str, tts_model: str = "F5-TTS", dj_voice: str = "naksh",
                 dj_filter: Optional[List[str]] = None, record_mode: bool = False,
                 record_hours: float = 0.0, state_file: Optional[str] = None):
        self.station_name = station_name
        self.llm_endpoint = llm_endpoint
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.dj_voice = dj_voice  # Voice preference based on playlist
        self.music_dir = music_dir
        self.dj_filter = dj_filter  # optional subset of DJ names to restrict the roster
        # Recording mode: fresh run from 0, isolated state files (LIVE state untouched)
        self.record_mode = bool(record_mode)
        self.record_hours = float(record_hours or 0.0)
        self.record_started_at = datetime.now()
        self.shift_hours = float(os.getenv("SHIFT_HOURS", "3"))  # rotating DJ shift length
        # Phonetic respelling: a hardcoded dictionary tuned for F5-TTS. A multilingual
        # engine (Qwen) may pronounce native names better WITHOUT it. TTS_PHONETIC=off
        # disables BOTH the respell() step and the "write phonetically" prompt rule.
        self.phonetic = os.getenv("TTS_PHONETIC", "on").strip().lower() not in ("0", "off", "false", "no")
        
        # Initialize components
        self.playlist = PlaylistManager(music_dir)
        self.playlist.scan_library()
        self.tts = TTSEngine(model=tts_model, main_dj_gender=self._voice_to_gender(dj_voice))
        self.mixer = RealtimeRadioMixer(output_device=os.getenv("AUDIO_OUTPUT") or None)
        self.mixer.start()
        
        # Session memory
        self.play_history: List[str] = []  # Track filepaths (recent, capped)
        self.current_song: Optional[Track] = None
        self.session_start = datetime.now()
        self.decisions_log: List[Dict] = []  # AI reasoning log
        self._song_id_map: Dict = {}  # Numeric ID -> Track (for LLM selection)
        
        # Cycle tracking (persistent across sessions)
        self.played_this_cycle: set = set()  # filepaths played since last cycle reset
        self.cycle_number: int = 1
        self.last_session_song: Optional[str] = None  # "Title - Artist" from previous session
        
        # Rotating DJ roster
        self.roster = self._load_roster()          # list of {name, voice, persona}
        self.current_dj_idx: int = 0
        self.shift_started_at = datetime.now()
        self.handoff_armed: bool = False           # True => next decision is the new DJ's hello
        self.resumed_gap_hours: float = 0.0        # downtime detected on resume (0 = none)
        self.dj_just_started: bool = False         # True => current DJ hasn't spoken yet this shift
        self.last_station_id_hour: Optional[str] = None  # clock-hour key of the last station ID ("2026-10-05 16")
        
        # For You Zone (listener sessions via a SEPARATE listener LLM)
        self.listener_llm = ListenerLLM()
        self.fyz_min_gap_songs = int(os.getenv("FYO_MIN_GAP_SONGS", "5"))   # min songs between sessions
        self.fyz_songs_since = 999         # songs since last For You Zone session
        self.fyz_used_names: List[str] = []
        self.fyz_used_cities: List[str] = []
        self.fyz_used_occasions: List[str] = []
        self.fyz_queue: List[dict] = []    # listener messages pending in the ACTIVE session
        self.fyz_session_no: int = 0       # counter for logging
        
        # State file (per-playlist, persists across sessions).
        # In RECORDING MODE we use an isolated, per-run state file and NEVER load
        # the LIVE state -> every recording starts fresh from 0 and the LIVE
        # radio_state_*.json is never read or written.
        if self.record_mode:
            self.state_file = self._record_state_file_path(music_dir)
            self.decisions_log_file = self._record_decisions_log_path(music_dir)
            self.play_history = []
            self.played_this_cycle = set()
            self.cycle_number = 1
            print(f"[Record] Fresh run from 0 (isolated state: {self.state_file})")
            print(f"[Record] LIVE state NOT touched")
        else:
            # An explicit state_file (e.g. qwen_radio_state_*.json) isolates this
            # run from the LIVE radio state -> the old state is never touched.
            self.state_file = state_file or self._state_file_path(music_dir)
            # Append-only decision log (JSONL). Unlike session_history_*.json (which is
            # overwritten each run) this is appended, so every break survives restarts.
            self.decisions_log_file = self._decisions_log_path(music_dir)
            self.load_state()

        # Apply record-mode shift length: total hours / number of DJs on rotation.
        if self.record_mode and self.record_hours > 0 and len(self.roster) > 1:
            self.shift_hours = self.record_hours / len(self.roster)
            print(f"[Record] Shift = {self.record_hours}h / {len(self.roster)} DJs "
                  f"= {self.shift_hours*60:.0f} min per DJ")
        elif self.record_mode and len(self.roster) <= 1:
            self.shift_hours = 0  # single DJ: no shift/handoff
        
        
        # Pre-generation queue (prepare next transition while playing)
        self.next_decision: Optional[AgenticDecision] = None
        self.next_dj_audio: Optional[str] = None
        
        print(f"[Agentic Radio] Initialized")
        print(f"[Agentic Radio] Library: {len(self.playlist.library)} songs")
        print(f"[Agentic Radio] DJ Voice: {dj_voice.upper()}")
        if len(self.roster) > 1:
            names = " -> ".join(d['name'] for d in self.roster)
            print(f"[Agentic Radio] Rotating DJs: {names} (shift {self.shift_hours}h)")
        print(f"[Agentic Radio] AI DJ: Full autonomy mode")
    
    def _fyz_seeds(self):
        """Load the curated seed pool for the For You Zone (cached)."""
        if getattr(self, "_fyz_seed_cache", None) is None:
            try:
                self._fyz_seed_cache = load_seeds("listener_seeds.json")
            except Exception as e:
                print(f"[For You Zone] Failed to load seeds: {e}")
                self._fyz_seed_cache = {"cities": [], "names": [], "occasions": []}
        return self._fyz_seed_cache

    def _roster_file_path(self, music_dir: str) -> str:
        """Roster file per playlist (dj_roster_<slug>.json), falls back to dj_roster.json"""
        slug = os.path.basename(os.path.normpath(music_dir))
        import re
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', slug).strip('_').lower()
        per = f"dj_roster_{slug}.json"
        if os.path.exists(per):
            return per
        return "dj_roster.json"
    
    def _load_roster(self) -> List[Dict]:
        """Load rotating DJ roster for this playlist.
        A playlist with no roster entry = single-DJ mode (no fallback to other playlists).
        An optional dj_filter (subset of DJ names) restricts who is on rotation."""
        path = self._roster_file_path(self.music_dir)
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            slug = os.path.basename(os.path.normpath(self.music_dir))
            import re
            slug = re.sub(r'[^a-zA-Z0-9]+', '_', slug).strip('_').lower()
            # A per-playlist file may be a bare list; the shared file is a dict keyed by slug
            if isinstance(data, list):
                roster = data
            else:
                roster = data.get(slug)
                if not roster:
                    print(f"[Roster] No entry for '{slug}' - single DJ mode")
                    return []
            # Apply optional DJ filter (case-insensitive match on name)
            if self.dj_filter:
                want = [d.strip().lower() for d in self.dj_filter]
                filtered = [d for d in roster if d.get('name', '').lower() in want]
                if filtered:
                    names = ", ".join(d['name'] for d in filtered)
                    print(f"[Roster] DJ filter {self.dj_filter} -> {names}")
                    roster = filtered
                else:
                    print(f"[Roster] ⚠️ filter {self.dj_filter} matched no DJ - using full roster")
            return roster
        except Exception as e:
            print(f"[Roster] Failed to load ({e}) - single DJ mode")
            return []
    
    def _state_file_path(self, music_dir: str) -> str:
        """Derive a per-playlist state file path from the music directory name"""
        import re
        name = os.path.basename(os.path.normpath(music_dir))
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        return f"radio_state_{slug}.json"

    def _decisions_log_path(self, music_dir: str) -> str:
        """Append-only per-playlist decision log (JSONL)."""
        import re
        name = os.path.basename(os.path.normpath(music_dir))
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        return f"decisions_log_{slug}.jsonl"

    def _record_state_file_path(self, music_dir: str) -> str:
        """Isolated state file for a recording run (never collides with LIVE state)."""
        import re
        name = os.path.basename(os.path.normpath(music_dir))
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"radio_state_{slug}_REC_{stamp}.json"

    def _record_decisions_log_path(self, music_dir: str) -> str:
        """Isolated decision log for a recording run."""
        import re
        name = os.path.basename(os.path.normpath(music_dir))
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"decisions_log_{slug}_REC_{stamp}.jsonl"

    def _log_decision_line(self, entry: dict):
        """Append ONE decision as a JSON line (survives restarts). Never raises."""
        try:
            with open(self.decisions_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Log] Decision line failed: {e}")
    
    def load_state(self):
        """Load persistent state from previous session (per-playlist, no decay)"""
        if not os.path.exists(self.state_file):
            print(f"[State] No previous state found - fresh start")
            return
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            self.play_history = state.get('play_history', [])
            self.played_this_cycle = set(state.get('played_this_cycle', []))
            self.cycle_number = state.get('cycle_number', 1)
            self.last_session_song = state.get('last_song', None)
            # Rotating DJ state
            self.current_dj_idx = state.get('current_dj_idx', 0)
            shift_iso = state.get('shift_started_at')
            if shift_iso:
                try:
                    self.shift_started_at = datetime.fromisoformat(shift_iso)
                except Exception:
                    self.shift_started_at = datetime.now()
            self.handoff_armed = state.get('handoff_armed', False)
            self.last_station_id_hour = state.get('last_station_id_hour')

            # How long was the station quiet? (now - last save)
            last_end = state.get('last_session_end')
            downtime_h = 0.0
            if last_end:
                try:
                    downtime_h = (datetime.now() - datetime.fromisoformat(last_end)).total_seconds() / 3600
                except Exception:
                    downtime_h = 0.0

            # --- Indefinite shift catch-up ---
            # Treat the shift clock as running forever: every whole shift_hours of
            # real time = one handoff, even while the laptop was asleep. The on-air
            # DJ resumes with the correct REMAINING time (even if only 10 min left).
            if self.roster and len(self.roster) > 1 and self.shift_hours > 0:
                advanced = False
                # (a) A goodbye aired but the hello never did -> the next DJ is already due.
                if self.handoff_armed:
                    self.current_dj_idx = (self.current_dj_idx + 1) % len(self.roster)
                    self.shift_started_at = self.shift_started_at + timedelta(hours=self.shift_hours)
                    self.handoff_armed = False
                    advanced = True
                # (b) Count whole shifts that elapsed while offline.
                elapsed = (datetime.now() - self.shift_started_at).total_seconds() / 3600
                n = int(elapsed // self.shift_hours)
                if n > 0:
                    self.current_dj_idx = (self.current_dj_idx + n) % len(self.roster)
                    self.shift_started_at = self.shift_started_at + timedelta(hours=n * self.shift_hours)
                    advanced = True
                    print(f"[DJ] {n} shift(s) passed while offline -> now on air: {self._current_dj()['name']}")
                self.dj_just_started = advanced
                self.resumed_gap_hours = downtime_h

            print(f"[State] Resumed from previous session ({self.state_file}):")
            if self.last_session_song:
                print(f"  - Last song: {self.last_session_song}")
            print(f"  - Cycle #{self.cycle_number}, {len(self.played_this_cycle)}/{len(self.playlist.library)} songs played this cycle")
            print(f"  - Recent history: {len(self.play_history)} songs")
            if downtime_h > 0.05:
                print(f"  - Station was quiet for {downtime_h:.1f}h")
            if self.roster:
                dj = self._current_dj()
                elapsed_now = (datetime.now() - self.shift_started_at).total_seconds() / 3600
                left = self.shift_hours - elapsed_now
                print(f"  - On air: {dj['name']} ({elapsed_now:.1f}h into {self.shift_hours}h shift, {left:.1f}h left)")
        except Exception as e:
            print(f"[State] Failed to load ({e}) - starting fresh")
    
    def save_state(self):
        """Save persistent state to disk (called after every song)"""
        try:
            last_song = None
            if self.play_history:
                t = self._get_track_by_filepath(self.play_history[-1])
                if t:
                    last_song = f"{t.title} - {t.artist}"
            state = {
                'playlist': os.path.basename(os.path.normpath(self.music_dir)),
                'last_song': last_song,
                'last_session_end': datetime.now().isoformat(),
                'cycle_number': self.cycle_number,
                'played_this_cycle': list(self.played_this_cycle),
                'play_history': self.play_history[-100:],  # cap to keep file small
                'total_played_all_time': len(self.play_history),
                # Rotating DJ
                'current_dj_idx': self.current_dj_idx,
                'shift_started_at': self.shift_started_at.isoformat(),
                'handoff_armed': self.handoff_armed,
                'last_station_id_hour': self.last_station_id_hour,
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[State] Save failed: {e}")
    
    # ----- Rotating DJ helpers -----
    def _current_dj(self) -> Optional[Dict]:
        """Return the currently on-air DJ dict, or None if single-DJ mode"""
        if not self.roster:
            return None
        return self.roster[self.current_dj_idx % len(self.roster)]
    
    def _next_dj(self) -> Optional[Dict]:
        """Return the next DJ in rotation"""
        if not self.roster:
            return None
        return self.roster[(self.current_dj_idx + 1) % len(self.roster)]
    
    def _shift_elapsed_hours(self) -> float:
        return (datetime.now() - self.shift_started_at).total_seconds() / 3600
    
    def _shift_expired(self) -> bool:
        """True if the current DJ has completed their shift"""
        return len(self.roster) > 1 and self._shift_elapsed_hours() >= self.shift_hours
    
    def _advance_dj(self):
        """Hand the mic to the next DJ and reset the shift clock"""
        if not self.roster:
            return
        old = self._current_dj()['name']
        self.current_dj_idx = (self.current_dj_idx + 1) % len(self.roster)
        new = self._current_dj()['name']
        self.shift_started_at = datetime.now()
        self.handoff_armed = False
        print(f"[DJ] Handoff complete: {old} -> {new} (new {self.shift_hours}h shift)")
    
    def _prep_tts_text(self, script: str) -> str:
        """Prepare a DJ script for TTS: phonetic respell (Hindi names) + number
        normalization (105.9 -> 'one oh five point nine') + light punctuation cleanup.
        Code owns this so the LLM can keep writing natural text.
        Set TTS_PHONETIC=off to skip the respell step (for multilingual engines)."""
        text = respell(script) if self.phonetic else script
        text = normalize_numbers(text)
        text = text.replace('!', '.').replace('...', ',')
        return text

    def _voice_to_gender(self, voice: str) -> str:
        """Map voice name to gender"""
        voice_gender_map = {
            "naksh": "male",
            "naksh_thick": "male",
            "ara": "female",
            "jr": "male",
        }
        return voice_gender_map.get(voice.lower(), "male")
    
    def start_broadcast(self):
        """Start autonomous broadcast loop"""
        print("\n🔴 GOING LIVE - AI DJ in control\n")
        if self.record_mode and self.record_hours > 0:
            print(f"[Record] Auto-stop after {self.record_hours}h (Ctrl+C stops early)\n")

        try:
            while True:
                # Recording mode: auto-stop once the requested duration elapsed.
                if self.record_mode and self.record_hours > 0:
                    elapsed_h = (datetime.now() - self.record_started_at).total_seconds() / 3600
                    if elapsed_h >= self.record_hours:
                        print(f"\n[Record] ⏹ Reached {self.record_hours}h - stopping recording.")
                        break
                self._autonomous_cycle()
        except KeyboardInterrupt:
            print("\n[Radio] Stopping broadcast...")
        finally:
            # Save session history on exit (isolated file in record mode)
            try:
                self.save_session_log()
            except Exception as e:
                print(f"[Radio] session log save failed: {e}")
            self.mixer.stop()
    
    def _autonomous_cycle(self):
        """Single autonomous broadcast cycle with pre-generation"""
        try:
            # Step 1: Use pre-generated decision or generate now
            if self.next_decision and self.next_dj_audio:
                print(f"\n[Using pre-generated transition]")
                decision = self.next_decision
                dj_audio_path = self.next_dj_audio
                self.next_decision = None
                self.next_dj_audio = None
                
                # Log the pre-generated decision (was missing before!)
                _pre_track = self._song_id_map.get(str(decision.next_song_id))
                _pre_name = f"{_pre_track.title} - {_pre_track.artist}" if _pre_track else decision.next_song_id
                _pre_repeat = getattr(decision, 'repeat_reason', None) or ''
                _pre_dj = getattr(decision, 'dj_name', None) or ''
                _pre_handoff = getattr(decision, 'is_handoff', False)
                _pre_fyz = getattr(decision, 'is_for_you_zone', False)
                _pre_read = getattr(decision, 'messages_read', 0) or 0
                _pre_bruce = bool(getattr(decision, 'talk_over_intro', False))
                print(f"\n{'='*60}")
                print(f"🤖 AI DJ DECISION #{len(self.decisions_log) + 1} (pre-generated)")
                print(f"{'='*60}")
                print(f"DJ:         {_pre_dj}{' [HANDOFF]' if _pre_handoff else ''}{f' [FOR YOU ZONE x{_pre_read}]' if _pre_fyz else ''}")
                print(f"Intent:     {decision.intent}")
                print(f"Reasoning:  {decision.reasoning}")
                print(f"Next Song:  {_pre_name}")
                if _pre_bruce:
                    print(f"BRUCE:      🎙️ talk over intro (post on last word)")
                if _pre_repeat:
                    print(f"REPEAT:     ♻️ {_pre_repeat}")
                print(f"Script:     {decision.script[:100]}...")
                print(f"{'='*60}\n")
                
                self.decisions_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'dj': _pre_dj,
                    'handoff': _pre_handoff,
                    'for_you_zone': _pre_fyz,
                    'listener': getattr(decision, 'listener', None),
                    'intent': decision.intent,
                    'reasoning': decision.reasoning,
                    'next_song': _pre_name,
                    'script': decision.script,
                    'repeat_reason': _pre_repeat,
                    'talk_over_intro': _pre_bruce,
                    'note': 'pre_generated'
                })
            else:
                print(f"\n[Generating transition...]")
                decision = self._get_llm_decision()
                
                _cur_repeat = getattr(decision, 'repeat_reason', None) or ''
                _cur_dj = getattr(decision, 'dj_name', None) or ''
                _cur_handoff = getattr(decision, 'is_handoff', False)
                _cur_fyz = getattr(decision, 'is_for_you_zone', False)
                _cur_read = getattr(decision, 'messages_read', 0) or 0
                _cur_bruce = bool(getattr(decision, 'talk_over_intro', False))
                _cur_track = self._song_id_map.get(str(decision.next_song_id))
                _cur_name = f"{_cur_track.title} - {_cur_track.artist}" if _cur_track else decision.next_song_id
                print(f"\n{'='*60}")
                print(f"🤖 AI DJ DECISION #{len(self.decisions_log) + 1}")
                print(f"{'='*60}")
                print(f"DJ:         {_cur_dj}{' [HANDOFF]' if _cur_handoff else ''}{f' [FOR YOU ZONE x{_cur_read}]' if _cur_fyz else ''}")
                print(f"Intent:     {decision.intent}")
                print(f"Reasoning:  {decision.reasoning}")
                print(f"Next Song:  {_cur_name}")
                if _cur_bruce:
                    print(f"BRUCE:      🎙️ talk over intro (post on last word)")
                if _cur_repeat:
                    print(f"REPEAT:     ♻️ {_cur_repeat}")
                print(f"Script:     {decision.script[:100]}...")
                print(f"{'='*60}\n")
                
                # Log decision
                self.decisions_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'dj': _cur_dj,
                    'handoff': _cur_handoff,
                    'for_you_zone': _cur_fyz,
                    'listener': getattr(decision, 'listener', None),
                    'intent': decision.intent,
                    'reasoning': decision.reasoning,
                    'next_song': _cur_name,
                    'script': decision.script,
                    'repeat_reason': _cur_repeat,
                    'talk_over_intro': _cur_bruce
                })
                
                # Generate TTS (use the on-air DJ's voice if rotating)
                print(f"[TTS] Generating: '{decision.script[:60]}...'")
                clean_script = self._prep_tts_text(decision.script)
                dj_audio_path = self.tts.generate(clean_script, language='english', voice_name=decision.dj_voice)
            
            # Step 2: Get selected track (resolve numeric ID via map)
            next_song = self._song_id_map.get(str(decision.next_song_id))
            if not next_song:
                # Try filepath lookup as fallback (in case LLM returned a path)
                next_song = self._get_track_by_filepath(decision.next_song_id)
            if not next_song:
                print(f"[ERROR] Song ID not found: {decision.next_song_id}")
                print(f"[Fallback] LLM hallucinated - picking random song from library")
                # Fallback: pick RANDOM song not in last 10 (was [0] = always same song!)
                import random
                recent = set(str(fp) for fp in self.play_history[-10:])
                available = [t for t in self.playlist.library if str(t.filepath) not in recent]
                if not available:
                    available = self.playlist.library  # If all played, use any
                next_song = random.choice(available)
                print(f"[Fallback] Selected: {next_song.title} - {next_song.artist}")
                
                # RE-GENERATE script with correct song
                print(f"[Fallback] Re-generating DJ script for correct song...")
                corrected_decision = self._get_llm_decision(force_song=next_song.filepath)
                decision.script = corrected_decision.script
                decision.intent = corrected_decision.intent
                decision.reasoning = corrected_decision.reasoning
                
                # Log the corrected decision
                self.decisions_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'intent': decision.intent,
                    'reasoning': decision.reasoning,
                    'next_song': str(next_song.filepath),
                    'script': decision.script,
                    'note': 'fallback_corrected'
                })
                
                # Generate TTS with corrected script (keep the DJ voice)
                clean_script = self._prep_tts_text(decision.script)
                dj_audio_path = self.tts.generate(clean_script, language='english', voice_name=decision.dj_voice)
            
            # Step 3+4: DJ voice + song. THREE modes, decided by CODE (reliable):
            #   RIDE (Bruce) : short script over a real intro -> the song's INTRO rides
            #                  (ducked) under the voice; music lifts to full on the last word.
            #   TALK-UP      : any "hit the post" that can't ride -> the music comes up
            #                  (from the top) in the LAST FEW SECONDS of the script and
            #                  swells to full right as the DJ finishes.
            #   NORMAL       : the DJ talks first, then the song starts from the TOP.
            song_track = self.mixer.load_audio(str(next_song.filepath), name=next_song.title, kind="music")
            intro = detect_intro(str(next_song.filepath))
            voice_track = self.mixer.load_audio(dj_audio_path, name="dj_intro", kind="voice")
            voice_track.data = trim_trailing_silence(voice_track.data, voice_track.samplerate)
            voice_len = voice_track.duration
            sr = voice_track.samplerate

            entry = max(0.0, voice_len - intro)   # RIDE: song start so the body lands on the last word
            duck = float(os.getenv("BRUCE_DUCK", "0.22"))
            lead = float(os.getenv("TALKUP_LEAD_S", "2.5"))       # TALK-UP: music comes on this early
            talkup_duck = float(os.getenv("TALKUP_DUCK", "0.5"))  # TALK-UP: level it swells in from

            # The DJ's intent: "I want to hit the post this break."
            want_post = bool(getattr(decision, 'talk_over_intro', False))
            max_voice = float(os.getenv("BRUCE_MAX_VOICE_S", "18"))
            min_intro = float(os.getenv("BRUCE_MIN_INTRO_S", "10"))
            max_gap = float(os.getenv("BRUCE_MAX_GAP_S", "4"))

            # RIDE needs a short script over a real intro with a tight gap.
            ride = (want_post and voice_len <= max_voice
                    and intro >= min_intro and entry <= max_gap)
            # TALK-UP covers every other "hit the post" - it needs a script long enough
            # to have a "last few seconds".
            talkup = want_post and not ride and voice_len >= lead + 1.5
            mode = "RIDE" if ride else ("TALK-UP" if talkup else "NORMAL")

            # Append-only audit line (survives restarts). One per break, with the
            # resolved mode + the real lengths that produced it.
            self._log_decision_line({
                'timestamp': datetime.now().isoformat(),
                'dj': getattr(decision, 'dj_name', None) or '',
                'handoff': bool(getattr(decision, 'is_handoff', False)),
                'for_you_zone': bool(getattr(decision, 'is_for_you_zone', False)),
                'intent': decision.intent,
                'next_song': f"{next_song.title} - {next_song.artist}",
                'want_post': want_post,
                'mode': mode,
                'voice_len': round(voice_len, 2),
                'intro': round(intro, 2),
                'entry': round(entry, 2),
                'script': decision.script,
                'reasoning': decision.reasoning,
            })

            if ride:
                # --- RIDE (Bruce): ride the intro, hit the post on the last word ---
                print(f"[Bruce] Ride intro: voice {voice_len:.1f}s, intro {intro:.1f}s, "
                      f"song enters {entry:.1f}s in, ducked to {int(duck*100)}%, "
                      f"music lifts at {voice_len:.1f}s (on your last word)")
                song_track.volume = duck
                if entry > 0.05:
                    song_track = AudioTrack(
                        data=prepend_silence(song_track.data, entry, sr),
                        samplerate=sr, name=song_track.name, volume=duck)
                self.mixer.remove_track("music")
                self.mixer.add_track(song_track, slot="music")
                self.mixer.add_track(voice_track, slot="voice")
                t0 = time.time()
                while time.time() - t0 < voice_len:
                    time.sleep(0.05)
                self.mixer.set_volume("music", 1.0)
                self.mixer.remove_track("voice")
                print("[Bruce] Post hit - music back to full")
            elif talkup:
                # --- TALK-UP: music comes up in the last few seconds, swells to full on the post ---
                start = max(0.0, voice_len - lead)   # when the music turns on
                print(f"[Talk-up] voice {voice_len:.1f}s -> music comes up at {start:.1f}s "
                      f"(last {lead:.1f}s), swelling {int(talkup_duck*100)}%->100% onto your last word")
                song_track = AudioTrack(
                    data=prepend_silence(song_track.data, start, sr),
                    samplerate=sr, name=song_track.name, volume=talkup_duck)
                self.mixer.remove_track("music")
                self.mixer.add_track(song_track, slot="music")
                self.mixer.add_track(voice_track, slot="voice")
                t0 = time.time()
                while True:
                    el = time.time() - t0
                    if el >= voice_len:
                        break
                    if el >= start and lead > 0:
                        frac = min(1.0, (el - start) / lead)
                        self.mixer.set_volume("music", talkup_duck + (1.0 - talkup_duck) * frac)
                    time.sleep(0.05)
                self.mixer.set_volume("music", 1.0)
                self.mixer.remove_track("voice")
                print("[Talk-up] Post hit - music at full")
            else:
                # --- NORMAL: DJ talks first, then the song starts from the TOP ---
                # The song is "delayed" by the script itself: it only begins once the DJ
                # stops, so the vocals never clash with the voice.
                if self.mixer.get_track_info("music"):
                    print("[Ducking] Lowering music volume to 30%")
                    self.mixer.set_volume("music", 0.3)

                self.mixer.add_track(voice_track, slot="voice")
                print("[Press 'S' to skip DJ intro]")
                while not voice_track.is_finished():
                    time.sleep(0.1)

                if self.mixer.get_track_info("music"):
                    print("[Ducking] Restoring music volume to 100%")
                    self.mixer.set_volume("music", 1.0)
                self.mixer.remove_track("voice")

                print(f"[Playing] 🎵 {next_song.title} - {next_song.artist} "
                      f"(song starts from the top after the {voice_len:.0f}s script)")
                self.mixer.remove_track("music")
                self.mixer.add_track(song_track, slot="music")
            
            # Step 5: PRE-GENERATE next transition while song plays
            # Wait 15 seconds before starting (let song establish)
            print("[Waiting 15s before pre-generating next transition...]")
            start_time = time.time()
            while not song_track.is_finished():
                elapsed = time.time() - start_time
                
                # After 15 seconds, start pre-generating if not done
                if elapsed > 15 and self.next_decision is None:
                    print("\n[Background] Pre-generating next transition...")
                    # Mark this song as played FIRST (avoid double-append on retry)
                    if str(next_song.filepath) not in self.play_history:
                        self.play_history.append(str(next_song.filepath))
                    self.played_this_cycle.add(str(next_song.filepath))  # cycle tracking
                    self.current_song = next_song
                    self.fyz_songs_since += 1   # For You Zone eligibility counter
                    
                    # Save session log + persistent state after EVERY song
                    try:
                        self.save_session_log()
                        self.save_state()
                    except Exception as save_err:
                        print(f"[History] Save failed: {save_err}")
                    
                    try:
                        # Generate next decision
                        next_decision = self._get_llm_decision()
                        print(f"[Background] Next intent: {next_decision.intent}")
                        
                        # Generate TTS
                        clean_script = self._prep_tts_text(next_decision.script)
                        next_dj_audio = self.tts.generate(clean_script, language='english', voice_name=next_decision.dj_voice)
                        
                        # Store for next cycle
                        self.next_decision = next_decision
                        self.next_dj_audio = next_dj_audio
                        print("[Background] ✓ Next transition ready!")
                    except Exception as e:
                        print(f"[Background] ERROR pre-generating: {e}")
                
                time.sleep(0.1)
            
        except Exception as e:
            print(f"[Radio] ERROR in cycle: {e}")
            import traceback
            traceback.print_exc()
            # Save on error too
            try:
                self.save_session_log()
            except:
                pass
            time.sleep(5)
    
    def _get_llm_decision(self, force_song: str = None) -> AgenticDecision:
        """Get fully autonomous decision from LLM"""
        # Build context
        now = datetime.now()
        hour = now.hour
        time_str = now.strftime('%I:%M %p %A')
        time_of_day = self._get_time_of_day(hour)
        
        # Recent play history (last 5 songs)
        recent_plays = []
        for track_filepath in self.play_history[-5:]:
            track = self._get_track_by_filepath(track_filepath)
            if track:
                recent_plays.append({
                    'title': track.title,
                    'artist': track.artist,
                    'genre': track.genre
                })
        
        # === HARD FLOOR: separation window (last 25 songs are un-choosable) ===
        # Auto-adjust so small libraries never run dry
        SEP_WINDOW = min(25, max(5, len(self.playlist.library) - 10))
        recent_window = [str(fp) for fp in self.play_history[-SEP_WINDOW:]]
        exclude_filepaths = set(recent_window)
        
        # === ARTIST SEPARATION (soft): artists in the last 5 songs get a hint ===
        ARTIST_SEP = 5
        recent_artists = set()
        for fp in self.play_history[-ARTIST_SEP:]:
            t = self._get_track_by_filepath(fp)
            if t and t.artist and t.artist != 'Unknown Artist':
                recent_artists.add(t.artist.lower())
        
        # Build ID map: simple numeric IDs are robust through JSON (no backslash issues)
        self._song_id_map = {}  # id_str -> Track
        
        # Two groups the LLM sees:
        #   group 1 = NOT played yet this cycle (preferred)
        #   group 2 = already played this cycle (allowed, but needs a strong reason)
        fresh_songs = []   # (track)
        replay_songs = []  # (track)
        
        if force_song:
            forced_track = self._get_track_by_filepath(force_song)
            fresh_songs = [forced_track] if forced_track else []
        else:
            for track in self.playlist.library:
                fp = str(track.filepath)
                if fp in exclude_filepaths:
                    continue  # hard floor: invisible to LLM
                if fp in self.played_this_cycle:
                    replay_songs.append(track)
                else:
                    fresh_songs.append(track)
        
        # If the whole library has been played this cycle → cycle complete, reset
        if not fresh_songs and not replay_songs:
            print("[Cycle] All songs exhausted after window filter — nothing eligible")
        elif not fresh_songs and replay_songs:
            # Every eligible song was already played this cycle → reset the cycle
            print(f"[Cycle] Cycle #{self.cycle_number} complete! All songs played. Resetting cycle.")
            self.cycle_number += 1
            self.played_this_cycle = set()
            fresh_songs = replay_songs
            replay_songs = []
        
        # Build the numbered choice lists for the prompt
        available_songs = []      # group 1 (fresh)
        replay_choices = []       # group 2 (already played)
        idx = 0
        
        for track in fresh_songs:
            sid = str(idx)
            self._song_id_map[sid] = track
            available_songs.append({
                'id': sid,
                'title': track.title,
                'artist': track.artist,
                'genre': track.genre or 'Unknown',
                'language': track.language,
                'year': track.year or 'Unknown'
            })
            idx += 1
        
        for track in replay_songs:
            sid = str(idx)
            self._song_id_map[sid] = track
            replay_choices.append({
                'id': sid,
                'title': track.title,
                'artist': track.artist,
                'genre': track.genre or 'Unknown',
                'language': track.language,
                'year': track.year or 'Unknown'
            })
            idx += 1
        
        # === ROTATING DJ / HANDOFF ===
        # Determine if this break is a shift handoff (goodbye or hello)
        handoff_mode = None       # None | 'goodbye' | 'hello'
        dj_for_break = self._current_dj()
        if self.roster and len(self.roster) > 1:
            if self.handoff_armed:
                handoff_mode = 'hello'
                dj_for_break = self._next_dj()
            elif self._shift_expired():
                handoff_mode = 'goodbye'
                dj_for_break = self._current_dj()

        # === STATION ID (FCC-style) ===
        # Real US radio identifies the station once per hour, on the break nearest the
        # top of the hour - NOT on every break. We track the clock-hour of the last ID
        # and only ask for one when the hour has turned. Everything else is plain DJ talk.
        hour_key = now.strftime("%Y-%m-%d %H")
        station_id_due = (self.last_station_id_hour != hour_key)

        # === FOR YOU ZONE (CODE schedules + owns facts; listener LLM writes; DJ reacts cold) ===
        # A "session" spans several breaks: CODE generates the whole batch of listener messages
        # up front, then the DJ decides per break how many to read (pattern is free), always
        # followed by a song (the min-1-song rule is automatic - every break is voice -> song).
        fyz_messages = None       # messages handed to the DJ this break
        if self.listener_llm.enabled and not force_song and not handoff_mode:
            if self.fyz_queue:
                # mid-session: hand the remaining messages to the DJ
                fyz_messages = list(self.fyz_queue)
            elif self.fyz_songs_since >= self.fyz_min_gap_songs:
                prof = time_profile()
                import random as _rnd
                if _rnd.random() < prof["sessions_chance"]:
                    n = _rnd.randint(prof["msg_min"], prof["msg_max"])
                    msgs = generate_session(
                        self.listener_llm, self._fyz_seeds(),
                        self.fyz_used_names, self.fyz_used_cities, self.fyz_used_occasions,
                        n, tone=prof["tone"])
                    if msgs:
                        self.fyz_queue = msgs
                        self.fyz_session_no += 1
                        fyz_messages = list(self.fyz_queue)
                        _win = "BUSY" if prof["busy"] else "quiet"
                        print(f"[For You Zone] Session #{self.fyz_session_no} ({_win}, {prof['tone']}): "
                              f"{len(msgs)} messages queued")
        
        # Build prompt
        prompt_instruction = "(FORCED SONG - you MUST pick this song)" if force_song else ""
        # Real shift timing for the on-air DJ (so the LLM stops inventing time references)
        _shift_elapsed_h = self._shift_elapsed_hours() if self.roster else 0.0
        _shift_remaining_h = max(0.0, self.shift_hours - _shift_elapsed_h) if self.roster else 0.0
        prompt = self._build_decision_prompt(
            time_str=time_str,
            time_of_day=time_of_day,
            recent_plays=recent_plays,
            available_songs=available_songs,
            replay_choices=replay_choices,
            recent_artists=recent_artists,
            current_song=self.current_song,
            force_instruction=prompt_instruction,
            cycle_number=self.cycle_number,
            last_session_song=self.last_session_song,
            dj_name=(dj_for_break['name'] if dj_for_break else None),
            dj_persona=(dj_for_break.get('persona', '') if dj_for_break else ''),
            handoff_mode=handoff_mode,
            handoff_from=(self._current_dj()['name'] if self.roster and handoff_mode == 'hello' else None),
            shift_elapsed_h=_shift_elapsed_h,
            shift_remaining_h=_shift_remaining_h,
            resumed_gap_h=self.resumed_gap_hours,
            dj_just_started=self.dj_just_started,
            for_you_zone=fyz_messages,
            station_id_due=station_id_due
        )
        
        # Call LLM with retry logic
        print(f"[LLM] Asking AI DJ for next decision...")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.llm_endpoint,
                    headers={"Authorization": f"Bearer {self.llm_api_key}"},
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.9")),
                        "stream": False
                    },
                    timeout=180  # Increased to 3 minutes
                )
                break  # Success, exit retry loop
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"[LLM] Timeout, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                else:
                    raise  # Final attempt failed, raise error
        
        result = response.json()
        
        # Parse response
        if 'choices' in result:
            content = result['choices'][0]['message']['content']
        else:
            raise RuntimeError(f"Invalid LLM response: {result}")
        
        # Extract JSON from response
        decision_json = self._extract_json(content)
        
        # Keep only known fields (LLMs occasionally invent extra keys -> would crash the dataclass)
        _known = {f for f in AgenticDecision.__dataclass_fields__}
        decision_json = {k: v for k, v in decision_json.items() if k in _known}
        decision = AgenticDecision(**decision_json)
        
        # Attach rotating-DJ metadata (computed, not from LLM)
        if dj_for_break:
            decision.dj_name = dj_for_break['name']
            decision.dj_voice = dj_for_break['voice']
        decision.is_handoff = bool(handoff_mode)
        decision.is_for_you_zone = bool(fyz_messages)
        # The DJ reports WHICH messages it read this break as a list of 1-based numbers,
        # e.g. [2, 1] = read #2 first then #1. It may read them in any order.
        _read = getattr(decision, 'messages_read', None)
        n_avail = len(fyz_messages) if fyz_messages else 0
        read_idx = self._resolve_messages_read(_read, fyz_messages, decision.script)
        # Floor: if we're mid-session, read at least 1 so the session always advances.
        if fyz_messages and not read_idx:
            read_idx = [1]
        decision.messages_read = len(read_idx)
        decision.listener = [fyz_messages[i - 1] for i in read_idx] if fyz_messages else None
        # Consume exactly the messages the DJ read (by number), keep the rest in order
        if fyz_messages and read_idx:
            _read_set = set(read_idx)
            self.fyz_queue = [m for i, m in enumerate(fyz_messages, 1) if i not in _read_set]
            if not self.fyz_queue:
                # Session complete: start the min-gap clock from HERE (session end)
                self.fyz_songs_since = 0
                print(f"[For You Zone] Session #{self.fyz_session_no} complete")
        
        # Handoff bookkeeping
        if handoff_mode == 'goodbye':
            # Arm the handoff so the NEXT break becomes the new DJ's hello
            self.handoff_armed = True
            print(f"[DJ] {dj_for_break['name']} signing off — handoff armed for next break")
        elif handoff_mode == 'hello':
            # The new DJ has now spoken: advance rotation + reset shift clock
            self._advance_dj()
        
        # Consume one-shot resume context (so "we're back" is said only once)
        self.resumed_gap_hours = 0.0
        self.dj_just_started = False
        # Mark this clock-hour's station ID as done (FCC-style: one per hour).
        # Handoff breaks skip the ID block, so they don't consume the hour.
        if station_id_due and handoff_mode not in ('hello', 'goodbye'):
            self.last_station_id_hour = hour_key
        
        return decision
    
    def _resolve_messages_read(self, raw, fyz_messages, script=""):
        """Resolve which For You Zone messages the DJ read this break.

        The DJ reports a list of 1-based numbers, e.g. [2, 1]. Accepts several shapes
        (list, int, "2,1", "2, 1") for robustness. Falls back to scanning the script for
        listener NAMES if the reported numbers are missing or all out of range, so a
        listener is never read twice just because the LLM reported the field oddly.
        Returns a de-duplicated, in-range list of ints (may be empty).
        """
        n = len(fyz_messages) if fyz_messages else 0
        if n == 0:
            return []

        idx = []
        # --- normalise the raw field into a list of ints ---
        if raw is None:
            vals = []
        elif isinstance(raw, (list, tuple)):
            vals = list(raw)
        elif isinstance(raw, int):
            vals = [raw]
        elif isinstance(raw, str):
            vals = re.findall(r"\d+", raw)
        else:
            vals = []

        for v in vals:
            try:
                i = int(v)
            except (TypeError, ValueError):
                continue
            if 1 <= i <= n and i not in idx:
                idx.append(i)

        # --- safety net: if nothing valid reported, scan the script for names ---
        if not idx and script:
            low = script.lower()
            for i, m in enumerate(fyz_messages, 1):
                nm = (m.get("name") or "").strip()
                if nm and re.search(r"\b" + re.escape(nm.lower()) + r"\b", low):
                    idx.append(i)

        return idx

    def _build_decision_prompt(self, time_str: str, time_of_day: str, 
                              recent_plays: List[dict], available_songs: List[dict],
                              replay_choices: List[dict] = None,
                              recent_artists: set = None,
                              current_song: Optional[Track] = None, force_instruction: str = "",
                              cycle_number: int = 1, last_session_song: Optional[str] = None,
                              dj_name: str = None, dj_persona: str = "",
                              handoff_mode: str = None, handoff_from: str = None,
                              shift_elapsed_h: float = 0.0, shift_remaining_h: float = 0.0,
                              resumed_gap_h: float = 0.0, dj_just_started: bool = False,
                              for_you_zone: dict = None, station_id_due: bool = True) -> str:
        """Build full autonomy prompt for LLM"""
        replay_choices = replay_choices or []
        recent_artists = recent_artists or set()
        
        recent_str = "\n".join([
            f"  - \"{p['title']}\" by {p['artist']} ({p['genre']})"
            for p in recent_plays
        ]) if recent_plays else "  (Session just started)"
        
        songs_str = json.dumps(available_songs, indent=2)
        
        # Group 2: already played this cycle (optional, needs a reason)
        if replay_choices:
            replay_str = json.dumps(replay_choices, indent=2)
            replay_block = f"""

Songs ALREADY PLAYED this cycle (choose one of these ONLY with a STRONG reason — e.g. "by popular demand", "bringing it back for the late crowd". Otherwise pick from the fresh list above):
{replay_str}
"""
        else:
            replay_block = ""
        
        # Artist separation hint (soft)
        if recent_artists:
            artists_list = ", ".join(sorted(recent_artists))
            artist_hint = f"\nArtist separation hint: these artists played very recently — avoid them for the next few songs if possible: {artists_list}\n"
        else:
            artist_hint = ""
        
        # Previous-session memory line
        if last_session_song:
            session_memory = f"\nPrevious session ended with: \"{last_session_song}\". You may greet returning listeners naturally if it fits.\n"
        else:
            session_memory = ""
        
        # Shift timing (real numbers, so the DJ doesn't invent time references)
        if shift_elapsed_h or shift_remaining_h:
            shift_time = (f"\nYour shift so far: {shift_elapsed_h:.1f} hours on air "
                          f"({shift_remaining_h:.1f}h remaining in your {self.shift_hours}h shift).\n")
        else:
            shift_time = ""
        
        # Returning-after-a-gap (laptop slept / stream was off) — human, light touch
        resume_block = ""
        if resumed_gap_h >= 0.5:
            gap = resumed_gap_h
            if gap >= 2:
                gap_txt = f"{gap:.0f} hours"
            else:
                gap_txt = f"{gap*60:.0f} minutes"
            resume_block = f"""
=== WE ARE BACK ON AIR (gentle) ===
The station was quiet for about {gap_txt} (the stream dropped / went off). You are now back on air.
- Acknowledge it LIGHTLY and warmly, in your own words — like a real DJ coming back from a dead-air gap.
- Do NOT over-explain, do NOT blame anyone, do NOT make it dramatic. One natural line is enough.
- Then carry on as normal, like nothing big happened.
"""
        
        # For You Zone: the DJ receives real listener messages COLD and reacts live.
        # A session can span several breaks; the DJ decides how many to read THIS break
        # (pattern is free) and reports it back via "messages_read".
        fyz_block = ""
        if for_you_zone:
            n_avail = len(for_you_zone)
            listing = []
            for i, m in enumerate(for_you_zone, 1):
                k = m.get("kind", "message")
                ktag = {"question": "QUESTION", "request": "REQUEST"}.get(k, "MESSAGE")
                loc = m['city'] + (', ' + m['region'] if m.get('region') else '')
                listing.append(f"  [{i}] ({ktag}) {m['name']} in {loc}:\n      \"{m['message']}\"")
            listing_str = "\n".join(listing)

            howto = """- These are REAL listeners getting through, live. You are seeing them for the FIRST TIME.
- You do NOT have to read them all in one go. This is a SEGMENT that can span a couple of songs.
  Decide WHICH of the {n} message(s) to read in THIS break, and list their numbers in "messages_read".
  - Example: if you read message [2] first, then message [1], set "messages_read": [2, 1].
  - Read them in whatever order feels right for the moment - you choose which one lands first.
  - If you read only some, the rest stay for your next break - so you can let each one breathe.
  - Reading 1 deep message and sitting with it is often better than rushing through 3.
  - You can also read 2-3 quick ones together if they're light.
- For EACH message you read: acknowledge them BY NAME and their town, and react like a real DJ:
  - QUESTION -> answer it with a real opinion, like taking a caller. Don't be a fortune cookie.
  - REQUEST  -> they asked for a vibe/era, not a specific track. YOU hold the crate. If something
    fits, play it. If nothing fits, be HONEST - never pretend, never invent a song you don't have
    ("that's not in the crate tonight, but here's something with the same spirit").
  - MESSAGE  -> read it, match their emotion. Heavy = gentle and composed, never chipper.
- Match the room. It is late and quiet? Be softer. It is peak evening? You can be warmer and bigger.
- Then land the whole thing into ONE song that fits the moment and introduce it.
- Do not be cheesy. Moved but composed. A real presenter, not a chatbot.""".replace("{n}", str(n_avail))

            fyz_block = f"""
=== IT'S FOR YOU ZONE (listeners reached out) ===
This break you are running your "It's For You Zone" segment - where real listeners get through on air.
You have {n_avail} message(s) waiting. You are seeing them for the FIRST TIME, live, just like your audience.

{listing_str}

How to handle it:
{howto}

IMPORTANT: In your JSON, set "messages_read" to the LIST of message numbers you actually read
this break, in the order you read them, e.g. [2, 1]. The ones you don't read stay for your next break.
"""

        current_str = ""
        if current_song:
            current_str = f"""
Just finished playing:
  - "{current_song.title}" by {current_song.artist}
  - Genre: {current_song.genre}, Language: {current_song.language}
"""
        
        # DJ identity block
        if dj_name:
            persona_line = f" Your vibe: {dj_persona}." if dj_persona else ""
            dj_identity = f'You are the on-air DJ "{dj_name}" for {self.station_name}.{persona_line}\nYou are {dj_name}. Speak naturally in first person — like a real radio host talking to friends, not an announcer.\n'
        else:
            dj_identity = f"You are the AI DJ for {self.station_name} with FULL AUTONOMY.\n"

        # === STATION ID block (FCC-style: once per hour, NOT every break) ===
        if station_id_due:
            station_id_block = f"""
=== STATION ID: DUE THIS BREAK (once-an-hour) ===
This break is the station's identification for this hour, like real US radio does at the top of the hour.
- Say the station name and frequency ONCE, naturally, somewhere in the script: "{self.station_name}".
- Weave it in like a real host would ("you're locked into {self.station_name}", "this is {self.station_name}", etc.) — do NOT make it a stiff legal announcement.
- This is the ONLY break this hour where you mention the station name/frequency.
"""
        else:
            station_id_block = f"""
=== STATION ID: NOT DUE (do NOT identify the station) ===
Real DJs do NOT say the station name or frequency on every break — that sounds like an advert and annoys listeners.
- Do NOT say "{self.station_name}" or the frequency (105.9 / one o five point nine) this break.
- Do NOT introduce yourself by name this break either.
- Just talk like a person: react to the song, tell a story, set up what's next. That's it.
- If you catch yourself starting with "I'm {dj_name}, you're locked into..." — stop. Say something real instead.
"""
        
        # Handoff block (rotating DJ)
        if handoff_mode == 'goodbye':
            handoff_block = f"""
=== SHIFT HANDOFF: GOODBYE BREAK ===
You ({dj_name}) are wrapping up your shift. This break introduces your LAST song.
- You have been on air for {shift_elapsed_h:.1f} hours. Speak from that real experience.
- Thank the listeners warmly for spending this time with you.
- Let them know the music keeps playing and another DJ is taking over next.
- Say goodbye in your own words. This is YOUR send-off.
- The song you pick now will be your final track before the new DJ takes over.
"""
        elif handoff_mode == 'hello':
            handoff_block = f"""
=== SHIFT HANDOFF: HELLO BREAK ===
You ({dj_name}) are just taking over the mic from {handoff_from}.
- Greet the listeners and introduce yourself by name.
- Warmly acknowledge {handoff_from} (thank them / send them off nicely).
- Then roll into your first song. This is your debut on this shift.
"""
        else:
            handoff_block = ""
        
        # A handoff break already has its own instructions (greet / sign off), so we don't
        # nag about station-ID frequency there — let the handoff block own the moment.
        if handoff_mode in ('hello', 'goodbye'):
            station_id_block = ""

        # Pronunciation rule: when phonetic respelling is ON (F5-TTS), the LLM writes
        # names phonetically. When OFF (multilingual engines like Qwen), the LLM writes
        # native names as-is and lets the engine pronounce them.
        if self.phonetic:
            pronunciation_block = """
CRITICAL PRONUNCIATION RULE for Hindi/Bollywood names:
Write Hindi names, movie titles, and song titles PHONETICALLY using English spelling so text-to-speech pronounces them correctly.

Examples:
- "Arijit Singh" → "Ah-ree-jeet Sing"
- "Kabhi Khushi Kabhie Gham" → "Kah-bee Koo-shee Kah-bee Gum"  
- "Rab Ne Bana Di Jodi" → "Rub Nay Bah-nah Dee Joe-dee"
- "Shah Rukh Khan" → "Shah Rook Kahn"
- "Tum Hi Ho" → "Toom Hee Hoh"
"""
        else:
            pronunciation_block = """
PRONUNCIATION RULE for Hindi/Bollywood names:
Write Hindi names, movie titles, and song titles in their NORMAL, CORRECT spelling (NOT phonetically).
The text-to-speech engine is multilingual and pronounces Hindi/Bollywood names correctly on its own.
- Write "Arijit Singh" (not "Ah-ree-jeet Sing")
- Write "Kabhi Khushi Kabhie Gham" (not "Kah-bee Koo-shee Kah-bee Gum")
- Write "Shah Rukh Khan" (not "Shah Rook Kahn")
- Keep Hindi words in natural English spelling as they are normally written.
"""

        prompt = f"""{dj_identity}
{station_id_block}{force_instruction}
{session_memory}{shift_time}{resume_block}{handoff_block}{fyz_block}
Current Context:
- Time: {time_str} ({time_of_day})
- Cycle: #{cycle_number} (a cycle = one pass through the whole library)
{current_str}
Recent play history (last 5 songs):
{recent_str}
{artist_hint}
Songs you have NOT played yet this cycle (PREFER THESE):
{songs_str}{replay_block}

Your task: Decide the next song AND generate the DJ transition script.
{pronunciation_block}
Decision Guidelines:
1. PREFER a song from the "NOT played yet this cycle" list. Pick it by its "id" number.
2. If (and only if) you pick from the "ALREADY PLAYED" list, you MUST give a STRONG reason in "reasoning" AND set "repeat_reason" in the JSON. Repeats without a clear reason are forbidden.
3. Avoid repetitive genres (mix it up!)
4. Respect the artist separation hint when possible.
5. Choose an intent that keeps listeners engaged:
   - "trivia": Share interesting music facts
   - "story": Behind-the-scenes anecdote or artist journey
   - "weather": Atmospheric vibes matching time/mood
   - "wisdom": Motivational quote or thought for the day - inspire your listeners
   - "dedication": Speak to real people out there (late-night studiers, morning commuters, heartbroken souls)
   - "celebration": Mark special moments, anniversaries, cultural events
   - "vibe-check": Connect emotionally with what listeners might be feeling
   - "for-you-zone": Reading a listener's real message on air (use this when the listener block above is present)
   - "energetic": Upbeat, get people moving
   - "chill": Relaxed, smooth transitions
   - "surprise": Unexpected deep cuts or genre shifts

6. Write a DJ script (MINIMUM 20 seconds, but go longer when the moment deserves it):
   - Mention what just played (artist, movie if Bollywood)
   - Tease what's coming next  
   - Add variety: fun facts, trivia, words of wisdom, motivational quotes, life lessons
   - Speak TO your listeners - they're REAL PEOPLE out there tuning in
   - Some moments deserve 20s, others deserve 60s - trust your instinct
   - Make them feel connected, inspired, or entertained
   - Be conversational and GENUINE
   - Use MINIMAL punctuation (commas okay, avoid exclamation marks)
   
Script length guide: 20s = ~50 words minimum, 60s = ~150 words. Let the intent guide the length.

7. OPTIONAL - "HIT THE POST" (the pro move):
   Sometimes a great DJ doesn't stop before the song - they ride the intro. The song
   comes up UNDER your voice, you keep talking over it, and your LAST word lands
   exactly as the song's beat/vocal kicks in. That is called "hitting the post".
   - Set "talk_over_intro": true when you want to hit the post this break - usually a
     confident, energetic, or celebratory break, or a handoff straight into a banger.
   - Set it false for quiet, heavy, or emotional breaks (there you want a clean beat of
     silence first, so the song lands on its own).
   - Do NOT do it every break - that becomes a formula. Mix it up: some breaks clean,
     some hitting the post. The surprise is the point.
   - When true, end your script on a strong, punchy closing line - because that last
     line is what will land ON the post. Do not trail off.
   - You may write a normal-length script when true - the code decides HOW to hit the
     post (ride the intro if it fits, otherwise bring the music up under your last few
     words). You just decide true or false.

Respond ONLY with valid JSON (no markdown):
{{
  "reasoning": "Brief explanation of your choice (2-3 sentences)",
  "intent": "trivia|story|weather|wisdom|dedication|celebration|vibe-check|for-you-zone|energetic|chill|surprise",
  "next_song_id": "0",
  "script": "Your DJ transition script here with phonetic Hindi (minimum 20s, longer if the moment calls for it)",
  "messages_read": [1],
  "talk_over_intro": false,
  "repeat_reason": "ONLY if you picked from the ALREADY PLAYED list — a strong justification. Empty string otherwise.",
  "vibe_notes": "Optional mood note"
}}
"""
        return prompt
    
    def _extract_json(self, content: str) -> dict:
        """Extract JSON from LLM response (handles markdown blocks)"""
        # Remove markdown code blocks if present
        content = content.strip()
        if content.startswith('```'):
            # Extract content between ```json and ```
            lines = content.split('\n')
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith('```'):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            content = '\n'.join(json_lines)
        
        return json.loads(content)
    
    def _get_track_by_filepath(self, filepath: str) -> Optional[Track]:
        """Get track by filepath (robust: handles backslash/forward-slash, duplicates, case)"""
        import os
        
        def robust_norm(p):
            # Convert all separators to forward slash, collapse duplicates, normalize, lowercase
            p = str(p).replace('\\', '/')
            while '//' in p:
                p = p.replace('//', '/')
            return os.path.normpath(p).lower()
        
        normalized_input = robust_norm(filepath)
        
        for track in self.playlist.library:
            if robust_norm(track.filepath) == normalized_input:
                return track
        return None
    
    def get_play_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get play history with track metadata"""
        history = []
        tracks_to_show = self.play_history[-limit:] if limit else self.play_history
        
        for filepath in tracks_to_show:
            track = self._get_track_by_filepath(filepath)
            if track:
                history.append({
                    'title': track.title,
                    'artist': track.artist,
                    'album': track.album,
                    'genre': track.genre,
                    'year': track.year,
                    'filepath': filepath
                })
        
        return history
    
    def save_session_log(self, output_path: str = None):
        """Save current session history to file (per-playlist)"""
        import json
        from datetime import datetime
        
        if output_path is None:
            # Per-playlist session log (same slug as state file)
            slug = self.state_file.replace('radio_state_', '').replace('.json', '')
            output_path = f"session_history_{slug}.json"
        
        # Detect repeats in history
        history = self.get_play_history()
        seen = {}
        repeats = []
        for i, h in enumerate(history, 1):
            key = f"{h['title']} - {h['artist']}"
            if key in seen:
                repeats.append({
                    'song': key,
                    'first_play': seen[key],
                    'repeat_play': i,
                    'gap': i - seen[key]
                })
            else:
                seen[key] = i
        
        log = {
            'session_start': self.session_start.isoformat(),
            'session_end': datetime.now().isoformat(),
            'cycle_number': self.cycle_number,
            'played_this_cycle': len(self.played_this_cycle),
            'library_size': len(self.playlist.library),
            'total_songs_played': len(self.play_history),
            'total_unique_songs': len(seen),
            'total_repeats': len(repeats),
            'repeats': repeats,
            'total_decisions': len(self.decisions_log),
            'play_history': history,
            'ai_decisions': self.decisions_log
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log, f, indent=2, ensure_ascii=False)
        
        repeat_note = f" | ⚠️ {len(repeats)} REPEATS" if repeats else " | no repeats"
        print(f"[Session] Saved: {len(self.play_history)} songs, {len(self.decisions_log)} decisions{repeat_note}")
        return output_path
    
    def _get_time_of_day(self, hour: int) -> str:
        """Get time of day label"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "late night"
