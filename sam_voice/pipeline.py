"""
Unified Voice Pipeline for Sam.
Integrates StateMachine, Wake Word Detector, VAD, STT, Agent Orchestrator, TTS, and AudioPlayer.
"""
import asyncio
from typing import Any

from sam_core.conversation.orchestrator import AgentOrchestrator
from sam_core.events.bus import EventBus, get_event_bus
from sam_core.events.types import Event
from sam_core.logger import get_logger
from sam_voice.audio_io import AudioPlayer
from sam_voice.events import (
    VOICE_BARGE_IN,
    VOICE_TRANSCRIPTION,
    VOICE_TTS_STARTED,
    VOICE_WAKE_DETECTED,
    BargeInEvent,
    TranscriptionEvent,
    WakeDetectedEvent,
)
from sam_voice.state_machine import VoiceStateMachine
from sam_voice.states import VoiceState
from sam_voice.stt.base import BaseSTTProvider
from sam_voice.tts.base import BaseTTSProvider
from sam_voice.vad import BaseVAD
from sam_voice.wake_word import BaseWakeWordDetector

logger = get_logger("voice.pipeline")


class VoicePipeline:
    """Coordinates voice interaction lifecycle."""

    def __init__(
        self,
        state_machine: VoiceStateMachine,
        wake_detector: BaseWakeWordDetector,
        vad: BaseVAD,
        stt: BaseSTTProvider,
        tts: BaseTTSProvider,
        orchestrator: AgentOrchestrator,
        player: AudioPlayer | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.state_machine = state_machine
        self.wake_detector = wake_detector
        self.vad = vad
        self.stt = stt
        self.tts = tts
        self.orchestrator = orchestrator
        self.player = player or AudioPlayer()
        self.event_bus = event_bus or get_event_bus()

        self._is_running = False
        self._loop_task: asyncio.Task[Any] | None = None

    @property
    def current_state(self) -> VoiceState:
        return self.state_machine.current_state

    async def process_wake_trigger(self, wake_word: str = "hey sam", confidence: float = 0.95) -> None:
        """Manually or externally trigger wake detection."""
        await self.state_machine.transition_to(VoiceState.WAKE_DETECTED, reason="wake_word_detected")
        await self.event_bus.publish(
            Event(
                event_type=VOICE_WAKE_DETECTED,
                payload=WakeDetectedEvent(
                    wake_word=wake_word,
                    confidence=confidence,
                ).model_dump(),
                source="voice.pipeline",
            )
        )
        await self.state_machine.transition_to(VoiceState.LISTENING, reason="wake_acknowledged")

    async def handle_barge_in(self) -> None:
        """Triggered when user speech is detected during speech playback."""
        if self.state_machine.current_state == VoiceState.SPEAKING:
            logger.info("Barge-in triggered: cutting off speech")
            self.player.stop()
            await self.state_machine.transition_to(VoiceState.INTERRUPTED, reason="barge_in")
            await self.event_bus.publish(
                Event(
                    event_type=VOICE_BARGE_IN,
                    payload=BargeInEvent(reason="barge_in").model_dump(),
                    source="voice.pipeline",
                )
            )
            await self.state_machine.transition_to(VoiceState.LISTENING, reason="post_barge_in_listen")

    async def process_utterance(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> str:
        """Full turn: STT -> Orchestrator -> TTS -> Playback."""
        if self.state_machine.current_state != VoiceState.LISTENING:
            await self.state_machine.transition_to(VoiceState.LISTENING, reason="direct_utterance_input")

        await self.state_machine.transition_to(VoiceState.PROCESSING, reason="transcribing_audio")
        transcription = await self.stt.transcribe(audio_data, sample_rate, language=language)

        await self.event_bus.publish(
            Event(
                event_type=VOICE_TRANSCRIPTION,
                payload=TranscriptionEvent(
                    text=transcription.text,
                    confidence=transcription.confidence,
                    language=transcription.language,
                    latency_ms=0.0,
                ).model_dump(),
                source="voice.pipeline",
            )
        )

        # Process conversational turn through orchestrator
        orchestrator_res = await self.orchestrator.process_user_turn(transcription.text)

        if orchestrator_res.confirmation_required:
            await self.state_machine.transition_to(
                VoiceState.WAITING_FOR_PERMISSION,
                reason="action_requires_approval",
            )
            return orchestrator_res.response_text

        # Synthesize and speak
        await self.state_machine.transition_to(VoiceState.SPEAKING, reason="synthesizing_response")
        await self.event_bus.publish(
            Event(
                event_type=VOICE_TTS_STARTED,
                payload={"text": orchestrator_res.response_text},
                source="voice.pipeline",
            )
        )

        synth_res = await self.tts.synthesize(orchestrator_res.response_text)
        if synth_res.audio_bytes:
            completed = await self.player.play(synth_res.audio_bytes, synth_res.duration_seconds)
            if not completed:
                # Interrupted via barge-in
                return orchestrator_res.response_text

        await self.state_machine.transition_to(VoiceState.IDLE, reason="utterance_completed")
        return orchestrator_res.response_text
