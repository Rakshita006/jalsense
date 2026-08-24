#!/usr/bin/env python
"""
test_tts.py — Manual TTS test script for JalSense.

Loads the real AI4Bharat model and generates actual WAV files.
Use this to verify the TTS pipeline before wiring it to the API.

Usage:
    python test_tts.py

Output for each test case:
    - Input Hindi text
    - Generated audio file path
    - Generation time (seconds)
    - Device used (cpu / cuda:0)

Files are saved to: generated_audio/
"""

import logging
import sys
import time
from dataclasses import dataclass
from typing import Optional

# Show only INFO+ so progress is readable
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from whatsapp_service.mock_analysis import AnalysisResult
from whatsapp_service.recommendation_service import generate_farmer_message
from whatsapp_service.tts_service import HindiTTSService, TTSError


# ── Test cases ────────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    name: str
    result: AnalysisResult


TEST_CASES: list[TestCase] = [
    TestCase(
        name="Low stress (no action needed)",
        result=AnalysisResult(
            village="Chitrakoot",
            crop="wheat",
            stress_score=20,
            stress_level="low",
            ndvi=0.75,
            ndwi=0.05,
            rain_probability=15,
            recommendation_hi="Abhi pani ki zarurat nahi hai.",
        ),
    ),
    TestCase(
        name="Moderate stress",
        result=AnalysisResult(
            village="Varanasi",
            crop="rice",
            stress_score=50,
            stress_level="moderate",
            ndvi=0.55,
            ndwi=-0.10,
            rain_probability=20,
            recommendation_hi="Thodi sinchai karein.",
        ),
    ),
    TestCase(
        name="High stress (irrigation recommended)",
        result=AnalysisResult(
            village="Ballia",
            crop="mustard",
            stress_score=75,
            stress_level="high",
            ndvi=0.40,
            ndwi=-0.25,
            rain_probability=10,
            recommendation_hi="Budhwar tak sinchai zaroor karein.",
        ),
    ),
    TestCase(
        name="Critical stress",
        result=AnalysisResult(
            village="Jhansi",
            crop="cotton",
            stress_score=92,
            stress_level="critical",
            ndvi=0.28,
            ndwi=-0.40,
            rain_probability=5,
            recommendation_hi="Aaj hi sinchai karein.",
        ),
    ),
    TestCase(
        name="High stress + high rain (wait for rain)",
        result=AnalysisResult(
            village="Ayodhya",
            crop="maize",
            stress_score=70,
            stress_level="high",
            ndvi=0.42,
            ndwi=-0.20,
            rain_probability=65,   # above RAIN_THRESHOLD — should recommend waiting
            recommendation_hi="Baarish ka intezar karein.",
        ),
    ),
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_tests() -> None:
    print("\n" + "=" * 60)
    print("  JalSense — Manual TTS Test")
    print("  Model: ai4bharat/indic-parler-tts")
    print("  NOTE: First run downloads ~1.5 GB model to HF cache.")
    print("=" * 60 + "\n")

    from whatsapp_service.config import get_settings
    settings = get_settings()

    # Shared service instance (model loaded once)
    svc = HindiTTSService(
        model_id=settings.tts_model_id,
        audio_dir=settings.tts_audio_dir,
        hf_token=settings.hf_token,
    )

    passed = 0
    failed = 0

    for i, tc in enumerate(TEST_CASES, start=1):
        print(f"[{i}/{len(TEST_CASES)}] {tc.name}")

        # Generate recommendation text
        msg = generate_farmer_message(tc.result)
        text_hi = msg["text_hi"]
        print(f"  Text  : {text_hi}")

        # Generate audio
        t0 = time.perf_counter()
        try:
            audio_path = svc.generate_audio(text_hi)
            elapsed = time.perf_counter() - t0
            device = svc.device or "cpu"
            print(f"  File  : {audio_path}")
            print(f"  Time  : {elapsed:.2f}s")
            print(f"  Device: {device}")
            print(f"  Status: PASSED\n")
            passed += 1
        except TTSError as exc:
            elapsed = time.perf_counter() - t0
            print(f"  Error : {exc}")
            print(f"  Time  : {elapsed:.2f}s")
            print(f"  Status: FAILED\n")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed / {failed} failed")
    print(f"  Audio files: generated_audio/")
    print("=" * 60 + "\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_tests()
