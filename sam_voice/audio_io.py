"""
Audio I/O management with support for cancellation and barge-in.
"""
import asyncio
from typing import Any

from sam_core.logger import get_logger

logger = get_logger("voice.audio_io")


class AudioPlayer:
    """Async audio player capable of immediate cancellation upon barge-in."""

    def __init__(self) -> None:
        self._is_playing = False
        self._current_task: asyncio.Task[Any] | None = None
        self._interrupted = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def was_interrupted(self) -> bool:
        return self._interrupted

    async def play(self, audio_data: bytes, duration_seconds: float = 0.1) -> bool:
        """
        Play audio asynchronously.
        Returns True if played to completion, False if interrupted/cancelled.
        """
        self._is_playing = True
        self._interrupted = False

        async def _playback_worker() -> None:
            await asyncio.sleep(duration_seconds)

        self._current_task = asyncio.create_task(_playback_worker())
        try:
            await self._current_task
            return True
        except asyncio.CancelledError:
            self._interrupted = True
            logger.info("Audio playback interrupted (barge-in)")
            return False
        finally:
            self._is_playing = False
            self._current_task = None

    def stop(self) -> None:
        """Immediately cut off audio playback (barge-in)."""
        if self._current_task and not self._current_task.done():
            self._interrupted = True
            self._current_task.cancel()
        self._is_playing = False
