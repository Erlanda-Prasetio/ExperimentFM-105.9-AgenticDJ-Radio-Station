"""
Agentic Radio - Entry Point
Select playlist folder and voice, then start autonomous AI DJ
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

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
    print(f"Mode:        Full Autonomy")
    print("="*60 + "\n")
    
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
            dj_voice=dj_voice
        )
        
        radio.start_broadcast()
        
    except KeyboardInterrupt:
        print("\n\n[Radio] Shutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Radio] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
