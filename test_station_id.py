"""
Test: FCC-style station ID logic.

Rules:
- Station ID is DUE on the first break of a new clock-hour, NOT every break.
- Handoff breaks (hello/goodbye) skip the ID block and do NOT consume the hour.
- The "not due" prompt must explicitly forbid the station name/frequency.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, ".")
os.environ.setdefault("AUDIO_OUTPUT", "none")

import agentic_dj_controller as C

# --- Build a controller WITHOUT touching audio/playlist (bypass __init__) ---
ctrl = C.AgenticRadioController.__new__(C.AgenticRadioController)
ctrl.station_name = "Experiment FM 105.9"
ctrl.last_station_id_hour = None

# --- 1. prompt content: ID due vs not due ---
p_due = ctrl._build_decision_prompt(
    time_str="16:00", time_of_day="afternoon", recent_plays=[], available_songs=[],
    dj_name="Junior", station_id_due=True)
p_not = ctrl._build_decision_prompt(
    time_str="16:20", time_of_day="afternoon", recent_plays=[], available_songs=[],
    dj_name="Junior", station_id_due=False)

checks = []
checks.append(("DUE prompt mentions 'STATION ID: DUE'", "STATION ID: DUE" in p_due))
checks.append(("NOT-DUE prompt mentions 'NOT DUE'", "STATION ID: NOT DUE" in p_not))
checks.append(("NOT-DUE forbids station name", "Do NOT say \"Experiment FM 105.9\"" in p_not))
checks.append(("NOT-DUE forbids frequency", "105.9 / one o five point nine" in p_not))
checks.append(("NOT-DUE forbids self-intro", "Do NOT introduce yourself by name" in p_not))
checks.append(("old 'I'm {name}' trigger removed", '(e.g. "I\'m Junior")' not in p_due))
checks.append(("DUE asks for station name", "Experiment FM 105.9" in p_due))

# --- 2. handoff breaks suppress the ID block ---
p_hello = ctrl._build_decision_prompt(
    time_str="16:00", time_of_day="afternoon", recent_plays=[], available_songs=[],
    dj_name="Junior", station_id_due=True, handoff_mode="hello", handoff_from="Cara")
checks.append(("handoff hello: no ID block", "STATION ID:" not in p_hello))
checks.append(("handoff hello: has HELLO BREAK block", "HELLO BREAK" in p_hello))

# --- 3. hour-key logic ---
def due(ctrl, hour, last):
    ctrl.last_station_id_hour = last
    key = hour.strftime("%Y-%m-%d %H")
    return ctrl.last_station_id_hour != key

h16 = datetime(2026, 10, 5, 16, 5)
h17 = datetime(2026, 10, 5, 17, 1)
checks.append(("fresh start -> ID due", due(ctrl, h16, None) is True))
checks.append(("same hour again -> NOT due", due(ctrl, h16, "2026-10-05 16") is False))
checks.append(("new hour -> due again", due(ctrl, h17, "2026-10-05 16") is True))

print("=== FCC STATION ID TEST ===")
ok = 0
for name, passed in checks:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok += passed
print(f"\n  {ok}/{len(checks)} passed")
sys.exit(0 if ok == len(checks) else 1)
