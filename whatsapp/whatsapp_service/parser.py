"""
parser.py — Parse commands, village names, and normalize crop names.

Accepts Hindi transliterations, Devanagari Unicode, and English names.
Maps recognized crop aliases to canonical English identifiers.
"""

from dataclasses import dataclass
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ── Command alias sets ────────────────────────────────────────────────────────

GREETING_COMMANDS: frozenset[str] = frozenset({
    "hi", "hello", "namaste", "start", "namaskar", "hey",
    "helo", "hii", "hiii", "shuru", "नमस्ते", "नमस्कार", "प्रणाम",
})

RESTART_COMMANDS: frozenset[str] = frozenset({
    "restart", "reset", "dobara", "phir se", "start over",
    "naya", "new", "फिर से", "दोबारा", "शुरू से",
})

HELP_COMMANDS: frozenset[str] = frozenset({
    "help", "madad", "sahayata", "info",
    "मदद", "सहायता", "जानकारी",
})


# ── Crop alias map ────────────────────────────────────────────────────────────
# Keys are lowercase aliases (Hindi transliterations + Devanagari + English).
# Values are canonical English crop names.
CROP_ALIASES: dict[str, str] = {
    # Wheat
    "gehun": "wheat",
    "gehu": "wheat",
    "genhu": "wheat",
    "गेहूं": "wheat",
    "गेहू": "wheat",
    "गेहूँ": "wheat",
    "wheat": "wheat",
    "\u0917\u0947\u0902\u0939\u0942": "wheat",
    "\u0917\u0947\u0939\u0942\u0901": "wheat",
    "\u0917\u0947\u0939\u0942": "wheat",
    "\u0917\u0947\u0902\u0939\u0941\u0902": "wheat",
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
    "भुट्टा": "maize",

    # Bajra / Pearl Millet
    "bajra": "pearl_millet",
    "bajri": "pearl_millet",
    "बाजरा": "pearl_millet",
    "बाजरी": "pearl_millet",
    "pearl millet": "pearl_millet",
    "millet": "pearl_millet",

    # Jowar / Sorghum
    "jowar": "sorghum",
    "jwar": "sorghum",
    "ज्वार": "sorghum",
    "sorghum": "sorghum",

    # Sugarcane
    "ganna": "sugarcane",
    "ganne": "sugarcane",
    "sugarcane": "sugarcane",
    "गन्ना": "sugarcane",
    "ईख": "sugarcane",

    # Soybean
    "soybean": "soybean",
    "soya": "soybean",
    "soyabean": "soybean",
    "सोयाबीन": "soybean",

    # Cotton
    "kapas": "cotton",
    "kapaas": "cotton",
    "cotton": "cotton",
    "कपास": "cotton",
    "रूई": "cotton",

    # Mustard
    "sarso": "mustard",
    "sarson": "mustard",
    "mustard": "mustard",
    "सरसों": "mustard",
    "सरसो": "mustard",
    "राई": "mustard",

    # Gram / Chickpea
    "chana": "chickpea",
    "gram": "chickpea",
    "chickpea": "chickpea",
    "चना": "chickpea",
    "छोले": "chickpea",

    # Potato / Aloo
    "aloo": "potato",
    "alu": "potato",
    "potato": "potato",
    "आलू": "potato",

    # Onion / Pyaaz
    "pyaaz": "onion",
    "pyaz": "onion",
    "kanda": "onion",
    "onion": "onion",
    "प्याज": "onion",
    "कांदा": "onion",

    # Groundnut / Moongfali
    "moongfali": "groundnut",
    "mungfali": "groundnut",
    "peanut": "groundnut",
    "groundnut": "groundnut",
    "मूंगफली": "groundnut",
}


@dataclass
class ParsedMessage:
    """Result of parsing a legacy single-message village+crop input."""
    village: str
    crop_raw: str
    crop: str
    is_crop_known: bool


# ── Command detection ─────────────────────────────────────────────────────────

def detect_command(text: str) -> Optional[str]:
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
    cleaned = re.sub(r"[^\w\s\-]", "", text.strip(), flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned or len(cleaned) < 2:
        logger.warning("Village input too short or empty: '%s'", text)
        return None
    logger.debug("Village parsed: '%s' -> '%s'", text, cleaned)
    return cleaned


# ── Crop normalization ────────────────────────────────────────────────────────

def normalize_crop(raw: str) -> tuple[str, bool]:
    key = re.sub(r"\s+", " ", raw.strip()).lower()
    canonical = CROP_ALIASES.get(key)
    if canonical:
        logger.debug("Crop normalized: '%s' -> '%s'", raw, canonical)
        return canonical, True

    logger.warning("Unknown crop alias: '%s'", raw)
    return key, False


def parse_message(text: str) -> Optional[ParsedMessage]:
    text = text.strip()
    parts = [p.strip() for p in text.split(",", maxsplit=1)]

    if len(parts) == 2 and all(parts):
        village_raw, crop_raw = parts
    else:
        tokens = text.split(maxsplit=1)
        if len(tokens) < 2:
            logger.warning("Cannot parse message (too few tokens): '%s'", text)
            return None
        village_raw, crop_raw = tokens[0], tokens[1]

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
