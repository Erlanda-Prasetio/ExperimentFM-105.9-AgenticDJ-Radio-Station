"""Record RLHF preference labels and analyze seed patterns.

Labels come from the user listening to TTS batches. Since no cheap automatic metric
separates clean takes from artefact-y ones, human preference IS the signal.
"""
import json
import os
import sys
from datetime import datetime

STORE = "tts_cache/rlhf/preferences.json"


def load():
    if os.path.exists(STORE):
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    return {"labels": [], "seed_scores": {}}


def save(data):
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def record(voice, batch, idx, seed, rating, notes):
    """rating: good | meh | bad. Idempotent: re-recording the same (voice,batch,idx) updates it."""
    d = load()
    # remove any existing entry for this exact take (avoid double-counting)
    d["labels"] = [l for l in d["labels"]
                   if not (l["voice"] == voice and l["batch"] == batch and l["idx"] == idx)]
    d["labels"].append({
        "voice": voice, "batch": batch, "idx": idx, "seed": seed,
        "rating": rating, "notes": notes,
        "at": datetime.now().isoformat(),
    })
    # rebuild seed_scores from scratch (so edits/removals stay consistent)
    scores = {}
    for l in d["labels"]:
        key = f"{l['voice']}:{l['seed']}"
        sc = scores.setdefault(key, {"voice": l["voice"], "seed": l["seed"],
                                     "good": 0, "meh": 0, "bad": 0})
        sc[l["rating"]] = sc.get(l["rating"], 0) + 1
    d["seed_scores"] = scores
    save(d)
    return d


def report():
    d = load()
    print(f"=== total labels: {len(d['labels'])} ===")
    by = {}
    for l in d["labels"]:
        by.setdefault(l["rating"], []).append(l["seed"])
    for r in ("good", "meh", "bad"):
        print(f"  {r:5}: {len(by.get(r, []))}")
    print()
    print("=== seeds by rating ===")
    for r in ("good", "meh", "bad"):
        seeds = by.get(r, [])
        if seeds:
            print(f"  {r.upper():5}: {seeds}")
    return d


if __name__ == "__main__":
    # Batch b1 labels (user feedback) - 8 random seeds, same text
    b1 = [
        (1, 560417, "meh",  "intonasi teriak, ada artefak"),
        (2, 456112, "good", "genuinely good"),
        (3, 736123, "good", "another good one"),
        (4, 187917, "meh",  "artefak di 'EF EM' (Experiment FM)"),
        (5, 686978, "bad",  "stuttering di 'in the NNNight'"),
        (6, 341520, "meh",  "the flattest so far"),
        (7, 564558, "bad",  "artefak di 'one oh' sama 'you are'"),
        (8, 94045,  "meh",  "first half artefak, sisanya not bad"),
    ]
    for idx, seed, rating, notes in b1:
        record("jr", "b1", idx, seed, rating, notes)

    # Batch b2: seed robustness test - 2 "good" seeds x 3 DIFFERENT texts
    # KEY FINDING: seed behaviour is CONSISTENT across texts.
    #   736123 -> always clean (GOLD). 456112 -> always weird intonation at sentence end.
    b2 = [
        (1, 456112, "meh",  "T1: intonasi 'smooth for the ride home' aneh"),
        (2, 736123, "good", "T1: better than s456112"),
        (3, 456112, "bad",  "T2: 'where you are' creepy"),
        (4, 736123, "good", "T2: jauh lebih human, not even a contest"),
        (5, 456112, "meh",  "T3: intonasi aneh di akhir kalimat (trend sama)"),
        (6, 736123, "good", "T3: selalu clean"),
    ]
    for idx, seed, rating, notes in b2:
        record("jr", "b2", idx, seed, rating, notes)

    # Batch b3: screening 12 new seeds on one text.
    # User: 4,5,6,7,9,12 good; rest bad. Note on 11: good but extra sound at sentence end.
    b3 = [
        (1, 498169, "bad",  ""),
        (2, 289471, "bad",  ""),
        (3, 743625, "bad",  ""),
        (4, 903725, "good", ""),
        (5, 528278, "good", ""),
        (6, 233578, "good", ""),
        (7, 135530, "good", ""),
        (8, 925593, "bad",  ""),
        (9, 565081, "good", ""),
        (10, 754240, "bad", ""),
        (11, 65718, "meh",  "bagus tapi ada suara tambahan di akhir kalimat"),
        (12, 241630, "good", ""),
    ]
    for idx, seed, rating, notes in b3:
        record("jr", "b3", idx, seed, rating, notes)

    # Batch b4: CROSS-TEXT robustness (6 candidates x 3 texts A/B/C).
    # Only 233578 stayed clean on all three. Others failed at least one text.
    # Confirms: one-text screening is nearly worthless; cross-text is the real test.
    # idx: 1-6 = text A, 7-12 = text B, 13-18 = text C
    b4 = [
        # text A
        (1, 903725, "good", "A: best A performance"),
        (2, 528278, "good", "A: pass"),
        (3, 233578, "good", "A: pass"),
        (4, 135530, "bad",  "A: artefak di 'through the night'"),
        (5, 241630, "bad",  "A: artefak di 'you with me through'"),
        (6, 565081, "bad",  "A: failed"),
        # text B
        (7, 903725, "bad",  "B: failed"),
        (8, 528278, "bad",  "B: massive artefak di 'headlight' & 'empty road'"),
        (9, 233578, "good", "B: pass"),
        (10, 135530, "good", "B: pass"),
        (11, 241630, "good", "B: best B performance"),
        (12, 565081, "good", "B: pass"),
        # text C
        (13, 903725, "bad",  "C: 'little longer' artefak aneh"),
        (14, 528278, "good", "C: pass"),
        (15, 233578, "good", "C: pass"),
        (16, 135530, "bad",  "C: artefak everywhere"),
        (17, 241630, "bad",  "C: intonasi aneh di 'little longer'"),
        (18, 565081, "good", "C: best C performance"),
    ]
    for idx, seed, rating, notes in b4:
        record("jr", "b4", idx, seed, rating, notes)

    report()
