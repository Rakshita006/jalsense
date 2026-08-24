"""
main.py — JalSense WhatsApp Service entry point.

Routes:
    POST /webhook/whatsapp   Twilio webhook handler
    GET  /health             Health check
    GET  /debug/sessions     Active sessions (dev only)

    POST /api/tts            Generate Hindi audio from text
    GET  /api/audio/{file}   Serve generated audio (dev only)
    POST /api/test-alert     Full pipeline: village+crop → analysis → audio

Message flow (POST /webhook/whatsapp):
    1. Validate Twilio request signature
    2. Extract Body + From from form data
    3. Call handle_message(From, Body)  ← state machine in conversation_handler.py
    4. Wrap reply(ies) in TwiML <Message> elements
    5. Return TwiML XML to Twilio

Twilio integration note:
    The Twilio webhook is ALWAYS wired here. When TWILIO_SKIP_SIGNATURE_VALIDATION
    is True (dev mode), no credentials are needed and any POST is accepted.
    Set it to False in production — the existing validate_twilio_signature() in
    twilio_service.py activates automatically.
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
from tts_router import router as tts_router

# ── Logging setup ─────────────────────────────────────────────────────────────

def _configure_logging(level: str) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
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


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="JalSense WhatsApp Service",
    description=(
        "Agricultural water-stress alert bot for Indian farmers via WhatsApp. "
        "Receives Twilio webhooks and replies in Hindi."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(tts_router, prefix="/api", tags=["tts"])

logger = logging.getLogger(__name__)


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health_check() -> dict[str, Any]:
    """Returns service health and active session count."""
    return {
        "status": "ok",
        "service": "jalsense-whatsapp",
        "active_sessions": len(conversation_store),
    }


# ── Webhook handler ───────────────────────────────────────────────────────────

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
    """
    Twilio webhook endpoint.

    Twilio posts form-encoded data.  We validate the signature, route through
    the conversation state machine, and return TwiML XML with the Hindi reply.

    When TWILIO_SKIP_SIGNATURE_VALIDATION=true (dev/mock mode), any POST is
    accepted so you can test locally with curl without real Twilio credentials.
    """
    logger.info("Webhook | from=%s | body='%.80s'", From, Body)

    # ── 1. Validate Twilio signature ───────────────────────────────────────
    if not await validate_twilio_signature(request):
        logger.error("Rejected: invalid Twilio signature from %s", From)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )

    # ── 2. Route through state machine ─────────────────────────────────────
    # handle_message manages all conversation logic, error handling, and
    # state transitions. It returns a list of reply strings.
    replies = handle_message(from_number=From, text=Body)

    # ── 3. Build TwiML — multiple <Message> elements for multi-part replies ─
    twiml_resp = MessagingResponse()
    for reply in replies:
        twiml_resp.message(reply)
    twiml_xml = str(twiml_resp)

    logger.info(
        "Reply sent | to=%s | messages=%d | first_80='%.80s'",
        From, len(replies), replies[0] if replies else "",
    )
    return Response(content=twiml_xml, media_type="text/xml")


# ── Debug endpoint (remove or protect before production) ─────────────────────

@app.get("/debug/sessions", tags=["ops"], include_in_schema=False)
async def debug_sessions() -> JSONResponse:
    """Lists all active in-memory sessions. Remove or protect in production."""
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


# ── Local dev runner ──────────────────────────────────────────────────────────

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
