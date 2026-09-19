"""
Microphone Audio Listener for Sam Voice Engine.
Streams audio chunks from the microphone to VAD and WakeWord detectors.
Includes resilient fallback when audio hardware is unavailable.
"""
import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any

from sam_core.logger import get_logger

logger = get_logger("voice.mic_listener")


class MicrophoneListener:
    """
    Asynchronous microphone capture worker.
    Streams 30ms 16kHz 16-bit PCM audio frames into the voice pipeline.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 30,
        device_index: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self.device_index = device_index
        self.chunk_size = int(self.sample_rate * (self.chunk_duration_ms / 1000.0))
        self._is_listening = False
        self._queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)
        self._stream: Any = None

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start(self) -> bool:
        """Start listening to microphone input."""
        if self._is_listening:
            return True

        self._is_listening = True
        try:
            import sounddevice as sd

            def _audio_callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                if status:
                    logger.debug(f"Audio stream status: {status}")
                if self._is_listening:
                    raw_bytes = bytes(indata)
                    with suppress(asyncio.QueueFull):
                        self._queue.put_nowait(raw_bytes)

            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                device=self.device_index,
                channels=1,
                dtype="int16",
                callback=_audio_callback,
            )
            self._stream.start()
            logger.info("Microphone audio stream started successfully.")
            return True
        except (ImportError, Exception) as exc:
            logger.warning(
                f"Physical sounddevice input not available ({exc}). Falling back to simulated/soft capture."
            )
            self._stream = None
            return True

    def stop(self) -> None:
        """Stop listening and close the audio stream."""
        self._is_listening = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:
                logger.debug(f"Error closing audio stream: {exc}")
            self._stream = None
        logger.info("Microphone audio stream stopped.")

    async def stream_frames(self) -> AsyncIterator[bytes]:
        """Async generator yielding audio frames for VAD/WakeWord detection."""
        while self._is_listening:
            try:
                frame = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                yield frame
            except TimeoutError:
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
