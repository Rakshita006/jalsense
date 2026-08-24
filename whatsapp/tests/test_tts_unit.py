"""
tests/test_tts_unit.py — Unit tests for the TTS and recommendation layers.

The AI4Bharat model is MOCKED — no model download happens during testing.
All 10 tests run in under 1 second.

Run with:
    pytest tests/test_tts_unit.py -v

To run the real model (slow, requires ~1.5 GB download):
    python test_tts.py
"""

import pytest
from unittest.mock import MagicMock, patch

from whatsapp_service.mock_analysis import AnalysisResult
from whatsapp_service.recommendation_service import (
    RAIN_THRESHOLD,
    generate_farmer_message,
)
from whatsapp_service.tts_service import HindiTTSService, TTSError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _result(
    stress_level: str = "high",
    rain_probability: int = 10,
    crop: str = "wheat",
    village: str = "Chitrakoot",
    stress_score: int = 75,
) -> AnalysisResult:
    """Build a minimal AnalysisResult for testing."""
    return AnalysisResult(
        village=village,
        crop=crop,
        stress_score=stress_score,
        stress_level=stress_level,
        ndvi=0.45,
        ndwi=-0.20,
        rain_probability=rain_probability,
        recommendation_hi="Test recommendation.",
    )


@pytest.fixture
def mock_tts_service(tmp_path):
    """
    HindiTTSService with the model loading and inference mocked out.
    Writes a tiny fake WAV-like file so generate_audio() succeeds.
    """
    svc = HindiTTSService(
        model_id="ai4bharat/indic-parler-tts",
        audio_dir=str(tmp_path),
    )

    # Simulate a loaded model
    svc._loaded = True
    svc._device = "cpu"

    fake_model = MagicMock()
    fake_model.config.sampling_rate = 22050
    svc._model = fake_model
    svc._tokenizer = MagicMock()
    svc._desc_tokenizer = MagicMock()

    return svc


# ── Test 1: Valid Hindi text → returns file path ──────────────────────────────

def test_generate_audio_valid_text(mock_tts_service: HindiTTSService, tmp_path):
    import numpy as np

    text = "Namaste. Aapke khet mein pani ki kami ka risk zyada hai."

    with patch.object(mock_tts_service, "_infer", return_value=np.zeros(22050)):
        path = mock_tts_service.generate_audio(text)

    assert path.endswith(".wav")
    import os
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0


# ── Test 2: Empty text → TTSError ─────────────────────────────────────────────

def test_generate_audio_empty_text(mock_tts_service: HindiTTSService):
    with pytest.raises(TTSError, match="empty"):
        mock_tts_service.generate_audio("")

    with pytest.raises(TTSError, match="empty"):
        mock_tts_service.generate_audio("   ")


# ── Test 3: None / invalid input → handled, no crash ─────────────────────────

def test_generate_audio_none_input(mock_tts_service: HindiTTSService):
    with pytest.raises(TTSError):
        mock_tts_service.generate_audio(None)  # type: ignore


# ── Test 4: Low stress recommendation ────────────────────────────────────────

def test_recommendation_low_stress():
    result = _result(stress_level="low", rain_probability=5)
    msg = generate_farmer_message(result)
    text = msg["text_hi"]
    assert text.startswith("Namaste.")
    # Should NOT mention irrigation urgently
    assert "jald" not in text
    assert "kripya" not in text.lower() or "sankat" not in text.lower()


# ── Test 5: Moderate stress recommendation ───────────────────────────────────

def test_recommendation_moderate_stress():
    result = _result(stress_level="moderate", rain_probability=5)
    msg = generate_farmer_message(result)
    text = msg["text_hi"]
    assert text.startswith("Namaste.")
    assert "sanket" in text or "taiyari" in text or "dhyan" in text


# ── Test 6: High stress recommendation ───────────────────────────────────────

def test_recommendation_high_stress():
    result = _result(stress_level="high", rain_probability=5)
    msg = generate_farmer_message(result)
    text = msg["text_hi"]
    assert text.startswith("Namaste.")
    # Should recommend irrigation
    assert "sinchai" in text


# ── Test 7: Critical stress recommendation ───────────────────────────────────

def test_recommendation_critical_stress():
    result = _result(stress_level="critical", rain_probability=3)
    msg = generate_farmer_message(result)
    text = msg["text_hi"]
    assert text.startswith("Namaste.")
    assert "sinchai" in text
    # Critical should be more urgent than high
    assert "bahut" in text or "jald" in text or "aaj" in text


# ── Test 8: High stress + high rain → wait, don't irrigate ───────────────────

def test_recommendation_high_stress_with_rain():
    rain_pct = RAIN_THRESHOLD + 10   # clearly above threshold
    result = _result(stress_level="high", rain_probability=rain_pct)
    msg = generate_farmer_message(result)
    text = msg["text_hi"]
    assert text.startswith("Namaste.")
    # Should NOT flatly say "Budhwar tak sinchai karo"
    # Should mention rain expectation
    assert "baarish" in text


# ── Test 9: TTS inference failure → TTSError, no crash ───────────────────────

def test_tts_inference_failure(mock_tts_service: HindiTTSService):
    with patch.object(mock_tts_service, "_infer", side_effect=RuntimeError("OOM")):
        with pytest.raises(TTSError, match="inference"):
            mock_tts_service.generate_audio("Namaste. Test.")


# ── Test 10: API response structure (via router logic) ────────────────────────

def test_api_test_alert_response_structure():
    """
    Verify that /api/test-alert always returns recommendation_hi
    even when TTS is disabled.
    """
    from fastapi.testclient import TestClient

    # Patch get_settings so TTS is disabled (no model load)
    mock_settings = MagicMock()
    mock_settings.tts_enabled = False
    mock_settings.tts_model_id = "ai4bharat/indic-parler-tts"
    mock_settings.tts_audio_dir = "generated_audio"
    mock_settings.hf_token = None
    mock_settings.twilio_whatsapp_from = "whatsapp:+17372212163"
    mock_settings.twilio_skip_signature_validation = True
    mock_settings.log_level = "WARNING"

    with patch("whatsapp_service.config.get_settings", return_value=mock_settings):
        with patch("tts_router.get_settings", return_value=mock_settings):
            from main import app
            client = TestClient(app)
            resp = client.post(
                "/api/test-alert",
                json={"village": "Chitrakoot", "crop": "wheat"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "recommendation_hi" in data
    assert data["recommendation_hi"].startswith("Namaste.")
    assert data["village"] == "Chitrakoot"
    assert data["crop"] == "wheat"
    assert "stress_score" in data
    assert "stress_level" in data
    # TTS disabled → no audio URL, but no crash
    assert data["audio_url"] is None
    assert data["error"] is not None   # "TTS disabled"
