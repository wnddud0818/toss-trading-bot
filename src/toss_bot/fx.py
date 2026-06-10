from __future__ import annotations

import logging
import time
from decimal import Decimal

from .config import FxSettings
from .models import Currency
from .utils import dec

logger = logging.getLogger(__name__)


class FxRateProvider:
    """USD/KRW 환율 캐시. Toss 환율 API 실패 시 마지막 값, 그것도 없으면 설정 fallback을 쓴다."""

    def __init__(self, toss_client, settings: FxSettings):
        self.toss_client = toss_client
        self.settings = settings
        self._rate: Decimal | None = None
        self._fetched_at: float = 0.0

    def usd_krw(self) -> Decimal:
        now = time.time()
        if self._rate is not None and now - self._fetched_at < self.settings.refresh_minutes * 60:
            return self._rate
        try:
            payload = self.toss_client.get_exchange_rate("USD", "KRW")
            rate = dec(payload.get("midRate") or payload.get("rate") or 0)
            if rate > 0:
                self._rate = rate
                self._fetched_at = now
                return rate
        except Exception:
            logger.warning("Exchange rate fetch failed; using cached or fallback rate", exc_info=True)
        if self._rate is not None:
            return self._rate
        return dec(self.settings.fallback_usd_krw)

    def to_krw(self, amount: Decimal, currency: Currency) -> Decimal:
        if currency == Currency.KRW:
            return amount
        return amount * self.usd_krw()

    def from_krw(self, amount: Decimal, currency: Currency) -> Decimal:
        if currency == Currency.KRW:
            return amount
        return amount / self.usd_krw()
