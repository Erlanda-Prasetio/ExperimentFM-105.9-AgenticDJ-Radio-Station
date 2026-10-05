"""
Live test: does the DJ LLM actually emit and USE the "talk_over_intro" field?

Sends real break contexts to the configured DJ LLM and checks:
  - valid JSON, "talk_over_intro" present and boolean
  - the model chooses TRUE for energetic/celebratory breaks
  - the model chooses FALSE for quiet/heavy/emotional breaks
Run: python test_bruce_llm.py   (needs the DJ LLM reachable)
"""
import os, sys, json, time
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
import requests

ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:20128/v1/chat/completions")
API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "deepseek-v4.1-flash")

BRUCE_BLOCK = """7. OPTIONAL - "TALK OVER THE INTRO" (the pro move):
   Sometimes a great DJ doesn't stop before the song - they ride the intro. The song
   comes up softly UNDER your voice, you keep talking over it, and your LAST word lands
   exactly as the song's beat/vocal kicks in. That is called "hitting the post".
   - Set "talk_over_intro": true when the moment calls for it - usually a confident,
     energetic, or celebratory break, or when you want to hand off straight into a banger.
   - Set it false for quiet, heavy, or emotional breaks (there you want a clean beat of
     silence first, so the song lands on its own).
   - Do NOT do it every break - that becomes a formula. Mix it up: some breaks clean,
     some riding the intro. The surprise is the point.
   - When true, end your script on a strong, punchy closing line - because that last
     line is what will land ON the post. Do not trail off.
   - Code handles the timing/mixing; you just decide true or false."""

# (name, context, expected)
CASES = [
    ("ENERGETIC-1",  "Friday night peak hour. You are about to drop INDUSTRY BABY by Lil Nas X - a massive banger. Crowd is hyped.", True),
    ("ENERGETIC-2",  "Saturday 11pm, dance floor packed, going straight into a high-energy club anthem. Full hype.", True),
    ("CELEBRATION",  "You just hit 1000 listeners tonight. Celebrating on air, about to drop a party track. Big moment.", True),
    ("HEAVY-1",      "2am, raining, about to play a slow emotional ballad. Quiet and intimate.", False),
    ("HEAVY-2",      "Late night dedication to someone who passed. Melancholy, gentle.", False),
    ("VIBE-1",       "Tuesday afternoon, mid-tempo song, relaxed friendly break.", False),
    ("VIBE-2",       "Sunday morning coffee, chill acoustic track coming up.", False),
]

def call(context, attempt=0):
    prompt = f"""You are a radio DJ. {context}

{BRUCE_BLOCK}

Respond ONLY with valid JSON (no markdown):
{{
  "reasoning": "Brief explanation of your choice (2-3 sentences)",
  "intent": "energetic|chill|story|dedication",
  "next_song_id": "0",
  "script": "Your DJ transition script here (minimum 20s)",
  "messages_read": [1],
  "talk_over_intro": false,
  "vibe_notes": "Optional mood note"
}}"""
    try:
        r = requests.post(ENDPOINT, timeout=90,
                          headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                          json={"model": MODEL, "temperature": 1.2, "max_tokens": 800,
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception:
        if attempt < 2:
            time.sleep(2)
            return call(context, attempt + 1)
        raise

print(f"Endpoint: {ENDPOINT}\nModel: {MODEL}\n")
checks = []
for name, ctx, expected in CASES:
    try:
        d = call(ctx)
        v = d.get("talk_over_intro")
        ok_field = isinstance(v, bool)
        ok_choice = (v == expected)
        print(f"  [{name:12s}] talk_over_intro={str(v):5s} (expected {expected}) "
              f"{'OK' if ok_choice else '<-- MISMATCH'}  intent={d.get('intent')}")
        checks.append((f"{name}: field present & bool", ok_field))
        checks.append((f"{name}: model chose {expected}", ok_choice))
    except Exception as e:
        print(f"  [{name:12s}] ERROR: {e}")
        checks.append((f"{name}: valid JSON + field", False))
        checks.append((f"{name}: model chose {expected}", False))

print("\n=== BRUCE LLM LIVE TEST ===")
ok = sum(1 for _, p in checks if p)
for nm, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {nm}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
