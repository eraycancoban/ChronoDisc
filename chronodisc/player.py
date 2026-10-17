"""
ChronoDisc Virtual Optical Needle Audio Player
Real-time low-latency audio stream engine with sample-accurate optical position tracking.
"""

import threading
import time
from typing import Optional, Callable, Tuple
import numpy as np
import sounddevice as sd

from .audio import samples_u8_to_audio_i16


class ChronoDiscPlayer:
    """
    Virtual Optical Needle audio engine.
    Streams decoded audio to sound output while providing real-time sample positions,
    VU meter levels, oscilloscope snapshots, and optical RGBA byte telemetry.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.audio_data: Optional[np.ndarray] = None  # int16 (N, 2)
        self.samples_u8: Optional[np.ndarray] = None  # uint8 (N, 4)
        self.total_samples: int = 0

        self._position: int = 0
        self._is_playing: bool = False
        self._volume: float = 1.0
        self._loop: bool = False

        self._stream: Optional[sd.OutputStream] = None
        self._lock = threading.Lock()

        # Telemetry cache for GUI
        self._latest_samples: np.ndarray = np.zeros((256, 2), dtype=np.int16)
        self._latest_peak_l: float = 0.0
        self._latest_peak_r: float = 0.0

        # State callback
        self.on_playback_end: Optional[Callable[[], None]] = None

    def load(self, samples_u8: np.ndarray, sample_rate: int = 44100):
        """
        Loads uint8 RGBA disc samples into the player.
        """
        self.stop()
        with self._lock:
            self.sample_rate = sample_rate
            self.samples_u8 = samples_u8
            self.audio_data = samples_u8_to_audio_i16(samples_u8)
            self.total_samples = len(self.audio_data)
            self._position = 0

    def play(self):
        """
        Starts or resumes audio playback.
        """
        if self.audio_data is None or self.total_samples == 0:
            return

        with self._lock:
            if self._is_playing:
                return

            if self._position >= self.total_samples:
                self._position = 0

            self._is_playing = True

            if self._stream is None or not self._stream.active:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=2,
                    dtype="int16",
                    callback=self._audio_callback,
                    finished_callback=self._finished_callback,
                    blocksize=1024
                )
                self._stream.start()

    def pause(self):
        """
        Pauses audio playback.
        """
        with self._lock:
            self._is_playing = False
        if self._stream and self._stream.active:
            self._stream.stop()

    def stop(self):
        """
        Stops audio playback and resets position to beginning.
        """
        with self._lock:
            self._is_playing = False
            self._position = 0
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def seek_sample(self, sample_idx: int):
        """
        Seeks immediately to sample index.
        """
        with self._lock:
            self._position = max(0, min(self.total_samples, sample_idx))

    def seek_normalized(self, norm_pos: float):
        """
        Seeks by normalized position in [0.0, 1.0].
        """
        target = int(norm_pos * self.total_samples)
        self.seek_sample(target)

    def set_volume(self, volume: float):
        """
        Sets playback volume in [0.0, 1.0].
        """
        self._volume = max(0.0, min(1.0, float(volume)))

    def set_loop(self, loop: bool):
        """
        Enables or disables loop playback.
        """
        self._loop = bool(loop)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def position(self) -> int:
        return self._position

    @property
    def current_time(self) -> float:
        return self._position / self.sample_rate if self.sample_rate > 0 else 0.0

    @property
    def duration(self) -> float:
        return self.total_samples / self.sample_rate if self.sample_rate > 0 else 0.0

    def get_current_telemetry(self) -> dict:
        """
        Returns real-time telemetry: current sample index, RGBA byte values,
        left/right int16 voltages, peak levels, and waveform chunk.
        """
        with self._lock:
            pos = min(self._position, max(0, self.total_samples - 1))
            if self.samples_u8 is not None and len(self.samples_u8) > pos:
                rgba = self.samples_u8[pos]
            else:
                rgba = np.array([0, 0, 0, 0], dtype=np.uint8)

            if self.audio_data is not None and len(self.audio_data) > pos:
                sample_lr = self.audio_data[pos]
            else:
                sample_lr = np.array([0, 0], dtype=np.int16)

            return {
                "position": pos,
                "total_samples": self.total_samples,
                "time_sec": pos / self.sample_rate if self.sample_rate > 0 else 0.0,
                "duration_sec": self.duration,
                "is_playing": self._is_playing,
                "rgba": (int(rgba[0]), int(rgba[1]), int(rgba[2]), int(rgba[3])),
                "sample_left": int(sample_lr[0]),
                "sample_right": int(sample_lr[1]),
                "peak_left": self._latest_peak_l,
                "peak_right": self._latest_peak_r,
                "waveform": self._latest_samples.copy()
            }

    def _audio_callback(self, outdata, frames, time_info, status):
        with self._lock:
            if not self._is_playing or self.audio_data is None:
                outdata.fill(0)
                return

            end_pos = self._position + frames
            if end_pos <= self.total_samples:
                chunk = self.audio_data[self._position:end_pos]
                self._position = end_pos
            else:
                # Track ended
                available = self.total_samples - self._position
                chunk = np.zeros((frames, 2), dtype=np.int16)
                if available > 0:
                    chunk[:available] = self.audio_data[self._position:]

                if self._loop:
                    remaining = frames - available
                    self._position = remaining
                    if remaining <= self.total_samples:
                        chunk[available:] = self.audio_data[:remaining]
                else:
                    self._position = self.total_samples
                    self._is_playing = False

            # Apply volume
            if self._volume != 1.0:
                chunk = (chunk.astype(np.float32) * self._volume).astype(np.int16)

            outdata[:] = chunk

            # Update visualizer cache
            n_cache = min(frames, 256)
            self._latest_samples = chunk[-n_cache:]
            self._latest_peak_l = float(np.max(np.abs(chunk[:, 0]))) / 32768.0
            self._latest_peak_r = float(np.max(np.abs(chunk[:, 1]))) / 32768.0

    def _finished_callback(self):
        if not self._loop and self.on_playback_end:
            self.on_playback_end()

