"""
Unit tests for Sam Phase 4 Voice Engine.
Tests State Machine transitions, VAD, wake-word, STT, TTS, AudioPlayer, and barge-in pipeline.
"""
import numpy as np
import pytest

from sam_core.ai.mock_provider import MockLLMProvider
from sam_core.ai.router import llm_router
from sam_core.conversation.orchestrator import AgentOrchestrator
from sam_voice.audio_io import AudioPlayer
from sam_voice.pipeline import VoicePipeline
from sam_voice.state_machine import InvalidVoiceStateTransition, VoiceStateMachine
from sam_voice.states import VoiceState
from sam_voice.stt.cloud_stt import MockSTTProvider
from sam_voice.tts.edge_tts_provider import EdgeTTSProvider
from sam_voice.tts.mock_tts_provider import MockTTSProvider
from sam_voice.vad import EnergyVAD
from sam_voice.wake_word import MockWakeWordDetector, OpenWakeWordDetector


@pytest.mark.asyncio
async def test_voice_state_machine_valid_transitions():
    sm = VoiceStateMachine()
    assert sm.current_state == VoiceState.IDLE

    await sm.transition_to(VoiceState.WAKE_DETECTED, "wake_word")
    assert sm.current_state == VoiceState.WAKE_DETECTED

    await sm.transition_to(VoiceState.LISTENING, "ready_to_record")
    assert sm.current_state == VoiceState.LISTENING

    await sm.transition_to(VoiceState.PROCESSING, "transcribing")
    assert sm.current_state == VoiceState.PROCESSING

    await sm.transition_to(VoiceState.SPEAKING, "replying")
    assert sm.current_state == VoiceState.SPEAKING

    # Test interruption (barge-in)
    await sm.transition_to(VoiceState.INTERRUPTED, "user_spoke")
    assert sm.current_state == VoiceState.INTERRUPTED

    await sm.transition_to(VoiceState.LISTENING, "listen_again")
    assert sm.current_state == VoiceState.LISTENING

    await sm.reset("reset_test")
    assert sm.current_state == VoiceState.IDLE


@pytest.mark.asyncio
async def test_voice_state_machine_invalid_transition_raises():
    sm = VoiceStateMachine()
    assert sm.current_state == VoiceState.IDLE

    # IDLE directly to SPEAKING is illegal
    with pytest.raises(InvalidVoiceStateTransition):
        await sm.transition_to(VoiceState.SPEAKING, "illegal")


def test_energy_vad_speech_detection():
    vad = EnergyVAD(energy_threshold=0.01, hangover_frames=2)

    # Silence (all zeros)
    silence = np.zeros(1600, dtype=np.int16).tobytes()
    assert not vad.is_speech(silence)

    # Loud speech / sine wave
    t = np.linspace(0, 0.1, 1600)
    loud_signal = (np.sin(2 * np.pi * 440 * t) * 20000).astype(np.int16).tobytes()
    assert vad.is_speech(loud_signal)

    # Hangover frame keeps speech active for 2 frames of silence
    assert vad.is_speech(silence)
    assert vad.is_speech(silence)
    # 3rd frame drops back to silence
    assert not vad.is_speech(silence)


def test_wake_word_detectors():
    mock_ww = MockWakeWordDetector(target_word="hey sam")
    chunk = b"\x00" * 3200

    # Default is not detected
    det, word, conf = mock_ww.process_audio(chunk)
    assert not det

    # Trigger mock result
    mock_ww.set_next_result(True, "hey sam", 0.98)
    det, word, conf = mock_ww.process_audio(chunk)
    assert det
    assert word == "hey sam"
    assert conf == 0.98

    # OpenWakeWord fallback handles audio gracefully
    oww = OpenWakeWordDetector(target_word="hey sam")
    det2, _, _ = oww.process_audio(chunk)
    assert not det2


def test_edge_tts_voice_selection():
    edge_provider = EdgeTTSProvider()

    # Devanagari Hindi text
    hi_voice = edge_provider.select_voice("नमस्ते, आप कैसे हैं?")
    assert hi_voice == "hi-IN-MadhurNeural"

    # Hinglish text
    hinglish_voice = edge_provider.select_voice("Haan Boss, main theek hoon.")
    assert hinglish_voice == "en-IN-PrabhatNeural"

    # Standard English
    en_voice = edge_provider.select_voice("All systems operational.")
    assert en_voice == "en-IN-PrabhatNeural"


@pytest.mark.asyncio
async def test_audio_player_barge_in_cancellation():
    player = AudioPlayer()
    assert not player.is_playing

    # Start playback of a 2-second audio simulation
    import asyncio
    play_task = asyncio.create_task(player.play(b"audio", duration_seconds=2.0))
    await asyncio.sleep(0.05)
    assert player.is_playing

    # Cut off with barge-in stop()
    player.stop()
    completed = await play_task
    assert not completed
    assert player.was_interrupted
    assert not player.is_playing


@pytest.mark.asyncio
async def test_voice_pipeline_full_turn():
    sm = VoiceStateMachine()
    ww = MockWakeWordDetector()
    vad = EnergyVAD()
    stt = MockSTTProvider(default_text="What time is it?")
    tts = MockTTSProvider()

    llm = MockLLMProvider("mock_voice")
    llm.queue_response("It is currently 10:00 AM, Boss.")
    llm_router.register(llm)
    llm_router.set_default_provider("mock_voice")
    orchestrator = AgentOrchestrator()
    player = AudioPlayer()

    pipeline = VoicePipeline(
        state_machine=sm,
        wake_detector=ww,
        vad=vad,
        stt=stt,
        tts=tts,
        orchestrator=orchestrator,
        player=player,
    )

    # Trigger wake word
    await pipeline.process_wake_trigger("hey sam", 0.99)
    assert pipeline.current_state == VoiceState.LISTENING

    # Process utterance
    response = await pipeline.process_utterance(b"audio_bytes")
    assert "Boss" in response
    assert pipeline.current_state == VoiceState.IDLE
    assert len(tts.synthesized_prompts) == 1
