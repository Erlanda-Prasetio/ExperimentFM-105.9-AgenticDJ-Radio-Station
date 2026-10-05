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

BRUCE_BLOCK = """7. OPTIONAL - "HIT THE POST" (the pro move):
   Sometimes a great DJ doesn't stop before the song - they ride the intro. The song
   comes up UNDER your voice, you keep talking over it, and your LAST word lands
   exactly as the song's beat/vocal kicks in. That is called "hitting the post".
   - Set "talk_over_intro": true when you want to hit the post this break - usually a
     confident, energetic, or celebratory break, or a handoff straight into a banger.
   - Set it false for quiet, heavy, or emotional breaks (there you want a clean beat of
     silence first, so the song lands on its own).
   - Do NOT do it every break - that becomes a formula. Mix it up: some breaks clean,
     some hitting the post. The surprise is the point.
   - When true, end your script on a strong, punchy closing line - because that last
     line is what will land ON the post. Do not trail off.
   - You may write a normal-length script when true - the code decides HOW to hit the
     post (ride the intro if it fits, otherwise bring the music up under your last few
     words). You just decide true or false."""

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
        # Robust extraction: strip fences, then grab the first {...} block
        if "```" in content:
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        if not content.startswith("{"):
            s, e = content.find("{"), content.rfind("}")
            if s != -1 and e != -1:
                content = content[s:e + 1]
        return json.loads(content)
    except Exception:
        if attempt < 3:
            time.sleep(2)
            return call(context, attempt + 1)
        raise

print(f"Endpoint: {ENDPOINT}\nModel: {MODEL}\n")
checks = []
rows = []
for name, ctx, expected in CASES:
    try:
        d = call(ctx)
        v = d.get("talk_over_intro")
        script = str(d.get("script", ""))
        words = len(script.split())
        rows.append((name, expected, v, words))
        ok_field = isinstance(v, bool)
        print(f"  [{name:12s}] talk_over_intro={str(v):5s} (expected {expected})  "
              f"intent={d.get('intent')}  words={words}")
        checks.append((f"{name}: field present & bool", ok_field))
        # Quiet/heavy/chill breaks must NEVER ride the intro (hard rule).
        if expected is False:
            checks.append((f"{name}: never rides (quiet/heavy)", v is False))
    except Exception as e:
        print(f"  [{name:12s}] ERROR: {e}")
        rows.append((name, expected, None, 0))
        checks.append((f"{name}: valid JSON + field", False))

# Aggregate behaviour (the LLM is stochastic at temp 1.2 - judge the pattern, not one sample):
#   - energetic breaks should ride SOMETIMES (Bruce fires)
#   - quiet/heavy breaks should ride NEVER
energetic = [r for r in rows if r[1] is True and isinstance(r[2], bool)]
quiet = [r for r in rows if r[1] is False and isinstance(r[2], bool)]
fired = sum(1 for r in energetic if r[2] is True)
leaked = sum(1 for r in quiet if r[2] is True)
checks.append((f"Bruce fires on some energetic breaks ({fired}/{len(energetic)})", fired >= 1))
checks.append((f"Bruce NEVER fires on quiet/heavy breaks ({leaked}/{len(quiet)})", leaked == 0))

print("\n=== BRUCE LLM LIVE TEST ===")
ok = sum(1 for _, p in checks if p)
for nm, p in checks:
    print(f"  [{'PASS' if p else 'FAIL'}] {nm}")
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
