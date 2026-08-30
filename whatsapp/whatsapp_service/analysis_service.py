"""
analysis_service.py — Clean abstraction over the water-stress analysis backend.

Delegates to mock_analysis.run_analysis() or teammate's backend API.
"""

import logging
from whatsapp_service.mock_analysis import AnalysisResult, run_analysis

logger = logging.getLogger(__name__)


# ── Farmer-facing display names ───────────────────────────────────────────────

_CROP_DISPLAY: dict[str, str] = {
    "wheat":         "Gehun (गेहूं)",
    "rice":          "Dhaan (धान)",
    "maize":         "Makka (मक्का)",
    "pearl_millet":  "Bajra (बाजरा)",
    "sorghum":       "Jowar (ज्वार)",
    "sugarcane":     "Ganna (गन्ना)",
    "soybean":       "Soyabean (सोयाबीन)",
    "cotton":        "Kapas (कपास)",
    "mustard":       "Sarson (सरसों)",
    "chickpea":      "Chana (चना)",
    "potato":        "Aloo (आलू)",
    "onion":         "Pyaaz (प्याज)",
    "groundnut":     "Moongfali (मूंगफली)",
}

_STRESS_DISPLAY: dict[str, tuple[str, str]] = {
    "critical": ("Bahut Zyada", "🔴"),
    "high":     ("Zyada",       "🟠"),
    "moderate": ("Theek-Theek", "🟡"),
    "low":      ("Sahi",        "🟢"),
}

_RISK_TEXT: dict[str, str] = {
    "critical": "Agle 2-3 din mein pani ki bahut zyada kami ka khatra hai.",
    "high":     "Agle 6 din mein pani ki kami ka risk hai.",
    "moderate": "Thodi pani ki kami ho sakti hai agle kuch dinon mein.",
    "low":      "Abhi pani ki sthiti theek hai.",
}


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_field(village: str, crop: str) -> AnalysisResult:
    """
    Analyze water stress for the given village and crop.
    Fast check for real backend API; instant deterministic fallback (<50ms).
    """
    logger.info("analyze_field | village='%s' | crop='%s'", village, crop)
    try:
        from whatsapp_service.config import get_settings
        import requests
        settings = get_settings()
        api_url = str(settings.analysis_api_url) if settings.analysis_api_url else ""
        if api_url and not api_url.startswith("mock://") and not "localhost:8080" in api_url:
            try:
                resp = requests.post(
                    api_url,
                    json={"village": village, "crop": crop},
                    timeout=(0.5, 2.0),
                )
                if resp.status_code == 200:
                    return AnalysisResult.model_validate(resp.json())
            except Exception as e:
                logger.debug("Real API fallback to mock: %s", e)
    except Exception as exc:
        logger.debug("Using mock fallback: %s", exc)

    return run_analysis(village, crop)


def format_report_hi(result: AnalysisResult) -> str:
    """
    Format an AnalysisResult as a farmer-friendly Hindi report card.
    """
    crop_display = _CROP_DISPLAY.get(result.crop, result.crop.capitalize())
    stress_label, stress_emoji = _STRESS_DISPLAY.get(
        result.stress_level, ("Pata nahi", "⚪")
    )
    risk_text = _RISK_TEXT.get(result.stress_level, "")

    lines = [
        "🌾 JalSense Report",
        "",
        f"Gaon: {result.village}",
        f"Fasal: {crop_display}",
        "",
        f"💧 Pani ka stress: {stress_label} {stress_emoji}",
        "",
        risk_text,
        "",
        f"👉 {result.recommendation_hi}",
    ]
    return "\n".join(lines)
