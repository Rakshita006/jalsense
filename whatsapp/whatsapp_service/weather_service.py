"""
weather_service.py — Live real-world weather forecast integration for Indian districts.

Uses Open-Meteo API (free, open, global ECMWF/GFS meteorological forecasts).
"""

import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# Coordinates lookup for common Indian districts / agricultural regions
_DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    "jaipur":     (26.9124, 75.7873),
    "jodhpur":    (26.2389, 73.0243),
    "kota":       (25.2138, 75.8648),
    "pali":       (25.7713, 73.3234),
    "jobner":     (26.9678, 75.3789),
    "ranpur":     (25.1052, 75.8427),
    "chomu":      (27.1706, 75.7245),
    "dodo":       (26.8833, 75.4333),
    "chitrakoot": (25.1760, 80.8540),
    "varanasi":   (25.3176, 82.9739),
    "ballia":     (25.7600, 84.1500),
    "jhansi":     (25.4484, 78.5685),
    "ayodhya":    (26.7922, 82.1998),
    "nagaur":     (27.2070, 73.7423),
    "bikaner":    (28.0229, 73.3119),
    "alwar":      (27.5530, 76.6346),
    "sikar":      (27.6094, 75.1398),
    "ajmer":      (26.4499, 74.6399),
}


def get_live_rain_forecast(village: str) -> tuple[int, bool]:
    """
    Fetch real live rain probability for the next 72 hours from global weather models.
    Returns: (max_rain_probability_pct, is_rain_expected)
    """
    v_clean = village.lower().strip()
    coords = _DISTRICT_COORDS.get(v_clean, (26.9124, 75.7873))

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords[0],
                "longitude": coords[1],
                "daily": ["precipitation_probability_max", "precipitation_sum"],
                "timezone": "Asia/Kolkata",
            },
            timeout=1.5,
        )
        if resp.status_code == 200:
            data = resp.json()
            probs = data.get("daily", {}).get("precipitation_probability_max", [0, 0, 0])
            next_3_days = probs[:3] if probs else [0]
            max_prob = max(next_3_days) if next_3_days else 0
            logger.info("Live weather fetched | location='%s' | 72h_max_rain=%d%%", village, max_prob)
            return max_prob, max_prob >= 40
    except Exception as exc:
        logger.warning("Could not fetch live weather for '%s': %s", village, exc)

    return 15, False
