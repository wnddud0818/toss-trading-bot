from __future__ import annotations

import logging

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class DiscordNotifier:
    def __init__(self, settings: Settings):
        self.webhook_url = settings.discord_webhook_url
        self.timeout = settings.toss.timeout_seconds

    def send(self, content: str) -> None:
        if not self.webhook_url:
            logger.info("Discord webhook is not configured: %s", content)
            return
        try:
            response = httpx.post(self.webhook_url, json={"content": content[:1900]}, timeout=self.timeout)
            response.raise_for_status()
        except Exception:
            logger.exception("Failed to send Discord notification")
