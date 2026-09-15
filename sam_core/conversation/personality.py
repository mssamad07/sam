"""
Centralized Sam Personality and Persona Specification.
Defines Sam's core identity, language adaptation, and behavioral guardrails.
"""
from enum import StrEnum

from sam_core.conversation.emotional_state import EmotionalContext, emotional_state_manager


class LanguagePreference(StrEnum):
    """Supported interaction languages."""
    AUTO = "auto"
    ENGLISH = "english"
    HINDI = "hindi"
    HINGLISH = "hinglish"


class SamPersonality:
    """Sam's persona, tone guidelines, and system prompt generator."""

    def __init__(
        self,
        user_nickname: str = "Boss",
        preferred_language: LanguagePreference = LanguagePreference.AUTO,
    ):
        self.user_nickname = user_nickname
        self.preferred_language = preferred_language

    def detect_language(self, text: str) -> str:
        """
        Lightweight heuristic to detect language: English, Hindi, or Hinglish.
        """
        if not text:
            return "English"

        # Check for Devanagari script
        devanagari_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        if devanagari_chars > len(text) * 0.2:
            return "Hindi"

        # Check common Hinglish markers
        hinglish_words = {
            "kya", "hai", "hain", "kaise", "karo", "karna", "batao", "kar", "ho", "nahi", "tha", "thi",
            "raha", "rahe", "rahi", "kaafi", "yaar", "theek", "badhiya", "chal", "chalo", "dekh", "dekho",
            "pe", "mein", "bhi", "toh", "mera", "meri", "mere", "hum", "aap", "tum", "shuru", "band", "ruk",
            "yeh", "woh", "bana", "banao", "do", "diya", "de", "jaldi", "se", "ko", "par", "ek", "kuch",
            "aur", "sab", "ab", "aaye", "aaya", "hua", "huye", "gaya", "gayi", "liye", "bhai"
        }
        words = set(text.lower().replace("?", " ").replace("!", " ").replace(".", " ").replace(",", " ").split())
        matched = words.intersection(hinglish_words)
        if len(matched) >= 1:
            return "Hinglish"

        return "English"

    def build_system_prompt(
        self,
        detected_language: str | None = None,
        emotional_context: EmotionalContext | None = None,
    ) -> str:
        """
        Construct the foundational system prompt embodying Sam.
        """
        ctx = emotional_context or emotional_state_manager.context
        lang = detected_language or "English or Hinglish as spoken by the user"

        return f"""You are Sam, a serious, capable, and trusted personal AI assistant and digital companion.

CORE IDENTITY:
- You address the user as "{self.user_nickname}".
- You are a reliable best friend, trusted advisor, and capable digital operator.
- Your personality is calm, intelligent, observant, honest, direct, and slightly witty when appropriate.
- You are never excessively enthusiastic, robotic, or preachy. Never use canned disclaimers like "As an AI language model...".
- You communicate naturally in Hindi, Hinglish, or English, dynamically mirroring the language and tone used by {self.user_nickname}.

NON-NEGOTIABLE PRINCIPLES:
1. TRUTHFULNESS: Never claim an operation succeeded unless the tool or underlying system actually confirmed success. If a tool failed or returned an error, state the failure plainly and constructively.
2. DISCIPLINED WORKFLOW: Follow Observe -> Think -> Plan -> Act -> Verify -> Report.
3. SECURITY & PERMISSIONS: Sensitive actions (such as file deletion, killing processes, shell commands, or purchases) strictly require confirmation. Never attempt to bypass the permission manager.
4. NO FAKE AUTONOMY: Never pretend to perform actions outside the tools available to you.

CURRENT INTERACTION CONTEXT:
- Active User Language Style: {lang}
- Current Emotional State: {ctx.current_state.value.upper()}
- Tone Guidance: {ctx.tone_guidance}

Respond naturally to {self.user_nickname}.
"""


# Global singleton instance
sam_personality = SamPersonality()
