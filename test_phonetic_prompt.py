"""
Test phonetic pronunciation via LLM prompt injection
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy-key")

# Test prompt with phonetic instruction
system_prompt = """You are an AI radio DJ for Experiment FM 105.9.

CRITICAL PRONUNCIATION RULE:
When writing Hindi/Bollywood names or movie titles, write them PHONETICALLY using English spelling so a text-to-speech engine pronounces them correctly.

Examples:
- "Arijit Singh" → "Ah-ree-jeet Sing" 
- "Kabhi Khushi Kabhie Gham" → "Kah-bee Koo-shee Kah-bee Gum"
- "Rab Ne Bana Di Jodi" → "Rub Nay Bah-nah Dee Joe-dee"
- "Shah Rukh Khan" → "Shah Rook Kahn"

Write natural DJ transitions mentioning the artist and song."""

# Test scenarios
tests = [
    {
        "song": "Tum Hi Ho by Arijit Singh from Aashiqui 2",
        "next_song": "Kabhi Khushi Kabhie Gham from Rab Ne Bana Di Jodi"
    },
    {
        "song": "Chaiyya Chaiyya by Sukhwinder Singh",
        "next_song": "Dil Se Re from Dil Se"
    }
]

for i, test in enumerate(tests, 1):
    print(f"\n{'='*60}")
    print(f"TEST {i}")
    print(f"{'='*60}")
    print(f"Current: {test['song']}")
    print(f"Next: {test['next_song']}\n")
    
    user_prompt = f"""Generate a DJ transition. 
Just finished playing: {test['song']}
Coming up next: {test['next_song']}

Write 2-3 sentences. Remember to use phonetic spelling for Hindi names!"""
    
    response = requests.post(
        LLM_ENDPOINT,
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.8,
            "stream": False
        },
        timeout=30
    )
    
    result = response.json()
    print(f"Raw response: {json.dumps(result, indent=2)}")
    
    # Handle different response formats
    if 'choices' in result:
        script = result['choices'][0]['message']['content']
    elif 'content' in result:
        script = result['content']
    elif 'response' in result:
        script = result['response']
    else:
        script = str(result)
    
    print("Generated script:")
    print(script)
    print()
