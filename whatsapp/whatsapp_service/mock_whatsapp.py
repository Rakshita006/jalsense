"""
mock_whatsapp.py — Simulated WhatsApp transport for offline development.

Allows full conversation testing without an active Twilio account.
When Twilio is reactivated, nothing in this module changes — it is only
used for local development and the pytest suite.

Usage:
    transport = MockWhatsApp()
    replies = transport.send_message("whatsapp:+919876543210", "Chitrakoot")
    for r in replies:
        print(r)

CLI:
    python test_conversation.py
"""

import logging
import sys
from typing import Optional

from whatsapp_service.conversation import ConversationStore
from whatsapp_service.conversation_handler import handle_message

logger = logging.getLogger(__name__)

_DEFAULT_NUMBER = "whatsapp:+919876543210"


class MockWhatsApp:
    """
    Simulated WhatsApp message transport.

    Wraps ``handle_message()`` and provides an interactive REPL for
    manual end-to-end testing without Twilio.

    The real Twilio flow in ``main.py`` calls ``handle_message()`` directly
    in exactly the same way, so behaviour is identical.
    """

    def __init__(self, store: Optional[ConversationStore] = None) -> None:
        """
        Args:
            store: ConversationStore to use.  Defaults to the module-level
                   singleton inside handle_message.  Pass a fresh store in
                   tests for session isolation between test cases.
        """
        self._store = store  # None → singleton used inside handle_message

    def send_message(self, from_number: str, text: str) -> list[str]:
        """
        Simulate sending a WhatsApp message and return the bot's replies.

        Args:
            from_number: Simulated farmer phone number.
            text:        Message text to send.

        Returns:
            list[str]: Bot reply messages (usually one; two during analysis).
        """
        logger.debug("Inbound  | from=%s | text='%.60s'", from_number, text)
        replies = handle_message(from_number, text, store=self._store)
        for i, r in enumerate(replies):
            logger.debug("Outbound | to=%s | msg[%d]='%.60s'", from_number, i, r)
        return replies

    def interactive_cli(
        self,
        from_number: str = _DEFAULT_NUMBER,
        stream_in=None,
        stream_out=None,
    ) -> None:
        """
        Interactive REPL loop that simulates a WhatsApp conversation.

        Reads from ``stream_in`` (defaults to stdin) and writes to
        ``stream_out`` (defaults to stdout).  Passing StringIO objects
        makes this fully testable without blocking.

        Type 'exit' or press Ctrl+C to quit.
        """
        _in = stream_in or sys.stdin
        _out = stream_out or sys.stdout

        def _print(msg: str) -> None:
            _out.write(msg + "\n")
            _out.flush()

        _print("=" * 56)
        _print("  JalSense Mock WhatsApp CLI")
        _print(f"  Farmer : {from_number}")
        _print("  Type 'exit' to quit.")
        _print("=" * 56)
        _print("")

        while True:
            try:
                _out.write("You: ")
                _out.flush()
                line = _in.readline()
            except (EOFError, KeyboardInterrupt):
                _print("\nGoodbye!")
                break

            if not line:          # EOF on piped input
                break

            user_input = line.rstrip("\n").strip()

            if user_input.lower() in ("exit", "quit", "bye"):
                _print("Goodbye!")
                break

            if not user_input:
                continue

            replies = self.send_message(from_number, user_input)
            for reply in replies:
                _print(f"\nBot: {reply}\n")
