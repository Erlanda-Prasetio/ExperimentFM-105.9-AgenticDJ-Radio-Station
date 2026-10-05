"""
Agentic DJ: reasoning + script generation
Decides transition types and generates natural scripts
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import random
import json
import requests
from playlist_manager import Track


@dataclass
class TransitionIntent:
    """DJ transition intent"""
    type: str  # standard, trivia, weather, news, vibe-check, surprise, silence
    reasoning: str
    context: dict


class DJAgent:
    """
    Agentic AI DJ with memory and reasoning
    """
    
    def __init__(self, llm_endpoint: str, llm_api_key: str, llm_model: str, station_name: str = "Experiment FM 105.9"):
        self.llm_endpoint = llm_endpoint
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model
        self.station_name = station_name
        
        # Session memory
        self.transition_history: List[str] = []  # Last 10 transition types
        self.session_start = datetime.now()
        self.songs_played = 0
        
        print(f"[DJ Agent] Initialized: {station_name}")
    
    def decide_intent(self, current_song: Track, next_song: Track) -> TransitionIntent:
        """
        Reasoning step: decide what type of transition to do
        Uses LLM to avoid repetition and stay engaging
        """
        # Get context
        hour = datetime.now().hour
        time_of_day = self._get_time_of_day(hour)
        recent_transitions = self.transition_history[-5:] if self.transition_history else []
        
        # Build reasoning prompt
        prompt = f"""You are the AI DJ for {self.station_name}, a late-night radio station.

Session context:
- Time: {datetime.now().strftime('%I:%M %p')} ({time_of_day})
- Songs played this session: {self.songs_played}
- Last 5 transitions: {recent_transitions if recent_transitions else 'None yet'}

Current song ending: "{current_song.title}" by {current_song.artist} ({current_song.language})
Next song: "{next_song.title}" by {next_song.artist} ({next_song.language})

Transition types available:
- standard: simple song A → B transition (40% baseline)
- trivia: fun fact about artist/song/album (20%)
- weather: mention weather and mood (10%)
- news: quick headline mention (5%)
- vibe-check: check in with listeners (10%)
- surprise: listener shoutout, dedication, or quirky comment (10%)
- silence: just let the music speak (5%)

DECIDE: What transition type should you do?

Rules:
- Avoid repeating the same type 3+ times in a row
- Match the time of day (intimate at night, upbeat in morning)
- Weather/news are rare surprises, not frequent
- Silence is powerful but use sparingly

Respond in JSON:
{{
  "type": "...",
  "reasoning": "brief explanation why this fits"
}}"""
        
        try:
            response = self._call_llm(prompt, max_tokens=150)
            data = json.loads(response)
            
            intent_type = data.get("type", "standard")
            reasoning = data.get("reasoning", "Default transition")
            
        except Exception as e:
            print(f"[DJ Agent] Intent decision failed: {e}, using standard")
            intent_type = "standard"
            reasoning = "Fallback to standard transition"
        
        # Store in memory
        self.transition_history.append(intent_type)
        if len(self.transition_history) > 10:
            self.transition_history.pop(0)
        
        return TransitionIntent(
            type=intent_type,
            reasoning=reasoning,
            context={
                "time_of_day": time_of_day,
                "hour": hour,
                "songs_played": self.songs_played
            }
        )
    
    def generate_script(self, intent: TransitionIntent, current_song: Track, 
                       next_song: Track, weather: Optional[str] = None,
                       news_headline: Optional[str] = None) -> str:
        """
        Generate DJ script based on intent
        Returns natural spoken script with pronunciation guides
        """
        # Build context
        hour = datetime.now().hour
        time_str = datetime.now().strftime('%I:%M %p')
        
        # Create style guide based on intent
        style_guides = {
            "standard": "casual and smooth",
            "trivia": "enthusiastic music nerd sharing cool facts",
            "weather": "observant and atmospheric",
            "news": "quick mention, then back to music",
            "vibe-check": "warm and checking in with late-night listeners",
            "surprise": "playful and spontaneous",
            "silence": "minimal, let music speak"
        }
        
        style = style_guides.get(intent.type, "casual")
        
        # Build pronunciation context
        pronun_guide = self._get_pronunciation_guide(current_song, next_song)
        
        # Generate script
        prompt = f"""You are the AI DJ for {self.station_name}.

Current context:
- Time: {time_str} ({intent.context['time_of_day']})
- Transition type: {intent.type}
- Style: {style}
- Songs played: {self.songs_played}

Song transition:
FROM: "{current_song.title}" by {current_song.artist}
  - Genre: {current_song.genre or 'Unknown'}
  - Language: {current_song.language}
  - Year: {current_song.year or 'Unknown'}

TO: "{next_song.title}" by {next_song.artist}
  - Genre: {next_song.genre or 'Unknown'}
  - Language: {next_song.language}
  - Year: {next_song.year or 'Unknown'}

{pronun_guide}

{"Weather: " + weather if weather and intent.type == "weather" else ""}
{"Headline: " + news_headline if news_headline and intent.type == "news" else ""}

Write a 15-25 second DJ transition script ({style}).

IMPORTANT for Bollywood/Indian songs:
- Movie name is MORE important than singer name
- Mention: "Song Title from Movie Name" (not just singer)
- Example: "Choodi Baji Hai from Hum Aapke Hain Koun"

CRITICAL PRONUNCIATION RULE for Hindi/Bollywood names:
Write Hindi names, movie titles, and song titles PHONETICALLY using English spelling so text-to-speech pronounces them correctly.

Examples:
- "Arijit Singh" → "Ah-ree-jeet Sing"
- "Kabhi Khushi Kabhie Gham" → "Kah-bee Koo-shee Kah-bee Gum"
- "Rab Ne Bana Di Jodi" → "Rub Nay Bah-nah Dee Joe-dee"
- "Shah Rukh Khan" → "Shah Rook Kahn"
- "Aashiqui 2" → "Ah-shee-kee Two"
- "Tum Hi Ho" → "Toom Hee Hoh"

Write the entire script with phonetic spelling for ALL Hindi words.

Formatting:
- Song titles in quotes: "Kabhi Khushi Kabhie Gham"
- Movie names in asterisks: *Dil To Pagal Hai*
- Write naturally, your voice handles Hindi pronunciation

Requirements:
- Natural spoken language (not written essay)
- Keep it conversational and warm
- Match the {intent.type} style
- Don't be overly enthusiastic or fake

Just the script, no stage directions:"""
        
        try:
            script = self._call_llm(prompt, max_tokens=200)
            return script.strip().strip('"')
        
        except Exception as e:
            print(f"[DJ Agent] Script generation failed: {e}")
            # Fallback simple script
            return f"That was {current_song.artist} with {current_song.title}. Here's {next_song.artist}."
    
    def generate_opening(self) -> str:
        """Generate station opening monologue"""
        hour = datetime.now().hour
        time_of_day = self._get_time_of_day(hour)
        time_str = datetime.now().strftime('%I:%M %p')
        
        prompt = f"""You are the AI DJ starting your show on {self.station_name}.

Time: {time_str} ({time_of_day})

Write a 15-20 second opening. Be warm, welcoming, and set the mood.
Mention it's an AI radio experiment. Keep it natural and conversational.

Just the script:"""
        
        try:
            return self._call_llm(prompt, max_tokens=150).strip().strip('"')
        except:
            return f"Hey there. You're listening to {self.station_name}. I'm your AI DJ, and we've got music for you tonight. Let's get started."
    
    def _call_llm(self, prompt: str, max_tokens: int = 200) -> str:
        """Call LLM API"""
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.95,  # Higher creativity (was 0.8)
            "stream": False
        }
        
        response = requests.post(
            self.llm_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        content = response.json()['choices'][0]['message']['content']
        
        # Strip thinking tags if present
        import re
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        content = content.strip()
        
        return content
    
    def _get_time_of_day(self, hour: int) -> str:
        """Convert hour to time of day label"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "late night"
    
    def _get_pronunciation_guide(self, current_song: Track, next_song: Track) -> str:
        """Build pronunciation context for non-English titles"""
        guides = []
        
        for song in [current_song, next_song]:
            if song.language != "English":
                guides.append(f"- '{song.title}' is in {song.language}")
        
        if guides:
            return "Pronunciation notes:\n" + "\n".join(guides)
        return ""
    
    def increment_song_count(self):
        """Track songs played"""
        self.songs_played += 1
