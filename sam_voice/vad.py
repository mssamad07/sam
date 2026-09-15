"""
Voice Activity Detection (VAD) module with EnergyVAD and SileroVAD fallback.
"""
import math
from abc import ABC, abstractmethod

import numpy as np


class BaseVAD(ABC):
    """Abstract base for Voice Activity Detection."""

    @abstractmethod
    def is_speech(self, chunk: bytes | np.ndarray) -> bool:
        """Determine if the provided audio chunk contains speech."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state/hangover counters."""
        pass


class EnergyVAD(BaseVAD):
    """
    RMS Energy-based VAD with adaptive background noise estimation and hangover frames.
    """

    def __init__(
        self,
        energy_threshold: float = 0.015,
        noise_adaptation_rate: float = 0.05,
        hangover_frames: int = 4,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.noise_adaptation_rate = noise_adaptation_rate
        self.hangover_frames = hangover_frames
        self._background_energy = energy_threshold * 0.5
        self._hangover_count = 0

    def _calculate_rms(self, chunk: bytes | np.ndarray) -> float:
        if isinstance(chunk, bytes):
            if len(chunk) < 2:
                return 0.0
            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            samples = chunk.astype(np.float32)
            if samples.max() > 1.0 or samples.min() < -1.0:
                samples = samples / 32768.0

        if len(samples) == 0:
            return 0.0
        mean_sq = float(np.mean(samples**2))
        return math.sqrt(mean_sq)

    def is_speech(self, chunk: bytes | np.ndarray) -> bool:
        rms = self._calculate_rms(chunk)
        dynamic_threshold = max(self.energy_threshold, self._background_energy * 2.2)

        if rms > dynamic_threshold:
            self._hangover_count = self.hangover_frames
            return True
        elif self._hangover_count > 0:
            self._hangover_count -= 1
            return True
        else:
            self._background_energy = (
                (1 - self.noise_adaptation_rate) * self._background_energy
                + self.noise_adaptation_rate * rms
            )
            return False

    def reset(self) -> None:
        self._hangover_count = 0
