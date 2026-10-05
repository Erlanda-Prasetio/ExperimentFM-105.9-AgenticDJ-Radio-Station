"""
Record the tune-sweep findings + lock Junior settings.

Findings (user, seed 736123 fixed):
  - intro-chat reference  : BOTH BAD -> discard candidate
  - calm ref, cfg 1.8 sp1.0: good, but "bablas tanpa berhenti" (runs on, no pauses)
  - calm ref, cfg 2.0 sp1.0: good, slightly MORE life on "one oh five point nine" -> WINNER
  - cfg 1.8 vs 2.0         : not much difference; both run on without stopping
"""
import json
import os

STORE = "tts_cache/rlhf/preferences.json"
POOL = "tts_cache/rlhf/seed_pool.json"
TUNE = "tts_cache/rlhf/tune_findings.json"

findings = {
    "voice": "jr",
    "seed": 736123,
    "text": "Experiment FM, one oh five point nine. That was a beautiful one to sit with, coming up next, something a little warmer for the ride home. Stay with me.",
    "reference_decision": {
        "intro_chat": "REJECTED - both takes bad",
        "calm_ad": "ACCEPTED - winner"
    },
    "cfg_decision": {
        "1.6": "not evaluated by user",
        "1.8": "good but flat-ish, runs on without stopping",
        "2.0": "WINNER - a little bit of life on 'one oh five point nine'",
        "note": "1.8 vs 2.0 not much different; both 'bablas tanpa berhenti'"
    },
    "speed_decision": "1.0 (0.90 not chosen)",
    "LOCKED": {"reference": "calm_ad", "cfg": 2.0, "speed": 1.0, "seed_pool": [736123, 233578]},
    "open_problem": "bablas tanpa berhenti = no pause/breath rhythm, inherited from the continuous ad-read reference"
}

with open(TUNE, "w", encoding="utf-8") as f:
    json.dump(findings, f, indent=2)
print("saved ->", TUNE)

# update the pool with the locked settings
if os.path.exists(POOL):
    with open(POOL, encoding="utf-8") as f:
        pool = json.load(f)
else:
    pool = {"voice": "jr", "robust_seeds": [736123, 233578]}

pool["cfg"] = 2.0
pool["speed"] = 1.0
pool["reference"] = "voice_references/voice_ref_jr.wav (calm ad segment 27.25-39.40s)"
pool["rejected"] = {"intro_chat_ref": "user: both tune intro IS SOO BAD"}
pool["open_problem"] = "no pauses (bablas) - needs deterministic pause injection"

with open(POOL, "w", encoding="utf-8") as f:
    json.dump(pool, f, indent=2)
print("updated ->", POOL)
print(json.dumps(pool, indent=2))
