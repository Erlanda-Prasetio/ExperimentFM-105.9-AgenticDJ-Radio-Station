"""Fill ID3 tags for the Spanish/Dembow folder from spanish_meta.json.

Safe: writes a backup list (spanish_id3_backup.json) so the tags can be stripped
again with --undo (the originals had NO tags). Language is set to 'Spanish'
(except the Chinese track). Nothing is deleted; tags are only added.

Usage:
    python fill_spanish_id3.py            # dry-run (show what would be written)
    python fill_spanish_id3.py --write    # actually write tags
    python fill_spanish_id3.py --undo     # strip tags this script added
"""
import os, sys, json

DIR = r"C:/sourceCode/YT_Downloader/downloads/ats_removed_non_english"
META = "spanish_meta.json"
BACKUP = "spanish_id3_backup.json"

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError


def load_meta():
    with open(META, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def dry_run():
    meta = load_meta()
    files = sorted(f for f in os.listdir(DIR) if f.lower().endswith(".mp3"))
    hit = miss = 0
    for f in files:
        stem = os.path.splitext(f)[0]
        m = meta.get(stem)
        if m:
            hit += 1
            print(f"  {stem[:42]:44s} -> {m['artist'][:38]:40s} | {m['genre']} {m.get('year','')}")
        else:
            miss += 1
            print(f"  {stem[:42]:44s} -> (NO MAPPING)")
    print(f"\nmatched {hit}/{len(files)}  |  missing {miss}")


def write_tags():
    meta = load_meta()
    files = sorted(f for f in os.listdir(DIR) if f.lower().endswith(".mp3"))
    done = []
    for f in files:
        stem = os.path.splitext(f)[0]
        m = meta.get(stem)
        if not m:
            print(f"  skip (no mapping): {f}")
            continue
        p = os.path.join(DIR, f)
        try:
            try:
                audio = EasyID3(p)
            except ID3NoHeaderError:
                audio = EasyID3()
            audio["title"] = stem
            audio["artist"] = m["artist"]
            if m.get("genre"):
                audio["genre"] = m["genre"]
            if m.get("year"):
                audio["date"] = m["year"]
            audio["language"] = "Mandarin" if "小白馬" in stem else "Spanish"
            audio.save(p)
            done.append(f)
            print(f"  tagged: {f}")
        except Exception as e:
            print(f"  ERROR {f}: {e}")
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False, indent=2)
    print(f"\nwrote tags to {len(done)} files; backup list -> {BACKUP}")


def undo():
    from mutagen.id3 import ID3
    files = json.load(open(BACKUP, encoding="utf-8"))
    for f in files:
        p = os.path.join(DIR, f)
        try:
            ID3(p).delete(p)
            print(f"  stripped: {f}")
        except Exception as e:
            print(f"  skip {f}: {e}")
    print("undo done")


if __name__ == "__main__":
    if "--undo" in sys.argv:
        undo()
    elif "--write" in sys.argv:
        write_tags()
    else:
        dry_run()
