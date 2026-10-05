# 🎵 Experiment FM 105.9

AI-powered radio station with a dynamic DJ that:
- Plays music from your library
- Generates contextual transitions using LLM reasoning
- Speaks naturally with F5-TTS (multilingual support)
- Adapts to time of day, song context, and listener engagement

## Architecture

```
Playlist → DJ Agent (LLM reasoning) → Script Generation → F5-TTS → Real-time Audio Mixer
                ↓
        Intent Decision
    (trivia, weather, vibe-check, etc.)
```

## Features

- **Agentic DJ**: Uses LLM to decide transition types (trivia, weather, vibe checks, surprises)
- **Multilingual**: Handles English, Spanish, Hindi, Indonesian songs with proper pronunciation
- **Real-time mixing**: Professional crossfades using sounddevice + numpy
- **Time-aware**: Adapts DJ personality to time of day
- **Session memory**: Avoids repetitive transitions

## Setup

1. **Install dependencies**:
```bash
cd C:/sourceCode/RadioExperiment
python -m venv .venv
source .venv/Scripts/activate  # Windows Git Bash
pip install sounddevice numpy scipy librosa pydub python-dotenv requests mutagen soundfile
```

2. **Configure**:
```bash
cp .env.example .env
# Edit .env with your settings
```

Required in `.env`:
- `MUSIC_DIR`: Path to your music library
- `LLM_ENDPOINT`: Your LLM API endpoint (e.g., local OpenAI-compatible server)
- `REFERENCE_VOICE`: Path to F5-TTS reference voice (optional but recommended)

3. **Run**:
```bash
python main.py
```

## Configuration

### `.env` settings:

- **STATION_NAME**: Station name (default: "Experiment FM 105.9")
- **MUSIC_DIR**: Music library path (scans MP3, FLAC, M4A, WAV)
- **LLM_ENDPOINT**: LLM API endpoint for DJ script generation
- **LLM_API_KEY**: API key (optional, depending on your endpoint)
- **TTS_MODEL**: TTS engine (default: F5-TTS)
- **REFERENCE_VOICE**: Voice cloning reference audio for F5-TTS
- **STATION_IDENT**: Optional station ident audio file
- **SAMPLERATE**: Audio sample rate (default: 44100)

## How It Works

### Startup Sequence
1. Play station ident (if configured)
2. LLM generates opening monologue
3. TTS converts to speech
4. Music starts

### Song Cycle
```
[Song A playing] (3-5 min)
  ↓
  [5 sec in] Background: prepare next transition
    ├─ LLM decides intent (trivia? weather? vibe-check?)
    ├─ LLM generates script
    └─ F5-TTS renders audio
  ↓
[Last 10 sec] Crossfade begins
  ├─ Lower song volume (ducking)
  ├─ DJ voice plays
  └─ Crossfade to next song
  ↓
[Song B playing]
  (repeat)
```

### DJ Intent Types

- **standard** (40%): Simple song transition
- **trivia** (20%): Fun facts about artist/song
- **weather** (10%): Atmospheric mood setting
- **news** (5%): Quick headline mention
- **vibe-check** (10%): Check in with listeners
- **surprise** (10%): Shoutouts, dedications, quirks
- **silence** (5%): Let music speak

Agent reasoning prevents repetition and matches time of day.

## Components

- **audio_engine.py**: Real-time mixer with crossfading
- **playlist_manager.py**: Music library scanner with metadata extraction
- **dj_agent.py**: Agentic DJ with reasoning and script generation
- **tts_engine.py**: F5-TTS integration
- **radio_controller.py**: Main orchestration loop
- **main.py**: Entry point

## Troubleshooting

**No audio output:**
- Check `python test_audio.py` works
- Verify correct audio device in sounddevice

**TTS fails:**
- Ensure F5-TTS is installed at `C:/sourceCode/TTS`
- Check reference voice file exists
- Test: `cd C:/sourceCode/TTS && source .venv/Scripts/activate && python -m f5_tts.infer_cli --text "test" --output test.wav`

**LLM timeout:**
- Check LLM endpoint is running
- Test: `curl -X POST http://127.0.0.1:20128/v1/chat/completions ...`

**No music found:**
- Verify MUSIC_DIR path in `.env`
- Ensure music files are .mp3, .flac, .m4a, or .wav

## Future Enhancements

- Web UI for live control (volume, skip, manual transitions)
- Weather API integration
- News feed integration
- Beat-matched transitions
- Listener requests via chat
- Multiple DJ personalities
- Scheduled programming

## License

Experimental project - use freely.
