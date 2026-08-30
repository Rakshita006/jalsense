"""
main.py — FastAPI application entry point.

Receives Twilio WhatsApp webhooks, routes them through the conversation
state machine (conversation_handler.py), and returns TwiML responses
with embedded native WhatsApp audio notes.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse

from whatsapp_service.config import get_settings
from whatsapp_service.conversation import conversation_store
from whatsapp_service.conversation_handler import handle_message
from whatsapp_service.twilio_service import validate_twilio_signature
from whatsapp_service.audio_mapper import get_audio_filename_for_stress
from tts_router import router as tts_router


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("JalSense WhatsApp service starting up")
    logger.info(
        "Twilio number: %s | Skip sig validation: %s",
        settings.twilio_whatsapp_from,
        settings.twilio_skip_signature_validation,
    )
    yield
    logger.info("JalSense WhatsApp service shutting down")


app = FastAPI(
    title="JalSense WhatsApp Service",
    description=(
        "Agricultural water-stress alert bot for Indian farmers via WhatsApp. "
        "Receives Twilio webhooks, generates natural Hindi voice notes, and replies in Hindi."
    ),
    version="0.6.0",
    lifespan=lifespan,
)

app.include_router(tts_router, prefix="/api", tags=["tts"])

logger = logging.getLogger(__name__)


@app.get("/health", tags=["ops"])
async def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "jalsense-whatsapp",
        "active_sessions": len(conversation_store),
    }


@app.post(
    "/webhook/whatsapp",
    tags=["whatsapp"],
    response_class=PlainTextResponse,
    summary="Twilio WhatsApp webhook",
)
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(default=""),
    From: str = Form(default=""),
    To: str = Form(default=""),
) -> Response:
    logger.info("Webhook | from=%s | body='%.80s'", From, Body)

    if not await validate_twilio_signature(request):
        logger.error("Rejected: invalid Twilio signature from %s", From)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )

    replies = handle_message(from_number=From, text=Body)
    settings = get_settings()

    twiml_resp = MessagingResponse()

    # Combine multi-part messages into a single complete WhatsApp message
    combined_body = "\n\n".join(replies)
    msg = twiml_resp.message(combined_body)

    # Attach direct playable native WhatsApp voice note if this is the final report
    if "JalSense Report" in combined_body and settings.tts_enabled:
        stress = "moderate"
        if "Bahut Zyada" in combined_body:
            stress = "critical"
        elif "Zyada" in combined_body:
            stress = "high"
        elif "Sahi" in combined_body:
            stress = "low"

        audio_file = get_audio_filename_for_stress(stress)
        if audio_file:
            base_url = str(settings.webhook_base_url).rstrip("/")
            if base_url and not base_url.startswith("mock://"):
                media_url = f"{base_url}/api/audio/{audio_file}"
                msg.media(media_url)

    twiml_xml = str(twiml_resp)

    logger.info(
        "Reply sent | to=%s | messages=1 | first_80='%.80s'",
        From, combined_body[:80],
    )
    return Response(content=twiml_xml, media_type="text/xml")


@app.get("/debug/sessions", tags=["ops"], include_in_schema=False)
async def debug_sessions() -> JSONResponse:
    sessions = [
        {
            "from_number": s.from_number,
            "state": s.state,
            "village": s.village,
            "crop": s.crop,
            "crop_raw": s.crop_raw,
            "query_count": s.query_count,
            "last_query_at": s.last_query_at.isoformat() if s.last_query_at else None,
        }
        for s in conversation_store.all_sessions()
    ]
    return JSONResponse({"sessions": sessions, "total": len(sessions)})


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
