"""
FINAL Junior settings lock + RLHF session summary.

After a long RLHF session (b1..b4 + newref + tune + stitch + freq), the user called
diminishing return and decided: the ORIGINAL hype reference at cfg 1.8/2.2 is still
the best trade-off, regardless of seed. Only fix the "105.9" phrase, then stop.
"""
import json

FINAL = {
    "voice": "jr",
    "reference": {
        "file": "voice_references/voice_ref_jr.wav",
        "segment": "0.0-10.4s (original energetic car-endorsement read)",
        "decision": "REVERTED from calm segment - calm killed artefacts but made it flat + bablas (no pauses)"
    },
    "cfg": 1.8,
    "speed": 1.0,
    "frequency_phrase": "one o five point nine  (RLHF freq test: v3 'o' cleanest, v5 comma 2nd)",
    "robust_seed_pool": [736123, 233578],
    "rejected": {
        "calm_ad_reference": "flat + bablas, worse trade than occasional artefacts",
        "intro_chat_reference": "user: both tune intro IS SOO BAD",
        "stitch_pause_injection": "diminishing return, stopped",
        "cfg_1.6": "not chosen",
        "cfg_2.0": "fine but 1.8 preferred"
    },
    "known_limitation": "occasional artefacts remain on 'Experiment FM' / frequency phrase - accepted as the better trade vs a flat voice",
    "user_verdict": "old 1.8 or 2.2 regardless of seed, is still better. maybe fix the 1 oh 5, and some knob, but that's it"
}

with open("tts_cache/rlhf/FINAL_junior_settings.json", "w", encoding="utf-8") as f:
    json.dump(FINAL, f, indent=2)

pool = {
    "voice": "jr",
    "cfg": 1.8,
    "speed": 1.0,
    "reference": "voice_references/voice_ref_jr.wav (hype, 0-10.4s)",
    "robust_seeds": [736123, 233578],
    "note": "cross-text verified; rotate these at generation time. Seed pool works (determinism confirmed) but yield is low; user chose the original reference over the calm one."
}
with open("tts_cache/rlhf/seed_pool.json", "w", encoding="utf-8") as f:
    json.dump(pool, f, indent=2)

print("saved FINAL_junior_settings.json + seed_pool.json")
print(json.dumps(FINAL, indent=2))
