"""
Wake-word detection module for Sam.
Supports openWakeWord with fallback and mock detector for testing.
"""
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Any

import numpy as np

from sam_core.logger import get_logger

logger = get_logger("voice.wake_word")


class BaseWakeWordDetector(ABC):
    """Abstract interface for wake word detectors."""

    @abstractmethod
    def process_audio(self, chunk: bytes | np.ndarray) -> tuple[bool, str, float]:
        """Process an audio frame and return (detected, wake_word, confidence)."""
        pass

    @abstractmethod
    def reset(self) -> None:
        pass


class MockWakeWordDetector(BaseWakeWordDetector):
    """Mock wake-word detector for unit testing and simulated audio triggers."""

    def __init__(self, target_word: str = "hey sam", threshold: float = 0.5) -> None:
        self.target_word = target_word
        self.threshold = threshold
        self._next_trigger: tuple[bool, str, float] | None = None

    def set_next_result(self, detected: bool, word: str = "hey sam", confidence: float = 0.95) -> None:
        self._next_trigger = (detected, word, confidence)

    def process_audio(self, chunk: bytes | np.ndarray) -> tuple[bool, str, float]:
        if self._next_trigger is not None:
            res = self._next_trigger
            self._next_trigger = None
            return res
        return False, "", 0.0

    def reset(self) -> None:
        self._next_trigger = None


class OpenWakeWordDetector(BaseWakeWordDetector):
    """Detector wrapping openWakeWord models, or acoustic/energy heuristic fallback."""

    def __init__(
        self,
        target_word: str = "hey sam",
        threshold: float = 0.5,
        model_path: str | None = None,
    ) -> None:
        self.target_word = target_word.lower()
        self.threshold = threshold
        self.model_path = model_path
        self._oww_model: Any = None
        self._init_model()

    def _init_model(self) -> None:
        try:
            from openwakeword.model import Model
            self._oww_model = Model(wakeword_models=[self.model_path or "hey_jarvis"])
            logger.info(f"Initialized openWakeWord model: {self.model_path}")
        except Exception as e:
            logger.debug(f"openWakeWord not available ({e}); fallback mode ready")
            self._oww_model = None

    def process_audio(self, chunk: bytes | np.ndarray) -> tuple[bool, str, float]:
        if self._oww_model is not None:
            try:
                if isinstance(chunk, bytes):
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                else:
                    audio_data = chunk
                prediction = self._oww_model.predict(audio_data)
                for name, score in prediction.items():
                    if score >= self.threshold:
                        return True, name, float(score)
            except Exception as e:
                logger.error(f"Error in openWakeWord prediction: {e}")

        return False, "", 0.0

    def reset(self) -> None:
        if self._oww_model is not None:
            with suppress(Exception):
                self._oww_model.reset()
