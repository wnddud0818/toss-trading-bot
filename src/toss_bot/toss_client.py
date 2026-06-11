from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from .config import Settings
from .models import OrderRequest


class TossApiError(RuntimeError):
    def __init__(self, status_code: int, code: str | None, message: str):
        super().__init__(f"Toss API error {status_code} {code or ''}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass
class TokenCache:
    access_token: str | None = None
    expires_at: float = 0

    def valid(self, refresh_margin_seconds: int) -> bool:
        return self.access_token is not None and time.time() < self.expires_at - refresh_margin_seconds


class TossClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self._client = client or httpx.Client(
            base_url=settings.toss.base_url,
            timeout=settings.toss.timeout_seconds,
        )
        self._token = TokenCache()

    def close(self) -> None:
        self._client.close()

    def issue_token(self) -> str:
        if not self.settings.toss_client_id or not self.settings.toss_client_secret:
            raise TossApiError(0, "missing-credentials", "Toss credentials are missing")
        response = self._client.post(
            "/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.toss_client_id,
                "client_secret": self.settings.toss_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            self._raise_for_response(response)
        payload = response.json()
        self._token = TokenCache(
            access_token=payload["access_token"],
            expires_at=time.time() + int(payload.get("expires_in", 0)),
        )
        return self._token.access_token

    def token(self) -> str:
        if not self._token.valid(self.settings.toss.token_refresh_margin_seconds):
            return self.issue_token()
        assert self._token.access_token is not None
        return self._token.access_token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        account_required: bool = False,
        retry_expired: bool = True,
    ) -> Any:
        headers = {"Authorization": f"Bearer {self.token()}"}
        if account_required:
            if self.settings.toss_account_seq is None:
                raise TossApiError(0, "missing-account", "TOSSINVEST_ACCOUNT_SEQ is missing")
            headers["X-Tossinvest-Account"] = str(self.settings.toss_account_seq)

        response = self._client.request(method, path, params=params, json=json, headers=headers)
        if response.status_code == 429:
            self._sleep_for_rate_limit(response)
            response = self._client.request(method, path, params=params, json=json, headers=headers)
        if response.status_code == 401 and retry_expired:
            error_code = self._error_code(response)
            if error_code == "expired-token":
                self.issue_token()
                return self.request(
                    method,
                    path,
                    params=params,
                    json=json,
                    account_required=account_required,
                    retry_expired=False,
                )
        if response.status_code >= 400:
            self._raise_for_response(response)
        payload = response.json()
        return payload.get("result", payload) if isinstance(payload, dict) else payload

    def get_accounts(self) -> Any:
        return self.request("GET", "/api/v1/accounts")

    def get_prices(self, symbols: list[str]) -> Any:
        return self.request("GET", "/api/v1/prices", params={"symbols": ",".join(symbols)})

    def get_candles(self, symbol: str, interval: str, count: int = 100, before: str | None = None) -> Any:
        params: dict[str, Any] = {"symbol": symbol, "interval": interval, "count": count}
        if before:
            params["before"] = before
        return self.request("GET", "/api/v1/candles", params=params)

    def get_orderbook(self, symbol: str) -> Any:
        return self.request("GET", "/api/v1/orderbook", params={"symbol": symbol})

    def get_price_limit(self, symbol: str) -> Any:
        return self.request("GET", "/api/v1/price-limits", params={"symbol": symbol})

    def get_stocks(self, symbols: list[str]) -> Any:
        return self.request("GET", "/api/v1/stocks", params={"symbols": ",".join(symbols)})

    def get_stock_warnings(self, symbol: str) -> Any:
        return self.request("GET", f"/api/v1/stocks/{symbol}/warnings")

    def get_market_calendar(self, country: str = "KR", date: str | None = None) -> Any:
        params = {"date": date} if date else None
        return self.request("GET", f"/api/v1/market-calendar/{country}", params=params)

    def get_exchange_rate(self, base_currency: str = "USD", quote_currency: str = "KRW") -> Any:
        return self.request(
            "GET",
            "/api/v1/exchange-rate",
            params={"baseCurrency": base_currency, "quoteCurrency": quote_currency},
        )

    def get_holdings(self, symbol: str | None = None) -> Any:
        params = {"symbol": symbol} if symbol else None
        return self.request("GET", "/api/v1/holdings", params=params, account_required=True)

    def get_buying_power(self, currency: str = "KRW") -> Any:
        return self.request(
            "GET",
            "/api/v1/buying-power",
            params={"currency": currency},
            account_required=True,
        )

    def get_sellable_quantity(self, symbol: str) -> Any:
        return self.request(
            "GET",
            "/api/v1/sellable-quantity",
            params={"symbol": symbol},
            account_required=True,
        )

    def get_commissions(self) -> Any:
        return self.request("GET", "/api/v1/commissions", account_required=True)

    def get_open_orders(
        self,
        symbol: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Any:
        params = {"status": "OPEN"}
        if symbol:
            params["symbol"] = symbol
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self.request("GET", "/api/v1/orders", params=params, account_required=True)

    def get_order(self, order_id: str) -> Any:
        return self.request("GET", f"/api/v1/orders/{order_id}", account_required=True)

    def create_order(self, order: OrderRequest) -> Any:
        body: dict[str, str] = {
            "clientOrderId": order.client_order_id or "",
            "symbol": order.symbol,
            "side": order.side.value,
            "orderType": order.order_type.value,
            "timeInForce": order.time_in_force,
            "quantity": self._decimal_text(order.quantity),
        }
        if not body["clientOrderId"]:
            body.pop("clientOrderId")
        if not body["timeInForce"]:
            body.pop("timeInForce")
        if order.price is not None:
            body["price"] = self._decimal_text(order.price)
        return self.request("POST", "/api/v1/orders", json=body, account_required=True)

    def cancel_order(self, order_id: str) -> Any:
        return self.request("POST", f"/api/v1/orders/{order_id}/cancel", json={}, account_required=True)

    def modify_order(self, order_id: str, order: OrderRequest) -> Any:
        body: dict[str, str] = {
            "orderType": order.order_type.value,
            "timeInForce": order.time_in_force,
            "quantity": self._decimal_text(order.quantity),
        }
        if not body["timeInForce"]:
            body.pop("timeInForce")
        if order.price is not None:
            body["price"] = self._decimal_text(order.price)
        return self.request("POST", f"/api/v1/orders/{order_id}/modify", json=body, account_required=True)

    def _sleep_for_rate_limit(self, response: httpx.Response) -> None:
        raw = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Reset") or "1"
        try:
            seconds = float(raw)
        except ValueError:
            seconds = 1.0
        time.sleep(min(max(seconds, 0.1), 30.0))

    def _raise_for_response(self, response: httpx.Response) -> None:
        try:
            payload = response.json()
        except ValueError:
            body = response.text.strip().replace("\r", " ").replace("\n", " ")
            if len(body) > 500:
                body = body[:500] + "...(truncated)"
            content_type = response.headers.get("content-type", "unknown")
            raise TossApiError(response.status_code, None, f"non-JSON response content-type={content_type}: {body}")
        if "error" in payload and isinstance(payload["error"], str):
            raise TossApiError(response.status_code, payload.get("error"), payload.get("error_description", ""))
        error = payload.get("error") or payload.get("result") or payload
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else str(payload)
        raise TossApiError(response.status_code, code, message)

    def _error_code(self, response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        error = payload.get("error") or payload
        return error.get("code") if isinstance(error, dict) else None

    def _decimal_text(self, value: Decimal) -> str:
        return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")
