# Quick Start Guide - Experiment FM 105.9

## What You Built

AI radio station dengan DJ yang:
- ✅ Reasoning (decide trivia/weather/vibe-check)
- ✅ Multilingual support (pronunciation guide)
- ✅ Real-time audio mixing (crossfade profesional)
- ✅ F5-TTS voice cloning (Carina voice)
- ✅ Station ident jingle

## Start Radio

```bash
cd C:/sourceCode/RadioExperiment
source .venv/Scripts/activate
python main.py
```

Colok headset, music starts automatically!

## What Happens

1. **Startup**: Station ident → DJ opening → Song 1
2. **During Song**: Agent reasoning → LLM script → F5-TTS audio
3. **Transition**: Crossfade musik → DJ voice → Next song
4. **Loop**: Repeat dengan dynamic intent

## Config (.env)

Edit untuk customize:
- `MUSIC_DIR` - your music folder
- `LLM_ENDPOINT` - your LLM API (currently: http://127.0.0.1:20128)
- `REFERENCE_VOICE` - voice cloning reference (currently: carina_7s.wav)

## Test Components

**Audio mixer only:**
```bash
python test_mixer.py
```

**Station ident:**
```bash
python generate_ident.py
```

## Architecture

```
┌─────────────┐
│  Playlist   │ Scans music library
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  DJ Agent   │ LLM reasoning → Script generation
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  F5-TTS     │ Text → Natural speech (multilingual)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ Audio Mixer │ Real-time mixing + crossfade
└──────┬──────┘
       │
       ↓
    🎧 Speakers
```

## DJ Intent Types

Agent decides per transition:
- **standard** (40%) - simple transition
- **trivia** (20%) - fun facts
- **weather** (10%) - mood setting
- **news** (5%) - headlines
- **vibe-check** (10%) - listener check-in
- **surprise** (10%) - shoutouts, quirks
- **silence** (5%) - just music

## Troubleshooting

**No music found:**
- Check MUSIC_DIR path in .env
- Ensure music files exist (.mp3, .flac, .m4a, .wav)

**LLM timeout:**
- Verify endpoint: http://127.0.0.1:20128
- Check if LLM server is running

**TTS fails:**
- F5-TTS installed at C:/sourceCode/TTS
- Reference file exists: carina_7s.wav

**No audio:**
- Test: `python test_audio.py`
- Check headphones plugged in

## Stop Radio

Press `Ctrl+C`

## Next Steps

- Add more music to library
- Test different times of day (DJ adapts)
- Watch session memory (no repetition)
- Try multilingual songs (pronunciation works)

Enjoy your AI radio! 🎵
