# RadioExperiment FM 105.9 - Context Refresher

**Last Updated:** October 4, 2026 (night)
**Project Status:** ✅ PRODUCTION READY - Fully Autonomous AI Radio + Persistent Anti-Repeat + Rotating DJ (Cara ↔ Junior) + For You Zone (two-LLM listener segment)

---

## 🎯 Project Goal

Build a fully autonomous AI radio station with:
- **Agentic AI DJ** - LLM decides songs, scripts, and intents autonomously
- **Multi-voice TTS** - F5-TTS with voice cloning
- **Professional audio processing** - Radio chain (compression, EQ, reverb, limiter)
- **Real-time mixing** - Seamless transitions with music ducking
- **Dynamic content** - Motivational quotes, trivia, listener dedications

---

## 📁 Project Structure

```
C:/sourceCode/RadioExperiment/
├── agenticMain.py                  # Entry point with playlist selector
├── agentic_dj_controller.py        # Autonomous AI DJ controller
├── audio_engine.py                 # Real-time mixer (sounddevice + numpy)
├── audio_processing.py             # Professional radio chain (pedalboard)
├── playlist_manager.py             # Music library & metadata
├── tts_engine.py                   # F5-TTS with radio processing
├── voice_config.py                 # Voice reference mappings + NAMED_VOICES (naksh/ara/jr)
├── dj_roster.json                  # Rotating DJ roster per playlist (Wow = Cara + Junior)
├── phonetic_respell.py             # Bollywood name pronunciation map
├── .env                            # Configuration (incl. SHIFT_HOURS=3)
├── voice_references/
│   ├── experiment_fm_intro_naksh.wav    # Indian English (male) — Naksh
│   ├── [DJ CARA (GTA V)] Hey.mp3        # Standard English (female) — Cara
│   ├── voice_ref_jr.wav                 # Standard English (male) — Junior
│   └── [7 other voice files]
├── tts_cache/                      # Generated audio cache
├── session_history_<playlist>.json # Per-playlist session log
└── radio_state_<playlist>.json     # Per-playlist persistent state (anti-repeat memory)

Music Libraries:
C:/sourceCode/YT_Downloader/downloads/
├── Punjab Classic In Order/        # Bollywood playlist (32 songs, Naksh voice)
├── ats_removed_non_english/        # Latin playlist (59 songs, adik's — metadata empty, not used yet)
└── Wow, this ist gud/              # English playlist (207 songs, CARA voice) ← ACTIVE FOCUS

State Files (per-playlist, auto-generated):
├── radio_state_wow_this_ist_gud.json       # Wow playlist memory
└── session_history_wow_this_ist_gud.json   # Wow playlist log

TTS Environment:
C:/sourceCode/TTS/
├── .venv/                          # Python virtual environment
└── [F5-TTS v1.1.22 installation]
```

---

## 🎛️ Current Configuration

### Environment (.env)
```bash
# LLM Endpoint
LLM_ENDPOINT=https://bandelbanget.xyz/v1/chat/completions
LLM_API_KEY=<user_key>

# Auto-selected based on folder choice:
# - "Punjab Classic In Order" → Naksh (male, Indian English)
# - "Wow, this ist gud" → CARA (female, standard English)
```

### Voice References

**NAKSH (Indian English, Male)**
- **File:** `experiment_fm_intro_naksh.wav`
- **Duration:** 15.9s, 44100Hz
- **Transcript:** "Namaste and welcome to Experiment FM one-oh-five point nine..."
- **Use:** Bollywood/Punjab playlist

**CARA (Standard English, Female)**
- **File:** `[DJ CARA (GTA V)] Hey.mp3`
- **Duration:** ~6s, expressive GTA radio DJ style
- **Transcript:** "Hey, welcome to Experiment FM one-oh-five point nine..."
- **Use:** English playlist
- **Status:** ✅ PERFECT QUALITY

### TTS Settings (F5-TTS)
```python
nfe_step = 64                       # Quality/speed balance
cfg_strength = 2.2 (CARA) / 1.6 (Naksh)  # Female needs higher guidance
sway_sampling_coef = -1.0           # Deterministic
speed = 1.05                        # 5% faster (pitch preserved)
```

### Audio Processing Chain
```python
# Professional broadcast sound (pedalboard + pyloudnorm)
- HighpassFilter(80Hz)              # Remove rumble
- PeakFilter(300Hz, +2.5dB)         # Low-mid warmth
- PeakFilter(3.5kHz, +1.5dB)        # Presence boost
- HighShelfFilter(8kHz, -2dB)       # Smooth highs
- Compressor(3:1, -18dB threshold)  # Smooth dynamics
- Reverb(room 0.15, wet 8%)         # Subtle space
- Limiter(-1dB)                     # Prevent clipping
- Loudness normalization (-16 LUFS) # Broadcast standard
```

### Mixer Settings
```python
samplerate = 44100Hz
channels = 2 (stereo)
blocksize = 4096                    # Larger buffer = stable (was 2048)
latency = 'high'                    # Prioritize stability over low-latency
```

---

## ✅ Completed Features

### 1. **Fully Autonomous AI DJ**
- [x] LLM picks songs from library (207 available in Wow)
- [x] AI decides intent: trivia, story, weather, wisdom, dedication, celebration, vibe-check, energetic, chill, surprise
- [x] Dynamic script length (20s minimum, up to 60s for special moments)
- [x] **Separation window (25 songs)** - last 25 songs invisible to LLM (hard floor, in code)
- [x] **Soft cycle** - prefers unplayed songs; replays allowed only with a strong reason
- [x] **Repeat narrative** - LLM must supply `repeat_reason` to replay
- [x] **Artist separation (5 songs, soft)** - hint to avoid recent artists
- [x] **Cycle auto-reset** - when all songs played, cycle resets naturally
- [x] Time-aware (morning/afternoon/evening/late-night)
- [x] Session memory (play history, decisions log)
- [x] **Persistent memory** - resumes from previous session (last song, cycle state)
- [x] Pre-generation: next transition prepared while song plays (seamless, zero-gap)

### 2. **Interactive Playlist Selection**
- [x] Menu-driven folder picker at startup (Windows-compatible number picker)
- [x] Auto voice mapping:
  - Punjab / ats_removed_non_english → Naksh (Indian English male)
  - Wow this ist gud → CARA (Standard English female)

### 3. **Professional Audio Quality**
- [x] Real-time mixer with music ducking (30% during DJ voice)
- [x] Radio processing chain (compression, EQ, reverb, limiter)
- [x] LUFS normalization (-16 LUFS broadcast standard)
- [x] Buffer optimization (4096 blocksize, no underruns)
- [x] Pitch-preserved speed adjustment (1.05x)

### 4. **Bollywood Pronunciation**
- [x] 150+ hardcoded phonetic respellings
- [x] Artists, movies, songs mapped (Arijit Singh → Ureejit Sing)
- [x] Auto-applied before TTS generation
- [x] Consistent pronunciation across sessions

### 5. **Session Tracking (Per-Playlist)**
- [x] Auto-save session history after EVERY song (real-time)
- [x] JSON export: play_history + ai_decisions + repeat_reason
- [x] Reasoning capture (why AI picked each song)
- [x] **Repeat detection** - auto-flags repeats with gap in log
- [x] Graceful shutdown with final save

### 6. **Anti-Repeat System (Persistent)**
- [x] **Hard floor**: last 25 songs excluded from LLM entirely (in code, not prompt)
- [x] **Soft cycle**: unplayed-first, replays need reason
- [x] **Cycle exhaustion**: all songs played → reset, natural repeat
- [x] **Artist separation**: 5-song soft hint
- [x] **State persists** across sessions, per-playlist, no decay

### 7. **Human Connection**
- [x] AI speaks TO real listeners (not generic broadcast)
- [x] Motivational quotes & words of wisdom
- [x] Listener dedications (late-night studiers, commuters, heartbroken souls)
- [x] Dynamic engagement (some 20s, some 60s based on moment)
- [x] Greets returning listeners using previous-session memory

### 8. **Rotating DJ (Cara ↔ Junior) — Wow playlist**
- [x] Per-playlist roster (`dj_roster.json`): Cara (female, `ara`) + Junior (male, `jr`)
- [x] Shift clock (`SHIFT_HOURS=3` in `.env`), persisted in `radio_state_<slug>.json`
- [x] **2-break handoff**: Break 1 = outgoing DJ's goodbye (intro to their LAST song) → song → Break 2 = incoming DJ's hello (acknowledges predecessor, intro to their FIRST song)
- [x] Each break speaks in the correct voice (`voice_name` passed per call to TTS)
- [x] Persona field OPTIONAL (empty = just the name; no persona needed for handoff)
- [x] Single-DJ playlists (Punjab, ats) unaffected — no roster entry = no handoff

---

## 🏗️ System Architecture

### Autonomous DJ Flow
```
STARTUP:
1. User selects playlist folder (arrow key menu)
2. Auto voice mapping (folder → voice)
3. Scan music library (extract MP3 metadata)
4. Initialize mixer, TTS engine, LLM endpoint
5. Start broadcast loop

AUTONOMOUS CYCLE:
┌─────────────────────────────────────────────────┐
│ 1. SONG SELECTION (in code, before LLM)          │
│    - HARD: exclude last 25 songs (invisible)     │
│    - Split eligible into:                        │
│      * FRESH (not played this cycle) → prefer    │
│      * REPLAY (played this cycle) → needs reason │
│    - Artist-separation hint (last 5 artists)     │
│    - If all played → cycle reset                 │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ 2. LLM DECISION (or use pre-generated)          │
│    - Analyze: time, cycle #, last session song   │
│    - Pick intent (trivia/wisdom/dedication/etc)  │
│    - Choose song (fresh preferred)               │
│    - If replay → supply repeat_reason            │
│    - Generate script (20-60s, dynamic)           │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ 3. TTS GENERATION                                │
│    - Apply phonetic respelling                   │
│    - Clean punctuation (! → .)                   │
│    - F5-TTS: raw audio generation                │
│    - Radio processing chain                      │
│    - Speed up 1.05x (pitch preserved)            │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ 4. PLAY DJ INTRO                                 │
│    - Duck music to 30% volume                    │
│    - Play DJ voice in "voice" slot               │
│    - Wait for completion                         │
│    - Restore music to 100%                       │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ 5. PLAY SONG                                     │
│    - Load selected track to "music" slot         │
│    - Mark played_this_cycle + play_history       │
│    - Save session log + state (EVERY song)       │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ 6. PRE-GENERATE NEXT (while song plays)         │
│    - Wait 15s for song to establish              │
│    - Background: next decision + TTS             │
│    - Ready → seamless transition                 │
└─────────────────────────────────────────────────┘
            ↓
         REPEAT (infinite loop)
```

### Audio Pipeline
```
TEXT → Phonetic Respelling → F5-TTS (raw) →
   → Radio Processing Chain → Speed 1.05x →
      → Cache → Real-time Mixer → Output
```

### Radio Processing Chain
```
RAW TTS WAV (24kHz) → Resample (48kHz) →
   → Highpass → EQ Warmth → EQ Presence →
      → Compress → Reverb → Limit →
         → LUFS Normalize → BROADCAST READY
```

---

## 🎯 AI DJ Intent System

**10 Dynamic Intents:**

1. **trivia** - Music facts, artist info
2. **story** - Behind-the-scenes, artist journeys
3. **weather** - Atmospheric, time/mood matching
4. **wisdom** - Motivational quotes, life lessons
5. **dedication** - Speak to real listeners (studiers, commuters, heartbroken)
6. **celebration** - Anniversaries, cultural moments
7. **vibe-check** - Emotional connection to listener feelings
8. **energetic** - Upbeat, get people moving
9. **chill** - Relaxed, smooth transitions
10. **surprise** - Unexpected deep cuts, genre shifts

**Script Length:** Minimum 20s, up to 60s based on intent. AI decides organically.

---

## 🔧 Bug Fixes Applied

1. ✅ **Audio buffer underflow** - blocksize 2048 → 4096, added latency='high'
2. ✅ **Robotic TTS** - cfg_strength tuning (1.6 male, 2.2 female)
3. ✅ **Flat female voice** - switched to DJ CARA (GTA V) expressive voice
4. ✅ **Speed too fast** - 1.15x → 1.05x (pitch preserved)
5. ✅ **LLM timeout** - added retry logic (3 attempts, 180s timeout)
6. ✅ **Thinking tag removal** - strip `<thinking>` from LLM
7. ✅ **Session history not saving** - now saves after EVERY song
8. ✅ **No gap transitions** - pre-generation while song plays
9. ✅ **Simple-term-menu Windows incompatibility** - replaced with number picker
10. ✅ **Wrong song plays (filepath bug)** - LLM returned `\\` double-backslash paths → switched to numeric IDs + robust_norm fallback
11. ✅ **Repeat loop (No Diggity gap-11)** - exclusion window was only 5 → now 25 + soft cycle
12. ✅ **Double-append history bug** - guard `if fp not in play_history`
13. ✅ **Only 1 decision logged** - pre-generated decisions now logged too
14. ✅ **Hallucinated song fallback** - was `available[0]` (same song) → now `random.choice`

---

## 📊 Quality Status

### ✅ English Playlist (CARA voice)
- **Quality:** PERFECT ⭐⭐⭐⭐⭐
- **Pronunciation:** Native, expressive
- **Engagement:** Dynamic, soulful, human-like
- **Audio:** Broadcast-ready with radio chain

### ⚠️ Bollywood Playlist (Naksh voice)
- **Quality:** GOOD (70-75%)
- **Pronunciation:** Phonetic mapping helps but not perfect
- **Engagement:** Same AI quality, voice less expressive
- **Audio:** Same radio chain quality
- **Future:** Could improve with better Naksh reference or XTTS-Hindi

---

## 🔑 Key Dependencies

### Python Packages
```
# Audio
sounddevice==0.5.3              # Real-time output
numpy==2.4.6                    # Audio processing
librosa==0.11.0                 # Audio loading
pedalboard==0.9.25              # Radio processing chain
pyloudnorm==0.2.0               # LUFS normalization

# TTS
f5-tts==1.1.22                  # Voice cloning

# Utilities
python-dotenv==1.0.1            # Config
requests==2.34.2                # LLM API
mutagen==1.48.0                 # MP3 metadata
```

### Hardware
- **GPU:** NVIDIA GeForce RTX 3050 4GB Laptop GPU
- **CPU:** Intel Core i5-13420H
- **CUDA:** Available, used by F5-TTS
- **PyTorch:** 2.6.0+cu124

---

## 📝 Design Decisions

### Why Agentic Architecture?
- Full LLM autonomy → more natural, varied content
- AI decides based on context (time, mood, recent songs)
- Emergent creativity within grounded constraints

### What Makes It Still "Agentic"? (important)
- **Guardrails ≠ loss of agency.** A real DJ also can't play a song that's not in the library or one just played 3 min ago. Constraints are the *environment*, not a violation of agency.
- **Division of labor:** CODE owns what's *possible & forbidden* (physics). LLM owns what's *better & said* (choice, words, reason).
- **Proof:** the earlier hallucination bug ("I Have Nothing" that didn't exist) was agency WITHOUT grounding → failure. Grounding is what makes an agent useful.
- **Spectrum:** light guardrails (us) = still agentic. Heavy rules that pick the song for the LLM = automation, not agency. If it ever feels like the DJ is "just obeying code," loosen the rules.
- **Rule of thumb:** code guards reality, LLM guards choice.

### Why Separation Window 25 (not 5, not shuffle-bag)?
- 5 → repeats too soon (No Diggity came back after 11)
- Shuffle-bag (no repeat until all 207 played) → too strict; user is OK with repeats after ~20-30 songs + a reason
- 25 → ~1.75 hours of no-repeat, still leaves 180+ candidates
- Auto-adjust `min(25, library-10)` so small libraries (Punjab 32) never run dry

### Why Soft Cycle + Repeat Reason (not hard no-repeat)?
- Radio standard is *controlled repetition* with separation rules — not "never repeat"
- Repeats with a DJ-provided reason feel *intentional* ("by popular demand"), like real radio
- Keeps variety (fresh-first) while allowing meaningful callbacks

### Why Pre-generation?
- Seamless transitions (zero gap between songs)
- LLM + TTS happens while music plays
- Professional radio flow

### Why cfg_strength Gender Split?
- Male voices (Naksh): 1.6 for natural delivery
- Female voices (CARA): 2.2 for expressive guidance
- F5-TTS female voices need stronger constraints

### Why Radio Processing Chain?
- Raw TTS sounds flat/robotic
- Professional broadcast sound: warmth, presence, space
- Removes "synthetic" feel completely

### Why 1.05x Speed?
- F5-TTS default slightly slow
- 5% faster = more engaging, radio-style pacing
- Pitch preserved (no chipmunk effect)

### Why Phonetic Respelling?
- LLM generates phonetics inconsistently
- Hardcoded = reliable, consistent pronunciation
- 150+ entries cover common Bollywood names

### Why DJ CARA (GTA V)?
- Expressive, energetic reference
- Much better than generic "ara" voice
- GTA radio DJs designed for engaging personality

---

## 🎙️ Rotating DJ (Cara ↔ Junior)

### Concept
Two DJs share the Wow playlist. The LLM knows the clock (via persisted shift state); after `SHIFT_HOURS`, the current DJ signs off and the next takes over — like a real radio shift change.

### Handoff = 2 breaks (across one song)
```
[Break 1] Cara says goodbye  →  intro to her LAST song
   ↓
   last song plays
   ↓
[Break 2] Junior says hello (acknowledges Cara)  →  intro to his FIRST song
   ↓
   Junior's shift begins (3h clock resets)
```

### Files & state
- `dj_roster.json` — keyed by playlist slug:
  ```json
  { "wow_this_ist_gud": [
      {"name": "Cara",   "voice": "ara", "persona": ""},
      {"name": "Junior", "voice": "jr",  "persona": ""}
  ] }
  ```
- `radio_state_wow_this_ist_gud.json` — adds `current_dj_idx`, `shift_started_at`, `handoff_armed`
- `voice_config.py` → `NAMED_VOICES` maps `ara`/`jr`/`naksh` → reference file + transcript + gender
- `tts_engine.generate(..., voice_name=...)` selects the voice per break

### Control flow (in code, not LLM)
```
each break:
  if handoff_armed:            mode = 'hello'   (new DJ speaks; then _advance_dj())
  elif shift_expired():        mode = 'goodbye' (arm handoff for next break)
  else:                        mode = None      (normal break)
```
The LLM is TOLD which mode it's in (identity + handoff instructions injected into the prompt); it only writes the words. Code owns *when*; LLM owns *what is said*.

### Why this keeps it agentic
- The DJ **knows it's their shift** and writes a genuine send-off / greeting — not a template.
- User's example (illustration, NOT a script template): *"you are listening to experiment fm … it's been nice to be with you guys … don't worry the music will be playing in the air for you … i'm cara, bye bye now"* → song → *"greeting experiment fm, i'm junior…"*.

### Why 3h shifts?
- Real radio shift norms are 4–5h (morning drive 4h, midday 5h, etc.); user picked 3h for more frequent handoffs.
- Configurable: `SHIFT_HOURS` in `.env` (persisted per playlist, no decay across sessions).

### Indefinite shift clock (survives laptop sleep/crash)
The shift clock counts **real elapsed time forever** — downtime counts as whole shifts.
On startup (`load_state`):
1. If `handoff_armed` (a goodbye aired but its hello never did), advance 1 and consume the flag.
2. Compute `n = floor(elapsed / SHIFT_HOURS)` whole shifts since `shift_started_at`; advance `n` and add `n*SHIFT_HOURS` to `shift_started_at` (keeps the correct **remaining** time, even if only 10 min).
3. Set `dj_just_started` when the rotation advanced → the resumed DJ gets a gentle "we're back" line.

Example: Cara on air, laptop off 9h → 3 shifts pass → rotation lands on **Junior** with a fresh 3h.
The DJ is told real numbers (`shift_elapsed_h`, `shift_remaining_h`) so it stops inventing time references
(earlier bug: it said *"it's been a minute since I've been on air"* with no idea how long it had actually been on).
A downtime gap ≥ 0.5h triggers ONE light, human "we're back on air" nod (option ii: mention it, don't dwell).

---

## 📻 For You Zone (two-LLM listener segment)

### The idea
A segment where **real-feeling listener messages get read on air** — dedications, confessions,
birthdays, "missing you", long-distance, get-well. The unique angle: it is written by a
**SEPARATE LLM** (different credentials, different brain) so the DJ receives it **COLD** and
reacts live. Information asymmetry is what makes it feel alive.

### The split (same philosophy as songs)
```
CODE          -> owns the FACTS   (which name/city, and occasion OR question, with anti-repeat)
LISTENER LLM  -> owns the WORDS   (a real human's message OR a question to the DJ)  [separate endpoint]
DJ LLM        -> owns the REACTION (reads it cold; answers a question, reacts to a message)
```

### Sessions (not single breaks)
A **session** is a batch of listener messages that spans several breaks. CODE generates the whole
batch up front (cheap: ~5s/message), then the DJ decides **per break** how many to read and reports
it via `messages_read`. The pattern is **free** — the DJ may read 1 and sit with it, or 3 in a row.
Every break is still `voice → song`, so the **min-1-song rule is automatic**.
Unread messages carry over to the next break until the session drains.

### Time-of-day behaviour (CODE owns the schedule)
Busy window = **17:00–23:00** (prime time); everything else = quiet (until tuned).

| | Busy (17–23) | Quiet (23–17) |
|---|---|---|
| Sessions per shift | 3–4 | ~1 |
| Messages per session | 4–5 | 2–3 |
| Tone | heavy / personal | light / casual |

The **listener LLM is told the time + tone** (`tone_line` in its prompt), so daytime notes are light
and quick while evening notes are deeper and more personal. Not just frequency — the *content* shifts.

### Time profile + session generation (helpers in `listener_llm.py`)
- `time_profile(now=None)` → `{busy, sessions_chance, msg_min, msg_max, tone}`
- `generate_session(listener_llm, seeds, used_*, n, tone)` → list of messages (anti-repeat carried)

### Three flavors
- **Message / dedication** (default): birthday, missing someone, long-distance, get-well, thank-you, etc.
  The DJ reads it, matches the emotion, plays a fitting song.
- **Question to the DJ** (~25%, `FYO_QUESTION_CHANCE`): the listener asks the DJ something
  ("what should I wear to my sister's wedding?", "how do I tell my parents I'm moving abroad?").
  The DJ **answers it live** like a presenter taking a caller — real opinion, personality, then a song.
- **Soft music request** (~25%, `FYO_REQUEST_CHANCE`): the listener asks for a VIBE, era, or mood
  ("got any 90s EDM?", "something with soul"), NOT a specific title — the listener LLM doesn't know
  the crate. **The DJ holds the crate and decides:** fulfill if something fits, or be HONEST if
  nothing does ("that era's not in the crate tonight, but here's something with the same spirit"),
  and never invent a song it doesn't have. It may also gently decline/redirect — that is personality.
  Key design: **listener = desire, DJ = decision. A request is a wish, not an order.**

### Geography (curated)
**US, UK/Europe, Singapore/Malaysia/Indonesia** — 49 cities, 60 names, 12 occasions, 16 questions, 14 requests.

### Flow
```
CODE gates it (min gap + chance)  ->  LISTENER LLM writes message
   ->  DJ prompt receives listener block COLD (name, city, occasion, exact words)
   ->  DJ reads it on air, reacts, picks a fitting song  ->  TTS
```

### Files
- `listener_llm.py` — `ListenerLLM` class + `pick_seed()` (CODE's fact-picker; picks occasion OR question)
- `listener_seeds.json` — curated pool: cities / names / occasions / questions (US, UK/Europe, SG/MY/ID)
- `.env`:
  ```
  LISTENER_LLM_ENDPOINT=http://127.0.0.1:20128/v1/chat/completions
  LISTENER_LLM_API_KEY=...
  LISTENER_LLM_MODEL=cbai/deepseek-v4.1-flash(medium)
  LISTENER_LLM_FALLBACK_ENDPOINT=https://bandelbanget.xyz/v1/chat/completions
  LISTENER_LLM_FALLBACK_API_KEY=...
  LISTENER_LLM_FALLBACK_MODEL=deepseek-v4.1-flash
  LISTENER_LLM_TEMPERATURE=1.15
  FYO_MIN_GAP_SONGS=5      # min songs between SESSIONS (code-enforced, from session end)
  FYO_BUSY_START=17        # prime-time window start (hour)
  FYO_BUSY_END=23          # prime-time window end (hour, exclusive)
  FYO_BUSY_CHANCE=0.35     # ~3-4 sessions per shift when busy
  FYO_OFF_CHANCE=0.10      # ~1 session per shift when quiet
  FYO_BUSY_MSGS_MIN=4      # messages per session (busy)
  FYO_BUSY_MSGS_MAX=5
  FYO_OFF_MSGS_MIN=2       # messages per session (quiet)
  FYO_OFF_MSGS_MAX=3
  FYO_QUESTION_CHANCE=0.25 # of messages, fraction that are questions TO the DJ
  FYO_REQUEST_CHANCE=0.25  # of messages, fraction that are soft music requests
  ```

### Control flow (in code, not LLM)
```
each break:
  if not force_song AND not handoff:
      if session active (fyz_queue not empty):
          hand remaining messages to the DJ           # DJ reads N, reports messages_read
      elif songs_since >= FYO_MIN_GAP_SONGS:
          prof = time_profile()                        # busy vs quiet
          if random() < prof.sessions_chance:
              n = randint(prof.msg_min, prof.msg_max)
              fyz_queue = generate_session(..., n, tone=prof.tone)
```
The DJ prompt gets an `=== IT'S FOR YOU ZONE ===` block listing all waiting messages and instructions
to read some now (reporting `messages_read`), name each person, match the emotion, then pick a fitting
song. Unread messages return next break until the queue drains. Min-gap restarts from session END.
Anti-repeat: `fyz_used_names / fyz_used_cities / fyz_used_occasions`.

### Voice (current)
The **DJ reads the listener's message aloud** (real-radio standard — like reading a text request).
Multiple distinct voices for "in-call" style listener playback is a **later job**.

### Proven working (real APIs, cold handoff)
**Message flavor** — Listener LLM → *"Farah in Duluth... my girlfriend's in Dublin... I'm proud of her and I miss her."*
DJ LLM (never saw it before) → *"Farah, wherever you are right now, that one went out over the air...
You don't need the same clock, you just need the same person."* → into *See You Again*.

**Question flavor** — Listener LLM → *"Amara from Cork: how do I tell my parents I'm moving abroad
without it turning into a massive row?"* DJ LLM answered live → *"There's no version of this conversation
that isn't a bit heavy... the row you're afraid of is usually not about the moving. It's about them being
scared they're losing you... Don't open with the facts. Open with what it means to you."* → into the song.

**Soft-request flavor (honesty test)** — Listener LLM → *"Reza from George Town, Penang: got any 90s
EDM or dance tonight?"* — but the crate is 2010s-only. DJ LLM did NOT lie → *"Reza, I'm going to be
straight with you, the pure nineties rave crate is not in the studio tonight, but I've got something
with the exact same spirit... It's Daft Punk with Get Lucky."* → honest, no invented song, kept control.

### Per-DJ agents (future, user's idea)
Cara and Junior currently share one brain with the name swapped in. The natural next step is
**each DJ as its own agent** with its own persistent memory (running jokes, callbacks, its own history).
The two-LLM For You Zone is the proof-of-concept for that multi-agent pattern.

---

## 🎯 Future Enhancements

### High Priority
- [x] For You Zone (two-LLM listener segment) — DONE (DJ reads listener messages cold)
- [ ] Distinct voices for listener "in-call" playback (multi-voice TTS)
- [ ] Ad breaks (GTA V / real US-UK ads / AI live reads) — needs LUFS normalization + min-gap
- [ ] Better Naksh reference (cleaner, more expressive)
- [ ] Hybrid XTTS-Hindi for Bollywood names only
- [ ] Web dashboard (now playing, AI reasoning, controls)
- [ ] Latin playlist prep (auto-tag metadata + Spanish voice)

### Medium Priority
- [ ] Auto-tagging (MusicBrainz/AcoustID) for metadata-less folders
- [ ] Multiple DJ personalities (chill vs energetic)
- [ ] Song request queue
- [ ] Time-based playlist switching

### Low Priority
- [ ] Social media auto-posting
- [ ] Listener analytics dashboard
- [ ] Multi-language support expansion
- [ ] Persistent learning system (track listener patterns)

---

## 🐛 Known Issues

1. **Bollywood pronunciation** - 70-75% quality (phonetic helps but not native)
2. **No skip controls** - Must wait for song to finish (can add later)
3. **Latin playlist (ats_removed_non_english)** - 59 songs, all missing metadata (Unknown Artist) + wrong voice (Naksh for Spanish songs). Not in use yet.

---

## 💡 Technical Notes

### Anti-Repeat Architecture (the key design)
- **Two-layer system**: hard floor (code) + soft cycle (LLM)
- **HARD FLOOR (in code)**: last `SEP_WINDOW = min(25, library-10)` songs are removed from the candidate list entirely. LLM never sees them → cannot violate. This is *physics*, not a decision.
- **SOFT CYCLE (in prompt)**: eligible songs split into FRESH (unplayed this cycle, preferred) and REPLAY (played, needs `repeat_reason`).
- **CYCLE EXHAUSTION**: when no FRESH songs remain, `cycle_number += 1` and `played_this_cycle` resets → natural repeat.
- **ARTIST SEPARATION (soft)**: last 5 artists passed as a hint, not enforced.
- **Division of labor**: CODE enforces what's *possible/forbidden*; LLM decides what's *better/said*. Keeps the DJ agentic (grounded, not hallucinating).

### State Persistence
- Per-playlist files: `radio_state_<slug>.json`, `session_history_<slug>.json`
- `radio_state` holds: `last_song`, `cycle_number`, `played_this_cycle`, `play_history` (capped 100)
- Loaded on startup (`load_state`), saved after every song (`save_state`) → **no decay across sessions**
- Switching playlists uses separate state files (no cross-contamination)

### Numeric Song IDs
- LLM selects songs by simple integer `"id"` (0,1,2...), NOT filepath
- Avoids Windows backslash escaping hell through JSON (`C:\\path` → mangled)
- `_song_id_map` resolves id → Track; `_get_track_by_filepath` (robust_norm) is the fallback

### F5-TTS Speed Adjustment
- Uses ffmpeg `atempo` filter (not librosa time_stretch)
- Preserves pitch via phase vocoder
- Applied AFTER radio processing chain

### LLM API Quirks
- Tamandata router needs `"stream": False`
- Sometimes times out → retry logic (3 attempts, 180s)
- Temperature 0.9 for creative DJ scripts

### Audio Mixing
- Real-time streaming (not pre-rendered)
- NumPy buffers with thread-safe locks
- Music ducking: instant volume changes (no fade)

### Caching Strategy
- MD5 hash of cleaned text
- Persistent across sessions
- Saves 15-30s per repeated transition

---

## 📞 User Preferences (From Memory)

- **Casual communication** (Indonesian/English mix, direct)
- **Hands-on samples** over theory
- **Blunt honesty** over politeness
- **Ship working code** then iterate
- **Quality bar:** "Edge TTS naturalness" (met with CARA + radio chain)
- **DJ personality:** Engaging, genuine, speaks TO listeners

---

## 🚀 Quick Start

```bash
# 1. Navigate to project
cd C:/sourceCode/RadioExperiment

# 2. Activate RadioExperiment venv
.venv/Scripts/activate

# 3. Run autonomous radio
python agenticMain.py

# 4. Select playlist:
#    [1] ats_removed_non_english [NAKSH voice]  (Latin, not ready)
#    [2] Punjab Classic In Order [NAKSH voice]  (Bollywood, 32)
#    [3] Wow, this ist gud [ARA voice]          (English, 207) ← use this

# 5. Controls:
#    Ctrl+C = graceful shutdown (auto-saves state + session log)

# 6. On next start: resumes from previous session
#    "[State] Resumed from previous session... Last song: ..."
```

---

## 📚 Reference Commands

```bash
# Check GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Test F5-TTS
cd C:/sourceCode/TTS
.venv/Scripts/activate
python -c "from f5_tts.api import F5TTS; tts = F5TTS(); print('✓')"

# Scan library
cd C:/sourceCode/RadioExperiment
python -c "from playlist_manager import PlaylistManager; pm = PlaylistManager('C:/sourceCode/YT_Downloader/downloads/Punjab Classic In Order/'); pm.scan_library(); print(f'{len(pm.library)} tracks')"

# Test radio processing
cd C:/sourceCode/RadioExperiment
python test_audio_quality.py  # Generates raw vs processed comparison
```

---

## 🎓 Lessons Learned

1. **Buffer size matters** - 2048 too small for i5-13420H under load
2. **Female voices need higher cfg_strength** - 2.2 vs 1.6 for males
3. **Radio chain transforms TTS quality** - compression/EQ/reverb removes robotic feel
4. **Pre-generation is key** - seamless transitions, professional flow
5. **Expressive references matter** - GTA DJ voices >> generic samples
6. **AI needs freedom** - removing 25-30s constraint → more natural scripts
7. **Phonetic mapping >> LLM phonetics** - consistency wins
8. **Hard rules go in code, soft rules go in prompt** - never ask the LLM to count/remember state (it hallucinates); filter it out instead
9. **Windows filepaths through JSON break** - use numeric IDs, not paths, as LLM-facing identifiers
10. **Agency needs grounding** - an unconstrained LLM hallucinates songs that don't exist; constraints make it useful, not less agentic
11. **Controlled repetition beats no-repeat** - real radio repeats hits on purpose; the trick is separation + a reason

---

## 🔗 Useful Links

- **F5-TTS:** https://github.com/SWivid/F5-TTS
- **Pedalboard:** https://github.com/spotify/pedalboard
- **PyLoudnorm:** https://github.com/csteinmetz1/pyloudnorm
- **LLM Endpoint:** https://bandelbanget.xyz/v1 (user's router)

---

**END OF CONTEXT REFRESHER**
