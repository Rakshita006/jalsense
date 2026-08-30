"""
mock_analysis.py — Deterministic water-stress analysis with LIVE real-time weather integration.
"""

import hashlib
import logging
from pydantic import BaseModel, Field
from whatsapp_service.weather_service import get_live_rain_forecast

logger = logging.getLogger(__name__)


class AnalysisResult(BaseModel):
    village: str = Field(..., description="Sanitized village name")
    crop: str = Field(..., description="Canonical crop identifier (English)")
    stress_score: int = Field(..., ge=0, le=100, description="0 (healthy) -> 100 (critical)")
    stress_level: str = Field(..., description="low | moderate | high | critical")
    ndvi: float = Field(..., description="Normalized Difference Vegetation Index [-1.0, 1.0]")
    ndwi: float = Field(..., description="Normalized Difference Water Index [-1.0, 1.0]")
    rain_probability: int = Field(..., ge=0, le=100, description="72h live forecast rain %")
    recommendation_hi: str = Field(..., description="Farmer-facing Hindi recommendation")


def _deterministic_hash(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)


def _score_to_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 66:
        return "high"
    if score >= 36:
        return "moderate"
    return "low"


def run_analysis(village: str, crop: str) -> AnalysisResult:
    """
    Run water-stress analysis combining satellite indices with LIVE real-world weather.
    """
    key = f"{village.lower()}:{crop.lower()}"
    h = _deterministic_hash(key)

    # 1. Satellite Indices (NDVI / NDWI)
    ndvi_raw = 0.20 + (h % 650) / 1000.0
    ndvi = round(min(max(ndvi_raw, 0.20), 0.85), 2)

    ndwi_raw = -0.35 + ((h >> 8) % 550) / 1000.0
    ndwi = round(min(max(ndwi_raw, -0.35), 0.20), 2)

    # Stress score inversely related to moisture & vegetation
    stress_score = int(min(max(100 - int(ndvi * 60 + (ndwi + 0.35) * 60), 0), 100))
    stress_level = _score_to_level(stress_score)

    # 2. Real-time Live Weather Forecast
    live_rain_pct, rain_expected = get_live_rain_forecast(village)

    # 3. Formulate Actionable Hindi Advice
    if rain_expected:
        recommendation_hi = (
            f"Agle 2-3 din mein {live_rain_pct}% barish ki sambhavna hai. "
            "Baarish ka intezar karein aur sthiti dekh kar sinchai ka nirnay lein."
        )
    elif stress_level == "critical":
        recommendation_hi = (
            "Aapke khet mein pani ki kami bahut zyada hai. "
            "Aaj hi sinchai karein, warna fasal ko nuksan ho sakta hai."
        )
    elif stress_level == "high":
        recommendation_hi = (
            "Aapke khet mein pani ki kami ka risk zyada hai. "
            "Agले 2-3 din mein sinchai karna uchit rahega."
        )
    elif stress_level == "moderate":
        recommendation_hi = (
            "Fasal mein thodi pani ki kami ho sakti hai. "
            "Agle 3-4 din mein mausam dekh kar sinchai karein."
        )
    else:
        recommendation_hi = (
            "Fasal ki sthiti achhi hai. "
            "Filhaal pani ki koi kami nahi hai. Niyamit dekhbhal karein."
        )

    logger.info(
        "Analysis result | village='%s' | crop='%s' | stress=%s(%d) | live_rain=%d%%",
        village, crop, stress_level, stress_score, live_rain_pct,
    )

    return AnalysisResult(
        village=village,
        crop=crop,
        stress_score=stress_score,
        stress_level=stress_level,
        ndvi=ndvi,
        ndwi=ndwi,
        rain_probability=live_rain_pct,
        recommendation_hi=recommendation_hi,
    )
