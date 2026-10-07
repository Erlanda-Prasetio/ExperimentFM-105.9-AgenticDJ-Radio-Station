# Experiment FM 105.9 — Fully Autonomous AI Radio

Stasiun radio AI yang jalan sendiri 24/7. LLM jadi talent on-air, code jadi engineer/manajer ruangan.
Pilih lagu, nulis script DJ, ngomong pakai suara hasil voice-clone, dan nerima "pesan pendengar"
di segmen **For You Zone** — semuanya otomatis, tanpa disentuh.

```
┌──────────────────────────────────────────────────────────────┐
│                      EXPERIMENT FM 105.9                      │
└──────────────────────────────────────────────────────────────┘
   PLAYLIST         DJ LLM              TTS             MIXER
  ┌────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────────┐
  │ scan   │──▶│ pilih lagu + │──▶│ F5-TTS   │──▶│ real-time    │
  │ library│   │ tulis script │   │ clone    │   │ mix + ducking│
  └────────┘   └──────────────┘   └──────────┘   └──────┬───────┘
                      ▲                                   │
                      │        ┌──────────────────┐       ▼
                      └────────│  FOR YOU ZONE    │   🔊 Speaker
                               │  listener LLM    │
                               │  (otak terpisah) │
                               └──────────────────┘
```

---

## Daftar Isi

1. [Konsep Inti](#konsep-inti)
2. [Arsitektur](#arsitektur)
3. [Fitur](#fitur)
4. [Struktur File](#struktur-file)
5. [Persiapan (Setup)](#persiapan-setup)
6. [Konfigurasi .env](#konfigurasi-env)
7. [Cara Menyalakan](#cara-menyalakan)
8. [Cara Kerja Tiap Bagian](#cara-kerja-tiap-bagian)
9. [For You Zone (detail)](#for-you-zone-detail)
10. [Troubleshooting](#troubleshooting)
11. [Yang Belum Selesai](#yang-belum-selesai)

---

## Konsep Inti

Filosofi desainnya satu kalimat:

> **Code = engineer/manajer ruangan (fisika & aturan). LLM = talent on-air (keputusan & kata-kata).**

- **Code** pegang yang fisik dan nggak bisa dinegosiasi: min-gap anti-ulang, separasi artis,
  jadwal shift, jam tayang, normalisasi LUFS, mixing. Talent **tidak pernah** menimpa board op.
- **LLM** pegang yang kreatif: pilih lagu apa, kenapa, gimana ngomongnya, seberapa panjang.
  Selama aturan fisik dipatuhi, talent bebas.

Pemisahan yang sama dipakai di For You Zone, tapi dengan **dua LLM berbeda** (lihat di bawah).

---

## Arsitektur

### 1. Otak DJ (DJ LLM)

Satu LLM (deepseek-v4.1-flash) yang tiap "break" (jeda antar lagu) menerima konteks lengkap:

- Jam berapa sekarang, sesi hari apa
- 5 lagu terakhir yang diputar
- Daftar lagu yang **belum** diputar di siklus ini (dia pilih lewat **ID numerik**)
- Hint separasi artis
- Siapa DJ-nya sekarang (Cara / Junior) + sisa waktu shift

Lalu dia balikin JSON:

```json
{
  "reasoning": "kenapa pilih lagu ini",
  "intent": "trivia|story|weather|wisdom|dedication|celebration|vibe-check|for-you-zone|energetic|chill|surprise",
  "next_song_id": "42",
  "script": "teks yang akan diucapkan DJ (minimal ~20 detik)",
  "messages_read": 1,
  "repeat_reason": "",
  "vibe_notes": ""
}
```

### 2. Rotating DJ (Cara ↔ Junior)

Dua DJ berbagi playlist, gantian tiap `SHIFT_HOURS` (default 3 jam). Handoff terjadi **dalam 2 break**:

```
[Break 1] Cara pamit  →  intro lagu terakhirnya
   ↓
   lagu terakhir diputar
   ↓
[Break 2] Junior nyapa (nyebut Cara)  →  intro lagu pertamanya
   ↓
   shift Junior mulai (clock reset)
```

- LLM nulis kata-katanya sendiri, bukan template.
- **Shift clock jalan terus** walau laptop mati/sleep. Kalau laptop mati 9 jam, itu dihitung
  sebagai 3 shift penuh, dan rotasi mendarat di DJ yang benar dengan sisa waktu yang benar.
- Daftar DJ per playlist ada di `dj_roster.json`. Playlist tanpa entri = mode single-DJ.

### 3. TTS (F5-TTS, voice cloning)

- Setiap DJ punya **voice reference** (file audio + transkripnya).
- F5-TTS meniru suara itu, lalu audio dilewatkan **rantai radio profesional**.
- Per-voice `cfg_strength` (seberapa setia ke referensi): `naksh=1.6`, `ara/Cara=2.2`, `jr/Junior=1.8`.
- Model di-load **sekali** lalu di-cache (kalau tidak, tiap break buang ~55 detik + leak VRAM).
- Audio di-cache per hash (teks + voice + speed + cfg + seed) → regenerasi instan.

**Rantai radio** (`audio_processing.py`, via pedalboard + pyloudnorm):
```
Highpass 80Hz → +2.5dB@300Hz → +1.5dB@3.5kHz → -2dB@8kHz+
→ Compressor 3:1 (thr -18dB) → Reverb 8% wet → Limiter -1dB → normalize -16 LUFS
```

### 4. For You Zone — dua LLM terpisah

Ini bagian uniknya. Segmen di mana "pesan pendengar" dibacakan on-air, **ditulis oleh LLM
yang berbeda** dari DJ:

```
CODE          → owns FAKTA   (nama/kota/occasion, anti-ulang)
LISTENER LLM  → owns KATA    (pesan manusia sungguhan)   [endpoint & credential SENDIRI]
DJ LLM        → owns REAKSI  (baca dingin, tanggapi live)
```

**Asimetri informasi** itulah yang bikin hidup: listener nulis tanpa tau DJ-nya siapa,
DJ baca untuk pertama kali di udara. Persis kayak radio beneran.

### 5. Mixer real-time (`audio_engine.py`)

- sounddevice OutputStream, callback jalan di thread terpisah → **musik tetap muter** saat
  main loop sibuk generate.
- Ducking: volume musik turun otomatis saat DJ ngomong, balik normal setelahnya.
- Pilih output device by nama substring, **prioritas A2DP** (stereo) di atas HFP (mono) untuk Bluetooth.

### 6. Pre-generation (tanpa dead air)

Saat lagu sedang diputar, setelah 15 detik sistem **generate break berikutnya di belakang layar**:
listener LLM → DJ LLM → TTS, semuanya sebelum lagu habis.

```
lagu mulai → tunggu 15s → [generate break berikutnya ~25s] → audio siap
```

Rata-rata lagu 3.7 menit, generate cuma ~25 detik. Buffer ~2 menit. Nol dead air.

---

## Fitur

- ✅ **DJ agentic** — LLM mutusin lagu + script sendiri, dengan intent & reasoning
- ✅ **Rotating DJ** — Cara ↔ Junior, handoff natural, shift clock tahan sleep/crash
- ✅ **Multi-voice TTS** — F5-TTS voice cloning, per-voice cfg
- ✅ **Anti-ulang** — hard floor (25 lagu terakhir tak bisa dipilih) + artist separation + cycle tracking
- ✅ **Phonetic respell** — nama Hindi/Bollywood di-respell otomatis biar TTS benar
- ✅ **For You Zone** — 2 LLM, pesan pendengar dingin, 3 rasa (pesan / pertanyaan / request musik)
- ✅ **Time-aware** — jadwal For You Zone berubah siang vs malam
- ✅ **Pre-generation** — audio siap sebelum lagu abis
- ✅ **Rantai radio profesional** — EQ, kompresi, reverb, limiter, normalisasi LUFS
- ✅ **Ducking otomatis** — musik turun saat DJ ngomong
- ✅ **"Bruce feature"** — DJ ngomong pas lagu mau masuk, kata terakhirnya mendarat tepat di post (beat/drop lagu). 3 mode: ride intro (script pendek), talk-up (script panjang, musik nyala di 2-3 detik terakhir), normal.
- ✅ **Recording mode** — rekam siaran langsung (lagu + DJ + For You Zone, lengkap) jadi **satu MP3** yang kompatibel ke HP/mobil/SD card.

---

## Recording Mode

Rekam siaran on-air lengkap (lagu + DJ turn + For You Zone + Bruce + ducking + limiter) jadi **satu file MP3** — siap dipindah ke HP, mobil, atau SD card.

```bash
# Rekam dengan roster penuh (semua DJ rotasi), sampai Ctrl+C
python agenticMain.py --record

# Rekam 2 jam, Cara + Junior (shift otomatis = 2h / 2 DJ = 1 jam per DJ)
python agenticMain.py --record --hours 2 -cara -junior

# Rekam 1 jam, Cara + Junior (shift = 30 menit per DJ)
python agenticMain.py --record --hours 1 -cara -junior

# Rekam single DJ: Cara doang (tanpa handoff; For You Zone tetap jalan)
python agenticMain.py --record --hours 2 -cara

# Bentuk aman (kalau single-dash bikin ragu)
python agenticMain.py --record --hours 2 --djs cara,junior
```

- **Recording mode = FRESH RUN.** Tiap `--record` bikin **state file baru** (`radio_state_<slug>_REC_<timestamp>.json`), playlist mulai dari **0**, FYZ queue fresh. **State LIVE lo nggak pernah dibaca/ditulis.**
- **`--hours N`** → auto-stop setelah N jam. **Ctrl+C** juga bisa kapan aja (file tetap difinalisasi).
- **Shift otomatis** = `--hours ÷ jumlah DJ`:
  | Recording | DJ | Shift/DJ |
  |---|---|---|
  | 1 jam | Cara + Junior | **30 menit** |
  | 2 jam | Cara + Junior | **1 jam** |
  | 3 jam | Cara + Junior + Jerry | **1 jam** |
  | 2 jam | Cara (1 DJ) | no handoff (FYZ tetap) |
- **1 DJ** → tanpa handoff, shift nggak berlaku, **FYZ tetap jalan**.
- **2 DJ** → handoff normal (pasangan bebas: cara+jerry, junior+jerry, cara+junior).
- **Tanpa flag DJ** → roster penuh (perilaku biasa, nggak berubah).
- **Output:** `recordings/<tanggal>_<jam>_<playlist>_<djs>_<hours>h.mp3` — MP3 CBR **192k, 44.1kHz stereo, ID3v2.3** (paling kompatibel). Otomatis di-tag pas berhenti.
- **Bitrate:** atur lewat `RECORD_BITRATE` di `.env` (default `192k`).
- **Aman:** encoder jalan di thread terpisah, jadi rekam **nggak** bikin audio patah-patah. Kalau `ffmpeg` nggak ada, rekaman berhenti tapi radio tetap jalan.

> Rekam **real-time**: 7 jam siaran = 7 jam merekam (radio tetap dengerin bareng). File `recordings/` nggak di-commit (gitignored).

---

## Offline Render (Qwen3-TTS) — lebih cepat dari real-time

Render siaran **tanpa speaker, tanpa nunggu real-time**, pakai **Qwen3-TTS 0.6B** (suara lebih halus dari F5). Bisa **pause/resume** dan **tahan crash**.

```bash
# Cara 3 jam + Junior 1 jam (shift normal), total 4 jam:
render.bat

# Atau langsung (venv Qwen):
C:/sourceCode/Qwen3-TTS/.venv/Scripts/python.exe render_offline.py ^
    --hours 4 --djs cara,junior --normal-shift

# Tes cepat (mock TTS, tanpa GPU):
... render_offline.py --mock --minutes 10 --djs cara,junior
```

**Kontrol saat jalan** (edit `render_control.json`):
| Nilai | Aksi |
|---|---|
| `{"action":"run"}` | jalan / lanjut |
| `{"action":"pause"}` | berhenti sebentar (proses idle, lanjut pas `run`) |
| `{"action":"stop"}` | stop + langsung assemble yang udah jadi |

- **Shift normal** (`--normal-shift`): tiap DJ pegang **`SHIFT_HOURS`** penuh (default 3h) → 4 jam = **Cara 3h + Junior 1h**. Tanpa flag ini, shift = `--hours ÷ jumlah DJ`.
- **Crash-safe:** tiap break+lagu jadi satu "part" (`recordings/_parts_*/part_NNNNN.f32` + `.done`). Kalau mati listrik / di-kill, jalanin lagi dengan **`--resume`** → lanjut dari part terakhir, **nggak ngulang dari 0**.
- **Kecepatan:** ~**1,6x real-time** (1 jam show ≈ 1,6 jam render), karena DJ cuma ngomong ~15% waktu × RTF Qwen ~10. Di GPU kecil (RTX 3050 4GB) Qwen **nggak bisa real-time**, tapi buat render offline ini cukup.
- **Output:** sama seperti Recording Mode — MP3 CBR **192k, 44.1kHz stereo, ID3v2.3**.
- **Aman:** nggak butuh audio device (bisa ditinggal, laptop nggak perlu speaker hidup). Radio LIVE (`agenticMain.py`) **nggak disentuh** — patch-nya cuma di proses render.

> Butuh **dua venv**: radio (`RadioExperiment/.venv`) + Qwen (`C:/sourceCode/Qwen3-TTS/.venv`). Script otomatis nge-append site-packages radio ke venv Qwen, jadi satu proses jalan semua. Model Qwen di `C:/sourceCode/Qwen3-TTS/models/` (~3GB).

---

## Struktur File

```
C:/sourceCode/RadioExperiment/
├── agenticMain.py              # ENTRY POINT — pilih playlist, start radio (+ --record)
├── agentic_dj_controller.py    # Jantung: DJ LLM, rotasi, handoff, For You Zone, pre-gen
├── session_recorder.py         # Rekam mix on-air ke satu MP3 (--record)
├── listener_llm.py             # Otak LISTENER terpisah + time profile + session generator
├── listener_seeds.json         # Pool fakta For You Zone (kota/nama/occasion/question/request)
├── tts_engine.py               # F5-TTS + radio processing + cache
├── voice_config.py             # Definisi voice (NAMED_VOICES: naksh/ara/jr)
├── audio_engine.py             # Mixer real-time + pemilihan output device (A2DP) + normalisasi loudness
├── song_intro.py               # Deteksi panjang intro lagu (untuk "Bruce feature")
├── audio_processing.py         # Rantai radio (pedalboard + pyloudnorm)
├── playlist_manager.py         # Scan library + metadata
├── phonetic_respell.py         # Map pengucapan nama Hindi/Bollywood
├── dj_roster.json              # Roster DJ per playlist (Wow = Cara + Junior)
├── .env                        # Konfigurasi (JANGAN di-commit!)
├── .env.example                # Template konfigurasi
├── voice_references/           # File referensi suara + transkrip
│   ├── experiment_fm_intro_naksh.wav   # Naksh (male, Indian English)
│   ├── [DJ CARA (GTA V)] Hey.mp3       # Cara (female)
│   └── voice_ref_jr.wav                # Junior (male)
├── tts_cache/                  # Cache audio hasil generate
├── radio_state_<playlist>.json # State persist (DJ aktif, shift, anti-ulang)
├── session_history_<playlist>.json  # Log sesi (lagu + reasoning)
├── CONTEXT_REFRESHER.md        # Dokumentasi arsitektur lengkap
└── README.md                   # File ini
```

> **Catatan:** `main.py`, `radio_controller.py`, `dj_agent.py`, `tts_xtts.py`, dan file `test_*`
> adalah versi lama / eksperimen. **Yang dipakai sekarang: `agenticMain.py` + `agentic_dj_controller.py`.**

---

## Persiapan (Setup)

### Prasyarat

| Komponen | Versi / Lokasi | Catatan |
|---|---|---|
| **Python** | 3.11 | venv ada di `RadioExperiment/.venv` |
| **FFmpeg** | ada di PATH | buat atempo & probe durasi |
| **NVIDIA GPU** | RTX 3050 4GB (atau lebih) | F5-TTS jalan di CUDA |
| **F5-TTS** | `C:/sourceCode/TTS/.venv` | install terpisah, torch 2.6+cu124 |

### 1. Aktifkan venv RadioExperiment

```bash
cd C:/sourceCode/RadioExperiment
source .venv/Scripts/activate       # Git Bash
# atau: .venv\Scripts\activate      # CMD/PowerShell
```

### 2. Pastikan F5-TTS sudah terinstall

Radio ini **meng-import F5-TTS dari venv terpisah** (`C:/sourceCode/TTS/.venv`).
Cek dulu:

```bash
"C:/sourceCode/TTS/.venv/Scripts/python.exe" -c "import f5_tts, torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
```

Harus keluar: `torch 2.6.0+cu124 cuda True`

Kalau belum ada F5-TTS:

```bash
# install F5-TTS di C:/sourceCode/TTS (repo sendiri)
cd C:/sourceCode/TTS
python -m venv .venv
.venv/Scripts/activate
pip install f5-tts torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

> **Model F5-TTS** (SWivid/F5-TTS) akan **otomatis ter-download** saat pertama kali dipanggil
> (~1.3GB) ke `C:/Users/<user>/.cache/huggingface/hub/models--SWivid--F5-TTS`.
> Koneksi internet dibutuhkan sekali saja.

### 3. Install dependency RadioExperiment

```bash
pip install sounddevice soundfile numpy librosa pedalboard pyloudnorm \
            python-dotenv requests mutagen psutil
```

Versi yang sudah terbukti jalan:

```
sounddevice 0.5.6   soundfile 0.14.0   numpy 2.4.6      librosa 0.11.0
pedalboard 0.9.25   pyloudnorm (ok)   python-dotenv 1.2.4   requests 2.34.2
mutagen 1.48.1      psutil 7.2.2
```

### 4. Siapkan voice references

Taruh file referensi suara di `voice_references/` sesuai yang didefinisikan di `voice_config.py`:

| Voice | File | Gender | cfg |
|---|---|---|---|
| **Naksh** | `experiment_fm_intro_naksh.wav` | male | 1.6 |
| **Cara** | `[DJ CARA (GTA V)] Hey.mp3` | female | 2.2 |
| **Junior** | `voice_ref_jr.wav` | male | 1.8 |

Tiap referensi butuh **transkrip** (ada di `voice_config.py` → `NAMED_VOICES`).
Transkrip harus cocok dengan isi audionya, kalau tidak kualitas clone turun.

### 5. Siapkan library musik

Taruh lagu (`.mp3/.flac/.m4a/.wav`) di subfolder dalam `C:/sourceCode/YT_Downloader/downloads/`.
Contoh: `downloads/Wow, this ist gud/`. Nama folder = playlist.

---

## Konfigurasi .env

Copy `.env.example` → `.env`, lalu isi. **Nilai lengkap yang dipakai sekarang:**

```bash
# --- Stasiun ---
STATION_NAME=Experiment FM 105.9
MUSIC_DIR=C:/sourceCode/YT_Downloader/downloads

# --- DJ LLM (otak utama, nulis script DJ) ---
LLM_ENDPOINT=https://bandelbanget.xyz/v1/chat/completions
LLM_API_KEY=<api-key-kamu>
LLM_MODEL=deepseek-v4.1-flash
LLM_TEMPERATURE=1.2                  # kreativitas script (0.9-1.2 enak)

# --- TTS ---
TTS_MODEL=F5-TTS
DJ_GENDER=male
TTS_SPEED=1.0                        # tempo playback (1.0 = normal, pitch tetap)
# TTS_CFG_STRENGTH=                  # opsional, override per-voice cfg

# --- Rotating DJ ---
SHIFT_HOURS=3                        # panjang shift tiap DJ

# --- Audio output ---
AUDIO_OUTPUT=NeraBox                 # substring nama device (kosong = default Windows)
SAMPLERATE=44100
STATION_IDENT=station_ident.wav

# --- For You Zone: LLM pendengar (otak TERPISAH, credential sendiri) ---
LISTENER_LLM_ENDPOINT=http://127.0.0.1:20128/v1/chat/completions
LISTENER_LLM_API_KEY=<api-key-listener>
LISTENER_LLM_MODEL=cbai/deepseek-v4.1-flash(medium)
LISTENER_LLM_FALLBACK_ENDPOINT=https://bandelbanget.xyz/v1/chat/completions
LISTENER_LLM_FALLBACK_API_KEY=<api-key-fallback>
LISTENER_LLM_FALLBACK_MODEL=deepseek-v4.1-flash
LISTENER_LLM_TEMPERATURE=1.15

# --- For You Zone: jadwal (diatur code, sadar waktu) ---
FYO_MIN_GAP_SONGS=5                  # min lagu antar SESI (dihitung dari akhir sesi)
FYO_BUSY_START=17                    # jam mulai prime time
FYO_BUSY_END=23                      # jam selesai prime time (eksklusif)
FYO_BUSY_CHANCE=0.35                 # ~3-4 sesi/shift saat rame
FYO_OFF_CHANCE=0.10                  # ~1 sesi/shift saat sepi
FYO_BUSY_MSGS_MIN=4                  # pesan/sesi saat rame
FYO_BUSY_MSGS_MAX=5
FYO_OFF_MSGS_MIN=2                   # pesan/sesi saat sepi
FYO_OFF_MSGS_MAX=3
FYO_QUESTION_CHANCE=0.25             # porsi pesan yang berupa PERTANYAAN ke DJ
FYO_REQUEST_CHANCE=0.25              # porsi pesan yang berupa REQUEST musik (soft)
```

### Penjelasan knob penting

| Knob | Fungsi | Kalau diubah |
|---|---|---|
| `SHIFT_HOURS` | Panjang shift DJ | 3 = rotasi tiap 3 jam |
| `TTS_SPEED` | Tempo suara DJ | 1.0 = normal, 1.05 = sedikit cepat |
| `MUSIC_LUFS` | Target loudness lagu | -16.0 = sama dgn suara DJ (seamless) |
| `MUSIC_MAX_GAIN_DB` | Batas boost lagu pelan | 8.0 = jangan terlalu dinaikin |
| `BRUCE_DUCK` | Seberapa pelan intro lagu saat DJ ngomong di atasnya | 0.22 = lagu kedengaran tipis di belakang suara |
| `BRUCE_MAX_VOICE_S` | Maks panjang script untuk mode ride | 18 = script lebih panjang → pindah ke talk-up |
| `BRUCE_MIN_INTRO_S` | Minimal panjang intro lagu untuk ride | 10 = intro pendek → talk-up |
| `BRUCE_MAX_GAP_S` | Maks beda voice vs intro untuk ride | 4 = beda > 4s → talk-up (anti dead air) |
| `TALKUP_LEAD_S` | Musik nyala berapa detik sebelum DJ selesai | 2.5 = musik muncul di 2.5 detik terakhir |
| `TALKUP_DUCK` | Level awal musik saat talk-up | 0.5 = mulai setengah, naik ke full pas DJ kelar |
| `LLM_TEMPERATURE` | Kreativitas script | naik = lebih liar, turun = lebih aman |
| `FYO_BUSY_*` | Jendela prime time | geser jam rame For You Zone |
| `FYO_*_CHANCE` | Frekuensi sesi | naik = For You Zone lebih sering |
| `FYO_*_MSGS_*` | Pesan per sesi | berapa banyak pendengar per sesi |
| `FYO_QUESTION_CHANCE` | Rasa pesan | porsi "tanya DJ" vs dedication |
| `FYO_REQUEST_CHANCE` | Rasa pesan | porsi "request musik" |
| `AUDIO_OUTPUT` | Device output | substring nama, kosong = default |

> **Credential For You Zone sengaja dipisah** dari DJ. Kalau mau, bisa pakai provider/akun
> yang berbeda total — itu inti dari desain dua-otak ini.

---

## Cara Menyalakan

```bash
cd C:/sourceCode/RadioExperiment
source .venv/Scripts/activate
python agenticMain.py
```

Lalu muncul menu pilih playlist:

```
============================================================
🎵 SELECT PLAYLIST FOLDER
============================================================
  [1] ats_removed_non_english [NAKSH voice]
  [2] Punjab Classic In Order [NAKSH voice]
  [3] Wow, this ist gud [ARA voice]
============================================================

Enter number (1-3) or Q to quit:
```

Pilih nomor → radio langsung live. **Ctrl+C** untuk stop.

### Mapping playlist → voice

Ada di `agenticMain.py` (`voice_map`). Playlist di luar mapping default ke `naksh`.
Untuk rotating DJ, atur di `dj_roster.json`:

```json
{
  "wow_this_ist_gud": [
    {"name": "Cara",   "voice": "ara", "persona": ""},
    {"name": "Junior", "voice": "jr",  "persona": ""}
  ]
}
```

`persona` opsional (biarkan `""` kalau tidak mau kepribadian terdefinisi).

### Yang bakal kelihatan di console

```
[Listener] Listener LLM ready: cbai/deepseek-v4.1-flash(medium)
[Agentic Radio] Rotating DJs: Cara, Junior (shift 3.0h)
🔴 GOING LIVE - AI DJ in control

[Playing] 🎵 <judul lagu>
[Waiting 15s before pre-generating next transition...]
[Background] Pre-generating next transition...
[For You Zone] Session #1 (BUSY, heavy): 5 messages queued
[Background] ✓ Next transition ready!

🤖 AI DJ DECISION #12 (pre-generated)
DJ:         Cara [FOR YOU ZONE x1]
Intent:     for-you-zone
...
```

---

## Cara Kerja Tiap Bagian

### Alur satu lagu (loop utama)

```
1. Pakai decision yang sudah di-pre-generate (atau generate sekarang)
2. TTS audio script DJ → play voice
3. Duck musik, play lagu
4. Tunggu 15s → generate break BERIKUTNYA di background:
      code decide For You Zone? → listener LLM nulis → DJ LLM reaksi → TTS
5. Simpan state + session log
6. Ulang
```

### Anti-ulang (code, bukan LLM)

- **Hard floor:** 25 lagu terakhir tak terlihat oleh LLM (tidak bisa dipilih sama sekali).
  Otomatis mengecil untuk library kecil.
- **Artist separation (soft):** artis di 5 lagu terakhir dikasih hint "hindari".
- **Cycle tracking:** LLM lebih suka lagu yang belum diputar di siklus ini.
  Kalau semua sudah diputar, siklus reset.
- **Repeat:** boleh, tapi wajib ada alasan kuat (`repeat_reason`).

### Phonetic respell

Nama Hindi/Bollywood di-respell pakai tabel di `phonetic_respell.py` (bukan LLM), misal:
`Arijit Singh → Ah-ree-jeet Sing`. Ini dipakai **sebelum** TTS biar pengucapannya benar.

### Pemilihan output device

`AUDIO_OUTPUT=NeraBox` → cari device yang namanya mengandung "nerabox".
Kalau Bluetooth, sistem **prioritas A2DP** (stereo) di atas HFP (mono/headset).
Kosongkan = pakai default Windows.

---

## For You Zone (detail)

### Tiga rasa pesan

| Rasa | Porsi | Pendengar bilang | DJ lakuin |
|---|---|---|---|
| **Message** | ~50% | *"papa aku meninggal, putar lagu buat dia"* | Baca, samain emosi, pilih lagu |
| **Question** | ~25% | *"aku pindah luar negeri, gimana bilang ke ortu?"* | Jawab live seperti presenter terima telepon |
| **Request** | ~25% | *"ada 90s EDM? kalau ada"* | Pegang crate: penuhi, atau JUJUR kalau tidak ada |

### Prinsip request

> **Pendengar = keinginan, DJ = keputusan. Request itu doa, bukan perintah.**

DJ **tidak boleh bohong**. Kalau tidak ada yang cocok, dia bilang jujur dan main yang semangatnya sama.
Ini yang bikin dia terasa punya integritas — bukan jukebox, bukan tukang turutin.

### Sesi (bukan satu break)

Satu **sesi** = batch pesan yang membentang beberapa break:

```
[sesi 5 pesan]
  break: DJ baca pesan 1        → lagu
  break: DJ baca pesan 2,3      → lagu
  break: DJ baca pesan 4,5      → lagu
  → balik program normal
```

- Code generate **semua pesan sesi di depan** (murah: ~5 detik/pesan).
- Tiap break, DJ pilih **berapa yang dibaca** dan lapor lewat `messages_read`.
- **Pattern bebas** — boleh 1 pesan dan direnungkan, boleh 3 nyambung.
- Sisa pesan balik break berikutnya sampai habis.
- **Min 1 lagu otomatis** karena tiap break selalu `voice → lagu`.

### Sadar waktu

| | Rame (17:00–23:00) | Sepi (23:00–17:00) |
|---|---|---|
| Sesi/shift | 3–4 | ~1 |
| Pesan/sesi | 4–5 | 2–3 |
| Nada | dalam / curhat | ringan / santai |

**Listener LLM dikasih tau jam + nada**, jadi siang nulis ringan ("selamat ulang tahun buat adikku"),
malam lebih dalam ("mama lagi treatment..."). Bukan cuma frekuensi — isinya juga geser.

### Pool fakta (`listener_seeds.json`)

- **Kota:** US, UK/Eropa, Singapura/Malaysia/Indonesia (49 kota)
- **Nama:** 60 nama (termasuk regional: Wei, Siti, Nurul, Dewi, Reza, dll)
- **Occasion:** 12 (birthday, missing-someone, heartbreak, get-well, dll)
- **Question:** 16 (ask-outfit, ask-moving, ask-ex, dll)
- **Request:** 14 (90s-edm, old-hiphop, slow-sad, dll)

Tambah bebas — makin banyak, makin jarang ulang. Anti-ulang nama/kota/occasion dijaga code.

---

## Troubleshooting

### "No module named f5_tts"
F5-TTS harus ada di `C:/sourceCode/TTS/.venv`. Cek:
```bash
"C:/sourceCode/TTS/.venv/Scripts/python.exe" -c "import f5_tts; print('ok')"
```

### TTS lambat banget pertama kali
Normal — model F5-TTS (~1.3GB) lagi di-load ke VRAM. Setelah itu cached (~16s/break).

### "Output device not found"
Nyalakan Bluetooth speaker dulu, cek nama device:
```bash
python -c "import sounddevice as sd; [print(i, d['name']) for i,d in enumerate(sd.query_devices()) if d['max_output_channels']>0]"
```
Lalu isi `AUDIO_OUTPUT` dengan substring yang cocok. Kosongkan untuk pakai default.

### For You Zone tidak muncul
- Cek `LISTENER_LLM_ENDPOINT` & `LISTENER_LLM_API_KEY` di `.env`
- Console harus cetak `[Listener] Listener LLM ready: ...`
- For You Zone butuh `FYO_MIN_GAP_SONGS` lagu dulu, dan tergantung `FYO_*_CHANCE`
- Set `FYO_OFF_CHANCE=1.0` + `FYO_MIN_GAP_SONGS=1` untuk test cepat

### LLM timeout / script aneh
Cek endpoint LLM hidup:
```bash
curl -X POST $LLM_ENDPOINT -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"'$LLM_MODEL'","messages":[{"role":"user","content":"hi"}],"stream":false}'
```

### Tidak ada suara
```bash
python test_audio.py
```
Cek speaker terhubung + `AUDIO_OUTPUT` benar.

### Bluetooth putus di tengah lagu
Belum ada auto-reconnect. Ctrl+C lalu nyalakan ulang.

---

## Yang Belum Selesai

- [ ] **Ad breaks** — iklan (GTA V / US-UK asli / AI live read). Butuh normalisasi LUFS + min-gap
      (kritis: cegah iklan nge-blast jam 3 pagi).
- [ ] **Voice berbeda untuk pendengar** — sekarang DJ yang bacakan pesan. Nanti bisa voice terpisah
      biar terasa seperti "telepon masuk".
- [ ] **Per-DJ agent** — sekarang Cara & Junior pakai satu otak, cuma beda nama. Idealnya masing-masing
      agent dengan memori sendiri (running joke, callback, history).
- [ ] **Best-of-N TTS** — generate 2-3 take, pilih terbaik (belum ada metrik otomatis yang handal).
- [ ] **Web dashboard** — now playing, reasoning AI, kontrol.
- [ ] **Better Naksh reference** — referensi suara yang lebih bersih & ekspresif.

---

## Lisensi & Catatan

Proyek pribadi/eksperimen. Voice reference dari berbagai sumber (game, iklan) — **jangan
disebarkan ulang untuk komersial** tanpa izin pemilik suara aslinya. LLM endpoint pakai
credential sendiri, jangan commit `.env`.

Selamat ngudara. 📻
