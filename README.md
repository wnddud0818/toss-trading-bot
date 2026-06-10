# Toss Trading Bot

토스증권 Open API로 국내주식(KOSPI/KOSDAQ)을 자동 매매하는 Python 트레이딩 봇입니다.

이 봇은 단기 수익률을 높일 가능성이 있는 **유동성 상위 종목의 추세 추종 + 장중 돌파 매매**를 기본 전략으로 사용합니다. 다만 자동매매에서 가장 큰 위험은 “수익 기회를 놓치는 것”보다 “잘못된 주문이 계속 나가는 것”이므로, 실거래 모드는 여러 개의 잠금장치가 모두 열려야만 동작합니다.

투자 수익을 보장하지 않습니다. 실거래 전에는 충분한 백테스트, 모의 운용, 소액 검증을 반드시 거쳐야 합니다.

## 참고 문서

- `docs/tossinvest-openapi-ai-reference.md`
- `docs/tossinvest-openapi-examples.md`
- 공식 안내: <https://developers.tossinvest.com/llms.txt>

주요 사용 API는 OAuth2 토큰, 국내 장 캘린더, 현재가, 캔들, 호가, 상하한가, 종목 경고, 계좌, 보유주식, 매수가능금액, 매도가능수량, 주문 생성/조회/취소/정정, 수수료 조회입니다.

## 설치

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

`.env`에 토스증권 Open API 값을 넣습니다.

```powershell
TOSSINVEST_CLIENT_ID=
TOSSINVEST_CLIENT_SECRET=
TOSSINVEST_ACCOUNT_SEQ=
DISCORD_WEBHOOK_URL=
ENABLE_LIVE_TRADING=false
```

설치 후 기본 점검을 실행합니다.

```powershell
toss-bot doctor
```

`doctor`는 인증, 계좌, 국내 장 캘린더, 국내 수수료 설정을 확인합니다.

## 실행 명령

```powershell
toss-bot backtest --from 2026-01-01 --to 2026-06-01
toss-bot run --mode paper
toss-bot run --mode paper --once
toss-bot reconcile --cancel-stale
toss-bot report --date 2026-06-10
```

실거래는 아래 조건이 모두 맞아야 실행됩니다.

```powershell
# config/settings.yaml
mode: live

# 실행 명령
toss-bot run --mode live

# .env
ENABLE_LIVE_TRADING=true
```

또한 `risk.paper_trading_days_completed`가 `risk.min_paper_trading_days` 이상이어야 합니다. 기본값은 20거래일입니다.

## 전략 개요

전략은 국내주식 단기 추세 추종에 맞춰 설계했습니다.

1. KOSPI/KOSDAQ에서 거래대금 상위 종목을 가져옵니다.
2. Toss 종목 정보로 KRW, ACTIVE, 보통주, 거래정지/정리매매 아님을 확인합니다.
3. 투자경고, 투자위험, 단기과열, VI, 신주인수권 등 제외 경고를 필터링합니다.
4. 20/60/120일 모멘텀을 변동성으로 나눠 상대강도를 계산합니다.
5. 추세 품질, 거래량 축적, 최근 고점 근접도, 거래대금 점수를 더합니다.
6. 장중 1분봉에서 전일 고가 또는 장중 박스권을 거래량과 함께 돌파할 때만 진입합니다.
7. VWAP 아래 돌파, 장중 과열, 과도한 갭상승, 상한가 근접 추격은 막습니다.
8. 손절, 트레일링 스탑, 이익 보호 스탑, 장중 급락, 시장 위험 회피, 최대 보유일로 청산합니다.

핵심 방향은 “크게 움직일 가능성이 있는 종목을 고르되, 이미 너무 뜨거운 구간에서는 따라붙지 않는 것”입니다.

## 실거래 안전장치

실제 주문 전에는 `ExecutionPlanner`가 아래 조건을 확인합니다.

- `/api/v1/orderbook`: 스프레드가 너무 넓으면 거절
- `/api/v1/orderbook`: 호가 잔량 대비 참여율을 제한해 주문 수량 축소
- `/api/v1/price-limits`: 상한가 근접 매수와 하한가 밖 매도 차단
- 국내주식 호가 단위에 맞춰 지정가 정렬
- 최소 주문 금액 미만 주문 차단
- 매수 가능 금액 확인
- 매도 가능 수량 확인
- 같은 종목 반대 방향 미체결 주문 확인
- 주문별 최대 금액 제한
- `clientOrderId` 생성으로 중복 요청 추적
- 주문 감사 로그 저장

장 운영 안전장치도 추가되어 있습니다.

- `/api/v1/market-calendar/KR` 기준으로 정규장 밖 주문 루프 차단
- 종가 단일가 시작 이후 신규 진입 차단
- `toss-bot reconcile --cancel-stale`로 오래된 미체결 국내주식 주문 취소
- 스케줄러가 장중 5분마다 미체결 주문을 점검

## 주요 설정

`config/settings.yaml`에서 조정합니다.

### universe

- `liquidity_top_n`: KRX 거래대금 상위 후보 수
- `watch_top_n`: Toss API로 검증할 후보 수
- `min_trading_value_krw`: 최소 거래대금
- `include_etf`: ETF 포함 여부
- `excluded_warning_types`: 제외할 Toss 종목 경고

### strategy

- `momentum_windows`: 모멘텀 기간
- `momentum_weights`: 기간별 가중치
- `trend_quality_weight`: 20일선/60일선 정렬 강도 가중치
- `volume_accumulation_weight`: 최근 거래량 축적 가중치
- `high_proximity_weight`: 최근 고점 근접 가중치
- `liquidity_weight`: 거래대금 가중치
- `min_20d_return_pct`, `min_60d_return_pct`: 최소 추세 수익률
- `max_5d_return_pct`: 단기 급등주 배제 기준
- `max_drawdown_from_high_pct`: 최근 고점 대비 낙폭 제한
- `require_vwap_confirmation`: VWAP 위 돌파만 허용
- `max_intraday_extension_pct`: 장중 과열 추격 제한
- `stop_loss_pct`: 고정 손절
- `trailing_stop_pct`: 기본 트레일링 스탑
- `profit_lock_trigger_pct`: 이익 보호 트레일링 시작 수익률
- `profit_lock_trailing_stop_pct`: 이익 보호 구간 트레일링 폭

### risk

- `max_symbol_weight`: 한 종목 최대 비중
- `min_cash_weight`: 유지 현금 비중
- `target_position_volatility_pct`: 변동성이 큰 종목의 주문금액 축소 기준
- `max_entry_risk_pct`: 1회 진입에서 감수할 계좌 손실 한도
- `daily_loss_limit_pct`: 일 손실 한도
- `weekly_loss_limit_pct`: 주 손실 한도
- `max_drawdown_pct`: 고점 대비 최대 낙폭 한도
- `max_live_order_amount_krw`: 실거래 1주문 최대 금액
- `min_paper_trading_days`: 실거래 전 최소 모의 운용일

### execution

- `max_entry_spread_bps`: 신규 진입 허용 최대 스프레드
- `max_exit_spread_bps`: 청산 허용 최대 스프레드
- `max_chase_bps`: 기준가 대비 추격 허용 폭
- `max_orderbook_participation`: 호가 잔량 대비 최대 참여율
- `price_limit_buffer_pct`: 상하한가 근접 회피 폭
- `stale_order_minutes`: 미체결 주문을 오래된 주문으로 보는 시간
- `cancel_stale_orders`: 스케줄러 미체결 주문 취소 여부

## 운영 순서

1. `toss-bot doctor`로 인증과 계좌 상태를 확인합니다.
2. `toss-bot backtest`로 전략이 비용 포함 후에도 의미 있는지 확인합니다.
3. `mode: paper`에서 최소 20거래일 이상 `toss-bot run --mode paper`를 돌립니다.
4. `reports/YYYY-MM-DD.md`에서 주문 감사와 체결 기록을 확인합니다.
5. 실거래 전 `max_live_order_amount_krw`를 아주 작게 낮춰 소액 검증합니다.
6. 실거래는 `.env`, 설정 파일, CLI 인자가 모두 live 조건을 만족할 때만 실행합니다.

## 개발 검증

```powershell
python -m pytest
python -m toss_bot --help
```

현재 테스트는 전략, 리스크, Toss 클라이언트, 실행 플래너, 브로커, 유니버스, 장 캘린더, 미체결 주문 정리를 검증합니다.

## 주의할 점

- 자동매매는 손실이 날 수 있습니다.
- API 응답 형식이나 거래 가능 시간은 바뀔 수 있으므로 공식 OpenAPI 문서를 수시로 확인해야 합니다.
- 수수료와 세금, 슬리피지, 미체결, 상하한가, 거래정지, VI는 백테스트보다 실거래 성과를 크게 낮출 수 있습니다.
- 라이브 모드 전환 전에는 반드시 소액으로 주문 생성, 취소, 매도 가능 수량 확인까지 검증하세요.
