#!/usr/bin/env python3
"""
CREATED_BY_AGENT
"""

from __future__ import annotations

import sys
from pathlib import Path

import cyclopts
from loguru import logger

from app.services.image_generation_service import image_generation_service


def _load_message(message: str | None, message_txt: Path | None) -> str:
    if message and message_txt:
        raise ValueError("Only one of --message or --message-txt can be provided.")
    if not message and not message_txt:
        raise ValueError("Either --message or --message-txt is required.")

    if message_txt:
        logger.debug("Loading message from file: {}", message_txt)
        text = message_txt.read_text(encoding="utf-8")
        message = text.strip()
    else:
        message = message.strip()

    if not message:
        raise ValueError("Message is empty.")

    return message


def _build_prompt(message: str) -> str:
    logger.debug("Building image prompt from message")
    return image_generation_service.build_image_prompt(
        agent_data={},
        chat_history=[],
        user_message=message,
        user_info="",
    )


def main(message: str | None = None, message_txt: Path | None = None) -> None:
    user_message = _load_message(message, message_txt)
    prompt = _build_prompt(user_message)
    sys.stdout.write(prompt)


if __name__ == "__main__":
    cyclopts.run(main)
