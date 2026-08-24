"""
conversation.py — In-memory conversation state store with state machine support.

Keeps track of conversation state, village, crop, and query timestamp
per farmer phone number.  Designed to be swapped for a Redis- or
PostgreSQL-backed implementation without changing the interface.
"""

import enum
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationState(str, enum.Enum):
    """
    Conversation state machine states.

    Transition diagram:
        NEW_USER            → WAITING_FOR_VILLAGE  (any message / greeting)
        WAITING_FOR_VILLAGE → WAITING_FOR_CROP     (valid village input)
        WAITING_FOR_CROP    → ANALYZING            (valid crop input)
        ANALYZING           → RESULT               (immediately after analysis)
        any state           → WAITING_FOR_VILLAGE  (restart / greeting command)
    """

    NEW_USER = "NEW_USER"
    WAITING_FOR_VILLAGE = "WAITING_FOR_VILLAGE"
    WAITING_FOR_CROP = "WAITING_FOR_CROP"
    ANALYZING = "ANALYZING"
    RESULT = "RESULT"


@dataclass
class ConversationSession:
    """State stored for a single farmer (keyed by phone number)."""

    from_number: str
    state: ConversationState = ConversationState.NEW_USER
    village: Optional[str] = None
    crop: Optional[str] = None
    crop_raw: Optional[str] = None          # What the farmer originally typed
    last_query_at: Optional[datetime] = None
    query_count: int = 0


class ConversationStore:
    """
    Thread-safe in-memory store for conversation sessions.

    Interface contract (to be preserved when swapping backends):
        get(from_number)               -> Optional[ConversationSession]
        upsert(from_number, **fields)  -> ConversationSession
        clear(from_number)             -> bool
        all_sessions()                 -> list[ConversationSession]
    """

    def __init__(self) -> None:
        self._store: dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    # ── Public API ─────────────────────────────────────────────────────────

    def get(self, from_number: str) -> Optional[ConversationSession]:
        """Return the session for ``from_number``, or ``None`` if not found."""
        with self._lock:
            session = self._store.get(from_number)
        if session:
            logger.debug(
                "Session found for %s | state=%s | queries=%d",
                from_number, session.state, session.query_count,
            )
        return session

    def upsert(
        self,
        from_number: str,
        state: Optional[ConversationState] = None,
        village: Optional[str] = None,
        crop: Optional[str] = None,
        crop_raw: Optional[str] = None,
    ) -> ConversationSession:
        """
        Create or update a session for ``from_number``.

        Only non-None fields overwrite existing values, so partial updates
        (e.g. only state changed) are safe.
        """
        with self._lock:
            existing = self._store.get(from_number)
            if existing is None:
                existing = ConversationSession(from_number=from_number)
                logger.info("New session created for %s", from_number)

            if state is not None:
                existing.state = state
            if village is not None:
                existing.village = village
            if crop is not None:
                existing.crop = crop
            if crop_raw is not None:
                existing.crop_raw = crop_raw

            existing.last_query_at = datetime.now(tz=timezone.utc)
            existing.query_count += 1
            self._store[from_number] = existing

        logger.debug(
            "Session upserted | number=%s | state=%s | village=%s | crop=%s | count=%d",
            from_number,
            existing.state,
            existing.village,
            existing.crop,
            existing.query_count,
        )
        return existing

    def clear(self, from_number: str) -> bool:
        """
        Remove the session for ``from_number``.
        Returns ``True`` if a session was deleted, ``False`` if none existed.
        """
        with self._lock:
            existed = from_number in self._store
            if existed:
                del self._store[from_number]
                logger.info("Session cleared for %s", from_number)
        return existed

    def all_sessions(self) -> list[ConversationSession]:
        """Return a snapshot of all active sessions (for debugging)."""
        with self._lock:
            return list(self._store.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


# ── Module-level singleton ────────────────────────────────────────────────────
# Imported and used directly by conversation_handler / main.
# Replace with a factory returning a Redis-backed store when ready.
conversation_store = ConversationStore()
