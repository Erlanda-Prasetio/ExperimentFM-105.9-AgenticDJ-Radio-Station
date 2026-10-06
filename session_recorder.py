"""
Session recorder - captures the live on-air mix to a single MP3.

Design:
  - The audio callback (real-time thread) calls push(frames) which is O(1):
    it only enqueues the already-mixed float32 block. NO disk/encoding there,
    so the radio never glitches.
  - A dedicated writer thread drains the queue into an ffmpeg process via stdin
    (raw f32le PCM in -> MP3 out). ffmpeg does the encoding off the audio thread.
  - Output is MP3 CBR 192k, 44100 Hz, stereo, ID3v2.3 = maximally compatible
    (phones, car head units, SD cards). One file for the whole session.

If ffmpeg is missing or dies, recording stops but the radio keeps playing.
"""
import os
import subprocess
import threading
from queue import Queue, Empty, Full
from datetime import datetime

import numpy as np


class SessionRecorder:
    """Records the final on-air mix to a single MP3 file."""

    def __init__(self, output_path: str, samplerate: int = 44100, channels: int = 2,
                 bitrate: str = "192k", queue_blocks: int = 1000,
                 title: str = None, artist: str = "Experiment FM 105.9",
                 album: str = "Experiment FM 105.9"):
        self.output_path = output_path
        self.samplerate = int(samplerate)
        self.channels = int(channels)
        self.bitrate = bitrate
        self.title = title or f"Experiment FM 105.9 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.artist = artist
        self.album = album

        self._q: Queue = Queue(maxsize=queue_blocks)
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._frames_written = 0
        self._dropped_blocks = 0
        self._error: str | None = None

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    # ---- lifecycle -------------------------------------------------------
    def start(self):
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            # input: raw 32-bit float little-endian PCM from our stdin pipe
            "-f", "f32le", "-ar", str(self.samplerate), "-ac", str(self.channels),
            "-i", "pipe:0",
            # output: widely-compatible MP3
            "-c:a", "libmp3lame", "-b:a", self.bitrate,
            "-ar", str(self.samplerate), "-ac", str(self.channels),
            "-id3v2_version", "3",
            "-y", self.output_path,
        ]
        self._proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        self._running = True
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()
        print(f"[Record] 🔴 Recording -> {self.output_path}")
        print(f"[Record]    {self.bitrate} MP3, {self.samplerate}Hz, {self.channels}ch, ID3v2.3")

    def push(self, frames: np.ndarray):
        """Called from the audio callback. Must be fast and never raise.

        frames: (n_samples, channels) float32 in [-1, 1].
        We hand off the array by reference (the callback allocates a fresh array
        each call), so this is just a queue append.
        """
        if not self._running:
            return
        try:
            self._q.put_nowait(frames)
        except Full:
            self._dropped_blocks += 1  # disk/encoder too slow; keep the radio alive

    def _writer_loop(self):
        while self._running or not self._q.empty():
            try:
                block = self._q.get(timeout=0.5)
            except Empty:
                continue
            try:
                arr = np.ascontiguousarray(block, dtype=np.float32)
                self._proc.stdin.write(arr.tobytes())
                self._frames_written += arr.shape[0]
            except Exception as e:
                self._error = f"write failed: {e}"
                break
        # flush
        try:
            self._proc.stdin.close()
        except Exception:
            pass

    def stop(self):
        """Stop recording, finalize the MP3, and tag it."""
        if not self._running and self._proc is None:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=60)
        if self._proc:
            try:
                self._proc.wait(timeout=60)
            except Exception:
                self._proc.kill()
            if self._proc.returncode not in (0, None):
                err = b""
                try:
                    err = self._proc.stderr.read() or b""
                except Exception:
                    pass
                print(f"[Record] ffmpeg exited {self._proc.returncode}: {err.decode(errors='ignore')[:300]}")
        dur = self._frames_written / float(self.samplerate)
        if self._dropped_blocks:
            print(f"[Record] ⚠️ dropped {self._dropped_blocks} block(s) (encoder fell behind)")
        if self._error:
            print(f"[Record] ⚠️ {self._error}")
        print(f"[Record] ⏹ stopped - {dur/3600:.2f}h captured ({dur:.0f}s)")
        self._tag()
        return self.output_path

    def _tag(self):
        """Write ID3 tags so phones/cars show a proper title."""
        try:
            from mutagen.id3 import ID3, TIT2, TPE1, TALB
            from mutagen.mp3 import MP3
            try:
                tags = ID3(self.output_path)
            except Exception:
                tags = ID3()
            tags.add(TIT2(encoding=3, text=self.title))
            tags.add(TPE1(encoding=3, text=self.artist))
            tags.add(TALB(encoding=3, text=self.album))
            tags.save(self.output_path, v2_version=3)
            print(f"[Record] 🏷️ tagged: {self.title}")
        except Exception as e:
            print(f"[Record] tag skip: {e}")
