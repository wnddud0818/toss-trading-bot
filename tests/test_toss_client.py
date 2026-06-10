from __future__ import annotations

from decimal import Decimal

import httpx

from toss_bot.config import Settings
from toss_bot.models import OrderRequest, OrderSide, OrderType
from toss_bot.toss_client import TossClient


def test_token_refreshes_after_expired_token():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url.path))
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"access_token": f"token-{len(calls)}", "token_type": "Bearer", "expires_in": 3600})
        if calls.count("/api/v1/accounts") == 1:
            return httpx.Response(401, json={"error": {"code": "expired-token", "message": "expired"}})
        return httpx.Response(200, json={"result": [{"accountSeq": 1}]})

    settings = Settings(toss_client_id="id", toss_client_secret="secret")
    client = TossClient(settings, httpx.Client(transport=httpx.MockTransport(handler), base_url=settings.toss.base_url))

    accounts = client.get_accounts()

    assert accounts == [{"accountSeq": 1}]
    assert calls.count("/oauth2/token") == 2


def test_429_retries_once_with_rate_limit_headers():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url.path))
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600})
        if calls.count("/api/v1/accounts") == 1:
            return httpx.Response(429, headers={"X-RateLimit-Reset": "0"}, json={"error": {"code": "rate-limit"}})
        return httpx.Response(200, json={"result": []})

    settings = Settings(toss_client_id="id", toss_client_secret="secret")
    client = TossClient(settings, httpx.Client(transport=httpx.MockTransport(handler), base_url=settings.toss.base_url))

    assert client.get_accounts() == []
    assert calls.count("/api/v1/accounts") == 2


def test_request_returns_bare_list_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600})
        return httpx.Response(200, json=[{"accountSeq": 1}])

    settings = Settings(toss_client_id="id", toss_client_secret="secret")
    client = TossClient(settings, httpx.Client(transport=httpx.MockTransport(handler), base_url=settings.toss.base_url))

    assert client.get_accounts() == [{"accountSeq": 1}]


def test_price_limit_wrapper_uses_toss_endpoint():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, dict(request.url.params)))
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600})
        return httpx.Response(200, json={"result": {"upperLimitPrice": "13000", "lowerLimitPrice": "7000"}})

    settings = Settings(toss_client_id="id", toss_client_secret="secret")
    client = TossClient(settings, httpx.Client(transport=httpx.MockTransport(handler), base_url=settings.toss.base_url))

    result = client.get_price_limit("000001")

    assert result["upperLimitPrice"] == "13000"
    assert ("/api/v1/price-limits", {"symbol": "000001"}) in seen


def test_create_order_sends_day_time_in_force_and_account_header():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth2/token":
            return httpx.Response(200, json={"access_token": "token", "token_type": "Bearer", "expires_in": 3600})
        seen.append((request.url.path, request.headers.get("X-Tossinvest-Account"), request.read()))
        return httpx.Response(200, json={"result": {"orderId": "order-1", "clientOrderId": "client-1"}})

    settings = Settings(toss_client_id="id", toss_client_secret="secret", toss_account_seq=7)
    client = TossClient(settings, httpx.Client(transport=httpx.MockTransport(handler), base_url=settings.toss.base_url))

    result = client.create_order(
        OrderRequest(
            "005930",
            OrderSide.BUY,
            OrderType.LIMIT,
            quantity=Decimal("10"),
            price=Decimal("70000"),
            client_order_id="client-1",
        )
    )

    assert result["orderId"] == "order-1"
    assert seen[0][0] == "/api/v1/orders"
    assert seen[0][1] == "7"
    assert b'"timeInForce":"DAY"' in seen[0][2]
