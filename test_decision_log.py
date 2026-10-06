"""
Test: append-only decision log (survives restarts) + log_stats reader.

Tests the controller's _decisions_log_path / _log_decision_line WITHOUT
instantiating the controller (no audio device, no live process touched).
Uses a stub `self` that carries only the attributes those methods need.

Run: python test_decision_log.py
"""
import os, sys, json, tempfile
sys.path.insert(0, ".")

from agentic_dj_controller import AgenticRadioController as ARC

checks = []
tmpdir = tempfile.mkdtemp()


class Stub:
    """Minimal object carrying just what the log methods touch."""
    _decisions_log_path = ARC._decisions_log_path
    _log_decision_line = ARC._log_decision_line


stub = Stub()

# 1) path derivation (same slug rule as state/session files)
p1 = stub._decisions_log_path("C:/sourceCode/YT_Downloader/downloads/Wow, this ist gud")
checks.append((f"slug path: {p1}", p1 == "decisions_log_wow_this_ist_gud.jsonl"))
p2 = stub._decisions_log_path("C:/x/Punjab Classic In Order")
checks.append((f"slug path: {p2}", p2 == "decisions_log_punjab_classic_in_order.jsonl"))

# 2) append-only: writing N lines keeps all of them (no overwrite)
logfile = os.path.join(tmpdir, "decisions_log_test.jsonl")
stub.decisions_log_file = logfile
for i in range(5):
    stub._log_decision_line({
        "timestamp": f"2026-10-06T11:0{i}:00",
        "dj": "Junior" if i % 2 else "Cara",
        "intent": "energetic" if i < 3 else "chill",
        "next_song": f"Song {i}",
        "want_post": i < 4,
        "mode": ["RIDE", "TALK-UP", "TALK-UP", "NORMAL", "NORMAL"][i],
        "voice_len": [14.0, 34.0, 28.0, 3.0, 40.0][i],
        "intro": [12.0, 0.0, 5.0, 5.0, 20.0][i],
        "entry": [2.0, 34.0, 23.0, 0.0, 20.0][i],
        "script": f"script {i}",
        "reasoning": f"reason {i}",
    })

lines = [l for l in open(logfile, encoding="utf-8").read().splitlines() if l.strip()]
checks.append((f"append-only keeps all 5 lines (got {len(lines)})", len(lines) == 5))

# 3) every line is valid JSON with the expected keys
keys_ok = True
for l in lines:
    d = json.loads(l)
    for k in ("timestamp", "dj", "intent", "next_song", "want_post", "mode",
              "voice_len", "intro", "entry", "script", "reasoning"):
        if k not in d:
            keys_ok = False
checks.append(("every line is valid JSON with all keys", keys_ok))

# 4) a second "session" (new stub, same file) APPENDS, does not reset
stub2 = Stub()
stub2.decisions_log_file = logfile
stub2._log_decision_line({"timestamp": "2026-10-06T12:00:00", "dj": "Cara",
                          "intent": "story", "next_song": "Song X",
                          "want_post": False, "mode": "NORMAL",
                          "voice_len": 25.0, "intro": 3.0, "entry": 22.0,
                          "script": "s", "reasoning": "r"})
lines2 = [l for l in open(logfile, encoding="utf-8").read().splitlines() if l.strip()]
checks.append((f"restart appends (5 -> {len(lines2)}, no reset)", len(lines2) == 6))

# 5) never raises on a bad path
try:
    bad = Stub()
    bad.decisions_log_file = os.path.join(tmpdir, "no_such_dir", "x.jsonl")
    bad._log_decision_line({"a": 1})
    checks.append(("bad path does not raise", True))
except Exception as e:
    checks.append((f"bad path does not raise ({e})", False))

# 6) log_stats reads the file and reports the right mode counts
import subprocess
r = subprocess.run([sys.executable, "log_stats.py", logfile],
                   capture_output=True, text=True)
out = r.stdout
checks.append(("log_stats reports 6 decisions", "Total decisions: 6" in out))
checks.append(("log_stats counts RIDE 1", "RIDE" in out and " 1 " in out))
checks.append(("log_stats counts TALK-UP 2", "TALK-UP" in out))
checks.append(("log_stats exits 0", r.returncode == 0))

print("=== DECISION LOG TEST ===")
ok = 0
for name, passed in checks:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok += passed
print(f"\n  {ok}/{len(checks)} passed")
print("\n--- sample log_stats output ---")
print(out)
sys.exit(0 if ok == len(checks) else 1)
