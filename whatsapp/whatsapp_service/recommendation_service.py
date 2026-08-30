"""
recommendation_service.py — Converts an AnalysisResult into a short,
farmer-friendly Hindi sentence suitable for TTS narration.
"""

import logging
from typing import TypedDict
from whatsapp_service.mock_analysis import AnalysisResult

logger = logging.getLogger(__name__)

RAIN_THRESHOLD: int = 40

_CROP_HINDI: dict[str, str] = {
    "wheat":         "gehun",
    "rice":          "dhaan",
    "maize":         "makka",
    "pearl_millet":  "bajra",
    "sorghum":       "jowar",
    "sugarcane":     "ganna",
    "soybean":       "soyabean",
    "cotton":        "kapas",
    "mustard":       "sarson",
    "chickpea":      "chana",
    "potato":        "aloo",
    "onion":         "pyaaz",
    "groundnut":     "moongfali",
}


class FarmerMessage(TypedDict):
    text_hi: str


_TEMPLATES_DRY: dict[str, str] = {
    "low": (
        "Namaste. Aapke {crop_hi} ke khet mein fasal ki sthiti achhi hai. "
        "Filhaal pani ki kami ka koi bada sanket nahi hai. "
        "Fasal par nazar banaye rakhein."
    ),
    "moderate": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami ke kuch sanket mil rahe hain. "
        "Fasal par dhyan rakhein aur zarurat ke anusaar sinchai ki taiyari karein."
    ),
    "high": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami ka risk zyada hai. "
        "Agle chhe din mein baarish ki sambhavna kam hai. "
        "Budhwar tak sinchai karna uchit rahega."
    ),
    "critical": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami ka sankat bahut zyada hai. "
        "Kripya aaj hi sinchai karein, warna fasal ko bahut nuksan ho sakta hai."
    ),
}

_TEMPLATES_RAIN: dict[str, str] = {
    "low": (
        "Namaste. Aapke {crop_hi} ke khet mein fasal ki sthiti theek hai. "
        "Agle kuch dinon mein baarish ki bhi sambhavna hai. "
        "Abhi sinchai ki zarurat nahi hai."
    ),
    "moderate": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami ke kuch sanket hain, "
        "lekin agle kuch din mein baarish ki achhi sambhavna hai. "
        "Filhaal sinchai rokna aur baarish ki sthiti dekhna uchit rahega."
    ),
    "high": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami ke sanket hain, "
        "lekin agle kuch din mein baarish ki sambhavna hai. "
        "Baarish ka intezar karein aur sthiti dekh kar sinchai ka nirnay lein."
    ),
    "critical": (
        "Namaste. Aapke {crop_hi} ke khet mein pani ki kami bahut zyada hai. "
        "Baarish ki kuch sambhavna hai, lekin fasal ki suraksha ke liye "
        "aaj hi thodi sinchai avashyak hai."
    ),
}


def generate_farmer_message(result: AnalysisResult) -> FarmerMessage:
    crop_hi = _CROP_HINDI.get(result.crop, result.crop)
    rain_expected = result.rain_probability >= RAIN_THRESHOLD
    level = result.stress_level

    templates = _TEMPLATES_RAIN if rain_expected else _TEMPLATES_DRY
    template = templates.get(level, _TEMPLATES_DRY["moderate"])
    text_hi = template.format(crop_hi=crop_hi)

    logger.info(
        "Recommendation | village='%s' | crop='%s' | stress=%s | "
        "rain=%d%% | rain_expected=%s | chars=%d",
        result.village, result.crop, level,
        result.rain_probability, rain_expected, len(text_hi),
    )

    return FarmerMessage(text_hi=text_hi)
