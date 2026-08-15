"""
conversation_handler.py — JalSense multi-turn conversation state machine.

Public API:
    handle_message(from_number, text, store=None) -> list[str]

All conversation logic lives here.  No Twilio, no FastAPI, no HTTP dependencies.
This makes the handler fully testable without any network or framework setup.

State transitions:
    NEW_USER            + any text       → greet + WAITING_FOR_VILLAGE
    WAITING_FOR_VILLAGE + valid village  → confirm + WAITING_FOR_CROP
    WAITING_FOR_CROP    + known crop     → "analyzing..." + RESULT report
    WAITING_FOR_CROP    + unknown crop   → re-prompt (state unchanged)
    any state           + "restart"      → reset + WAITING_FOR_VILLAGE
    any state           + "help"         → help text (state unchanged)
    any state           + greeting       → greet + WAITING_FOR_VILLAGE
"""

import logging
from typing import Optional

from whatsapp_service.analysis_service import analyze_field, format_report_hi
from whatsapp_service.conversation import (
    ConversationState,
    ConversationStore,
    conversation_store,
)
from whatsapp_service.parser import detect_command, normalize_crop, parse_village

logger = logging.getLogger(__name__)


# ── Fixed reply strings ───────────────────────────────────────────────────────

_GREET = (
    "Namaste! \U0001f331 Main JalSense hoon.\n\n"
    "Apne gaon ka naam bhejiye.\n"
    "Example: Chitrakoot"
)

_ASK_CROP = (
    "Bahut badhiya \U0001f44d\n\n"
    "Aap kaunsi fasal uga rahe hain?\n"
    "Example: Gehun"
)

_ANALYZING = (
    "Dhanyavaad. \U0001f33e\n\n"
    "Main aapke khet ka satellite, weather aur water-stress analysis "
    "kar raha hoon.\n\n"
    "Kripya thoda intezar karein..."
)

_HELP = (
    "JalSense aapko fasal aur pani ki sthiti ke baare mein jaankari deta hai.\n\n"
    "Shuru karne ke liye apne gaon ka naam bhejiye."
)

_INVALID_VILLAGE = "Kripya apne gaon ka naam bhejiye."

_INVALID_CROP = (
    "Kripya fasal ka naam dobara bhejiye.\n\n"
    "Udaharan:\n"
    "Gehun\n"
    "Dhaan\n"
    "Sarson\n"
    "Makka\n"
    "Kapas"
)

_RESTART_CONFIRM = (
    "Theek hai, nayi shuruat karte hain. \U0001f504\n\n"
    "Apne gaon ka naam bhejiye.\n"
    "Example: Chitrakoot"
)

_RESULT_DONE = (
    "Koi aur gaon ya fasal check karne ke liye 'restart' likhiye.\n"
    "Madad ke liye 'help' likhiye."
)

_ANALYSIS_ERROR = (
    "Khed hai, analysis mein kuch gadbad ho gayi. \U0001f614\n\n"
    "Kripya dobara apne gaon ka naam bhejiye."
)

_EMPTY_MSG = (
    "Kripya kuch likhiye.\n\n"
    "Gaon ka naam bhejiye, jaise: Chitrakoot"
)


# ── State machine ─────────────────────────────────────────────────────────────

def handle_message(
    from_number: str,
    text: str,
    store: Optional[ConversationStore] = None,
) -> list[str]:
    """
    Process an incoming farmer message and return a list of reply strings.

    Usually returns a single-element list.  Returns two elements when
    transitioning WAITING_FOR_CROP → RESULT:
        [0] "analyzing…" acknowledgement
        [1] The full Hindi report card

    Args:
        from_number: Farmer's unique identifier (phone / WhatsApp number).
        text:        Raw message text received from the farmer.
        store:       ConversationStore to use. Defaults to the module-level
                     singleton. Pass a fresh store in tests for isolation.

    Returns:
        list[str]: One or more reply messages to send back.
    """
    _store = store if store is not None else conversation_store

    # ── Guard: empty message ───────────────────────────────────────────────
    text_stripped = text.strip()
    if not text_stripped:
        logger.warning("Empty message from %s", from_number)
        return [_EMPTY_MSG]

    # ── Special commands — checked before state, override everything ───────
    cmd = detect_command(text_stripped)

    if cmd == "restart":
        _store.clear(from_number)
        _store.upsert(from_number, state=ConversationState.WAITING_FOR_VILLAGE)
        logger.info("Restart | %s", from_number)
        return [_RESTART_CONFIRM]

    if cmd == "help":
        logger.info("Help command | %s", from_number)
        return [_HELP]

    # ── Resolve current state ─────────────────────────────────────────────
    session = _store.get(from_number)
    current_state = session.state if session else ConversationState.NEW_USER

    # ── Greeting command or brand-new user ────────────────────────────────
    if cmd == "hi" or current_state == ConversationState.NEW_USER:
        _store.upsert(from_number, state=ConversationState.WAITING_FOR_VILLAGE)
        logger.info("Greeted | %s", from_number)
        return [_GREET]

    # ── WAITING_FOR_VILLAGE ───────────────────────────────────────────────
    if current_state == ConversationState.WAITING_FOR_VILLAGE:
        village = parse_village(text_stripped)
        if not village:
            logger.warning("Invalid village | %s | input='%s'", from_number, text_stripped)
            return [_INVALID_VILLAGE]

        _store.upsert(
            from_number,
            state=ConversationState.WAITING_FOR_CROP,
            village=village,
        )
        logger.info("Village set | %s | village='%s'", from_number, village)
        return [_ASK_CROP]

    # ── WAITING_FOR_CROP ──────────────────────────────────────────────────
    if current_state == ConversationState.WAITING_FOR_CROP:
        crop, is_known = normalize_crop(text_stripped)
        if not is_known:
            logger.warning("Unknown crop | %s | input='%s'", from_number, text_stripped)
            return [_INVALID_CROP]

        village = (session.village if session else None) or "Unknown"

        # Transition → ANALYZING
        _store.upsert(
            from_number,
            state=ConversationState.ANALYZING,
            crop=crop,
            crop_raw=text_stripped,
        )

        # Run analysis (sync mock; real API call replaces this in analysis_service.py)
        try:
            result = analyze_field(village, crop)
        except Exception as exc:
            logger.exception(
                "Analysis failed | village='%s' | crop='%s' | %s", village, crop, exc
            )
            _store.upsert(from_number, state=ConversationState.WAITING_FOR_VILLAGE)
            return [_ANALYSIS_ERROR]

        # Transition → RESULT
        _store.upsert(from_number, state=ConversationState.RESULT)
        logger.info(
            "Analysis done | %s | village='%s' | crop='%s' | stress=%s",
            from_number, village, crop, result.stress_level,
        )

        report = format_report_hi(result)
        return [_ANALYZING, report]

    # ── RESULT — already have a completed analysis ────────────────────────
    if current_state == ConversationState.RESULT:
        return [_RESULT_DONE]

    # ── Fallback (should never reach here) ────────────────────────────────
    logger.error("Unhandled state '%s' for %s — resetting", current_state, from_number)
    _store.clear(from_number)
    return [_GREET]
