"""
audio_mapper.py — Maps water-stress levels and conditions to generated Hindi voice notes.
"""

from pathlib import Path
from typing import Optional

# Pre-rendered high-quality AI4Bharat voice advisory notes for instant WhatsApp delivery (<1s)
_VOICE_NOTES: dict[str, str] = {
    "low": "alert_9ffe09c04f53.wav",
    "moderate": "alert_f2a1503daa9a.wav",
    "high": "alert_a0c543d789ea.wav",
    "critical": "alert_74955019e0b3.wav",
    "rain": "alert_51021251245e.wav",
}


def get_audio_filename_for_stress(stress_level: str, rain_probability: int = 0) -> Optional[str]:
    """
    Get the matching pre-generated audio filename for the stress level.
    """
    if rain_probability >= 40:
        return _VOICE_NOTES.get("rain")
    return _VOICE_NOTES.get(stress_level.lower(), _VOICE_NOTES["moderate"])
