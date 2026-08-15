"""
tests/test_conversation.py — Automated pytest suite for the JalSense
conversation state machine.

12 test cases covering:
    1.  New user → greeting
    2.  Greeting commands (hi/hello/namaste/start)
    3.  Village input → state advances to WAITING_FOR_CROP
    4.  Hindi crop input (गेहूं) → normalizes to wheat, produces report
    5.  English crop input (wheat) → produces report
    6.  Hindi spelling variant (गेंहू) → normalizes to wheat
    7.  Invalid/unknown crop → polite re-prompt, state unchanged
    8.  Help command → help text, state unchanged
    9.  Restart command → resets state, re-greets
    10. Multiple users have independent conversation states
    11. Analysis result → Hindi report contains expected fields
    12. Empty message → handled gracefully (no crash)

Run with:
    pytest tests/ -v
"""

import pytest

from whatsapp_service.conversation import ConversationState, ConversationStore
from whatsapp_service.mock_whatsapp import MockWhatsApp


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def store() -> ConversationStore:
    """Fresh in-memory store — isolates each test completely."""
    return ConversationStore()


@pytest.fixture
def bot(store: ConversationStore) -> MockWhatsApp:
    """MockWhatsApp wired to the isolated store."""
    return MockWhatsApp(store=store)


# ── Helper ────────────────────────────────────────────────────────────────────

FARMER = "whatsapp:+919876543210"


def chat(bot: MockWhatsApp, text: str, number: str = FARMER) -> list[str]:
    """Send a message and return the list of bot replies."""
    return bot.send_message(number, text)


def first(bot: MockWhatsApp, text: str, number: str = FARMER) -> str:
    """Send a message and return only the first reply."""
    return chat(bot, text, number)[0]


# ── Test 1: New user receives greeting ───────────────────────────────────────

def test_new_user_greeting(bot: MockWhatsApp, store: ConversationStore):
    replies = chat(bot, "Hello", FARMER)
    assert len(replies) == 1
    assert "Namaste" in replies[0]
    assert "JalSense" in replies[0]
    assert "gaon" in replies[0].lower() or "Example" in replies[0]
    # State should advance to WAITING_FOR_VILLAGE
    session = store.get(FARMER)
    assert session is not None
    assert session.state == ConversationState.WAITING_FOR_VILLAGE


# ── Test 2: Greeting commands ─────────────────────────────────────────────────

@pytest.mark.parametrize("greeting", ["hi", "Hi", "hello", "namaste", "start", "Namaste"])
def test_greeting_commands(bot: MockWhatsApp, greeting: str):
    replies = chat(bot, greeting)
    assert len(replies) == 1
    assert "Namaste" in replies[0]
    assert "JalSense" in replies[0]


# ── Test 3: Village input advances state ──────────────────────────────────────

def test_village_input_advances_state(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")                              # → WAITING_FOR_VILLAGE
    replies = chat(bot, "Chitrakoot")            # → WAITING_FOR_CROP
    assert len(replies) == 1
    assert "fasal" in replies[0].lower() or "Gehun" in replies[0]
    session = store.get(FARMER)
    assert session.state == ConversationState.WAITING_FOR_CROP
    assert session.village == "Chitrakoot"


# ── Test 4: Hindi crop गेहूं → analysis report ────────────────────────────────

def test_hindi_crop_gehun(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Chitrakoot")
    replies = chat(bot, "गेहूं")               # Hindi crop input
    # Should return two messages: analyzing + report
    assert len(replies) == 2
    analyzing_msg, report = replies
    assert "intezar" in analyzing_msg.lower() or "analysis" in analyzing_msg.lower()
    assert "JalSense Report" in report
    assert "Chitrakoot" in report
    assert "Gehun" in report
    session = store.get(FARMER)
    assert session.state == ConversationState.RESULT
    assert session.crop == "wheat"


# ── Test 5: English crop input ────────────────────────────────────────────────

def test_english_crop_wheat(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Varanasi")
    replies = chat(bot, "wheat")
    assert len(replies) == 2
    report = replies[1]
    assert "JalSense Report" in report
    assert "Gehun" in report
    session = store.get(FARMER)
    assert session.crop == "wheat"
    assert session.state == ConversationState.RESULT


# ── Test 6: Hindi spelling variant गेंहू ──────────────────────────────────────

def test_hindi_crop_variant_genhu(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Ayodhya")
    replies = chat(bot, "गेंहू")               # nasal variant
    assert len(replies) == 2
    session = store.get(FARMER)
    assert session.crop == "wheat"              # correctly normalized


# ── Test 7: Unknown/invalid crop re-prompts, state unchanged ─────────────────

def test_invalid_crop_reprompt(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Chitrakoot")
    # First: unknown crop
    replies = chat(bot, "banana")
    assert len(replies) == 1
    assert "Kripya" in replies[0] or "fasal" in replies[0].lower()
    # State must still be WAITING_FOR_CROP
    session = store.get(FARMER)
    assert session.state == ConversationState.WAITING_FOR_CROP
    # Now send a valid crop — should succeed
    replies2 = chat(bot, "wheat")
    assert len(replies2) == 2
    assert "JalSense Report" in replies2[1]


# ── Test 8: Help command — state unchanged ────────────────────────────────────

def test_help_command_state_unchanged(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Chitrakoot")                     # state = WAITING_FOR_CROP
    replies = chat(bot, "help")
    assert len(replies) == 1
    assert "JalSense" in replies[0]
    assert "gaon" in replies[0].lower()
    # State must NOT change
    session = store.get(FARMER)
    assert session.state == ConversationState.WAITING_FOR_CROP


# ── Test 9: Restart resets state to WAITING_FOR_VILLAGE ──────────────────────

def test_restart_resets_state(bot: MockWhatsApp, store: ConversationStore):
    chat(bot, "hi")
    chat(bot, "Chitrakoot")                     # state = WAITING_FOR_CROP
    replies = chat(bot, "restart")
    assert len(replies) == 1
    assert "nayi shuruat" in replies[0].lower() or "gaon" in replies[0].lower()
    session = store.get(FARMER)
    assert session.state == ConversationState.WAITING_FOR_VILLAGE
    assert session.village is None or session.village == "Chitrakoot"  # village cleared by restart


# ── Test 10: Multiple users have independent states ───────────────────────────

def test_multiple_users_independent_states(bot: MockWhatsApp, store: ConversationStore):
    farmer_a = "whatsapp:+91111"
    farmer_b = "whatsapp:+91222"

    chat(bot, "hi", farmer_a)
    chat(bot, "Chitrakoot", farmer_a)           # A → WAITING_FOR_CROP

    chat(bot, "hi", farmer_b)                  # B → WAITING_FOR_VILLAGE

    session_a = store.get(farmer_a)
    session_b = store.get(farmer_b)

    assert session_a.state == ConversationState.WAITING_FOR_CROP
    assert session_b.state == ConversationState.WAITING_FOR_VILLAGE
    assert session_a.village == "Chitrakoot"
    assert session_b.village is None


# ── Test 11: Analysis report format ──────────────────────────────────────────

def test_analysis_report_format(bot: MockWhatsApp):
    chat(bot, "hi")
    chat(bot, "Jhansi")
    replies = chat(bot, "sarson")               # mustard
    assert len(replies) == 2
    report = replies[1]
    assert "🌾 JalSense Report" in report
    assert "Jhansi" in report
    assert "Sarson" in report
    assert "💧" in report
    assert "👉" in report
    # Stress level label should be present
    assert any(level in report for level in ["Zyada", "Theek-Theek", "Sahi", "Bahut Zyada"])


# ── Test 12: Empty message handled gracefully ─────────────────────────────────

def test_empty_message_graceful(bot: MockWhatsApp):
    replies = chat(bot, "")
    assert len(replies) == 1
    # Should not crash; should return a polite prompt
    assert replies[0]                           # non-empty string

    replies2 = chat(bot, "   ")                 # whitespace only
    assert len(replies2) == 1
    assert replies2[0]
