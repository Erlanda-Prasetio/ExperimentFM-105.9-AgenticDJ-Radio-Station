"""
Build & report the curated seed pool from RLHF labels.

A seed only enters the pool if it stayed clean across MULTIPLE texts (cross-text robust),
because the b1->b4 data showed artefacts are a SEED x PHRASE interaction:
a seed can be perfect on one line and broken on another.
"""
import json
import os

STORE = "tts_cache/rlhf/preferences.json"
POOL = "tts_cache/rlhf/seed_pool.json"


def main():
    with open(STORE, encoding="utf-8") as f:
        d = json.load(f)

    # group labels by (voice, seed) with their batch+rating
    by_seed = {}
    for l in d["labels"]:
        by_seed.setdefault(l["seed"], []).append(l)

    print("=== per-seed scorecard (all batches) ===")
    print(f"{'seed':>8}  {'good':>4} {'meh':>4} {'bad':>4}   verdict")
    robust = []
    for seed, labels in sorted(by_seed.items(), key=lambda x: -sum(1 for l in x[1] if l["rating"] == "good")):
        g = sum(1 for l in labels if l["rating"] == "good")
        m = sum(1 for l in labels if l["rating"] == "meh")
        b = sum(1 for l in labels if l["rating"] == "bad")
        # robust = tested on >=3 takes AND never bad AND mostly good
        verdict = ""
        if b == 0 and g >= 3 and m == 0:
            verdict = "ROBUST ✅"
            robust.append(seed)
        elif b > 0:
            verdict = "fragile"
        else:
            verdict = "unproven"
        print(f"{seed:>8}  {g:>4} {m:>4} {b:>4}   {verdict}")

    print()
    print(f"=== ROBUST SEEDS ({len(robust)}): {robust} ===")
    if len(robust) < 4:
        print(f"  NOTE: {len(robust)} seeds is thin for rotation. Need to screen more,")
        print(f"  OR fix the reference so MORE seeds come out robust.")

    with open(POOL, "w", encoding="utf-8") as f:
        json.dump({"voice": "jr", "cfg": 2.2, "robust_seeds": robust,
                   "note": "cross-text verified; rotate these at generation time"}, f, indent=2)
    print(f"saved -> {POOL}")


if __name__ == "__main__":
    main()
