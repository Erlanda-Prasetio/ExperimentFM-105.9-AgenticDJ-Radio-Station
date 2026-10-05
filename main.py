#!/usr/bin/env python3
"""
Experiment FM 105.9
AI Radio Station with Dynamic DJ

Usage:
    python main.py

Controls:
    Ctrl+C - Stop radio
    S - Skip to last 30 seconds of current song (testing)
    
Press Ctrl+C to stop.
"""
import os
import sys
import signal
from pathlib import Path
from dotenv import load_dotenv
import threading

from radio_controller import RadioController


def load_config():
    """Load configuration from .env file"""
    # Load .env
    env_file = Path(__file__).parent / ".env"
    
    if not env_file.exists():
        print("ERROR: .env file not found")
        print("Copy .env.example to .env and configure it")
        sys.exit(1)
    
    load_dotenv(env_file)
    
    # Build config dict
    config = {
        'station_name': os.getenv('STATION_NAME', 'Experiment FM 105.9'),
        'music_dir': os.getenv('MUSIC_DIR'),
        'llm_endpoint': os.getenv('LLM_ENDPOINT'),
        'llm_api_key': os.getenv('LLM_API_KEY', ''),
        'llm_model': os.getenv('LLM_MODEL', 'gpt-4'),
        'tts_model': os.getenv('TTS_MODEL', 'F5-TTS'),
        'dj_gender': os.getenv('DJ_GENDER', 'male'),
        'station_ident': os.getenv('STATION_IDENT'),
        'samplerate': int(os.getenv('SAMPLERATE', '44100'))
    }
    
    # Validate
    if not config['music_dir']:
        print("ERROR: MUSIC_DIR not set in .env")
        sys.exit(1)
    
    if not Path(config['music_dir']).exists():
        print(f"ERROR: Music directory not found: {config['music_dir']}")
        sys.exit(1)
    
    if not config['llm_endpoint']:
        print("ERROR: LLM_ENDPOINT not set in .env")
        sys.exit(1)
    
    return config


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════╗
║                                               ║
║        🎵  EXPERIMENT FM 105.9  🎵           ║
║                                               ║
║     AI Radio with Dynamic DJ Agent            ║
║                                               ║
╚═══════════════════════════════════════════════╝
""")
    
    # Load config
    config = load_config()
    
    # Create radio controller
    radio = RadioController(config)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n[Main] Received interrupt signal")
        radio.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start radio
    radio.start()
    
    # Keep main thread alive
    print("\n[Main] Radio is running...")
    print("[Main] Press Ctrl+C to stop")
    print("[Main] Press 'S' + Enter to skip to last 30 seconds\n")
    
    # Input thread for skip command
    def input_handler():
        while radio.running:
            try:
                cmd = input().strip().lower()
                if cmd == 's':
                    radio.skip_to_end()
            except:
                pass
    
    input_thread = threading.Thread(target=input_handler, daemon=True)
    input_thread.start()
    
    try:
        while radio.running:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        radio.stop()


if __name__ == "__main__":
    main()
