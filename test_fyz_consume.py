"""
Regression test: For You Zone message consumption (the "Wesley read twice" bug).

THE BUG (before the fix):
  The DJ may read listener messages in ANY order, e.g. [3, 1]. The old code assumed
  it always read the first N, so it logged the wrong messages AND left the actually-read
  ones in the queue -> a listener got read twice with a different response.

THE FIX:
  The DJ reports the NUMBERS it read ("messages_read": [3, 1]); the code consumes exactly
  those and keeps the rest in order.
"""
import os
import sys
sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import agentic_dj_controller as C

ctrl = C.AgenticRadioController.__new__(C.AgenticRadioController)

# Reproduce the real data from the live log
MSGS = [
    {"name": "Arif",   "city": "Bangor", "region": "Maine",    "kind": "question", "message": "job interview tomorrow"},
    {"name": "Sofia",  "city": "Fargo",  "region": "ND",       "kind": "question", "message": "staring at a text from my ex"},
    {"name": "Wesley", "city": "Porto",  "region": "",         "kind": "question", "message": "concert on my own?"},
]

checks = []

# --- 1. THE EXACT BUG: DJ reads [3, 1] (Wesley first, then Arif) ---
read = ctrl._resolve_messages_read([3, 1], MSGS)
checks.append(("reported [3,1] -> resolved [3,1]", read == [3, 1]))
# consumed = everything NOT in {3,1} = message #2 (Sofia) stays
consumed = [m for i, m in enumerate(MSGS, 1) if i not in set(read)]
checks.append(("Sofia (#2) stays, Wesley removed", [m['name'] for m in consumed] == ["Sofia"]))
# the messages actually logged as read
logged = [MSGS[i-1]['name'] for i in read]
checks.append(("logged reads are [Wesley, Arif]", logged == ["Wesley", "Arif"]))

# --- 2. Robustness: string form "2, 1" ---
checks.append(("string '2, 1' parsed", ctrl._resolve_messages_read("2, 1", MSGS) == [2, 1]))
# --- 3. Robustness: plain int 2 ---
checks.append(("int 2 -> [2]", ctrl._resolve_messages_read(2, MSGS) == [2]))
# --- 4. Out-of-range ignored ---
checks.append(("out-of-range [9] ignored", ctrl._resolve_messages_read([9], MSGS) == []))
# --- 5. Duplicates de-duped ---
checks.append(("dupes [1,1,2] -> [1,2]", ctrl._resolve_messages_read([1, 1, 2], MSGS) == [1, 2]))

# --- 6. Safety net: bad field, but names appear in the script ---
script = "First up, Wesley in Porto. And then Arif from Bangor."
r = ctrl._resolve_messages_read(None, MSGS, script)
checks.append(("name-scan fallback finds Wesley+Arif", set(r) == {3, 1}))

# --- 7. Full end-to-end: session advances without repeats ---
# IMPORTANT: each break the prompt re-numbers the REMAINING messages from 1,
# so the DJ reports numbers relative to the CURRENT queue (not the original list).
queue = list(MSGS)
seen = []
# break1: [Arif, Sofia, Wesley] -> read #3 (Wesley)
# break2: [Arif, Sofia]         -> read #2 (Sofia)
# break3: [Arif]                -> read #1 (Arif)
for report in ([3], [2], [1]):
    rd = ctrl._resolve_messages_read(report, queue)
    seen.extend(queue[i-1]['name'] for i in rd)
    queue = [m for i, m in enumerate(queue, 1) if i not in set(rd)]
checks.append(("full session: each read once", sorted(seen) == ["Arif", "Sofia", "Wesley"]))
checks.append(("full session: queue emptied", queue == []))

print("=== FYZ MESSAGE-CONSUMPTION TEST ===")
ok = 0
for name, passed in checks:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok += passed
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
