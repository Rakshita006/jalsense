"""
tts_service.py — HindiTTSService backed by AI4Bharat Indic Parler-TTS.

The model (ai4bharat/indic-parler-tts) is loaded ONCE on first use and
cached for the lifetime of the process.  GPU is used if available;
falls back to CPU automatically.

Public API:
    get_tts_service() -> HindiTTSService   (process-level singleton)
    HindiTTSService.generate_audio(text: str) -> str   (WAV file path)

Swap point:
    To replace with a different TTS backend, subclass HindiTTSService
    and override _load_model() and _infer().  get_tts_service() can
    be updated to return the new subclass.
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Custom exception ──────────────────────────────────────────────────────────

class TTSError(Exception):
    """
    Raised when TTS generation fails at any stage.
    The message is safe to surface in API responses (no stack trace,
    no secrets).
    """


# ── Service class ─────────────────────────────────────────────────────────────

class HindiTTSService:
    """
    Hindi TTS service backed by AI4Bharat Indic Parler-TTS.

    Model loading is deferred to the first call to generate_audio()
    so the FastAPI server starts instantly even before the model warms up.

    Thread safety: the model is loaded once under a simple guard flag.
    For production multi-worker deployments, load the model at startup
    in the FastAPI lifespan handler instead.
    """

    # Voice description sent to Parler-TTS to control voice characteristics.
    # Tuned for an Indian farmer audience: clear, moderate speed, warm tone.
    _VOICE_DESCRIPTION: str = (
        "A female speaker delivers clear Hindi speech at a moderate, "
        "easy-to-follow pace. The voice is warm and friendly, with slight "
        "expressiveness suitable for agricultural advice. "
        "The recording has no background noise."
    )

    _MAX_TEXT_LENGTH: int = 1000
    _MIN_TEXT_LENGTH: int = 1

    def __init__(
        self,
        model_id: str = "ai4bharat/indic-parler-tts",
        audio_dir: str = "generated_audio",
        hf_token: Optional[str] = None,
    ) -> None:
        """
        Args:
            model_id:  HuggingFace model identifier.
            audio_dir: Directory where WAV files are saved.
            hf_token:  HuggingFace auth token — NEVER logged.
        """
        self._model_id = model_id
        self._audio_dir = Path(audio_dir)
        self._hf_token = hf_token   # intentionally not logged anywhere
        self._device: Optional[str] = None
        self._model = None
        self._tokenizer = None
        self._desc_tokenizer = None
        self._loaded: bool = False

        self._audio_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "HindiTTSService created | model=%s | audio_dir=%s",
            model_id, self._audio_dir,
        )

    # ── Model lifecycle ───────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """
        Load the Parler-TTS model and tokenizers.  Called at most once.

        Raises:
            TTSError: If the model cannot be loaded (missing package,
                      network error, authentication failure).
        """
        if self._loaded:
            return

        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise TTSError(
                "TTS packages not installed. Run: "
                "pip install git+https://github.com/huggingface/parler-tts.git soundfile torch"
            ) from exc

        import torch

        self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logger.info(
            "Loading TTS model | model=%s | device=%s", self._model_id, self._device
        )
        t0 = time.perf_counter()

        hf_kwargs: dict = {}
        if self._hf_token:
            hf_kwargs["token"] = self._hf_token

        try:
            self._model = (
                ParlerTTSForConditionalGeneration
                .from_pretrained(self._model_id, **hf_kwargs)
                .to(self._device)
            )
            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_id, **hf_kwargs
            )
            self._desc_tokenizer = AutoTokenizer.from_pretrained(
                self._model_id, **hf_kwargs
            )
        except Exception as exc:
            logger.error("TTS model load failed: %s", type(exc).__name__)
            raise TTSError("Model loading failed — check HF_TOKEN and network") from exc

        elapsed = time.perf_counter() - t0
        self._loaded = True
        logger.info(
            "TTS model ready | device=%s | load_time=%.1fs", self._device, elapsed
        )

    # ── Inference ─────────────────────────────────────────────────────────────

    def _infer(self, text: str):
        """
        Run model inference on ``text``.

        Returns:
            numpy.ndarray: Raw audio samples.

        Raises:
            TTSError: On inference failure.
        """
        import torch

        try:
            prompt_inputs = self._tokenizer(text, return_tensors="pt").to(self._device)
            desc_inputs = self._desc_tokenizer(
                self._VOICE_DESCRIPTION, return_tensors="pt"
            ).to(self._device)

            with torch.no_grad():
                generation = self._model.generate(
                    input_ids=desc_inputs.input_ids,
                    attention_mask=desc_inputs.attention_mask,
                    prompt_input_ids=prompt_inputs.input_ids,
                    prompt_attention_mask=prompt_inputs.attention_mask,
                )

            return generation.cpu().numpy().squeeze()

        except Exception as exc:
            logger.error("Inference error: %s", type(exc).__name__)
            raise TTSError("Voice generation failed during inference") from exc

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_audio(self, text: str) -> str:
        """
        Generate Hindi speech and save it as a WAV file.

        Args:
            text: Hindi text to speak. Should be 1–3 sentences, max 1000 chars.

        Returns:
            Absolute path to the saved WAV file (in audio_dir).

        Raises:
            TTSError: On empty input, inference failure, or save failure.
        """
        import soundfile as sf

        # ── Input validation ───────────────────────────────────────────────
        text_stripped = (text or "").strip()
        if len(text_stripped) < self._MIN_TEXT_LENGTH:
            raise TTSError("Input text is empty")
        if len(text_stripped) > self._MAX_TEXT_LENGTH:
            raise TTSError(
                f"Input text too long ({len(text_stripped)} chars, max {self._MAX_TEXT_LENGTH})"
            )

        # ── Ensure model is ready ─────────────────────────────────────────
        self._load_model()

        # ── Generate audio ────────────────────────────────────────────────
        filename = f"alert_{uuid.uuid4().hex[:12]}.wav"
        output_path = self._audio_dir / filename

        logger.info(
            "TTS generation started | device=%s | text_len=%d chars",
            self._device, len(text_stripped),
        )
        t0 = time.perf_counter()

        try:
            audio_array = self._infer(text_stripped)
        except TTSError:
            raise
        except Exception as exc:
            logger.error("TTS inference failed: %s", type(exc).__name__)
            raise TTSError("Voice generation failed during inference") from exc

        elapsed = time.perf_counter() - t0
        logger.info("TTS generation completed | time=%.2fs | file=%s", elapsed, filename)

        # ── Save WAV ──────────────────────────────────────────────────────
        try:
            sf.write(
                str(output_path),
                audio_array,
                self._model.config.sampling_rate,
            )
        except Exception as exc:
            logger.error("Audio save failed: %s", type(exc).__name__)
            raise TTSError("Failed to save audio file") from exc

        size_kb = output_path.stat().st_size // 1024
        logger.info("Audio saved | path=%s | size=%dKB", output_path, size_kb)
        return str(output_path)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def device(self) -> Optional[str]:
        """Device in use (cpu / cuda:0). None if model not yet loaded."""
        return self._device

    @property
    def is_loaded(self) -> bool:
        """True after the first successful model load."""
        return self._loaded


# ── Process-level singleton ───────────────────────────────────────────────────
# get_tts_service() is the public accessor — all FastAPI routes use this.

_instance: Optional[HindiTTSService] = None


def get_tts_service() -> HindiTTSService:
    """
    Return the process-level HindiTTSService singleton.

    Creates the instance on first call using settings from config.py.
    The underlying model is loaded lazily (on first generate_audio() call).
    """
    global _instance
    if _instance is None:
        from whatsapp_service.config import get_settings
        s = get_settings()
        _instance = HindiTTSService(
            model_id=s.tts_model_id,
            audio_dir=s.tts_audio_dir,
            hf_token=s.hf_token,
        )
    return _instance
