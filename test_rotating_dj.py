"""Isolated test of rotating DJ + handoff logic."""
from datetime import datetime, timedelta

class FakeController:
    def __init__(self, roster, shift_hours=3):
        self.roster = roster
        self.shift_hours = shift_hours
        self.current_dj_idx = 0
        self.shift_started_at = datetime.now()
        self.handoff_armed = False
        self.log = []

    def _current_dj(self):
        return self.roster[self.current_dj_idx % len(self.roster)] if self.roster else None
    def _next_dj(self):
        return self.roster[(self.current_dj_idx + 1) % len(self.roster)] if self.roster else None
    def _shift_elapsed_hours(self):
        return (datetime.now() - self.shift_started_at).total_seconds() / 3600
    def _shift_expired(self):
        return len(self.roster) > 1 and self._shift_elapsed_hours() >= self.shift_hours
    def _advance_dj(self):
        old = self._current_dj()['name']
        self.current_dj_idx = (self.current_dj_idx + 1) % len(self.roster)
        new = self._current_dj()['name']
        self.shift_started_at = datetime.now()
        self.handoff_armed = False
        self.log.append(f"HANDOFF {old}->{new}")

    def decide(self):
        handoff_mode = None
        dj = self._current_dj()
        if len(self.roster) > 1:
            if self.handoff_armed:
                handoff_mode = 'hello'; dj = self._next_dj()
            elif self._shift_expired():
                handoff_mode = 'goodbye'; dj = self._current_dj()
        if handoff_mode == 'goodbye':
            self.handoff_armed = True
        elif handoff_mode == 'hello':
            self._advance_dj()
        return dj['name'] if dj else None, handoff_mode

ROSTER = [
    {"name": "Cara", "voice": "ara"},
    {"name": "Junior", "voice": "jr"},
]

print("=== TEST 1: normal break (shift not expired) ===")
c = FakeController(ROSTER, shift_hours=3)
name, mode = c.decide()
print(f"  dj={name}, mode={mode}")
assert name == "Cara" and mode is None

print("=== TEST 2: shift expired -> goodbye ===")
c.shift_started_at = datetime.now() - timedelta(hours=3, minutes=1)
name, mode = c.decide()
print(f"  dj={name}, mode={mode}, armed={c.handoff_armed}")
assert name == "Cara" and mode == "goodbye" and c.handoff_armed is True

print("=== TEST 3: next break -> hello (Junior takes over) ===")
name, mode = c.decide()
print(f"  dj={name}, mode={mode}, idx={c.current_dj_idx}, armed={c.handoff_armed}")
assert name == "Junior" and mode == "hello"
assert c.current_dj_idx == 1 and c.handoff_armed is False

print("=== TEST 4: back to normal as Junior ===")
name, mode = c.decide()
print(f"  dj={name}, mode={mode}")
assert name == "Junior" and mode is None

print("=== TEST 5: Junior shift expires -> wraps back to Cara ===")
c.shift_started_at = datetime.now() - timedelta(hours=4)
name, mode = c.decide()  # goodbye Junior
print(f"  goodbye: dj={name}, mode={mode}")
assert name == "Junior" and mode == "goodbye"
name, mode = c.decide()  # hello Cara (wrap-around)
print(f"  hello:   dj={name}, mode={mode}, idx={c.current_dj_idx}")
assert name == "Cara" and mode == "hello" and c.current_dj_idx == 0

print("\n=== TEST 6: single DJ (no roster) -> never handoff ===")
c2 = FakeController([{"name":"Solo","voice":"ara"}], shift_hours=3)
c2.shift_started_at = datetime.now() - timedelta(hours=10)
name, mode = c2.decide()
print(f"  dj={name}, mode={mode}")
assert mode is None

print("\n✓ ALL ROTATING-DJ TESTS PASSED")
print("log:", c.log)
