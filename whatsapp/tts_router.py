"""
tts_router.py — FastAPI router for TTS development/testing endpoints.

Registered in main.py under the /api prefix.

Endpoints:
    POST /api/tts              — generate audio from Hindi text
    GET  /api/audio/{filename} — serve generated WAV (dev only)
    POST /api/test-alert       — full pipeline: village+crop → mock analysis
                                 → recommendation → audio

NOTE: The audio serving endpoint (/api/audio) is for local development ONLY.
For production / Twilio integration, replace with a cloud storage URL
(S3, GCS, or Cloudinary) so Twilio can fetch the audio over HTTPS.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from whatsapp_service.analysis_service import analyze_field
from whatsapp_service.config import get_settings
from whatsapp_service.recommendation_service import generate_farmer_message
from whatsapp_service.tts_service import TTSError, get_tts_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=1000,
        description="Hindi text to synthesize into speech",
        examples=["Namaste. Aapke khet mein pani ki kami ka risk zyada hai."],
    )


class TTSResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None


class AlertRequest(BaseModel):
    village: str = Field(..., min_length=1, description="Village name")
    crop: str = Field(
        ..., min_length=1,
        description="Crop name (English canonical: wheat, rice, mustard, maize, cotton)",
        examples=["wheat"],
    )


class AlertResponse(BaseModel):
    success: bool
    village: str
    crop: str
    stress_score: int
    stress_level: str
    recommendation_hi: str
    audio_url: Optional[str] = None
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _audio_url_for(filename: str) -> str:
    """Build the /api/audio/<filename> URL."""
    return f"/api/audio/{filename}"


# ── POST /api/tts ─────────────────────────────────────────────────────────────

@router.post(
    "/tts",
    response_model=TTSResponse,
    tags=["tts"],
    summary="Generate Hindi audio from text",
)
async def generate_tts(request: TTSRequest) -> TTSResponse:
    """
    Accept Hindi text and return a URL to a generated WAV file.

    Internally calls HindiTTSService.generate_audio().
    On first request, the TTS model is loaded (~30 s on CPU).
    Subsequent requests are faster (model stays in memory).
    """
    settings = get_settings()
    if not settings.tts_enabled:
        return TTSResponse(success=False, error="TTS is disabled (TTS_ENABLED=false in .env)")

    logger.info("POST /api/tts | text_len=%d", len(request.text))

    try:
        svc = get_tts_service()
        audio_path = svc.generate_audio(request.text)
        filename = Path(audio_path).name
        return TTSResponse(success=True, audio_url=_audio_url_for(filename))

    except TTSError as exc:
        logger.warning("TTSError in /api/tts: %s", exc)
        return TTSResponse(success=False, error=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in /api/tts: %s", exc)
        return TTSResponse(success=False, error="Voice generation failed")


# ── GET /api/audio/{filename} ─────────────────────────────────────────────────

@router.get(
    "/audio/{filename}",
    tags=["tts"],
    summary="Serve generated audio file (dev only)",
    response_class=FileResponse,
)
async def serve_audio(filename: str) -> FileResponse:
    """
    Serve a generated WAV file by name.

    FOR LOCAL DEVELOPMENT ONLY. In production, serve audio from
    cloud storage (S3/GCS) so Twilio can fetch it over public HTTPS.

    Security: directory traversal is blocked.
    """
    settings = get_settings()
    audio_dir = Path(settings.tts_audio_dir).resolve()
    file_path = (audio_dir / filename).resolve()

    # Block directory traversal attacks (e.g. filename = "../../etc/passwd")
    if not str(file_path).startswith(str(audio_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    logger.info("Serving audio | file=%s", filename)
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=filename,
    )


# ── POST /api/test-alert ──────────────────────────────────────────────────────

@router.post(
    "/test-alert",
    response_model=AlertResponse,
    tags=["tts"],
    summary="Full pipeline: village + crop → analysis → recommendation → audio",
)
async def test_alert(request: AlertRequest) -> AlertResponse:
    """
    End-to-end development test endpoint.

    Flow:
        1. village + crop  →  mock_analysis.run_analysis()
        2. AnalysisResult  →  recommendation_service.generate_farmer_message()
        3. Hindi text      →  tts_service.generate_audio()
        4. Return full result JSON including audio URL

    The text recommendation is ALWAYS returned even if TTS fails,
    so the caller can still display/send the Hindi text fallback.
    """
    settings = get_settings()
    logger.info(
        "POST /api/test-alert | village='%s' | crop='%s'",
        request.village, request.crop,
    )

    # ── Step 1: Analysis ──────────────────────────────────────────────────
    try:
        result = analyze_field(request.village, request.crop)
    except Exception as exc:
        logger.exception("Analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analysis backend failed")

    # ── Step 2: Recommendation ────────────────────────────────────────────
    farmer_msg = generate_farmer_message(result)
    text_hi = farmer_msg["text_hi"]

    # ── Step 3: Audio (degrades gracefully on failure) ────────────────────
    audio_url: Optional[str] = None
    error_msg: Optional[str] = None

    if not settings.tts_enabled:
        error_msg = "TTS disabled (TTS_ENABLED=false)"
    else:
        try:
            svc = get_tts_service()
            audio_path = svc.generate_audio(text_hi)
            filename = Path(audio_path).name
            audio_url = _audio_url_for(filename)
        except TTSError as exc:
            logger.warning("TTS failed in /api/test-alert: %s", exc)
            error_msg = "Voice generation failed"
        except Exception as exc:
            logger.exception("Unexpected TTS error: %s", exc)
            error_msg = "Voice generation failed"

    return AlertResponse(
        success=True,
        village=result.village,
        crop=result.crop,
        stress_score=result.stress_score,
        stress_level=result.stress_level,
        recommendation_hi=text_hi,
        audio_url=audio_url,
        error=error_msg,
    )
