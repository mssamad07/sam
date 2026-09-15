"""
Unit tests for Sam personality, language adaptation, and system prompt generation.
"""
from sam_core.conversation.personality import SamPersonality


def test_language_detection():
    personality = SamPersonality()

    # English
    assert personality.detect_language("Can you please check the weather today?") == "English"

    # Devanagari Hindi
    assert personality.detect_language("नमस्ते सैम, आप कैसे हैं?") == "Hindi"

    # Hinglish
    assert personality.detect_language("Sam, Spotify pe gaana play karo na please") == "Hinglish"
    assert personality.detect_language("Boss, yeh repo bana do jaldi se") == "Hinglish"


def test_custom_nickname_and_prompt_assembly():
    personality = SamPersonality(user_nickname="Sir")
    prompt = personality.build_system_prompt(detected_language="Hinglish")

    assert "Sir" in prompt
    assert "TRUTHFULNESS" in prompt
    assert "Observe -> Think -> Plan -> Act -> Verify -> Report" in prompt
    assert "Hinglish" in prompt
