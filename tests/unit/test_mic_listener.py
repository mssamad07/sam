"""
Unit tests for MicrophoneListener.
"""
from sam_voice.mic_listener import MicrophoneListener


def test_mic_listener_lifecycle():
    listener = MicrophoneListener()
    assert listener.is_listening is False
    success = listener.start()
    assert success is True
    assert listener.is_listening is True
    listener.stop()
    assert listener.is_listening is False
