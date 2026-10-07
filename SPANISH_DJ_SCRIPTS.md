# Spanish DJ — Reference Scripts (Experiment FM 105.9)

Untuk **voice cloning** (Qwen3-TTS / F5-TTS). Pilih SATU script, minta calon DJ baca
script itu, rekam bersih (5–10 detik ideal), lalu simpan:
  - `ref_audio` = file audio hasil rekaman
  - `ref_text`  = TEKS SCRIPT ITU, PERSIS kata per kata (harus match audio!)

Script di bawah sudah pakai nama **Ramón**. Kalau DJ-nya bukan Ramón, ganti semua
"Ramón" dengan namanya. Untuk DJ wanita: buang kata yang terlalu maskulin
(mis. "cómodos" -> "cómodas").

CATATAN BAHASA:
  - "buenas noches" (BUKAN "buenos") — noches itu feminin
  - "muchachos" (BUKAN "muchacos")
  - Angka frekuensi ditulis kata: "uno cero cinco punto nueve" (jangan "105.9")

Set env: QWEN_LANGUAGE=Spanish

================================================================================
A. CORTO — ideal buat cloning (5–10 detik), Latin netral
================================================================================
Hola, muy buenas noches. Están escuchando Experiment FM, uno cero cinco punto nueve. Soy Ramón, y esta noche la música es toda suya.

EN: "Hello, very good evening. You're listening to Experiment FM, one oh five
point nine. I'm [NAME], and tonight the music is all yours."

================================================================================
B. SPANGLISH — English + Spanish campur (kaya contoh lo)
================================================================================
Hey, what's up everybody, this is Experiment FM. Buenas noches, mi gente. Uno cero cinco punto nueve. Soy Ramón, y hoy tenemos salsa, dembow, reggaetón... todo lo mejor.

EN: "Hey what's up everybody, this is Experiment FM. Good evening, my people.
One oh five point nine. I'm [NAME], and today we have salsa, dembow, reggaeton...
all the best."

================================================================================
C. DOMINICANO / DEMBOW — energy (cocok buat playlist adik lo)
================================================================================
¡Qué lo qué! Aquí Experiment FM, uno cero cinco punto nueve, la emisora que se respeta. Soy Ramón, y esta noche le metemos dembow hasta que amanezca.

EN: "What's up! Here's Experiment FM, one oh five point nine, the station that
commands respect. I'm [NAME], and tonight we're throwing dembow until sunrise."

================================================================================
D. NOCHE TARDE — hangat, buat dedikasi
================================================================================
Buenas noches, mi gente linda. Es un placer acompañarlos esta noche en Experiment FM, uno cero cinco punto nueve. Soy Ramón. Pónganse cómodos, que la música ya viene.

EN: "Good evening, my beautiful people. It's a pleasure to keep you company
tonight on Experiment FM, one oh five point nine. I'm [NAME]. Get comfortable,
the music is coming."

================================================================================
E. INTRO LARGO — station intro (~15–20 detik, seperti intro Naksh)
================================================================================
¡Hola, hola! Muy buenas noches, y bienvenidos a Experiment FM, uno cero cinco punto nueve. Soy Ramón, y estoy aquí para acompañarlos toda la noche. Tenemos preparado lo mejor de la música latina: salsa, bachata, dembow y reggaetón. Así que suban el volumen, relájense, y dejen que la música se encargue del resto.

EN: "Hello, hello! Very good evening, and welcome to Experiment FM, one oh five
point nine. I'm [NAME], and I'm here to keep you company all night. We've
prepared the best of Latin music: salsa, bachata, dembow and reggaeton. So turn
up the volume, relax, and let the music take care of the rest."

================================================================================
PERSONA (opsional — buat prompt LLM DJ, bukan buat audio)
================================================================================
"Warm Latin American radio host. Speaks natural Spanish (with light Spanglish,
the way real DJs talk). Passionate about salsa, dembow and reggaeton. Treats
listeners like family — 'mi gente'. Energetic but sincere, never cheesy."

================================================================================
CARA PAKAI (ringkas)
================================================================================
1. Pilih script (A/B/C/D/E) -> kasih ke calon DJ.
2. Rekam dia baca script itu (bersih, tanpa musik, 5-10s idealnya).
3. Simpan audio -> mis. voice_references/voice_ref_spanish.wav
4. Tambahkan entry di voice_config.py (NAMED_VOICES):
     "spanish_dj": {
         "name": "<NamaDJ>",
         "file": str(VOICE_DIR / "voice_ref_spanish.wav"),
         "transcript": "<TEKS SCRIPT YANG DIBACA, PERSIS>",
         "gender": "male" | "female",
         "persona": "<persona di atas>",
         "cfg": 1.6
     }
5. Set QWEN_LANGUAGE=Spanish, lalu jalankan qwenMain.py --voice spanish_dj.
