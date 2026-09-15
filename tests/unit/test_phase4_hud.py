"""
Unit tests for Sam Phase 4 Windows HUD client and UI.
"""

from sam_clients.windows_hud.gui import HUDWindow
from sam_clients.windows_hud.hud_client import HUDClient


def test_hud_client_event_listeners():
    client = HUDClient()
    events_received = []

    client.on("voice.state_changed", lambda d: events_received.append(d))
    client._handle_server_event("voice.state_changed", {"new_state": "listening"})

    assert client.current_state == "listening"
    assert len(events_received) == 1
    assert events_received[0]["new_state"] == "listening"


def test_hud_client_transcription_and_response_tracking():
    client = HUDClient()
    client._handle_server_event("voice.transcription", {"text": "Hey Sam, check battery"})
    assert client.last_transcription == "Hey Sam, check battery"

    client._handle_server_event("voice.tts_started", {"text": "Battery is at 85%, Boss."})
    assert client.last_response == "Battery is at 85%, Boss."


def test_hud_window_initialization():
    client = HUDClient()
    hud = HUDWindow(hud_client=client)

    # Verify Tkinter widget structure can be constructed
    root = hud.build_ui()
    assert root is not None
    assert root.title() == "Sam AI Assistant"

    # State update
    hud.update_state("speaking")
    assert "Speaking" in hud._status_label.cget("text")

    # Transcription update
    hud.update_transcription("Open calculator")
    assert hud._transcription_label.cget("text") == "Open calculator"

    # Permission prompt
    hud.show_permission_prompt({"tool_name": "kill_process", "arguments": {"process_name": "notepad.exe"}})
    assert "kill_process" in hud._permission_desc.cget("text")

    hud.hide_permission_prompt()

    # Destroy window cleanly after test
    root.destroy()
