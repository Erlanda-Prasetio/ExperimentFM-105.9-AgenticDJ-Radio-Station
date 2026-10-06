"""Undo: strip the ID3 tags this run added (originals had none)."""
import os, sys, json
sys.path.insert(0, "C:/sourceCode/TTS/.venv/Lib/site-packages")
from mutagen.id3 import ID3
DIR = r"C:/sourceCode/YT_Downloader/downloads/Wow, this ist gud"
files = json.load(open("id3_backup.json", encoding="utf-8"))
for f in files:
    p = os.path.join(DIR, f)
    try:
        ID3(p).delete(p)
        print("stripped", f)
    except Exception as e:
        print("skip", f, e)
print("undo done")
