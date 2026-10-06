"""
Read the append-only decision log and show Bruce stats.

Usage:
    python log_stats.py                       # stats for the Wow playlist (default)
    python log_stats.py <path-to-jsonl>       # a specific log file
    python log_stats.py --tail 20             # also print the last 20 decisions

The log is written by agentic_dj_controller.py::_log_decision_line() - one JSON
line per break, appended (never overwritten), so it survives restarts.
"""
import os, sys, glob, json
from collections import Counter


def find_log():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        return sys.argv[1]
    files = sorted(glob.glob("decisions_log_*.jsonl"), key=os.path.getmtime, reverse=True)
    if not files:
        print("No decisions_log_*.jsonl found. Run the radio first.")
        sys.exit(1)
    return files[0]


def tail_n():
    if "--tail" in sys.argv:
        i = sys.argv.index("--tail")
        if i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                pass
        return 10
    return 0


def main():
    path = find_log()
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass

    print(f"Log: {path}")
    print(f"Total decisions: {len(entries)}")
    if not entries:
        return
    print(f"First: {entries[0].get('timestamp')}")
    print(f"Last : {entries[-1].get('timestamp')}")

    # Bruce stats
    modes = Counter(e.get("mode", "?") for e in entries)
    print("\n=== Bruce mode (all breaks) ===")
    for m in ("RIDE", "TALK-UP", "NORMAL"):
        n = modes.get(m, 0)
        pct = 100 * n / len(entries)
        print(f"  {m:8s}: {n:4d}  ({pct:5.1f}%)")

    want = [e for e in entries if e.get("want_post")]
    print(f"\n=== When the DJ WANTED to hit the post ({len(want)} breaks) ===")
    if want:
        wm = Counter(e.get("mode") for e in want)
        for m in ("RIDE", "TALK-UP", "NORMAL"):
            n = wm.get(m, 0)
            print(f"  {m:8s}: {n:4d}  ({100*n/len(want):5.1f}%)")
        # why NORMAL despite wanting the post? (script too short)
        norm = [e for e in want if e.get("mode") == "NORMAL"]
        for e in norm[:5]:
            print(f"    NORMAL: voice={e.get('voice_len')}s intro={e.get('intro')}s "
                  f"(script too short for talk-up)")

    # DJ split
    print("\n=== By DJ ===")
    for dj, n in Counter(e.get("dj", "?") for e in entries).most_common():
        print(f"  {dj:10s}: {n}")

    # Intent split
    print("\n=== By intent ===")
    for it, n in Counter(e.get("intent", "?") for e in entries).most_common():
        print(f"  {it:14s}: {n}")

    t = tail_n()
    if t:
        print(f"\n=== Last {t} decisions ===")
        for e in entries[-t:]:
            print(f"  [{e.get('timestamp','')[:19]}] {e.get('dj','?'):8s} "
                  f"{e.get('mode','?'):7s} want={str(e.get('want_post')):5s} "
                  f"v={e.get('voice_len')}s i={e.get('intro')}s  {e.get('next_song','')}")


if __name__ == "__main__":
    main()
