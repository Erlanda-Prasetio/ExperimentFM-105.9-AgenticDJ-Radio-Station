"""Device-free mixer + virtual clock for offline (faster-than-real-time) rendering.

Nothing here touches the live radio: the live process keeps using
audio_engine.RealtimeRadioMixer and the real clock. The offline renderer patches
its own copy of the controller module's names to use these instead.

Design
------
* OfflineMixer subclasses RealtimeRadioMixer but opens no sound device. Instead,
  render(seconds) pumps the SAME _audio_callback in fixed-size blocks, so all the
  mixing/ducking/limiting logic is byte-identical to the live radio.
* Each DJ break + song is captured as one crash-safe "part":
      parts/part_00000.f32   (raw int16 little-endian PCM)
      parts/part_00000.f32.done   (created only when the part is complete)
  A crash or a pause therefore never corrupts earlier audio; resume just
  deletes any incomplete part and continues.
* VirtualClock stands in for the controller's `time` module: sleep(s) advances a
  virtual clock by s seconds AND renders s seconds of audio. So every wall-clock
  wait in the controller (ducking ramps, song length, shift clock) behaves
  exactly as on air - but the show renders as fast as TTS allows.
"""
import os
import glob
from datetime import datetime, timedelta

import numpy as np

from audio_engine import RealtimeRadioMixer


class OfflineMixer(RealtimeRadioMixer):
    """RealtimeRadioMixer with no sound device; render() drives the callback."""

    def __init__(self, *a, **kw):
        kw.setdefault("blocksize", 2048)
        super().__init__(*a, **kw)
        self._parts_dir = None
        self._part_chunks = []
        self._part_index = 0
        self._frames_total = 0
        self._recording = False

    # --- no device --------------------------------------------------------
    def start(self):
        self.running = True
        print("[OfflineMixer] ready (no audio device)")

    def stop(self):
        self.running = False

    # --- parts ------------------------------------------------------------
    def set_parts_dir(self, d):
        self._parts_dir = d
        os.makedirs(d, exist_ok=True)
        done = sorted(glob.glob(os.path.join(d, "part_*.f32.done")))
        self._part_index = len(done)
        for f in glob.glob(os.path.join(d, "part_*.f32")):
            if not os.path.exists(f + ".done"):
                print(f"[OfflineMixer] discarding incomplete part: {os.path.basename(f)}")
                try:
                    os.remove(f)
                except OSError:
                    pass
        print(f"[OfflineMixer] parts dir ready ({self._part_index} complete part(s))")

    def begin_part(self):
        self._part_chunks = []
        self._recording = True

    def end_part(self):
        self._recording = False
        if not self._part_chunks or not self._parts_dir:
            self._part_chunks = []
            return None
        data = np.concatenate(self._part_chunks, axis=0)
        path = os.path.join(self._parts_dir, f"part_{self._part_index:05d}.f32")
        s16 = (np.clip(data, -1.0, 1.0) * 32767.0).astype("<i2")
        with open(path, "wb") as f:
            f.write(s16.tobytes())
        open(path + ".done", "w").close()
        self._part_index += 1
        self._part_chunks = []
        return path

    # --- render -----------------------------------------------------------
    def render(self, seconds):
        n = int(round(seconds * self.samplerate))
        if n <= 0:
            return
        remaining = n
        while remaining > 0:
            frames = min(self.blocksize, remaining)
            buf = np.zeros((frames, self.channels), dtype=np.float32)
            self._audio_callback(buf, frames, None, None)
            if self._recording:
                self._part_chunks.append(buf.copy())
            remaining -= frames
            self._frames_total += frames

    def captured_seconds(self):
        return self._frames_total / self.samplerate


class VirtualClock:
    """Replaces the controller's `time` module. sleep() renders audio + advances time."""

    def __init__(self, start_dt: datetime = None):
        self.mixer = None
        self.virtual = 0.0
        self.start_dt = start_dt or datetime.now()

    def time(self):
        return self.virtual

    def monotonic(self):
        return self.virtual

    def perf_counter(self):
        return self.virtual

    def sleep(self, secs):
        if secs and secs > 0:
            if self.mixer is not None:
                self.mixer.render(secs)
            self.virtual += secs

    def now(self) -> datetime:
        return self.start_dt + timedelta(seconds=self.virtual)


class DatetimeShim:
    """Stands in for the `datetime` class inside the controller module."""

    def __init__(self, clock: VirtualClock):
        self._clock = clock

    def now(self, tz=None):
        return self._clock.now()

    @staticmethod
    def fromisoformat(s):
        return datetime.fromisoformat(s)

    @staticmethod
    def strptime(s, fmt):
        return datetime.strptime(s, fmt)


def install_patches(clock: VirtualClock, mixer_holder: dict):
    """Patch the controller MODULE (not the file) so it uses our offline pieces."""
    import agentic_dj_controller as ctl

    ctl.time = clock
    ctl.datetime = DatetimeShim(clock)

    def _mixer_factory(*a, **kw):
        m = OfflineMixer(*a, **kw)
        mixer_holder["m"] = m
        return m

    ctl.RealtimeRadioMixer = _mixer_factory

    from qwen_tts_engine import QwenTTSEngine
    ctl.TTSEngine = QwenTTSEngine
