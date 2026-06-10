from __future__ import annotations

from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR

from .models import Currency, MarketCountry

KR_SEGMENTS = {"KOSPI", "KOSDAQ", "KR_ETC"}
US_SEGMENTS = {"NYSE", "NASDAQ", "AMEX", "US_ETC"}

CURRENCY_BY_MARKET = {
    MarketCountry.KR: Currency.KRW,
    MarketCountry.US: Currency.USD,
}

MONEY_STEP = {
    Currency.KRW: Decimal("1"),
    Currency.USD: Decimal("0.01"),
}

# Toss/KRX 심볼은 6자리 숫자, 미국 티커는 영문(BRK.B 등 '.', '-' 포함)이다.
def market_for_symbol(symbol: str) -> MarketCountry:
    return MarketCountry.KR if symbol.isdigit() else MarketCountry.US


def currency_for(market: MarketCountry) -> Currency:
    return CURRENCY_BY_MARKET[market]


def segments_for(market: MarketCountry) -> set[str]:
    return KR_SEGMENTS if market == MarketCountry.KR else US_SEGMENTS


def round_money(value: Decimal, currency: Currency) -> Decimal:
    return value.quantize(MONEY_STEP[currency], rounding=ROUND_DOWN)


def kr_tick_size(price: Decimal) -> Decimal:
    if price < Decimal("2000"):
        return Decimal("1")
    if price < Decimal("5000"):
        return Decimal("5")
    if price < Decimal("20000"):
        return Decimal("10")
    if price < Decimal("50000"):
        return Decimal("50")
    if price < Decimal("200000"):
        return Decimal("100")
    if price < Decimal("500000"):
        return Decimal("500")
    return Decimal("1000")


def us_tick_size(price: Decimal) -> Decimal:
    return Decimal("0.01") if price >= Decimal("1") else Decimal("0.0001")


def tick_size(price: Decimal, market: MarketCountry) -> Decimal:
    return kr_tick_size(price) if market == MarketCountry.KR else us_tick_size(price)


def align_price(price: Decimal, *, side: str, market: MarketCountry) -> Decimal:
    tick = tick_size(price, market)
    rounding = ROUND_CEILING if side == "BUY" else ROUND_FLOOR
    return (price / tick).to_integral_value(rounding=rounding) * tick


# FDR/S&P500 스크래핑 실패에 대비한 기본 미국 후보군. 유동성 상위 대형주 위주로,
# 실제 편입은 Toss 종목 검증과 거래대금 랭킹을 다시 거친다.
DEFAULT_US_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "BRK.B", "LLY",
    "JPM", "XOM", "UNH", "V", "WMT", "MA", "PG", "JNJ", "COST", "ORCL",
    "HD", "ABBV", "BAC", "MRK", "CVX", "KO", "NFLX", "AMD", "PEP", "ADBE",
    "CRM", "TMO", "WFC", "CSCO", "MCD", "ACN", "ABT", "LIN", "IBM", "GE",
    "TXN", "QCOM", "CAT", "DIS", "INTU", "AMAT", "VZ", "PFE", "GS", "AXP",
    "MS", "NKE", "RTX", "UBER", "HON", "AMGN", "BKNG", "NOW", "ISRG", "PLTR",
    "SPGI", "T", "LOW", "UNP", "COP", "SCHW", "ELV", "BLK", "SYK", "C",
    "BA", "DE", "PANW", "LMT", "MU", "GILD", "ADI", "SBUX", "MDLZ", "REGN",
]
