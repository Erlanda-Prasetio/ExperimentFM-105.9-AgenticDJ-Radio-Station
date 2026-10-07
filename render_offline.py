"""Offline renderer for Experiment FM - Qwen3-TTS, faster-than-real-time, pause/resume.

Run with the Qwen venv (radio venv site-packages are appended automatically):

    C:/sourceCode/Qwen3-TTS/.venv/Scripts/python.exe render_offline.py --hours 4 -cara -junior

What it does
------------
* Reuses the REAL controller logic (agentic_dj_controller) - song choice, DJ
  rotation, handoffs, For You Zone, Bruce modes - but swaps in:
    - OfflineMixer   (no sound device; render() drives the same audio callback)
    - VirtualClock   (time.sleep(s) renders s seconds of audio + advances a clock)
    - QwenTTSEngine  (Qwen3-TTS 0.6B Base instead of F5-TTS)
* Renders each break+song as one crash-safe "part" (parts/part_NNNNN.f32 + .done).
* Pause / resume via control.json  {"action": "run"|"pause"|"stop"}  (checked
  between songs). Stop assembles whatever is done into one MP3.
* Final output: MP3 CBR 192k, 44100 Hz, stereo, ID3v2.3 (max compatibility).

The LIVE radio (audio_engine/agenticMain) is never touched.
"""
import os
import sys
import json
import time as _realtime
import glob
import subprocess
import argparse
from datetime import datetime

# --- make the radio venv importable from the Qwen venv --------------------
RADIO_SP = "C:/sourceCode/RadioExperiment/.venv/Lib/site-packages"
if os.path.isdir(RADIO_SP) and RADIO_SP not in sys.path:
    sys.path.append(RADIO_SP)

from dotenv import load_dotenv
load_dotenv()

CONTROL_FILE = "render_control.json"
STATUS_FILE = "render_status.json"


# --------------------------------------------------------------------------
def read_control():
    try:
        with open(CONTROL_FILE, "r", encoding="utf-8") as f:
            return (json.load(f).get("action") or "run").lower()
    except Exception:
        return "run"


def write_status(d):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


class MockTTS:
    """Fast fake TTS for plumbing tests (2s tone) - no GPU, no model."""

    def __init__(self, *a, **kw):
        self.cache_dir = "tts_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def generate(self, text, output_path=None, **kw):
        import numpy as np
        import soundfile as sf
        dur = 2.0
        sr = 24000
        t = np.arange(int(dur * sr)) / sr
        wav = 0.05 * np.sin(2 * np.pi * 440 * t).astype("float32")
        if not output_path:
            output_path = os.path.join(self.cache_dir, f"mock_{abs(hash(text)) % 10**8}.wav")
        sf.write(output_path, wav, sr)
        return output_path

    def preload(self):
        pass


# --------------------------------------------------------------------------
def assemble(parts_dir, out_path, samplerate, channels, bitrate="192k", title=None):
    # The .done marker signals completeness; the PCM lives in the .f32 beside it.
    markers = sorted(glob.glob(os.path.join(parts_dir, "part_*.f32.done")))
    parts = [m[:-len(".done")] for m in markers if os.path.exists(m[:-len(".done")])]
    if not parts:
        print("[Assemble] no complete parts - nothing to assemble")
        return None
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-f", "s16le", "-ar", str(samplerate), "-ac", str(channels), "-i", "pipe:0",
           "-c:a", "libmp3lame", "-b:a", bitrate,
           "-ar", str(samplerate), "-ac", str(channels),
           "-id3v2_version", "3", "-y", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    total = 0
    for p in parts:
        with open(p, "rb") as f:
            data = f.read()
        proc.stdin.write(data)
        total += len(data) // (2 * channels)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        err = proc.stderr.read().decode(errors="ignore")[:300]
        print(f"[Assemble] ffmpeg failed: {err}")
        return None
    dur = total / samplerate
    # ID3
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, TALB
        try:
            tags = ID3(out_path)
        except Exception:
            tags = ID3()
        tags.add(TIT2(encoding=3, text=title or f"Experiment FM 105.9 - {datetime.now():%Y-%m-%d %H:%M}"))
        tags.add(TPE1(encoding=3, text="Experiment FM 105.9"))
        tags.add(TALB(encoding=3, text="Experiment FM 105.9"))
        tags.save(out_path, v2_version=3)
    except Exception as e:
        print(f"[Assemble] tag skip: {e}")
    print(f"[Assemble] {len(parts)} parts -> {out_path}  ({dur/3600:.2f}h / {dur:.0f}s)")
    return out_path


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="C:/sourceCode/YT_Downloader/downloads/Wow, this ist gud")
    ap.add_argument("--hours", type=float, default=0.0)
    ap.add_argument("--minutes", type=float, default=0.0)
    ap.add_argument("--djs", default="")
    ap.add_argument("--parts-dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--mock", action="store_true", help="use fake fast TTS (plumbing test)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--normal-shift", action="store_true",
                    help="use SHIFT_HOURS per DJ (normal rotation) instead of hours/#DJs")
    args = ap.parse_args()

    target_hours = args.hours + (args.minutes / 60.0)
    djs = [x.strip() for x in args.djs.split(",") if x.strip()]

    import re
    slug = os.path.basename(os.path.normpath(args.playlist))
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    djtag = "-".join(d.lower() for d in djs) if djs else "all"
    parts_dir = args.parts_dir or os.path.join("recordings", f"_parts_{stamp}_{slug}_{djtag}")
    out_path = args.out or os.path.join(
        "recordings",
        f"{stamp}_{slug}_{djtag}_qwen{f'_{target_hours:g}h' if target_hours else ''}.mp3")

    print("=" * 64)
    print("EXPERIMENT FM 105.9 - OFFLINE QWEN RENDER")
    print("=" * 64)
    print(f"  playlist : {args.playlist}")
    print(f"  target   : {target_hours:.2f}h virtual" if target_hours else "  target   : (unlimited)")
    print(f"  djs      : {djs or 'full roster'}")
    print(f"  tts      : {'MOCK (fast)' if args.mock else 'Qwen3-TTS 0.6B'}")
    print(f"  parts    : {parts_dir}")
    print(f"  output   : {out_path}")
    print(f"  control  : {CONTROL_FILE}  (action=run|pause|stop)")
    print("=" * 64, flush=True)

    # --- patches ----------------------------------------------------------
    from offline_mixer import VirtualClock, install_patches
    clock = VirtualClock(datetime.now())
    holder = {}
    install_patches(clock, holder)

    import agentic_dj_controller as ctl
    if args.mock:
        ctl.TTSEngine = MockTTS

    # --- build controller (record mode = isolated state) ------------------
    radio = ctl.AgenticRadioController(
        music_dir=args.playlist,
        station_name="Experiment FM 105.9",
        llm_endpoint=os.getenv("LLM_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions"),
        llm_api_key=os.getenv("LLM_API_KEY", "dummy"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4"),
        tts_model="Qwen3-TTS",
        dj_voice="jerry",
        dj_filter=djs or None,
        record_mode=True,
        record_hours=target_hours,
    )
    mixer = radio.mixer
    clock.mixer = mixer

    # Normal rotation: each DJ keeps their full SHIFT_HOURS (e.g. 3h), so a 4h
    # render = Cara 3h then Junior 1h. Without this, record-mode divides the
    # total by the number of DJs (4/2 = 2h each).
    if args.normal_shift:
        radio.shift_hours = float(os.getenv("SHIFT_HOURS", "3"))
        print(f"[Render] normal shift: {radio.shift_hours:g}h per DJ "
              f"(roster: {' -> '.join(d['name'] for d in radio.roster)})")

    # stable state/decision files so --resume can find them
    radio.state_file = f"radio_state_{slug}_OFFLINE.json"
    radio.decisions_log_file = f"decisions_log_{slug}_OFFLINE.jsonl"

    if args.resume and os.path.exists(radio.state_file):
        try:
            with open(radio.state_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            radio.play_history = st.get("play_history", [])
            radio.played_this_cycle = set(st.get("played_this_cycle", []))
            radio.cycle_number = st.get("cycle_number", 1)
            radio.current_dj_idx = st.get("current_dj_idx", 0)
            radio.shift_started_at = clock.now()   # reset shift clock (aired-time from here)
            radio.last_station_id_hour = None
            print(f"[Resume] loaded {len(radio.play_history)} played, cycle #{radio.cycle_number}")
        except Exception as e:
            print(f"[Resume] failed ({e}) - starting fresh")

    mixer.set_parts_dir(parts_dir)

    # reset control to 'run'
    write_status({"state": "starting", "parts": 0, "virtual_h": 0.0})

    # --- render loop ------------------------------------------------------
    radio.record_started_at = clock.now()
    real_t0 = _realtime.time()
    parts_done = mixer._part_index
    stop_reason = "done"
    try:
        while True:
            act = read_control()
            while act == "pause":
                write_status({"state": "paused", "parts": parts_done,
                              "virtual_h": round((clock.now() - radio.record_started_at).total_seconds() / 3600, 3)})
                print("[Render] ⏸ paused (set control.json action=run to resume)", flush=True)
                _realtime.sleep(2)
                act = read_control()
            if act == "stop":
                stop_reason = "user stop"
                break

            if target_hours > 0:
                el_h = (clock.now() - radio.record_started_at).total_seconds() / 3600
                if el_h >= target_hours:
                    stop_reason = f"reached {target_hours:g}h"
                    break

            mixer.begin_part()
            radio._autonomous_cycle()
            mixer.end_part()
            parts_done = mixer._part_index
            el_h = (clock.now() - radio.record_started_at).total_seconds() / 3600
            real_m = (_realtime.time() - real_t0) / 60.0
            write_status({"state": "rendering", "parts": parts_done,
                          "virtual_h": round(el_h, 3), "real_min": round(real_m, 1),
                          "target_h": target_hours})
            speed = (el_h / (real_m / 60.0)) if real_m > 0 else 0
            print(f"[Render] part {parts_done} | virtual {el_h:.2f}h | real {real_m:.1f}min | "
                  f"x{speed:.2f} vs realtime", flush=True)
    except KeyboardInterrupt:
        stop_reason = "Ctrl+C"
        print("\n[Render] interrupted")
    finally:
        try:
            radio.save_session_log()
            radio.save_state()
        except Exception:
            pass

    print(f"\n[Render] stopped ({stop_reason}) - assembling {parts_done} part(s)...")
    write_status({"state": "assembling", "parts": parts_done})
    out = assemble(parts_dir, out_path, mixer.samplerate, mixer.channels,
                   bitrate=os.getenv("RECORD_BITRATE", "192k"))
    if out:
        print(f"[Render] ✅ DONE -> {out}")
        write_status({"state": "done", "parts": parts_done, "out": out})
    else:
        write_status({"state": "failed", "parts": parts_done})


if __name__ == "__main__":
    main()
