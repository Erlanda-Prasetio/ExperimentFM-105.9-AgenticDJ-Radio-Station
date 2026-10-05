"""
For You Zone - dedicated LISTENER LLM.

A SEPARATE brain from the DJ (its own credentials, its own persona, its own temperature).
It writes real, human listener messages. The DJ LLM then receives them COLD and reacts live.

The whole point is INFORMATION ASYMMETRY: the listener writes without knowing the DJ,
the DJ reads it for the first time on air. That is what makes it feel alive.

Split of responsibility (same philosophy as songs):
  CODE          -> owns the FACTS  (which city / name / occasion, with anti-repeat)
  LISTENER LLM  -> owns the WORDS  (the actual human message)
  DJ LLM        -> owns the REACTION (reads it cold, responds live)
"""
import os
import json
import random
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class ListenerLLM:
    """Dedicated LLM that writes listener messages for the For You Zone."""

    def __init__(self):
        self.endpoint = os.getenv("LISTENER_LLM_ENDPOINT")
        self.api_key = os.getenv("LISTENER_LLM_API_KEY")
        self.model = os.getenv("LISTENER_LLM_MODEL")
        # fallback (second provider)
        self.fb_endpoint = os.getenv("LISTENER_LLM_FALLBACK_ENDPOINT")
        self.fb_api_key = os.getenv("LISTENER_LLM_FALLBACK_API_KEY")
        self.fb_model = os.getenv("LISTENER_LLM_FALLBACK_MODEL")
        self.temperature = float(os.getenv("LISTENER_LLM_TEMPERATURE", "1.15"))

        self.enabled = bool(self.endpoint and self.api_key)
        if self.enabled:
            print(f"[Listener] Listener LLM ready: {self.model}")
        else:
            print("[Listener] No credentials found - For You Zone disabled")

    # ---------- transport ----------
    def _call(self, endpoint, key, model, prompt, timeout=120):
        r = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "stream": False,
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    # ---------- public ----------
    def generate(self, seed, avoid_names=None, avoid_cities=None, tone="any"):
        """Generate one listener message for the given seed.
        tone: 'light' | 'heavy' | 'any' - shapes how deep/personal the message is.
        Returns dict {name, city, region, occasion, kind, message} or None on failure."""
        if not self.enabled:
            return None
        avoid_names = avoid_names or []
        avoid_cities = avoid_cities or []
        prompt = self._build_prompt(seed, avoid_names, avoid_cities, tone)

        content = None
        try:
            content = self._call(self.endpoint, self.api_key, self.model, prompt)
        except Exception as e:
            print(f"[Listener] Main endpoint failed ({type(e).__name__}) - trying fallback")
            if self.fb_endpoint and self.fb_api_key:
                try:
                    content = self._call(self.fb_endpoint, self.fb_api_key, self.fb_model, prompt)
                except Exception as e2:
                    print(f"[Listener] Fallback failed too ({type(e2).__name__}) - skipping For You Zone")
                    return None
            else:
                print("[Listener] No fallback configured - skipping")
                return None

        return self._parse(content, seed)

    # ---------- internals ----------
    def _build_prompt(self, seed, avoid_names, avoid_cities, tone="any"):
        avoid_n = ", ".join(avoid_names[-8:]) if avoid_names else "(none yet)"
        avoid_c = ", ".join(avoid_cities[-8:]) if avoid_cities else "(none yet)"

        # Time-of-day shapes how open people are. Busy evening/late = deeper, daytime = lighter.
        if tone == "heavy":
            tone_line = ("It is the busy evening/night hours, when people are off work, alone with their "
                         "thoughts, and more open. Be more personal, more honest, a little deeper. "
                         "Do not force sadness, but let real feeling through if it fits.")
        elif tone == "light":
            tone_line = ("It is the daytime hours, when people are busy at work or school and just "
                         "sending quick notes. Keep it light, warm, and simple - not heavy or confessional.")
        else:
            tone_line = "Write in a natural, real tone."

        if seed.get("kind") == "question":
            return f"""You are NOT a DJ. You are NOT an assistant. You are a REAL, ordinary person
who called the request line of a radio station (Experiment FM 105.9) to ask the DJ a question.

The station's "For You Zone" lets real listeners talk to the DJ on air. You are ONE of those
listeners, and you have a genuine question for whoever is on air right now.

YOUR DETAILS (use exactly these - do not change them):
  Name: {seed['name']}
  City: {seed['city']}, {seed['region']}
  What you want to ask about: {seed['occasion_hint']}

TONE FOR RIGHT NOW: {tone_line}

RULES:
- Write like a REAL person asking a DJ a question. Casual, plain, a little unsure, human.
- It should be a QUESTION - you actually want the DJ's take. Not rhetorical, not a statement.
- Match the tone of the topic above. Keep it light OR sincere, whatever fits - don't force it.
- 1 to 2 sentences, spoken out loud. This is what the DJ will read on air.
- Do NOT mention the station name. Do NOT say the DJ's name.
- Do NOT be cheesy or "produced". Just a person asking something they actually wonder about.
- Do NOT reuse these recent names: {avoid_n}
- Do NOT reuse these recent cities: {avoid_c}

Respond ONLY with valid JSON, no markdown:
{{
  "message": "your actual question, plain and human"
}}"""

        if seed.get("kind") == "request":
            return f"""You are NOT a DJ. You are NOT an assistant. You are a REAL, ordinary person
who called the request line of a radio station (Experiment FM 105.9).

The station's "For You Zone" lets real listeners ask the DJ for something on air. You are ONE of
those listeners. You want to hear a certain KIND of music - a mood, a vibe, an era - not a specific song.

YOUR DETAILS (use exactly these - do not change them):
  Name: {seed['name']}
  City: {seed['city']}, {seed['region']}
  What you're in the mood for: {seed['occasion_hint']}

TONE FOR RIGHT NOW: {tone_line}

RULES:
- Ask the DJ for the VIBE you described - a mood, genre, or era. NOT a specific song or artist title.
  (You don't know what's in their crate. You're hoping, not ordering.)
- Be casual and real, like a text to a station. A little hopeful, not demanding.
- You may say "if you have it" or "if you've got anything like that" - you know they might not.
- 1 to 2 sentences, spoken out loud. This is what the DJ will read on air.
- Do NOT mention the station name. Do NOT say the DJ's name.
- Do NOT be cheesy or "produced". Just a person asking for a sound they want to hear.
- Do NOT reuse these recent names: {avoid_n}
- Do NOT reuse these recent cities: {avoid_c}

Respond ONLY with valid JSON, no markdown:
{{
  "message": "your actual request, plain and human"
}}"""

        # default: a message / dedication
        return f"""You are NOT a DJ. You are NOT an assistant. You are a REAL, ordinary person
reaching out to the request line of a radio station (Experiment FM 105.9).

The station's "For You Zone" plays messages from real listeners around the world.
You are ONE of those listeners. Write your message in your OWN voice, like a real human.

YOUR DETAILS (use exactly these - do not change them):
  Name: {seed['name']}
  City: {seed['city']}, {seed['region']}
  Reason for reaching out: {seed['occasion_hint']}

TONE FOR RIGHT NOW: {tone_line}

RULES:
- Write like a REAL person texting/calling a radio station. Casual, plain, imperfect. Real people are not poetic.
- Match the emotional tone of the reason above. Do not force it to be happy or sad - be true to it.
- 1 to 3 sentences, spoken out loud. This is what the DJ will read on air.
- Do NOT mention the station name or the DJ by name.
- Do NOT write anything radio-ish, cheesy, or "produced". Just a person's honest words.
- Do NOT reuse these recent names: {avoid_n}
- Do NOT reuse these recent cities: {avoid_c}

Respond ONLY with valid JSON, no markdown:
{{
  "message": "your actual words, plain and human"
}}"""

    def _parse(self, content, seed):
        content = content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else content
            if content.lower().startswith("json"):
                content = content[4:]
        content = content.strip()
        try:
            data = json.loads(content)
            msg = (data.get("message") or "").strip()
        except Exception:
            # model returned raw text instead of JSON - accept it as the message
            msg = content.strip().strip('"')
        if not msg:
            return None
        return {
            "name": seed["name"],
            "city": seed["city"],
            "region": seed["region"],
            "country": seed.get("country", ""),
            "occasion": seed["occasion"],
            "kind": seed.get("kind", "message"),
            "message": msg,
        }


# ---------- seed selection (CODE owns the facts) ----------
def load_seeds(path="listener_seeds.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_seed(seeds, used_names=None, used_cities=None, used_occasions=None,
              question_chance=None, request_chance=None):
    """Pick a city+name combo plus a flavor:
      - message/dedication (default)
      - question to the DJ   (~FYO_QUESTION_CHANCE)
      - soft music request   (~FYO_REQUEST_CHANCE)
    Returns a seed dict ready for ListenerLLM.generate()."""
    used_names = set(used_names or [])
    used_cities = set(used_cities or [])
    used_occasions = set(used_occasions or [])

    cities = seeds["cities"]
    names = seeds["names"]
    occasions = seeds["occasions"]
    questions = seeds.get("questions", [])
    requests = seeds.get("requests", [])

    if question_chance is None:
        question_chance = float(os.getenv("FYO_QUESTION_CHANCE", "0.25"))
    if request_chance is None:
        request_chance = float(os.getenv("FYO_REQUEST_CHANCE", "0.25"))

    def _choose(pool, used, key):
        def _val(x):
            return x[key] if isinstance(x, dict) else x
        fresh = [x for x in pool if _val(x) not in used]
        return random.choice(fresh if fresh else pool)

    city = _choose(cities, used_cities, "city")
    name = _choose(names, used_names, "name")

    def _build(entry, kind):
        return {
            "name": name,
            "city": city["city"],
            "region": city["region"],
            "country": city.get("country", ""),
            "occasion": entry["key"],
            "occasion_hint": entry["hint"],
            "mood": entry["mood"],
            "kind": kind,
        }

    # Roll the flavor: question / request / message
    roll = random.random()
    if questions and roll < question_chance:
        return _build(_choose(questions, used_occasions, "key"), "question")
    if requests and roll < question_chance + request_chance:
        return _build(_choose(requests, used_occasions, "key"), "request")
    return _build(_choose(occasions, used_occasions, "key"), "message")


# ---------- time-of-day profile (CODE owns the schedule) ----------
def time_profile(now=None):
    """Return the For You Zone profile for the current time.

    Busy window (default 17:00-23:00) = prime time: more sessions, more messages per
    session, and a heavier/more personal tone (people are off work, alone, open).
    Everything else = quiet: ~1 session per shift, fewer messages, lighter tone.

    Returns dict: {busy, sessions_chance, msg_min, msg_max, tone}
    """
    from datetime import datetime as _dt
    now = now or _dt.now()
    h = now.hour
    busy_start = int(os.getenv("FYO_BUSY_START", "17"))
    busy_end = int(os.getenv("FYO_BUSY_END", "23"))

    busy = busy_start <= h < busy_end
    if busy:
        return {
            "busy": True,
            "sessions_chance": float(os.getenv("FYO_BUSY_CHANCE", "0.35")),
            "msg_min": int(os.getenv("FYO_BUSY_MSGS_MIN", "4")),
            "msg_max": int(os.getenv("FYO_BUSY_MSGS_MAX", "5")),
            "tone": "heavy",
        }
    return {
        "busy": False,
        "sessions_chance": float(os.getenv("FYO_OFF_CHANCE", "0.10")),
        "msg_min": int(os.getenv("FYO_OFF_MSGS_MIN", "2")),
        "msg_max": int(os.getenv("FYO_OFF_MSGS_MAX", "3")),
        "tone": "light",
    }


def generate_session(listener_llm, seeds, used_names, used_cities, used_occasions,
                     n_messages, tone="any"):
    """Generate a whole For You Zone session: n_messages distinct listener messages.

    CODE picks the count (from the time profile); the listener LLM writes each one.
    Mutates the used_* lists so anti-repeat carries across the session.
    Returns list of message dicts (may be shorter than n_messages if some fail).
    """
    out = []
    for _ in range(max(1, n_messages)):
        seed = pick_seed(seeds, used_names, used_cities, used_occasions)
        msg = listener_llm.generate(seed, used_names, used_cities, tone=tone)
        if msg:
            out.append(msg)
            used_names.append(msg["name"])
            used_cities.append(msg["city"])
            used_occasions.append(msg["occasion"])
    return out
