"""
Voice reference configuration for multi-language DJ
Maps languages to voice references with transcripts
"""
from pathlib import Path
import random

# Base path
VOICE_DIR = Path("voice_references")

# Voice references with transcripts
VOICES = {
    "english": {
        "male": {
            "file": str(VOICE_DIR / "experiment_fm_intro_naksh.wav"),
            "transcript": "Namaste and welcome to Experiment FM one-oh-five point nine. I'm your host for the evening. We've got an amazing collection of Bollywood hits lined up for you tonight, from the classics to the latest chartbusters. So sit back, relax, and let the music take over."
        },
        "female": {
            "file": str(VOICE_DIR / "[DJ CARA (GTA V)] Hey.mp3"),
            "transcript": "Hey, welcome to Experiment FM one-oh-five point nine. I'm your AI host for tonight. We've got an incredible mix of music from around the world, so sit back, relax, and let's get into it."
        }
    },
    "indonesian": {
        "male": {
            "file": str(VOICE_DIR / "indo_radio_naksh.mp3.wav"),
            "transcript": "Selamat malam, kalian sedang mendengarkan Experiment FM. Malam ini kita punya koleksi lagu Indonesia yang luar biasa. Dari Jakarta sampai Bali, musik terbaik untuk menemani malam kalian."
        },
        "female": {
            "file": str(VOICE_DIR / "indo_radio_liora.mp3.wav"),
            "transcript": "Selamat malam, kalian sedang mendengarkan Experiment FM. Malam ini kita punya koleksi lagu Indonesia yang luar biasa. Dari Jakarta sampai Bali, musik terbaik untuk menemani malam kalian."
        }
    },
    "spanish": {
        "male": {
            "file": str(VOICE_DIR / "spanish_radio_sirius.mp3.wav"),
            "transcript": "Hola amigos, bienvenidos a Experiment FM, uno cero cinco punto nueve. Esta noche tenemos música increíble de toda América Latina. Desde reggaeton hasta baladas, todo lo mejor para ustedes."
        },
        "female": {
            "file": str(VOICE_DIR / "spanish_radio_ara.mp3.wav"),
            "transcript": "Hola amigos, bienvenidos a Experiment FM, uno cero cinco punto nueve. Esta noche tenemos música increíble de toda América Latina. Desde reggaeton hasta baladas, todo lo mejor para ustedes."
        }
    },
    "hindi": {
        "male": {
            "file": str(VOICE_DIR / "hindi_radio_naksh.mp3.wav"),
            "transcript": "Namaste doston, aap sun rahe hain Experiment FM. Aaj raat humne aapke liye Bollywood se lekar indie music tak, sabhi kuch taiyar kiya hai. Toh chaliye, music ke saath enjoy karte hain."
        },
        "female": {
            "file": str(VOICE_DIR / "hindi_radio_ara.mp3.wav"),
            "transcript": "Namaste doston, aap sun rahe hain Experiment FM. Aaj raat humne aapke liye Bollywood se lekar indie music tak, sabhi kuch taiyar kiya hai. Toh chaliye, music ke saath enjoy karte hain."
        }
    }
}

# Named DJ voices (for rotating DJ / handoff)
# persona is OPTIONAL - leave empty string if you don't want a defined personality
NAMED_VOICES = {
    "naksh": {
        "name": "Naksh",
        "file": str(VOICE_DIR / "experiment_fm_intro_naksh.wav"),
        "transcript": "Namaste and welcome to Experiment FM one-oh-five point nine. I'm your host for the evening. We've got an amazing collection of Bollywood hits lined up for you tonight, from the classics to the latest chartbusters. So sit back, relax, and let the music take over.",
        "gender": "male",
        "persona": "",
        "cfg": 1.6
    },
    "ara": {
        "name": "Cara",
        "file": str(VOICE_DIR / "[DJ CARA (GTA V)] Hey.mp3"),
        "transcript": "Hey, welcome to Experiment FM one-oh-five point nine. I'm your AI host for tonight. We've got an incredible mix of music from around the world, so sit back, relax, and let's get into it.",
        "gender": "female",
        "persona": "",
        "cfg": 2.2
    },
    "jr": {
        "name": "Junior",
        "file": str(VOICE_DIR / "voice_ref_jr.wav"),
        "transcript": "Hey, it's JR. Now if you're looking to buy a new car, truck, or SUV, there is no better place to do it than at Castle Rock Chevrolet Buick GMC. My girl Natalie over there is an absolute gem.",
        "gender": "male",
        "persona": "",
        "cfg": 1.8
    },
    "uk": {
        "name": "Rebecca",
        "file": str(VOICE_DIR / "voice_ref_uk.wav"),
        "transcript": "Thanks a lot, Jamie. The time now is 7.01pm and you are locked in to Freeze FM with me, Kali Trainor, where I will be bringing you the biggest and baddest tunes of the last seven days.",
        "gender": "female",
        "persona": "",
        "cfg": 2.2
    },
    "meg": {
        "name": "Megan",
        "file": str(VOICE_DIR / "voice_ref_megan.wav"),
        "transcript": "Honestly, being on stage as Mayo is like a whole different vibe, you know? Like, Megan is just me, chilling, but when I get up there, it's like this total energy shift. I've always loved that contrast. It's actually so funny how a name can change how you feel.",
        "gender": "female",
        "persona": "",
        "cfg": 2.0
    },
    "ethan": {
        "name": "Ethan",
        "file": str(VOICE_DIR / "voice_ref_ethan.wav"),
        "transcript": "It's like if Radiohead had a baby with a synthesizer then that baby was raised by wolves who only listened to 80s New Wave. Just, just listen.",
        "gender": "male",
        "persona": "",
        "cfg": 2.4,
        "speed": 0.9,
        "eq": {
            "peaks": [[3500, -5.0, 1.0], [6500, -4.0, 1.2]],
            "shelves": [[9000, -4.5]]
        }
    },
    "jerry": {
        "name": "Jerry",
        "file": str(VOICE_DIR / "voice_ref_jerry.wav"),
        "transcript": "Hey, welcome to Experiment FM 105.9. I'm your AI host for tonight, and we've got an incredible mix of music from around the world.",
        "gender": "male",
        "persona": "",
        "cfg": 2.4,
        "speed": 1.05
    },
}


def get_named_voice(name: str) -> dict:
    """Get a named DJ voice (for rotating DJ / handoff). Returns None if unknown."""
    if not name:
        return None
    return NAMED_VOICES.get(name.lower())

# Language aliases
LANGUAGE_MAP = {
    "english": "english",
    "en": "english",
    "indonesian": "indonesian",
    "id": "indonesian",
    "spanish": "spanish",
    "es": "spanish",
    "hindi": "hindi",
    "hi": "hindi",
    "telugu": "hindi",  # Use Hindi voice for Telugu
    "tamil": "hindi",    # Use Hindi voice for Tamil
    "punjabi": "hindi"   # Use Hindi voice for Punjabi
}


def get_voice(language: str, gender: str = None) -> dict:
    """
    Get voice reference for a language
    
    Args:
        language: Language code or name
        gender: "male" or "female" (random if None)
    
    Returns:
        dict with 'file' and 'transcript'
    """
    # Normalize language
    lang = LANGUAGE_MAP.get(language.lower(), "english")
    
    # Random gender if not specified
    if gender is None:
        gender = random.choice(["male", "female"])
    
    return VOICES[lang][gender]


def get_main_dj_voice(gender: str = "male") -> dict:
    """Get main English DJ voice"""
    return VOICES["english"][gender]
