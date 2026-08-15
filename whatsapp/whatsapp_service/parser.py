"""
parser.py — Incoming WhatsApp message parsing, command detection,
            village parsing, and crop-name normalization.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ── Command alias sets ────────────────────────────────────────────────────────

GREETING_COMMANDS: frozenset[str] = frozenset({
    "hi", "hello", "namaste", "start", "namaskar", "hey",
    "helo", "hii", "hiii", "shuru", "शुरू", "नमस्ते",
})

RESTART_COMMANDS: frozenset[str] = frozenset({
    "restart", "reset", "dobara", "phir se", "start over",
    "naya", "new", "फिर से", "दोबारा",
})

HELP_COMMANDS: frozenset[str] = frozenset({
    "help", "madad", "sahayata", "info",
    "मदद", "सहायता",
})


# ── Crop alias map ────────────────────────────────────────────────────────────
# Keys are lowercase aliases (Hindi transliterations + Devanagari + English).
# Values are canonical English crop names.
CROP_ALIASES: dict[str, str] = {
    # Wheat — including Devanagari spelling variants
    "gehun": "wheat",
    "gehu": "wheat",
    "gehun": "wheat",
    "gehu": "wheat",
    "गेहूं": "wheat",    # anusvara
    "गेहूँ": "wheat",    # chandrabindu
    "गेंहू": "wheat",    # nasal variant
    "गेहू": "wheat",
    "wheat": "wheat",
    "gandum": "wheat",
    # Rice / Paddy
    "chawal": "rice",
    "chaawal": "rice",
    "dhaan": "rice",
    "dhan": "rice",
    "चावल": "rice",
    "धान": "rice",
    "rice": "rice",
    "paddy": "rice",
    # Maize / Corn
    "makka": "maize",
    "makkai": "maize",
    "maize": "maize",
    "corn": "maize",
    "मक्का": "maize",
    "मकई": "maize",
    # Sugarcane
    "ganna": "sugarcane",
    "ganne": "sugarcane",
    "sugarcane": "sugarcane",
    "गन्ना": "sugarcane",
    "गन्ने": "sugarcane",
    # Soybean
    "soybean": "soybean",
    "soya": "soybean",
    "soyabean": "soybean",
    "सोयाबीन": "soybean",
    # Cotton
    "kapas": "cotton",
    "cotton": "cotton",
    "कपास": "cotton",
    # Mustard
    "sarso": "mustard",
    "sarson": "mustard",
    "mustard": "mustard",
    "सरसों": "mustard",
    "सरसो": "mustard",
    # Gram / Chickpea
    "chana": "chickpea",
    "gram": "chickpea",
    "chickpea": "chickpea",
    "चना": "chickpea",
}


@dataclass
class ParsedMessage:
    """Result of parsing a legacy single-message village+crop input."""

    village: str
    crop_raw: str        # Original string the farmer typed
    crop: str            # Normalized English crop name (or original if unknown)
    is_crop_known: bool  # False if we couldn't map the crop name


# ── Command detection ─────────────────────────────────────────────────────────

def detect_command(text: str) -> Optional[str]:
    """
    Detect if the text is a known command.

    Returns:
        'hi'      — greeting / start
        'restart' — reset conversation
        'help'    — show help
        None      — not a command; treat as content input
    """
    normalized = text.strip().lower()
    if normalized in GREETING_COMMANDS:
        return "hi"
    if normalized in RESTART_COMMANDS:
        return "restart"
    if normalized in HELP_COMMANDS:
        return "help"
    return None


# ── Village parsing ───────────────────────────────────────────────────────────

def parse_village(text: str) -> Optional[str]:
    """
    Sanitize and return a village name from raw user input.

    Accepts Unicode letters (covers Devanagari), digits, spaces, hyphens.
    Returns ``None`` if the result is empty or suspiciously short (< 2 chars).
    """
    # Remove characters that are not word chars, whitespace, or hyphens
    cleaned = re.sub(r"[^\w\s\-]", "", text.strip(), flags=re.UNICODE).strip()
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned or len(cleaned) < 2:
        logger.warning("Village input too short or empty: '%s'", text)
        return None

    logger.debug("Village parsed: '%s' -> '%s'", text, cleaned)
    return cleaned


# ── Crop normalization ────────────────────────────────────────────────────────

def normalize_crop(raw: str) -> tuple[str, bool]:
    """
    Map a raw crop string to a canonical English name.

    Normalizes whitespace and lowercases before lookup.

    Returns:
        (canonical_name, is_known)
        If not recognized, returns (raw.lower().strip(), False).
    """
    # Normalize: strip, collapse whitespace, lowercase
    key = re.sub(r"\s+", " ", raw.strip()).lower()
    canonical = CROP_ALIASES.get(key)
    if canonical:
        logger.debug("Crop normalized: '%s' -> '%s'", raw, canonical)
        return canonical, True

    logger.warning("Unknown crop alias: '%s'", raw)
    return key, False


# ── Legacy combined message parser (kept for backward compatibility) ──────────

def parse_message(text: str) -> Optional[ParsedMessage]:
    """
    Parse a farmer's single-message input into village + crop.

    Expected format: "<village>, <crop>"
    Tolerates extra whitespace, missing comma (falls back to space split).

    Returns ``None`` if the message cannot be parsed.

    NOTE: This function is used by the legacy single-message flow and
    tests.  New code should use the state machine (conversation_handler.py)
    which collects village and crop in separate messages.
    """
    text = text.strip()

    # Primary strategy: split on comma
    parts = [p.strip() for p in text.split(",", maxsplit=1)]

    if len(parts) == 2 and all(parts):
        village_raw, crop_raw = parts
    else:
        # Fallback: split on whitespace — first token is village, rest is crop
        tokens = text.split(maxsplit=1)
        if len(tokens) < 2:
            logger.warning("Cannot parse message (too few tokens): '%s'", text)
            return None
        village_raw, crop_raw = tokens[0], tokens[1]

    # Sanitize: allow Unicode letters, digits, spaces, hyphens only
    village = re.sub(r"[^\w\s\-]", "", village_raw, flags=re.UNICODE).strip()
    crop_raw_clean = re.sub(r"[^\w\s\-]", "", crop_raw, flags=re.UNICODE).strip()

    if not village or not crop_raw_clean:
        logger.warning("Empty village or crop after sanitization: '%s'", text)
        return None

    crop, is_known = normalize_crop(crop_raw_clean)

    logger.info(
        "Message parsed | village='%s' | crop_raw='%s' | crop='%s' | known=%s",
        village,
        crop_raw_clean,
        crop,
        is_known,
    )

    return ParsedMessage(
        village=village,
        crop_raw=crop_raw_clean,
        crop=crop,
        is_crop_known=is_known,
    )
