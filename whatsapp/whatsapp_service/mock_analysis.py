"""
mock_analysis.py — Deterministic mock of the water-stress analysis.

CONTRACT: The ``AnalysisResult`` model and the ``run_analysis`` function
signature MUST be kept in sync with the real ``POST /api/analyze`` endpoint.

When the real backend is ready, replace the body of ``run_analysis`` with:

    async def run_analysis(village: str, crop: str) -> AnalysisResult:
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
"""

import hashlib
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── Shared response schema ────────────────────────────────────────────────────
# This Pydantic model mirrors the JSON returned by POST /api/analyze exactly.
# Both the mock and the real call return an AnalysisResult instance.

class AnalysisResult(BaseModel):
    """Water-stress analysis result for a village + crop pair."""

    village: str = Field(..., description="Village name as received")
    crop: str = Field(..., description="Normalized English crop name")
    stress_score: int = Field(..., ge=0, le=100, description="0–100 water stress score")
    stress_level: str = Field(..., description="'low' | 'moderate' | 'high' | 'critical'")
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index")
    ndwi: float = Field(..., description="Normalized Difference Water Index")
    rain_probability: int = Field(..., ge=0, le=100, description="Rain probability % (next 72 h)")
    recommendation_hi: str = Field(..., description="Hindi recommendation text for the farmer")


# ── Stress-level thresholds ───────────────────────────────────────────────────
def _score_to_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "moderate"
    return "low"


# ── Hindi recommendation templates ───────────────────────────────────────────
_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "critical": {
        "default": (
            "Aapke khet mein pani ki kami bahut zyada hai. "
            "Aaj hi sinchai karein, warna fasal ko nuksan ho sakta hai. "
            "Kal tak barish ki sambhavna bahut kam hai."
        ),
    },
    "high": {
        "default": (
            "Aapke khet mein pani ki kami ka risk zyada hai. "
            "Budhwar tak sinchai zaroor karein."
        ),
    },
    "moderate": {
        "default": (
            "Fasal mein thodi pani ki kami ho sakti hai. "
            "Agले 3-4 din mein mausam dekh kar sinchai karein."
        ),
    },
    "low": {
        "default": (
            "Abhi fasal theek hai. Pani ki kami nahi hai. "
            "Agar barish nahi hoti to 5-7 din baad sinchai karein."
        ),
    },
}


def _get_recommendation(level: str, crop: str) -> str:
    level_recs = _RECOMMENDATIONS.get(level, _RECOMMENDATIONS["moderate"])
    return level_recs.get(crop, level_recs["default"])


# ── Mock deterministic values ─────────────────────────────────────────────────
def _mock_values(village: str, crop: str) -> dict:
    """
    Generate stable mock values for a given village+crop combination.
    Uses a hash so the same inputs always return the same numbers
    (makes manual testing reproducible).
    """
    seed = int(hashlib.md5(f"{village.lower()}:{crop.lower()}".encode()).hexdigest(), 16)

    stress_score = 40 + (seed % 55)          # range 40–94
    ndvi = round(0.30 + (seed % 60) / 100, 2)  # range 0.30–0.89
    ndwi = round(-0.50 + (seed % 60) / 100, 2) # range -0.50 – 0.09
    rain_probability = seed % 45              # range 0–44 %

    return {
        "stress_score": stress_score,
        "ndvi": ndvi,
        "ndwi": ndwi,
        "rain_probability": rain_probability,
    }


# ── Public API (matches the future real implementation) ───────────────────────
def run_analysis(village: str, crop: str) -> AnalysisResult:
    """
    Return a mock AnalysisResult for the given village and crop.

    Replace the body of this function (keeping the signature) to call
    the real POST /api/analyze endpoint.
    """
    logger.info("Mock analysis | village='%s' | crop='%s'", village, crop)

    values = _mock_values(village, crop)
    level = _score_to_level(values["stress_score"])
    recommendation = _get_recommendation(level, crop)

    result = AnalysisResult(
        village=village,
        crop=crop,
        stress_level=level,
        recommendation_hi=recommendation,
        **values,
    )

    logger.debug("Mock result: %s", result.model_dump())
    return result
