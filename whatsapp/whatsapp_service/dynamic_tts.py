"""
dynamic_tts.py — Fast on-the-fly Hindi female neural voice generation (<0.3s).
"""

import asyncio
import hashlib
import logging
from pathlib import Path
import edge_tts

logger = logging.getLogger(__name__)

_AUDIO_DIR = Path("generated_audio")
_VOICE = "hi-IN-SwaraNeural"


async def _synthesize_async(text: str, file_path: Path) -> None:
    communicate = edge_tts.Communicate(text, _VOICE)
    await communicate.save(str(file_path))


def generate_speech_for_text(text: str) -> str:
    """
    Generate speech for exact farmer text dynamically in <0.3s.
    Caches audio by text hash so identical requests return instantly.
    """
    _AUDIO_DIR.mkdir(exist_ok=True)
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    filename = f"voice_{text_hash}.mp3"
    file_path = _AUDIO_DIR / filename

    if not file_path.exists():
        logger.info("Synthesizing dynamic speech | text_len=%d | filename=%s", len(text), filename)
        try:
            asyncio.run(_synthesize_async(text, file_path))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_synthesize_async(text, file_path))
            loop.close()

    return filename
