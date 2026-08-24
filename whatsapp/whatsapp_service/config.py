"""
config.py — Application configuration loaded from environment variables.

All settings are read from a .env file (or real environment).
The app fails fast at startup if any required variable is missing.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Central settings object.  Access via ``get_settings()``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Twilio ────────────────────────────────────────────────
    twilio_account_sid: str = Field(..., description="Twilio Account SID")
    twilio_auth_token: str = Field(..., description="Twilio Auth Token")
    twilio_whatsapp_from: str = Field(
        ..., description="Twilio WhatsApp sender number (e.g. whatsapp:+14155238886)"
    )

    # ── Webhook ───────────────────────────────────────────────
    webhook_base_url: str = Field(
        ..., description="Public base URL used for Twilio signature validation"
    )
    twilio_skip_signature_validation: bool = Field(
        default=True,
        description="Set False in production to enforce Twilio request validation",
    )

    # ── Downstream Analysis API ───────────────────────────────
    # Not used in mock mode; here so the swap-in is trivial.
    analysis_api_url: str = Field(
        default="http://localhost:8080/api/analyze",
        description="URL of the real analysis API (teammate's FastAPI backend)",
    )
    analysis_api_timeout_seconds: int = Field(
        default=10, description="HTTP timeout for the analysis API call"
    )

    # ── Application ───────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Python logging level")
    app_port: int = Field(default=8000, description="Uvicorn port")

    # ── AI4Bharat TTS ─────────────────────────────────────────
    # hf_token is optional — only required if the model becomes gated.
    hf_token: Optional[str] = Field(
        default=None,
        description="HuggingFace auth token (set if model requires authentication)",
    )
    tts_model_id: str = Field(
        default="ai4bharat/indic-parler-tts",
        description="HuggingFace model ID for Indic Parler-TTS",
    )
    tts_audio_dir: str = Field(
        default="generated_audio",
        description="Directory where generated WAV files are saved",
    )
    tts_enabled: bool = Field(
        default=True,
        description="Set False to disable TTS (useful for fast unit tests)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}, got '{v}'")
        return upper

    @field_validator("twilio_whatsapp_from")
    @classmethod
    def validate_whatsapp_prefix(cls, v: str) -> str:
        if not v.startswith("whatsapp:"):
            raise ValueError(
                f"twilio_whatsapp_from must start with 'whatsapp:', got '{v}'"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Raises ``ValidationError`` on startup if any required var is missing.
    """
    settings = Settings()  # type: ignore[call-arg]
    logger.info(
        "Settings loaded | webhook_base_url=%s | skip_sig_validation=%s",
        settings.webhook_base_url,
        settings.twilio_skip_signature_validation,
    )
    return settings
