"""
analysis_service.py — Clean abstraction over the water-stress analysis backend.

Currently delegates to mock_analysis.run_analysis().

SWAP POINT: When the real backend (teammate's FastAPI) is ready, replace
the body of ``analyze_field()`` with the code shown in the docstring below.
The rest of the codebase (conversation_handler, tests) does NOT change.
"""

import logging

from whatsapp_service.mock_analysis import AnalysisResult, run_analysis

logger = logging.getLogger(__name__)


# ── Farmer-facing display names ───────────────────────────────────────────────

_CROP_DISPLAY: dict[str, str] = {
    "wheat":     "Gehun",
    "rice":      "Dhaan",
    "maize":     "Makka",
    "sugarcane": "Ganna",
    "soybean":   "Soyabean",
    "cotton":    "Kapas",
    "mustard":   "Sarson",
    "chickpea":  "Chana",
}

_STRESS_DISPLAY: dict[str, tuple[str, str]] = {
    # (Hindi label, emoji)
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

    Currently calls the mock analysis. To connect the real backend,
    replace this function body with:

        import httpx
        from whatsapp_service.config import get_settings
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.analysis_api_timeout_seconds) as client:
            resp = await client.post(
                settings.analysis_api_url,
                json={"village": village, "crop": crop},
            )
            resp.raise_for_status()
            return AnalysisResult.model_validate(resp.json())

    The AnalysisResult schema and all downstream code stay unchanged.
    """
    logger.info("analyze_field | village='%s' | crop='%s'", village, crop)
    return run_analysis(village, crop)


def format_report_hi(result: AnalysisResult) -> str:
    """
    Format an AnalysisResult as a farmer-friendly Hindi report card.

    Example output:
        🌾 JalSense Report

        Gaon: Chitrakoot
        Fasal: Gehun

        💧 Pani ka stress: Zyada 🟠

        Agle 6 din mein pani ki kami ka risk hai.

        👉 Budhwar tak sinchai zaroor karein.
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
