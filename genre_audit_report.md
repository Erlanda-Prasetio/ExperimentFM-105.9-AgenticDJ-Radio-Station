# Genre Audit — ats_removed_non_english (59 lagu)

Sumber kebenaran: `spanish_meta.json` → ditulis ke ID3 tag → dibaca radio.
Restart radio supaya tag baru kepakai (scan_library jalan sekali saat startup).

## FIXED (5)

| Lagu | Artist | Lama | Baru | Sumber |
|---|---|---|---|---|
| El Cucu | La Sonora Dinamita | Merengue | Cumbia | user + 103 BPM + name-collision |
| Si, Es Así | El Alfa & Kim Loaiza | Reggaeton | Dembow | user |
| Tití Me Preguntó | Bad Bunny | Reggaeton | Dembow | Univision/Apple: "entre el dembow y el trap" |
| Tú Con Él | Rauw Alejandro | Reggaeton | Salsa | Wikipedia: cover salsa Frankie Ruiz (2024) |
| (NUEVAYoL diverifikasi Reggaeton — benar, no change) | | | | user |

## LOW CONFIDENCE — keputusan user (mungkin perlu dengar)

| Lagu | Artist | Tag skrg | Kandidat | Catatan |
|---|---|---|---|---|
| In Da Getto | J Balvin & Skrillex | Reggaeton | Reggaeton (OK) | Wikipedia: "reggaeton, house"; Billboard: "reggaeton, dance, dembow" — multi-genre, tag skrg aman |
| Pepas | Farruko | Reggaeton | Reggaeton (OK) | Wikipedia ES: "guaracha electronica / EDM" — secara teknis guaracha, tapi umum disebut reggaeton |
| Una Aventura | Ozuna | Reggaeton | Reggaeton (OK) | LOS40: "reggaeton clasico" |

## VERIFIED CORRECT (no change)

Dembow: El Alfa (semua), Jey One, Don Miguelo, Dixson Waz, Yoan Retro (Bailalo Rocky 124bpm
Dembow per DJpoolRecords), DJ Chulo NYC/PANTI Y COLALE (Diario Libre: dembow), Arlene MC
MamaZota (Dembow), Leo RD/Dilon Baby Yo Soy Dominicano (dembow).
Salsa: Marc Anthony (semua), El Gran Combo, Joe Arroyo, Grupo Niche, Guayacan (Oiga Mire Vea),
**Montuno Encendido - La Sonora Estelar (user: "salsa kok")**.
Bachata: Obsesion (Aventura).
Mandopop: 阳光彩虹小白马.

## TITLE CLEANUP

- **Montuno Encendido**: ID3 title was "Montuno Encendido - La Sonora Estelar" (artist name
  duplicated into title → DJ would say "X by La Sonora Estelar by La Sonora Estelar").
  Fixed: ID3 title -> "Montuno Encendido". Filename + meta key kept as-is (fill_spanish_id3
  matches by filename stem, so the key must equal the file stem).

## AUDIT COMPLETE — 59/59 files have metadata, 59/59 match meta keys.

