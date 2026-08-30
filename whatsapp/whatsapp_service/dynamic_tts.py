"""
dynamic_tts.py — Fast on-the-fly Hindi female neural voice generation (<0.3s).
"""

import hashlib
import logging
from pathlib import Path
import edge_tts

logger = logging.getLogger(__name__)

_AUDIO_DIR = Path("generated_audio")
_VOICE = "hi-IN-SwaraNeural"


async def generate_speech_for_text_async(text: str) -> str:
    """
    Generate speech for exact farmer text dynamically in <0.3s (Async for FastAPI).
    """
    _AUDIO_DIR.mkdir(exist_ok=True)
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    filename = f"voice_{text_hash}.mp3"
    file_path = _AUDIO_DIR / filename

    if not file_path.exists():
        logger.info("Synthesizing dynamic speech async | text_len=%d | filename=%s", len(text), filename)
        communicate = edge_tts.Communicate(text, _VOICE)
        await communicate.save(str(file_path))

    return filename


def generate_speech_for_text(text: str) -> str:
    """
    Synchronous helper for standalone scripts/tests.
    """
    import asyncio
    return asyncio.run(generate_speech_for_text_async(text))
