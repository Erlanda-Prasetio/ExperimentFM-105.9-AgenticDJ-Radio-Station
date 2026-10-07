"""
Qwen Live Radio - Entry Point (clone of agenticMain.py)

Differences from agenticMain.py:
  * TTS  : Qwen3-TTS 0.6B Base (voice clone) instead of F5-TTS
  * LLM  : cbai/claude-opus-4.7-1m (override via --llm / QWEN_LLM_MODEL)

Same LIVE radio as the F5 version: songs + DJ turns + For You Zone + Bruce +
ducking + limiter. Runs in the Qwen venv (radio venv site-packages appended).

Usage:
    C:/sourceCode/Qwen3-TTS/.venv/Scripts/python.exe qwenMain.py
    C:/sourceCode/Qwen3-TTS/.venv/Scripts/python.exe qwenMain.py --llm cbai/deepseek-v4.1-flash(medium)

NOTE: Qwen is slow (RTF ~4 on this laptop) so a LIVE run can hit dead air on
short songs. This entry point is for LIVE HEARING / testing; for a clean
recording use render_offline.py instead.
"""
import os
import sys

# --- make the radio venv importable from the Qwen venv --------------------
RADIO_SP = "C:/sourceCode/RadioExperiment/.venv/Lib/site-packages"
if os.path.isdir(RADIO_SP) and RADIO_SP not in sys.path:
    sys.path.append(RADIO_SP)

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LLM = os.getenv("QWEN_LLM_MODEL", "cbai/claude-opus-4.7-1m")

# Isolated state file: the Qwen live run NEVER reads or writes the F5 live state
# (radio_state_<slug>.json). It keeps its own progress instead.
QWEN_STATE_FILE = "qwen_radio_state_wow_this_ist_gud.json"


def parse_args(argv):
    """Parse --llm MODEL, --hours N, and DJ-filter flags (-cara -junior)."""
    hours = 0.0
    dj_filter = []
    llm = DEFAULT_LLM

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--llm" and i + 1 < len(argv):
            llm = argv[i + 1]
            i += 2
            continue
        if a.startswith("--llm="):
            llm = a.split("=", 1)[1]
            i += 1
            continue
        if a == "--hours" and i + 1 < len(argv):
            try:
                hours = float(argv[i + 1])
            except ValueError:
                print(f"[Args] --hours needs a number, got {argv[i+1]!r}")
            i += 2
            continue
        if a.startswith("--hours="):
            try:
                hours = float(a.split("=", 1)[1])
            except ValueError:
                print(f"[Args] --hours needs a number, got {a!r}")
            i += 1
            continue
        if a == "--djs" and i + 1 < len(argv):
            dj_filter += [x.strip() for x in argv[i + 1].split(",") if x.strip()]
            i += 2
            continue
        if a.startswith("--djs="):
            dj_filter += [x.strip() for x in a.split("=", 1)[1].split(",") if x.strip()]
            i += 1
            continue
        if a.startswith("-") and not a.startswith("--") and a not in ("-h",):
            dj_filter.append(a[1:])
            i += 1
            continue
        i += 1

    return llm, dj_filter, hours


def select_playlist_folder():
    """Interactive folder selector (Windows compatible)."""
    base_dir = "C:/sourceCode/YT_Downloader/downloads"

    if not os.path.exists(base_dir):
        print(f"[Error] Download folder not found: {base_dir}")
        return None, None

    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

    if not folders:
        print(f"[Error] No playlist folders found in {base_dir}")
        return None, None

    voice_map = {
        "ats_removed_non_english": "naksh",
        "Punjab Classic In Order": "naksh",
        "Wow, this ist gud": "ara",
    }

    print("\n" + "=" * 60)
    print("🎵 SELECT PLAYLIST FOLDER  (QWEN LIVE)")
    print("=" * 60)
    for i, folder in enumerate(folders, 1):
        voice = voice_map.get(folder, "naksh")
        print(f"  [{i}] {folder} [{voice.upper()} voice]")
    print("=" * 60)

    while True:
        try:
            choice = input(f"\nEnter number (1-{len(folders)}) or Q to quit: ").strip()
            if choice.upper() == 'Q':
                print("\n[Cancelled] No folder selected")
                return None, None
            choice_num = int(choice)
            if 1 <= choice_num <= len(folders):
                selected_folder = folders[choice_num - 1]
                selected_voice = voice_map.get(selected_folder, "naksh")
                folder_path = os.path.join(base_dir, selected_folder)
                print(f"\n✓ Selected: {selected_folder}")
                print(f"✓ Voice: {selected_voice.upper()}")
                print(f"✓ Path: {folder_path}\n")
                return folder_path, selected_voice
            else:
                print(f"[Error] Please enter a number between 1 and {len(folders)}")
        except ValueError:
            print("[Error] Invalid input. Please enter a number or Q")


def main():
    argv = sys.argv[1:]
    llm_model, dj_filter, hours = parse_args(argv)

    music_dir, dj_voice = select_playlist_folder()
    if not music_dir or not dj_voice:
        print("[Error] Playlist selection failed. Exiting.")
        return

    llm_endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions")
    llm_api_key = os.getenv("LLM_API_KEY", "dummy")

    print("=" * 60)
    print("🎙️  EXPERIMENT FM 105.9 - QWEN LIVE (Agentic AI DJ)")
    print("=" * 60)
    print(f"Playlist:    {music_dir}")
    print(f"DJ Voice:    {dj_voice.upper()}")
    print(f"TTS:         Qwen3-TTS 0.6B Base")
    print(f"LLM:         {llm_model}")
    print(f"Endpoint:    {llm_endpoint}")
    if dj_filter:
        print(f"DJ filter:   {', '.join(dj_filter)}")
    print("Mode:        LIVE (Ctrl+C to stop)")
    print("=" * 60 + "\n")

    try:
        # Swap in the Qwen TTS engine and build the SAME controller.
        import agentic_dj_controller as ctl
        from qwen_tts_engine import QwenTTSEngine
        ctl.TTSEngine = QwenTTSEngine

        radio = ctl.AgenticRadioController(
            music_dir=music_dir,
            station_name="Experiment FM 105.9",
            llm_endpoint=llm_endpoint,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            tts_model="Qwen3-TTS",
            dj_voice=dj_voice,
            dj_filter=dj_filter or None,
            record_mode=False,          # LIVE: normal state file
            record_hours=0.0,
            state_file=QWEN_STATE_FILE,  # isolated: never touches the F5 live state
        )

        radio.start_broadcast()
        print("\n[Radio] Broadcast ended.")

    except KeyboardInterrupt:
        print("\n\n[Radio] Shutting down gracefully...")
    except Exception as e:
        print(f"\n[Radio] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
