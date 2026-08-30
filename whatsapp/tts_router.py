"""
tts_router.py — FastAPI router for TTS endpoints.

Endpoints:
    POST /api/tts         — Generate Hindi audio from arbitrary text
    GET  /api/audio/{fn}  — Serve a generated audio file (MP3 / WAV)
    POST /api/test-alert  — Full pipeline test: analysis + recommendation + audio
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


def _audio_url_for(filename: str) -> str:
    return f"/api/audio/{filename}"


@router.post(
    "/tts",
    response_model=TTSResponse,
    tags=["tts"],
    summary="Generate Hindi audio from text",
)
async def generate_tts(request: TTSRequest) -> TTSResponse:
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


@router.get(
    "/audio/{filename}",
    tags=["tts"],
    summary="Serve generated audio file",
    response_class=FileResponse,
)
async def serve_audio(filename: str) -> FileResponse:
    settings = get_settings()
    audio_dir = Path(settings.tts_audio_dir).resolve()
    file_path = (audio_dir / filename).resolve()

    if not str(file_path).startswith(str(audio_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    logger.info("Serving audio | file=%s | media_type=%s", filename, media_type)
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.post(
    "/test-alert",
    response_model=AlertResponse,
    tags=["tts"],
    summary="Full pipeline: village + crop -> analysis -> recommendation -> audio",
)
async def test_alert(request: AlertRequest) -> AlertResponse:
    settings = get_settings()
    logger.info(
        "POST /api/test-alert | village='%s' | crop='%s'",
        request.village, request.crop,
    )

    try:
        result = analyze_field(request.village, request.crop)
    except Exception as exc:
        logger.exception("Analysis failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analysis backend failed")

    farmer_msg = generate_farmer_message(result)
    text_hi = farmer_msg["text_hi"]

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
