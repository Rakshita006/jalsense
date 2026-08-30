"""
audio_mapper.py — Maps water-stress levels and conditions to crystal-clear female Hindi voice notes.
"""

from typing import Optional

# High-quality natural female Hindi neural voice notes (MP3 format for native WhatsApp playback)
_VOICE_NOTES: dict[str, str] = {
    "low": "alert_low.mp3",
    "moderate": "alert_moderate.mp3",
    "high": "alert_high.mp3",
    "critical": "alert_critical.mp3",
    "rain": "alert_rain.mp3",
}


def get_audio_filename_for_stress(stress_level: str, rain_probability: int = 0) -> Optional[str]:
    """
    Get the matching female voice audio filename for the stress level.
    """
    if rain_probability >= 40:
        return _VOICE_NOTES.get("rain")
    return _VOICE_NOTES.get(stress_level.lower(), _VOICE_NOTES["moderate"])
