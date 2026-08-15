#!/usr/bin/env python
"""
test_conversation.py — Interactive JalSense mock WhatsApp CLI.

Runs the full farmer conversation flow in your terminal without
needing an active Twilio account.

Usage:
    python test_conversation.py
    python test_conversation.py whatsapp:+919999999999   # custom number

Type 'exit' to quit the session.
"""

import logging
import sys

# Suppress library noise in the CLI — keep it readable
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(name)s | %(message)s",
    stream=sys.stderr,
)

from whatsapp_service.mock_whatsapp import MockWhatsApp


def main() -> None:
    from_number = sys.argv[1] if len(sys.argv) > 1 else "whatsapp:+919876543210"
    transport = MockWhatsApp()
    transport.interactive_cli(from_number=from_number)


if __name__ == "__main__":
    main()
