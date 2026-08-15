"""
twilio_service.py — Twilio webhook validation and TwiML response builder.

Responsibilities:
  1. Validate that incoming requests genuinely come from Twilio.
  2. Build a structured Hindi reply from an AnalysisResult.
  3. Return TwiML <Message> XML.
"""

import logging

from fastapi import Request
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from whatsapp_service.config import get_settings
from whatsapp_service.mock_analysis import AnalysisResult

logger = logging.getLogger(__name__)


# ── Emoji decoration per stress level ────────────────────────────────────────
_STRESS_EMOJI: dict[str, str] = {
    "critical": "🔴",
    "high":     "🟠",
    "moderate": "🟡",
    "low":      "🟢",
}

_STRESS_LABEL_HI: dict[str, str] = {
    "critical": "अत्यधिक",
    "high":     "अधिक",
    "moderate": "मध्यम",
    "low":      "कम",
}


# ── Signature validation ──────────────────────────────────────────────────────

async def validate_twilio_signature(request: Request) -> bool:
    """
    Verify that the incoming request is from Twilio using HMAC-SHA1.

    When ``TWILIO_SKIP_SIGNATURE_VALIDATION=true`` (development), always
    returns True and logs a warning.
    """
    settings = get_settings()

    if settings.twilio_skip_signature_validation:
        logger.warning(
            "Twilio signature validation is DISABLED (dev mode). "
            "Set TWILIO_SKIP_SIGNATURE_VALIDATION=false in production."
        )
        return True

    validator = RequestValidator(settings.twilio_auth_token)

    # Reconstruct the full URL Twilio signed
    url = str(request.url)
    form_data = dict(await request.form())
    signature = request.headers.get("X-Twilio-Signature", "")

    valid = validator.validate(url, form_data, signature)
    if not valid:
        logger.warning(
            "Invalid Twilio signature | url=%s | sig=%s", url, signature
        )
    return valid


# ── Reply formatting ──────────────────────────────────────────────────────────

def format_hindi_reply(result: AnalysisResult) -> str:
    """
    Compose the Hindi WhatsApp message from an AnalysisResult.

    Example output:
        🌾 JalSense Alert — Chitrakoot / wheat

        💧 Paani ka stress: अधिक (78/100)
        🌿 NDVI: 0.62 | 💦 NDWI: -0.19
        🌧 Barish ki sambhavna: 12%

        📋 Salah:
        Aapke khet mein pani ki kami ka risk zyada hai. Budhwar tak sinchai karein.

        _Powered by JalSense 🌱_
    """
    emoji = _STRESS_EMOJI.get(result.stress_level, "⚪")
    label_hi = _STRESS_LABEL_HI.get(result.stress_level, result.stress_level)

    lines = [
        f"🌾 *JalSense Alert — {result.village} / {result.crop}*",
        "",
        f"{emoji} *Paani ka stress:* {label_hi} ({result.stress_score}/100)",
        f"🌿 *NDVI:* {result.ndvi}  |  💦 *NDWI:* {result.ndwi}",
        f"🌧 *Barish ki sambhavna (72 ghante):* {result.rain_probability}%",
        "",
        "📋 *Salah:*",
        result.recommendation_hi,
        "",
        "_Powered by JalSense 🌱_",
    ]
    return "\n".join(lines)


def format_error_reply(detail: str = "") -> str:
    """Hindi fallback message when parsing fails."""
    base = (
        "Khed hai, aapka sandesh samajh nahi aaya. 😔\n\n"
        "Kripya is tarah likhein:\n"
        "*<gaon ka naam>, <fasal ka naam>*\n\n"
        "Udaharan:  _Chitrakoot, gehun_"
    )
    if detail:
        base += f"\n\n_(Error: {detail})_"
    return base


def format_unknown_crop_reply(village: str, crop_raw: str) -> str:
    """Warn the farmer we didn't recognise their crop, then proceed with raw name."""
    return (
        f"⚠️ Hamne '{crop_raw}' fasal ko nahi pehchana.\n"
        f"Analysis chal rahi hai, lekin result galat ho sakta hai.\n\n"
        f"Supported faslein: gehun, chawal, makka, ganna, soya, kapas, sarson, chana."
    )


# ── TwiML builder ─────────────────────────────────────────────────────────────

def build_twiml_response(message: str) -> str:
    """Wrap ``message`` in a TwiML MessagingResponse and return the XML string."""
    resp = MessagingResponse()
    resp.message(message)
    xml = str(resp)
    logger.debug("TwiML response built | length=%d chars", len(xml))
    return xml
