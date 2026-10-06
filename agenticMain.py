"""
Agentic Radio - Entry Point
Select playlist folder and voice, then start autonomous AI DJ

Recording mode (captures the live on-air mix to one MP3):
    python agenticMain.py --record                  # normal roster, record
    python agenticMain.py --record -cara -junior    # only Cara + Junior rotate
    python agenticMain.py --record -cara            # single DJ (no handoff, FYZ still on)

DJ flags: -jerry -cara -junior  (single dash + name, any order)
Equivalent safe form: --djs cara,junior
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()


def parse_args(argv):
    """Parse --record, --hours N, and DJ-filter flags.

    Supports the user's style: -cara -junior  (single dash + DJ name)
    and the explicit:          --djs cara,junior
    """
    record = "--record" in argv
    hours = 0.0
    dj_filter = []

    i = 0
    while i < len(argv):
        a = argv[i]
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
        # single-dash + name  (e.g. -cara, -junior). Skip known single flags.
        if a.startswith("-") and not a.startswith("--") and a not in ("-h",):
            dj_filter.append(a[1:])
            i += 1
            continue
        i += 1

    return record, dj_filter, hours


def _record_path(music_dir: str, dj_filter, hours: float = 0.0) -> str:
    """Build recordings/<date>_<time>_<slug>_<djs>_<hours>h.mp3"""
    import re
    slug = os.path.basename(os.path.normpath(music_dir))
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug).strip('-').lower()
    djs = "-".join(d.lower() for d in dj_filter) if dj_filter else "all"
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    dur = f"_{hours:g}h" if hours > 0 else ""
    return os.path.join("recordings", f"{stamp}_{slug}_{djs}{dur}.mp3")


def select_playlist_folder():
    """Interactive folder selector (Windows compatible)"""
    # Scan for playlist folders
    base_dir = "C:/sourceCode/YT_Downloader/downloads"
    
    if not os.path.exists(base_dir):
        print(f"[Error] Download folder not found: {base_dir}")
        return None, None
    
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    
    if not folders:
        print(f"[Error] No playlist folders found in {base_dir}")
        return None, None
    
    # Folder → Voice mapping
    voice_map = {
        "ats_removed_non_english": "naksh",    # Indian English (Naksh)
        "Punjab Classic In Order": "naksh",    # Indian English
        "Wow, this ist gud": "ara",            # Standard English (CARA)
    }
    
    # Display menu
    print("\n" + "="*60)
    print("🎵 SELECT PLAYLIST FOLDER")
    print("="*60)
    for i, folder in enumerate(folders, 1):
        voice = voice_map.get(folder, "naksh")
        print(f"  [{i}] {folder} [{voice.upper()} voice]")
    print("="*60)
    
    # Get selection
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
    record, dj_filter, hours = parse_args(argv)

    # Interactive folder + voice selection
    music_dir, dj_voice = select_playlist_folder()
    
    if not music_dir or not dj_voice:
        print("[Error] Playlist selection failed. Exiting.")
        return
    
    # Get configuration
    llm_endpoint = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions")
    llm_api_key = os.getenv("LLM_API_KEY", "dummy")
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    
    print("="*60)
    print("🎙️  EXPERIMENT FM 105.9 - AGENTIC AI DJ")
    print("="*60)
    print(f"Playlist:    {music_dir}")
    print(f"DJ Voice:    {dj_voice.upper()}")
    print(f"LLM:         {llm_endpoint}")
    print(f"Mode:        {'RECORDING (fresh from 0)' if record else 'Full Autonomy'}")
    if dj_filter:
        print(f"DJ filter:   {', '.join(dj_filter)}")
    if record:
        print(f"Duration:    {hours:g}h" if hours > 0 else "Duration:    until Ctrl+C")
        print(f"RECORDING:   ON -> {_record_path(music_dir, dj_filter, hours)}")
    print("="*60 + "\n")
    
    recorder = None
    try:
        # Initialize and start
        from agentic_dj_controller import AgenticRadioController
        
        radio = AgenticRadioController(
            music_dir=music_dir,
            station_name="Experiment FM 105.9",
            llm_endpoint=llm_endpoint,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            tts_model="F5-TTS",
            dj_voice=dj_voice,
            dj_filter=dj_filter or None,
            record_mode=record,
            record_hours=hours,
        )

        # Attach recorder BEFORE going live so the first block is captured
        if record:
            from session_recorder import SessionRecorder
            out_path = _record_path(music_dir, dj_filter, hours)
            recorder = SessionRecorder(
                output_path=out_path,
                samplerate=radio.mixer.samplerate,
                channels=radio.mixer.channels,
                bitrate=os.getenv("RECORD_BITRATE", "192k"),
            )
            radio.mixer.attach_recorder(recorder)
            recorder.start()

        radio.start_broadcast()
        print("\n[Radio] Broadcast ended.")

    except KeyboardInterrupt:
        print("\n\n[Radio] Shutting down gracefully...")
    except Exception as e:
        print(f"\n[Radio] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Always finalize the recording (normal end OR Ctrl+C)
        if recorder is not None:
            try:
                recorder.stop()
                print(f"[Record] saved: {recorder.output_path}")
            except Exception as e:
                print(f"[Record] stop failed: {e}")


if __name__ == "__main__":
    main()
