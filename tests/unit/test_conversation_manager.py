"""
Unit tests for ConversationManager session lifecycle and context assembly.
"""
from sam_core.ai.models import MessageRole
from sam_core.conversation.manager import ConversationManager


def test_session_lifecycle_and_context_assembly():
    cm = ConversationManager(max_context_messages=10)
    session = cm.get_or_create_session("sess-1")
    assert session.session_id == "sess-1"

    # Add user message
    u_msg = cm.add_user_message("Sam, kaise ho?", session_id="sess-1")
    assert u_msg.role == MessageRole.USER
    assert session.detected_language == "Hinglish"

    # Add assistant message
    a_msg = cm.add_assistant_message("Main badhiya hoon, Boss!", session_id="sess-1")
    assert a_msg.role == MessageRole.ASSISTANT

    # Context assembly
    context = cm.get_full_context(session_id="sess-1")
    assert len(context) == 3  # System prompt + User msg + Assistant msg
    assert context[0].role == MessageRole.SYSTEM
    assert "Sam" in context[0].content


def test_sliding_window_budgeting():
    cm = ConversationManager(max_context_messages=4)
    session_id = "sess-budget"

    # Add 6 messages
    for i in range(6):
        cm.add_user_message(f"Message {i}", session_id=session_id)

    sess = cm.get_or_create_session(session_id)
    # Should be trimmed to 4 most recent messages
    assert len(sess.messages) == 4
    assert sess.messages[-1].content == "Message 5"
    assert sess.messages[0].content == "Message 2"


def test_clear_session():
    cm = ConversationManager()
    cm.add_user_message("test", session_id="sess-clear")
    assert len(cm.get_or_create_session("sess-clear").messages) == 1

    cm.clear_session("sess-clear")
    assert len(cm.get_or_create_session("sess-clear").messages) == 0
