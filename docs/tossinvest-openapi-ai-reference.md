# 토스증권 Open API AI 개발 레퍼런스

- 생성일: 2026-06-09 18:26:15 KST
- OpenAPI 버전: `3.1.0`
- API 문서 버전: `1.0.3`
- Base URL: `https://openapi.tossinvest.com`
- 출처: https://developers.tossinvest.com/docs

## Source of Truth

- 브라우저 문서/출처: https://developers.tossinvest.com/docs
- LLM 안내 파일: https://developers.tossinvest.com/llms.txt
- 개요 Markdown: https://openapi.tossinvest.com/openapi-docs/overview.md
- Canonical OpenAPI JSON: https://openapi.tossinvest.com/openapi-docs/latest/openapi.json

이 문서는 위 OpenAPI JSON을 파싱해 AI 코딩 에이전트가 빠르게 참조할 수 있게 재구성한 요약형 계약서입니다. 정확한 최신 필드와 예시는 항상 OpenAPI JSON을 최종 기준으로 확인하세요.

요청/응답/스키마 예시 전체 추출본은 [tossinvest-openapi-examples.md](./tossinvest-openapi-examples.md)를 함께 참고하세요.

## 구현 핵심

- 모든 API는 OAuth 2.0 Client Credentials Grant로 발급한 액세스 토큰을 사용합니다.
- `Authorization: Bearer {access_token}` 헤더는 기본적으로 필요합니다. 단, 토큰 발급 엔드포인트는 폼 요청입니다.
- 계좌, 보유자산, 주문, 주문조회, 거래가능정보 API는 추가로 `X-Tossinvest-Account: {accountSeq}` 헤더가 필요합니다.
- 시장/종목/시세 정보 API는 사용자 계좌와 무관하므로 Bearer 토큰만으로 호출합니다.
- 에러 응답은 `error.requestId`, `error.code`, `error.message`, 선택적 `error.data`를 가진 envelope 형태입니다.
- 429 응답을 받으면 `Retry-After`를 우선 사용하고, 지수 백오프와 jitter를 적용하세요.

## 빠른 호출 흐름

```bash
curl -s -X POST 'https://openapi.tossinvest.com/oauth2/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=$TOSSINVEST_CLIENT_ID' \
  -d 'client_secret=$TOSSINVEST_CLIENT_SECRET'

curl -s 'https://openapi.tossinvest.com/api/v1/prices?symbols=005930' \
  -H 'Authorization: Bearer $ACCESS_TOKEN'

curl -s 'https://openapi.tossinvest.com/api/v1/holdings' \
  -H 'Authorization: Bearer $ACCESS_TOKEN' \
  -H 'X-Tossinvest-Account: 1'
```

## Rate Limits

Rate limit은 클라이언트와 API 그룹 단위로 적용됩니다. 정상 응답과 429 응답 모두에서 현재 한도를 응답 헤더로 확인할 수 있습니다.

| 그룹 | 기본 한도 | 피크 시간 한도 |
|---|---:|---|
| `AUTH` | 초당 5회 | - |
| `ACCOUNT` | 초당 1회 | - |
| `ASSET` | 초당 5회 | - |
| `STOCK` | 초당 5회 | - |
| `MARKET_INFO` | 초당 3회 | - |
| `MARKET_DATA` | 초당 10회 | - |
| `MARKET_DATA_CHART` | 초당 5회 | - |
| `ORDER` | 초당 6회 | 09:00-09:10 KST 초당 3회 |
| `ORDER_HISTORY` | 초당 5회 | - |
| `ORDER_INFO` | 초당 6회 | 09:00-09:10 KST 초당 3회 |

| 헤더 | 의미 |
|---|---|
| `X-RateLimit-Limit` | 현재 허용된 초당 요청 수 |
| `X-RateLimit-Remaining` | 남은 토큰 수 |
| `X-RateLimit-Reset` | 토큰 1개 재충전까지 예상 초 |
| `Retry-After` | 429 응답에서 권장 재시도 대기 초 |

## 엔드포인트 인덱스

| 그룹 | Method | Path | operationId | 계좌 헤더 | RateLimit | 설명 |
|---|---|---|---|---:|---|---|
| Auth | `POST` | `/oauth2/token` | `issueOAuth2Token` | N | `AUTH` | OAuth2 액세스 토큰 발급 |
| Market Data | `GET` | `/api/v1/candles` | `getCandles` | N | `MARKET_DATA_CHART` | 캔들 차트 조회 |
| Market Data | `GET` | `/api/v1/orderbook` | `getOrderbook` | N | `MARKET_DATA` | 호가 조회 |
| Market Data | `GET` | `/api/v1/price-limits` | `getPriceLimit` | N | `MARKET_DATA` | 상/하한가 조회 |
| Market Data | `GET` | `/api/v1/prices` | `getPrices` | N | `MARKET_DATA` | 현재가 조회 |
| Market Data | `GET` | `/api/v1/trades` | `getTrades` | N | `MARKET_DATA` | 최근 체결 내역 조회 |
| Stock Info | `GET` | `/api/v1/stocks` | `getStocks` | N | `STOCK` | 종목 기본 정보 조회 |
| Stock Info | `GET` | `/api/v1/stocks/{symbol}/warnings` | `getStockWarnings` | N | `STOCK` | 매수 유의사항 조회 |
| Market Info | `GET` | `/api/v1/exchange-rate` | `getExchangeRate` | N | `MARKET_INFO` | 환율 조회 |
| Market Info | `GET` | `/api/v1/market-calendar/KR` | `getKrMarketCalendar` | N | `MARKET_INFO` | 국내 장 운영 정보 조회 |
| Market Info | `GET` | `/api/v1/market-calendar/US` | `getUsMarketCalendar` | N | `MARKET_INFO` | 해외 장 운영 정보 조회 |
| Account | `GET` | `/api/v1/accounts` | `getAccounts` | N | `ACCOUNT` | 계좌 목록 조회 |
| Asset | `GET` | `/api/v1/holdings` | `getHoldings` | Y | `ASSET` | 보유 주식 조회 |
| Order | `POST` | `/api/v1/orders` | `createOrder` | Y | `ORDER` | 주문 생성 |
| Order | `POST` | `/api/v1/orders/{orderId}/cancel` | `cancelOrder` | Y | `ORDER` | 주문 취소 |
| Order | `POST` | `/api/v1/orders/{orderId}/modify` | `modifyOrder` | Y | `ORDER` | 주문 정정 |
| Order History | `GET` | `/api/v1/orders` | `getOrders` | Y | `ORDER_HISTORY` | 주문 목록 조회 |
| Order History | `GET` | `/api/v1/orders/{orderId}` | `getOrder` | Y | `ORDER_HISTORY` | 주문 상세 조회 |
| Order Info | `GET` | `/api/v1/buying-power` | `getBuyingPower` | Y | `ORDER_INFO` | 매수 가능 금액 조회 |
| Order Info | `GET` | `/api/v1/commissions` | `getCommissions` | Y | `ORDER_INFO` | 매매 수수료 조회 |
| Order Info | `GET` | `/api/v1/sellable-quantity` | `getSellableQuantity` | Y | `ORDER_INFO` | 판매 가능 수량 조회 |

## Auth - 인증

### POST /oauth2/token

- operationId: `issueOAuth2Token`
- 공식 API Markdown: [AuthApi.md#issueOAuth2Token](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/AuthApi.md#issueOAuth2Token)
- 인증: 토큰 불필요/별도 인증 없음
- 계좌 헤더: 불필요
- RateLimit 그룹: `AUTH`
- 요약: OAuth2 액세스 토큰 발급
- 구현 메모: OAuth 2.0 Client Credentials Grant 로 access token 을 발급합니다. - 요청 본문은 `application/x-www-form-urlencoded` 으로 전송합니다. - 발급된 token 은 다른 모든 API 의 `Authorization: Bearer {access_token}` 헤더에 사용합니다. - 응답 형식은 BFF 공통 envelope 이 아닌 OAuth2 표준 형식을 따릅니다. - refresh token 은 제공되지 않습니다. 만료 시 동일 엔드포인트로 재발급합니다. - client 당 유효한 access token 은 1 개입니다. 재발급 시 이전에 발급된 token 은 즉시 무효화됩니다.

#### Request Body

- 필수 여부: Y
- Content-Type: `application/x-www-form-urlencoded`
- Schema: `OAuth2TokenRequest`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `grant_type` | Y | `string` | client_credentials | - | 인증 방식. `client_credentials` 만 지원합니다. |
| `client_id` | Y | `string` | - | - | 발급받은 클라이언트 ID |
| `client_secret` | Y | `string(password)` | - | - | 발급받은 클라이언트 시크릿. 노출되지 않도록 서버 측에서만 사용합니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: OAuth2TokenResponse` | 토큰 발급 성공 |
| `400` | `application/json: OAuth2ErrorResponse` | 잘못된 요청. 필수 파라미터 누락, 지원하지 않는 grant_type 등. |
| `401` | `application/json: OAuth2ErrorResponse` | 클라이언트 인증 실패. `client_id` / `client_secret` 가 잘못되었거나 클라이언트가 비활성 상태인 경우. |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |

## Market Data - 시세

### GET /api/v1/candles

- operationId: `getCandles`
- 공식 API Markdown: [MarketDataApi.md#getCandles](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketDataApi.md#getCandles)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_DATA_CHART`
- 요약: 캔들 차트 조회
- 구현 메모: 종목의 캔들(OHLCV) 차트 데이터를 조회합니다. 최대 200개 봉을 반환합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbol` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |
| `interval` | `query` | Y | `string` | 1m, 1d | - | 봉 단위 |
| `count` | `query` | N | `integer` | - | min=1, max=200, default=100 | 조회 봉 수 (최대 200) |
| `before` | `query` | N | `string(date-time)` | - | - | 페이지네이션 상한 (exclusive, ISO 8601). 이 시각보다 이전의 봉만 반환합니다. 미지정 시 가장 최신 봉부터 반환. 다음 페이지 요청 시 이전 응답의 `nextBefore` 값을 그대로 전달합니다. |
| `adjusted` | `query` | N | `boolean` | - | default=True | 수정주가 적용 여부. `true` 면 수정주가 적용, `false` 면 미적용. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시세 조회 중 일시적 오류 |

### GET /api/v1/orderbook

- operationId: `getOrderbook`
- 공식 API Markdown: [MarketDataApi.md#getOrderbook](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketDataApi.md#getOrderbook)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_DATA`
- 요약: 호가 조회
- 구현 메모: 매수/매도 호가 및 잔량을 조회합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbol` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시세 조회 중 일시적 오류 |

### GET /api/v1/price-limits

- operationId: `getPriceLimit`
- 공식 API Markdown: [MarketDataApi.md#getPriceLimit](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketDataApi.md#getPriceLimit)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_DATA`
- 요약: 상/하한가 조회
- 구현 메모: 종목의 당일 상한가 및 하한가를 조회합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbol` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시세 조회 중 일시적 오류 |

### GET /api/v1/prices

- operationId: `getPrices`
- 공식 API Markdown: [MarketDataApi.md#getPrices](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketDataApi.md#getPrices)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_DATA`
- 요약: 현재가 조회
- 구현 메모: 종목의 현재가 정보를 조회합니다. 최대 200건 까지 다건 조회를 지원하며 콤마(`,`)로 구분합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbols` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.,\-]+$ | 종목 심볼. 최대 200 개를 콤마(`,`)로 구분. 예: `005930,000660` 또는 `AAPL,MSFT`. 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시세 조회 중 일시적 오류 |

### GET /api/v1/trades

- operationId: `getTrades`
- 공식 API Markdown: [MarketDataApi.md#getTrades](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketDataApi.md#getTrades)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_DATA`
- 요약: 최근 체결 내역 조회
- 구현 메모: 당일 최근 체결 내역을 조회합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbol` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |
| `count` | `query` | N | `integer` | - | min=1, max=50, default=50 | 조회 건수 (최대 50) |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시세 조회 중 일시적 오류 |

## Stock Info - 종목 정보

### GET /api/v1/stocks

- operationId: `getStocks`
- 공식 API Markdown: [StockInfoApi.md#getStocks](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/StockInfoApi.md#getStocks)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `STOCK`
- 요약: 종목 기본 정보 조회
- 구현 메모: 종목의 기본 정보를 조회합니다. `symbols` 를 콤마로 구분하여 최대 200건 까지 다건 조회를 지원합니다. 종목명, 시장, 통화, 상장 상태, 거래정지 여부 등 트레이딩에서 필요한 참조 데이터를 제공합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbols` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.,\-]+$ | 종목 심볼. 콤마로 구분하여 최대 200건. 예: 005930 또는 005930,AAPL. 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `403` | `application/json: ErrorResponse` | 권한 부족 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 종목 심볼 조회 중 일시적 오류 |

### GET /api/v1/stocks/{symbol}/warnings

- operationId: `getStockWarnings`
- 공식 API Markdown: [StockInfoApi.md#getStockWarnings](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/StockInfoApi.md#getStockWarnings)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `STOCK`
- 요약: 매수 유의사항 조회
- 구현 메모: 종목의 매수 유의사항 및 변동성 완화(VI) 발동 정보를 조회합니다. **포함 종류**: 정리매매(`LIQUIDATION_TRADING`), 단기과열종목(`OVERHEATED`), 투자경고(`INVESTMENT_WARNING`), 투자위험(`INVESTMENT_RISK`), VI 정적/동적/혼합(`VI_STATIC` / `VI_DYNAMIC` / `VI_STATIC_AND_DYNAMIC`), 신주인수권(`STOCK_WARRANTS`). 전체 enum 은 `StockWarning.warningType` 참조. **"활성"의 시간 기준**: 응답 시점 기준으로 `startDate <= 오늘 <= endDate` 인 항목 (또는 `endDate` 가 `null` 인 진행 중 항목). **응답 정렬**: `startDate` 내림차순 (최근 발동된...

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `symbol` | `path` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `403` | `application/json: ErrorResponse` | 권한 부족 |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 종목 심볼 조회 중 일시적 오류 |

## Market Info - 시장 정보

### GET /api/v1/exchange-rate

- operationId: `getExchangeRate`
- 공식 API Markdown: [MarketInfoApi.md#getExchangeRate](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketInfoApi.md#getExchangeRate)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_INFO`
- 요약: 환율 조회
- 구현 메모: KRW ↔ USD 환율 정보를 조회합니다. - **갱신 주기 1분**, 참고용 표시 환율. 실제 주문 시 적용되는 거래 환율과 다를 수 있습니다. - `dateTime` 미지정 시 **현재 시점의 유효 환율**이 응답됩니다. - 응답의 `validFrom` ~ `validUntil` 은 해당 환율의 **유효 시간 윈도** (보통 1분) 입니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `dateTime` | `query` | N | `string(date-time)` | - | - | 조회할 환율 시각. 특정 시점의 환율을 조회할 수 있습니다. |
| `baseCurrency` | `query` | Y | `string` | KRW, USD | - | 기준 통화 |
| `quoteCurrency` | `query` | Y | `string` | KRW, USD | - | 표시 통화 (quote currency) |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `404` | `application/json: ErrorResponse` | 환율 정보 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시장 정보 조회 중 일시적 오류 |

### GET /api/v1/market-calendar/KR

- operationId: `getKrMarketCalendar`
- 공식 API Markdown: [MarketInfoApi.md#getKrMarketCalendar](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketInfoApi.md#getKrMarketCalendar)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_INFO`
- 요약: 국내 장 운영 정보 조회
- 구현 메모: 국내 시장의 거래 가능 시간을 조회합니다. 통합 모드 (KRX+NXT) 기준이며, 특수장(시간외종가/시간외단일가)은 제외됩니다. 전일/당일/익일 3영업일 정보를 반환합니다. 모든 시간은 KST(+09:00) 기준.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `date` | `query` | N | `string(date)` | - | - | 조회 기준일 (YYYY-MM-DD) |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시장 정보 조회 중 일시적 오류 |

### GET /api/v1/market-calendar/US

- operationId: `getUsMarketCalendar`
- 공식 API Markdown: [MarketInfoApi.md#getUsMarketCalendar](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/MarketInfoApi.md#getUsMarketCalendar)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `MARKET_INFO`
- 요약: 해외 장 운영 정보 조회
- 구현 메모: 미국 시장의 장 운영 시간을 조회합니다. 4 세션(`dayMarket`, `preMarket`, `regularMarket`, `afterMarket`) 별로 nullable. 휴장 시 4 세션 모두 null. 전일/당일/익일 3영업일 정보를 반환합니다. 모든 시간은 KST(+09:00) 기준.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `date` | `query` | N | `string(date)` | - | - | 조회 기준일 (YYYY-MM-DD, 미국 현지 날짜) |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 시장 정보 조회 중 일시적 오류 |

## Account - 계좌

### GET /api/v1/accounts

- operationId: `getAccounts`
- 공식 API Markdown: [AccountApi.md#getAccounts](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/AccountApi.md#getAccounts)
- 인증: Bearer token 필요
- 계좌 헤더: 불필요
- RateLimit 그룹: `ACCOUNT`
- 요약: 계좌 목록 조회
- 구현 메모: 사용자의 계좌 목록을 조회합니다. - 현재는 **종합매매 (`BROKERAGE`) 계좌만 반환**하며, 계좌가 없으면 빈 배열. 자녀계좌는 사용할 수 없습니다. - 응답의 `accountSeq` 는 **다른 모든 사용자 컨텍스트 API** (보유 주식, 주문, 매수가능금액 등) 의 `X-Tossinvest-Account` 헤더에 사용합니다. - `accountType` enum 은 `BROKERAGE` / `OVERSEAS_DERIVATIVES` / `PENSION_SAVINGS` / `RESHORING_INVESTMENT` 가 정의되어 있으나 본 API 에서는 현재 `BROKERAGE` 만 노출됩니다. enum 의미는 `Account.accountType` schema 참조.

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 서비스 일시 불가 |

## Asset - 보유 자산

### GET /api/v1/holdings

- operationId: `getHoldings`
- 공식 API Markdown: [AssetApi.md#getHoldings](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/AssetApi.md#getHoldings)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ASSET`
- 요약: 보유 주식 조회
- 구현 메모: 보유 주식 정보를 조회합니다. 국내(KR)·미국(US) 주식만 포함하며, 해외 옵션·채권은 제외합니다. 보유 종목이 없으면 요약 금액은 0이고 items는 빈 배열입니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `symbol` | `query` | N | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KR: 6자리 숫자 (예: 005930), US: 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. 제공 시 해당 종목만 필터링하여 반환하며, 요약 필드도 해당 종목 기준으로 재계산합니다. 미제공 시 전체 보유 종목을 반환합니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | X-Tossinvest-Account 헤더 누락 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 보유 자산 조회 중 일시적 오류 |

## Order - 주문 실행

### POST /api/v1/orders

- operationId: `createOrder`
- 공식 API Markdown: [OrderApi.md#createOrder](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderApi.md#createOrder)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER`
- 요약: 주문 생성
- 구현 메모: 매수 또는 매도 주문을 생성합니다. **수량 지정 방식** — `quantity`, `orderAmount` 중 정확히 하나를 사용: - `quantity`: 주문 수량 (주 단위). 지정한 수량만큼 주문 - `orderAmount`: 주문 금액 (달러). 지정한 금액만큼 주문하며, 체결 수량은 시장가에 따라 결정. US MARKET 전용 **금액 주문 (`orderAmount`)**: 정규장 시간에만 가능합니다. 정규장 외 시간에 호출 시 `422 amount-order-outside-regular-hours` 를 반환합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |

#### Request Body

- 필수 여부: Y
- Content-Type: `application/json`
- Schema: `OrderCreateRequest`

- 형태: `oneOf` 중 하나
  - Variant 1: `object`
  | 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
  |---|---:|---|---|---|---|
  | `clientOrderId` | N | `string` | - | maxLen=36, pattern=^[a-zA-Z0-9\-_]+$ | 클라이언트 지정 주문 식별자. 멱등성 키로 사용됩니다. - 미전달: 멱등성 미적용. 매 요청을 별개 주문으로 처리합니다. - 전달: 동일 값으로 재요청 시 이전 주문 결과를 그대로 재반환합니다. 서버는 자동 생성하지 않습니다. 최대 36자, 영숫자 및 `-`, `_` 허용. 멱등성 키는 10분간 유효하며, 이후 동일 값으로 재요청 시 새 주문으로 처리됩니다. |
  | `symbol` | Y | `string` | - | - | 종목 심볼. KRX: 6자리 숫자, US: 영문 티커 |
  | `side` | Y | `string` | BUY, SELL | - | 주문 방향 |
  | `orderType` | Y | `string` | LIMIT, MARKET | - | 호가 유형. - `LIMIT`: 지정가 - `MARKET`: 시장가 |
  | `timeInForce` | N | `string` | DAY, CLS | default=DAY | 주문 유효 조건 (Time In Force). 미전달 시 `DAY`. `orderType` 과 결합되어 주문 방식이 결정됩니다 (예: `LIMIT` + `CLS` = LOC). - `DAY`: 당일 유효 (Day). 정규장 종료까지 미체결분은 자동 취소됩니다. - `CLS`: 장 마감 주문 (At the Close). 현재 미국 주식 + `orderType=LIMIT` 조합만 지원합니다. |
  | `quantity` | Y | `string(decimal)` | - | maxLen=30, pattern=^\d+$ | 주문 수량 (주 단위). 지정한 수량만큼 주문합니다. 정수만 가능합니다. (소수점 불가능. 소수점 주문 시 Amount-based variant 의 `orderAmount` 를 사용해야 합니다.) |
  | `price` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 주문 가격. `orderType`이 `LIMIT` 일 때만 사용합니다. - `LIMIT`: 필수. 미전달 시 `400 invalid-request`. - `MARKET`: 전달 불가. 전달 시 `400 invalid-request`. KR: 정수 (원 단위). 호가 단위에 맞아야 합니다 (예: 50,000~200,000원 구간은 100원 단위). KR 은 호가 단위에 맞지 않으면 `400 i... |
  | `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. |
  - Variant 2: `object`
  | 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
  |---|---:|---|---|---|---|
  | `clientOrderId` | N | `string` | - | maxLen=36, pattern=^[a-zA-Z0-9\-_]+$ | 클라이언트 지정 주문 식별자. 멱등성 키로 사용됩니다. - 미전달: 멱등성 미적용. 매 요청을 별개 주문으로 처리합니다. - 전달: 동일 값으로 재요청 시 이전 주문 결과를 그대로 재반환합니다. 서버는 자동 생성하지 않습니다. 최대 36자, 영숫자 및 `-`, `_` 허용. 멱등성 키는 10분간 유효하며, 이후 동일 값으로 재요청 시 새 주문으로 처리됩니다. |
  | `symbol` | Y | `string` | - | - | US 종목 심볼 (영문 티커). 금액 기반 주문은 US MARKET 전용입니다. |
  | `side` | Y | `string` | BUY, SELL | - | 주문 방향 |
  | `orderType` | Y | `string` | MARKET | - | 호가 유형. 금액 기반 주문은 `MARKET` 만 허용합니다. |
  | `orderAmount` | Y | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 주문 금액 (달러). 지정한 금액만큼 주문합니다. 체결 수량은 체결 시점의 시장가에 따라 결정됩니다. Quantity-based 와의 차이: quantity 는 수량을 확정하고 비용이 변동하며, orderAmount 는 금액을 확정하고 수량이 변동합니다. 정규장 시간에만 접수 가능합니다. 정규장 시간 외 요청 시 `422 amount-order-outside-regular-hours` 에러를... |
  | `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `409` | `application/json: ErrorResponse` | 중복 요청 |
| `422` | `application/json: ErrorResponse` | 비즈니스 규칙 위반 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 주문 처리 중 일시적 오류 또는 시스템 점검 |

### POST /api/v1/orders/{orderId}/cancel

- operationId: `cancelOrder`
- 공식 API Markdown: [OrderApi.md#cancelOrder](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderApi.md#cancelOrder)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER`
- 요약: 주문 취소
- 구현 메모: 기존 주문을 취소합니다. 이미 체결된 주문은 취소할 수 없습니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `orderId` | `path` | Y | `string` | - | - | 주문 식별자. 서버에서 발급한 opaque token 입니다. |

#### Request Body

- 필수 여부: N
- Content-Type: `application/json`
- Schema: `object`

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | X-Tossinvest-Account 헤더 누락 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 주문을 찾을 수 없음 |
| `409` | `application/json: ErrorResponse` | 취소 불가 상태 |
| `422` | `application/json: ErrorResponse` | 비즈니스 규칙 위반 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 주문 처리 중 일시적 오류 |

### POST /api/v1/orders/{orderId}/modify

- operationId: `modifyOrder`
- 공식 API Markdown: [OrderApi.md#modifyOrder](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderApi.md#modifyOrder)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER`
- 요약: 주문 정정
- 구현 메모: 기존 주문의 가격 또는 수량을 정정합니다. **KR 주식:** `quantity` 필수. 양의 정수만 허용합니다. **US 주식:** `quantity` 제공 불가. 가격 변경만 지원합니다. `quantity` 제공 시 `400 us-modify-quantity-not-supported` 에러를 반환합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `orderId` | `path` | Y | `string` | - | - | 주문 식별자. 서버에서 발급한 opaque token 입니다. |

#### Request Body

- 필수 여부: Y
- Content-Type: `application/json`
- Schema: `OrderModifyRequest`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orderType` | Y | `string` | LIMIT, MARKET | - | 변경할 호가 유형. - `LIMIT`: 지정가 - `MARKET`: 시장가 |
| `quantity` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+$ | 변경할 수량. **KR 주식: 필수.** 양의 정수만 허용합니다 (미전달/0/음수/소수점은 `400 invalid-request`). US 주식: 전달 불가. 제공 시 `400 us-modify-quantity-not-supported` 에러. |
| `price` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 변경할 가격. `orderType`이 `LIMIT` 일 때만 사용합니다. - `LIMIT`: 필수. 미전달 시 `400 invalid-request`. - `MARKET`: 전달 불가. 전달 시 `400 invalid-request`. KR: 정수 (원 단위). 호가 단위에 맞아야 합니다. 맞지 않으면 `400 invalid-request` 에러. US: 소수점 (달러 단위). - $1 미만... |
| `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. 30억원 이상의 주문은 본 플래그와 무관하게 `422 max-order-amount-exceeded` 에러를 반환합니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 주문 또는 계좌 없음 |
| `409` | `application/json: ErrorResponse` | 정정 불가 상태 |
| `422` | `application/json: ErrorResponse` | 비즈니스 규칙 위반 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 주문 처리 중 일시적 오류 |

## Order History - 주문 조회

### GET /api/v1/orders

- operationId: `getOrders`
- 공식 API Markdown: [OrderHistoryApi.md#getOrders](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderHistoryApi.md#getOrders)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER_HISTORY`
- 요약: 주문 목록 조회
- 구현 메모: 주문 목록을 조회합니다. status 파라미터로 주문 상태를 필터링합니다. **지원하는 status 값:** - 진행 중 주문: `OPEN` -- PENDING, PARTIAL_FILLED, PENDING_CANCEL, PENDING_REPLACE 상태의 주문을 반환 - 종료된 주문: `CLOSED` -- 현재 호출 시 `400 closed-not-supported` 를 반환합니다. symbol을 지정하면 해당 종목의 주문만 필터링하여 반환합니다. **페이징 동작:** - `status=OPEN`: 모든 대기 중 주문을 전량 반환합니다. `limit`, `cursor` 는 무시되며, `from`/`to` 만 주문 생성일(`orderedAt`, KST 기준) 범위 필터로 적용됩니다 (미지정 시 전체 기간). - `status=CLOSED`: 미...

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `status` | `query` | Y | `string` | OPEN, CLOSED | - | 주문 라이프사이클 그룹 필터. 이 값은 각 주문의 세부 상태(`orders[].status`)를 **그룹화한 라벨**이며, `orders[].status` 와 값 체계가 다릅니다. - `OPEN`: 진행 중 주문 그룹 — `orders[].status` ∈ `{PENDING, PARTIAL_FILLED, PENDING_CANCEL, PENDING_REPLACE}` - `CLOSED`: 종료된... |
| `symbol` | `query` | N | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. 지정 시 해당 종목의 주문만 조회. KRX: 6자리 숫자 (`005930`), US: 영문 티커 (`AAPL`). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |
| `from` | `query` | N | `string(date)` | - | - | 조회 시작일 (inclusive, KST 기준). 주문 생성 시간(`orderedAt`) 기준. 미지정 시 전체 기간. `status=CLOSED` 는 미지원이므로 현재 효과가 없습니다. |
| `to` | `query` | N | `string(date)` | - | - | 조회 종료일 (inclusive, KST 기준). 주문 생성 시간(`orderedAt`) 기준. 미지정 시 전체 기간. `status=CLOSED` 는 미지원이므로 현재 효과가 없습니다. |
| `cursor` | `query` | N | `string` | - | - | 페이지네이션 커서. `OPEN` 에서는 무시되며, `CLOSED` 는 미지원이므로 현재 효과가 없습니다. |
| `limit` | `query` | N | `integer` | - | min=1, max=100, default=20 | 페이지 크기. `OPEN` 에서는 무시됩니다 (전량 반환). `CLOSED` 는 미지원이므로 현재 효과가 없습니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 주문 조회 중 일시적 오류 |

### GET /api/v1/orders/{orderId}

- operationId: `getOrder`
- 공식 API Markdown: [OrderHistoryApi.md#getOrder](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderHistoryApi.md#getOrder)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER_HISTORY`
- 요약: 주문 상세 조회
- 구현 메모: 특정 주문의 상세 정보를 조회합니다. 모든 주문 상태(체결 완료, 취소, 거부 등)의 주문을 조회할 수 있습니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `orderId` | `path` | Y | `string` | - | - | 주문 식별자. 서버에서 발급한 opaque token 입니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | X-Tossinvest-Account 헤더 누락 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 주문을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 주문 조회 중 일시적 오류 |

## Order Info - 거래 가능 정보

### GET /api/v1/buying-power

- operationId: `getBuyingPower`
- 공식 API Markdown: [OrderInfoApi.md#getBuyingPower](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderInfoApi.md#getBuyingPower)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER_INFO`
- 요약: 매수 가능 금액 조회
- 구현 메모: 매수 주문 시 사용할 수 있는 매수 가능 금액을 조회합니다. 미수거래를 제외한 현금 기반 매수 가능 금액(미수 미발생 기준)을 반환합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `currency` | `query` | Y | `string` | KRW, USD | - | 통화 코드 |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 계좌 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 거래 가능 정보 조회 중 일시적 오류 |

### GET /api/v1/commissions

- operationId: `getCommissions`
- 공식 API Markdown: [OrderInfoApi.md#getCommissions](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderInfoApi.md#getCommissions)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER_INFO`
- 요약: 매매 수수료 조회
- 구현 메모: 현재 계좌의 시장별 매매 수수료율을 조회합니다. 국내주식과 해외주식의 수수료 정보를 배열로 반환합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 거래 가능 정보 조회 중 일시적 오류 |

### GET /api/v1/sellable-quantity

- operationId: `getSellableQuantity`
- 공식 API Markdown: [OrderInfoApi.md#getSellableQuantity](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Apis/OrderInfoApi.md#getSellableQuantity)
- 인증: Bearer token 필요
- 계좌 헤더: 필요
- RateLimit 그룹: `ORDER_INFO`
- 요약: 판매 가능 수량 조회
- 구현 메모: 특정 종목의 판매 가능 수량을 조회합니다.

#### Parameters

| 이름 | 위치 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---|---:|---|---|---|---|
| `X-Tossinvest-Account` | `header` | Y | `integer(int64)` | - | - | API 요청 시 사용할 계좌의 accountSeq. `GET /api/v1/accounts` 응답의 `accountSeq` 값을 사용합니다. |
| `symbol` | `query` | Y | `string` | - | pattern=^[A-Za-z0-9.\-]+$ | 종목 심볼. KRX: 6자리 숫자 (예: 005930), US: 영문 티커 (예: AAPL). 영문 대/소문자, 숫자, '.', '-' 만 허용한다. |

#### Responses

| Status | Schema | 설명 |
|---|---|---|
| `200` | `application/json: allOf<ApiResponse + object>` | 성공 |
| `400` | `application/json: ErrorResponse` | 잘못된 요청 |
| `401` | `application/json: ErrorResponse` | 인증 실패. `WWW-Authenticate: Bearer ...` 헤더가 함께 내려갑니다. |
| `404` | `application/json: ErrorResponse` | 종목을 찾을 수 없음 |
| `429` | `application/json: ErrorResponse` | 요청 한도 초과. 포함 헤더의 의미는 아래 `headers` 정의를 참조합니다. |
| `500` | `application/json: ErrorResponse` | 거래 가능 정보 조회 중 일시적 오류 |

## Schema Catalog

아래 모델 목록은 OpenAPI `components.schemas` 전체를 포함합니다. `oneOf` 모델은 가능한 variant를 모두 표시합니다.

### Account

- 공식 모델 Markdown: [Account](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Account.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `accountNo` | Y | `string` | - | - | 계좌번호 |
| `accountSeq` | Y | `integer(int64)` | - | - | 계좌 식별 키. 주문 등 API 호출 시 이 값을 사용 |
| `accountType` | Y | `string` | BROKERAGE, OVERSEAS_DERIVATIVES, PENSION_SAVINGS, RESHORING_INVESTMENT | - | 계좌 유형. 현재는 BROKERAGE 만 지원합니다. - BROKERAGE: 종합매매. 국내·해외 주식 통합 매매 계좌 - OVERSEAS_DERIVATIVES: 해외파생. 해외 파생상품 거래 계좌 - PENSION_SAVINGS: 연금저축. 세제혜택 연금저축 계좌 - RESHORING_INVESTMENT: RIA 계좌 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |

### AfterMarketSession

- 공식 모델 Markdown: [AfterMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/AfterMarketSession.md)
- 타입: `object`
- 설명: 애프터마켓 세션 (NXT)

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 애프터마켓 시작 |
| `singlePriceAuctionEndTime` | N | `oneOf<string(date-time) | null>` | - | - | 애프터마켓 내 시가단일가 구간 종료. |
| `endTime` | Y | `string(date-time)` | - | - | 애프터마켓 전체 종료 |

### ApiError

- 공식 모델 Markdown: [ApiError](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/ApiError.md)
- 타입: `object`
- 설명: 에러 객체. 에러 식별에 필요한 최소 정보(`requestId`, `code`, `message`)와 필요 시 해결 힌트(`data`)를 포함합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `requestId` | Y | `string` | - | - | 요청을 식별하는 고유 ID. 응답 헤더 `X-Request-Id` 와 동일한 값입니다. 토스증권 CS 문의 시 첨부를 권장합니다. |
| `code` | Y | `string` | - | - | 에러 코드. flat string 식별자. 도메인 에러는 이유를 직접 표현하는 단일 식별자 (예: `invalid-request`, `order-not-found`) 를 사용합니다. 클라이언트는 unknown code 를 허용하도록 구현해야 합니다. |
| `message` | Y | `string` | - | - | 사용자에게 노출 가능한 에러 메시지. 내부 정책상 노출이 제한되는 경우 빈 문자열로 내려갈 수 있으므로 클라이언트는 `code` 기반으로 메시지를 자체 매핑할 것을 권장합니다. |
| `data` | N | `map<string,-> | null` | - | - | 에러 해결 힌트. 에러 코드별로 포함 여부와 키 구조가 다르며, 없는 경우 필드 자체가 생략됩니다. 모든 표준 키가 항상 함께 내려가지 않으며, 각 에러 코드에 해당하는 서브셋만 포함됩니다. ## 표준 키 (camelCase) \| 키 \| 타입 \| 설명 \| \|---\|---\|---\| \| `field` \| string \| 검증 실패 원인 필드. 외부 API 에 노출된 이름 (r... |

### ApiResponse

- 공식 모델 Markdown: [ApiResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/ApiResponse.md)
- 타입: `object`
- 설명: 성공 응답 envelope. 200 응답에 사용됩니다. 각 엔드포인트의 성공 응답 스키마는 `allOf` 로 본 스키마를 상속하며 `result` 를 구체 타입으로 specialize 합니다. 실패 응답은 별도의 `ErrorResponse` 스키마를 사용합니다 (4xx/5xx). `result` 와 `error` 는 동시에 나타나지 않습니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `result` | Y | `object` | - | - | 성공 응답의 페이로드. 엔드포인트별 타입이 다르며, 각 엔드포인트 스펙에서 `allOf` 로 구체 타입을 명시합니다. |

### BuyingPowerResponse

- 공식 모델 Markdown: [BuyingPowerResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/BuyingPowerResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `cashBuyingPower` | Y | `string(decimal)` | - | maxLen=30 | 현금 기반 매수 가능 금액 (미수 미발생 기준). 순수 현금으로 매수할 수 있는 금액. KRW: 정수 (원 단위). USD: 소수점 포함 (달러 단위). |

### Candle

- 공식 모델 Markdown: [Candle](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Candle.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `timestamp` | Y | `string(date-time)` | - | - | 봉 시작 시각 |
| `openPrice` | Y | `string(decimal)` | - | maxLen=30 | 시가 |
| `highPrice` | Y | `string(decimal)` | - | maxLen=30 | 고가 |
| `lowPrice` | Y | `string(decimal)` | - | maxLen=30 | 저가 |
| `closePrice` | Y | `string(decimal)` | - | maxLen=30 | 종가 |
| `volume` | Y | `string(decimal)` | - | maxLen=30 | 거래량 |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |

### CandlePageResponse

- 공식 모델 Markdown: [CandlePageResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/CandlePageResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `candles` | Y | `array<Candle>` | - | - | 캔들 목록 |
| `nextBefore` | N | `string(date-time) | null` | - | - | 다음 페이지 조회 시 `before` 쿼리 파라미터에 그대로 전달. 마지막 페이지면 null. |

### Commission

- 공식 모델 Markdown: [Commission](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Commission.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `marketCountry` | Y | `MarketCountry` | KR, US | - | 시장 국가 구분. - KR: 국내 주식 (KRX) - US: 미국 주식 (NYSE, NASDAQ 등) 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `commissionRate` | Y | `string(decimal)` | - | maxLen=30 | 수수료율 (%). 예: 0.015는 0.015% |
| `startDate` | N | `string(date) | null` | - | - | 수수료 적용 시작일 (YYYY-MM-DD, KST 기준). 해외주식은 null |
| `endDate` | N | `string(date) | null` | - | - | 수수료 적용 종료일 (YYYY-MM-DD, KST 기준). 무기한 적용 시 null |

### Cost

- 공식 모델 Markdown: [Cost](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Cost.md)
- 타입: `object`
- 설명: 비용. 거래 통화(currency) 기준

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `commission` | Y | `string(decimal)` | - | maxLen=30 | 수수료 |
| `tax` | N | `string(decimal) | null` | - | maxLen=30 | 세금. 세금이 없는 경우 null |

### Currency

- 공식 모델 Markdown: [Currency](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Currency.md)
- 타입: `string`
- 설명: 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다.
- Enum/Const: KRW, USD

- 속성 없음 또는 primitive/enum 모델

### DailyProfitLoss

- 공식 모델 Markdown: [DailyProfitLoss](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/DailyProfitLoss.md)
- 타입: `object`
- 설명: 일간 손익. 거래 통화(currency) 기준

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `amount` | Y | `string(decimal)` | - | maxLen=30 | 일간 손익금액 |
| `rate` | Y | `string(decimal)` | - | maxLen=30 | 일간 손익률. 소수비율 (0.0141 = 1.41%) |

### ErrorResponse

- 공식 모델 Markdown: [ErrorResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/ErrorResponse.md)
- 타입: `object`
- 설명: 에러 응답 envelope. 4xx/5xx 응답에 사용됩니다. 성공 응답은 별도의 `ApiResponse` 스키마를 사용합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `error` | Y | `ApiError` | - | - | 에러 객체. 에러 식별에 필요한 최소 정보(`requestId`, `code`, `message`)와 필요 시 해결 힌트(`data`)를 포함합니다. |

### ExchangeRateResponse

- 공식 모델 Markdown: [ExchangeRateResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/ExchangeRateResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `baseCurrency` | Y | `Currency` | KRW, USD | - | 기준 통화 |
| `quoteCurrency` | Y | `Currency` | KRW, USD | - | 표시 통화 (quote currency) |
| `rate` | Y | `string(decimal)` | - | maxLen=30 | 매수 환율 (1 baseCurrency = ? quoteCurrency) |
| `midRate` | Y | `string(decimal)` | - | maxLen=30 | 매매기준율 (은행간 mid rate) |
| `basisPoint` | Y | `string(decimal)` | - | maxLen=30 | 매매기준율(midRate) 대비 basis points. (rate - midRate) / midRate * 10000 |
| `rateChangeType` | Y | `string` | UP, EQUAL, DOWN | - | 등락 구분 |
| `validFrom` | Y | `string(date-time)` | - | - | 환율 유효 시작 시각 |
| `validUntil` | Y | `string(date-time)` | - | - | 환율 유효 종료 시각 |

### HoldingsItem

- 공식 모델 Markdown: [HoldingsItem](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/HoldingsItem.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `symbol` | Y | `string` | - | - | 종목 심볼. KR: 6자리 숫자, US: 티커 |
| `name` | Y | `string` | - | - | 종목명 |
| `marketCountry` | Y | `MarketCountry` | KR, US | - | 시장 국가 구분. - KR: 국내 주식 (KRX) - US: 미국 주식 (NYSE, NASDAQ 등) 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `quantity` | Y | `string(decimal)` | - | maxLen=30 | 보유 수량 |
| `lastPrice` | Y | `string(decimal)` | - | maxLen=30 | 현재가. 거래 통화(currency) 기준 |
| `averagePurchasePrice` | Y | `string(decimal)` | - | maxLen=30 | 매수 평균가. 거래 통화(currency) 기준 |
| `marketValue` | Y | `MarketValue` | - | - | 시장 평가. 거래 통화(currency) 기준 |
| `profitLoss` | Y | `ProfitLoss` | - | - | 손익. 거래 통화(currency) 기준 |
| `dailyProfitLoss` | Y | `DailyProfitLoss` | - | - | 일간 손익. 거래 통화(currency) 기준 |
| `cost` | Y | `Cost` | - | - | 비용. 거래 통화(currency) 기준 |

### HoldingsOverview

- 공식 모델 Markdown: [HoldingsOverview](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/HoldingsOverview.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `totalPurchaseAmount` | Y | `allOf<Price>` | - | - | 투자원금. 전체 보유 종목의 통화별 합산 |
| `marketValue` | Y | `OverviewMarketValue` | - | - | 시장 평가금액. 전체 보유 종목의 통화별 합산 |
| `profitLoss` | Y | `OverviewProfitLoss` | - | - | 손익. 전체 보유 종목의 통화별 합산 |
| `dailyProfitLoss` | Y | `OverviewDailyProfitLoss` | - | - | 일간 손익. 전체 보유 종목의 통화별 합산 |
| `items` | Y | `array<HoldingsItem>` | - | - | 보유 종목 목록. 보유 종목이 없으면 빈 배열 |

### IntegratedHour

- 공식 모델 Markdown: [IntegratedHour](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/IntegratedHour.md)
- 타입: `object`
- 설명: 거래 가능 시간. 특수장(시간외종가/시간외단일가) 제외, 통합 모드 (KRX+NXT) 기준. 세 세션(`preMarket`, `regularMarket`, `afterMarket`) 각각 nullable. 해당 세션이 휴장이면 null, 세 세션 모두 null 이면 상위 `integrated` 자체가 null.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `preMarket` | N | `oneOf<PreMarketSession | null>` | - | - | 프리마켓 (NXT 접속매매). NXT 프리마켓이 휴장이면 null |
| `regularMarket` | N | `oneOf<RegularMarketSession | null>` | - | - | 정규장. KRX·NXT 정규장의 합집합. 둘 다 휴장이면 null |
| `afterMarket` | N | `oneOf<AfterMarketSession | null>` | - | - | 애프터마켓 (NXT). NXT 애프터마켓이 휴장이면 null |

### KrMarketCalendarResponse

- 공식 모델 Markdown: [KrMarketCalendarResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/KrMarketCalendarResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `today` | Y | `KrMarketDay` | - | - | - |
| `previousBusinessDay` | Y | `KrMarketDay` | - | - | - |
| `nextBusinessDay` | Y | `KrMarketDay` | - | - | - |

### KrMarketDay

- 공식 모델 Markdown: [KrMarketDay](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/KrMarketDay.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `date` | Y | `string(date)` | - | - | 영업일 (KST 기준) |
| `integrated` | N | `oneOf<IntegratedHour | null>` | - | - | 거래 가능 시간 (통합 모드 (KRX+NXT) 기준). 둘 다 휴장이면 null |

### KrMarketDetail

- 공식 모델 Markdown: [KrMarketDetail](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/KrMarketDetail.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `liquidationTrading` | Y | `boolean` | - | - | 정리매매 여부 (상장폐지 절차 진행 중). |
| `nxtSupported` | Y | `boolean` | - | - | NXT 대체거래소 지원 여부 |
| `krxTradingSuspended` | Y | `boolean` | - | - | KRX 거래정지 여부 |
| `nxtTradingSuspended` | N | `boolean | null` | - | - | NXT 거래정지 여부. NXT 미지원 종목(nxtSupported=false)은 null |

### MarketCountry

- 공식 모델 Markdown: [MarketCountry](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/MarketCountry.md)
- 타입: `string`
- 설명: 시장 국가 구분. - KR: 국내 주식 (KRX) - US: 미국 주식 (NYSE, NASDAQ 등) 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다.
- Enum/Const: KR, US

- 속성 없음 또는 primitive/enum 모델

### MarketValue

- 공식 모델 Markdown: [MarketValue](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/MarketValue.md)
- 타입: `object`
- 설명: 시장 평가. 거래 통화(currency) 기준

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `purchaseAmount` | Y | `string(decimal)` | - | maxLen=30 | 매입금액 |
| `amount` | Y | `string(decimal)` | - | maxLen=30 | 시장 평가금액 |
| `amountAfterCost` | Y | `string(decimal)` | - | maxLen=30 | 세금/수수료 공제 후 평가금액 |

### OAuth2ErrorResponse

- 공식 모델 Markdown: [OAuth2ErrorResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OAuth2ErrorResponse.md)
- 타입: `object`
- 설명: OAuth2 토큰 발급 실패 응답. `/oauth2/token` 엔드포인트는 BFF 공통 `ErrorResponse` envelope 이 아닌 OAuth2 표준 포맷으로 응답합니다. 클라이언트는 `code` 가 아닌 `error` 필드로 에러를 식별해야 합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `error` | Y | `string` | invalid_request, invalid_client, invalid_grant, unauthorized_client, unsupported_grant_type | - | 에러 코드. |
| `error_description` | N | `string` | - | - | 에러 상세 설명 (선택). 메시지에 non-ASCII 문자가 포함되는 경우 생략될 수 있습니다. |
| `error_uri` | N | `string(uri)` | - | - | 에러 정보가 게시된 페이지 URI (선택). |

### OAuth2TokenRequest

- 공식 모델 Markdown: [OAuth2TokenRequest](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OAuth2TokenRequest.md)
- 타입: `object`
- 설명: OAuth2 Client Credentials Grant 토큰 발급 요청. `application/x-www-form-urlencoded` 으로 전송합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `grant_type` | Y | `string` | client_credentials | - | 인증 방식. `client_credentials` 만 지원합니다. |
| `client_id` | Y | `string` | - | - | 발급받은 클라이언트 ID |
| `client_secret` | Y | `string(password)` | - | - | 발급받은 클라이언트 시크릿. 노출되지 않도록 서버 측에서만 사용합니다. |

### OAuth2TokenResponse

- 공식 모델 Markdown: [OAuth2TokenResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OAuth2TokenResponse.md)
- 타입: `object`
- 설명: 토큰 발급 성공 응답. BFF 의 공통 `ApiResponse` envelope 을 사용하지 않고 OAuth2 표준 형식으로 응답합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `access_token` | Y | `string` | - | - | JWT 형식의 access token. 모든 API 요청의 `Authorization: Bearer` 헤더에 담습니다. |
| `token_type` | Y | `string` | Bearer | - | 토큰 타입. 항상 `Bearer`. |
| `expires_in` | Y | `integer(int64)` | - | - | 토큰 만료까지 남은 초. |

### Order

- 공식 모델 Markdown: [Order](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Order.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orderId` | Y | `string` | - | - | 주문 식별자 |
| `symbol` | Y | `string` | - | - | 종목 심볼. KRX: 6자리 숫자, US: 영문 티커 |
| `side` | Y | `string` | BUY, SELL | - | 주문 방향 |
| `orderType` | Y | `string` | LIMIT, MARKET | - | 호가 유형. - `LIMIT`: 지정가 - `MARKET`: 시장가 클라이언트는 unknown code 를 허용하도록 구현해야 합니다. |
| `timeInForce` | Y | `string` | DAY, CLS, OPG | - | 주문 유효 조건 (Time In Force). `orderType` 과 결합되어 주문 방식이 결정됩니다 (예: `LIMIT` + `CLS` = LOC). - `DAY`: 당일 유효 (Day) - `CLS`: 장 마감 주문 (At the Close) - `OPG`: 장 개시 주문 (At the Opening). 현재는 지원하지 않습니다. 클라이언트는 unknown code 를 허용하도록 구현해... |
| `status` | Y | `OrderStatus` | PENDING, PENDING_CANCEL, PENDING_REPLACE, PARTIAL_FILLED, FILLED, CANCELED, REJECTED, CANCEL_REJECTED, REPLACE_REJECTED, REPLACED | - | 주문 상태. - `PENDING`: 체결 대기. 주문이 접수되어 체결을 대기 중인 상태 - `PENDING_CANCEL`: 취소 대기. 취소 요청이 접수되어 브로커 응답을 대기 중인 상태 - `PENDING_REPLACE`: 정정 대기. 정정 요청이 접수되어 브로커 응답을 대기 중인 상태 - `PARTIAL_FILLED`: 부분 체결. 주문 수량 중 일부만 체결된 상태 - `FILLED`:... |
| `price` | N | `string(decimal) | null` | - | maxLen=30 | 주문 가격 (native currency). MARKET 주문 시 null |
| `quantity` | Y | `string(decimal)` | - | maxLen=30 | 주문 수량 |
| `orderAmount` | N | `string(decimal) | null` | - | maxLen=30 | 주문 금액 (USD). 금액 기반 US 시장가 매수 주문에만 해당. 그 외 null |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `orderedAt` | Y | `string(date-time)` | - | - | 주문 시간 (ISO 8601, KST) |
| `canceledAt` | N | `string(date-time) | null` | - | - | 취소 시간 (ISO 8601, KST). 해당 없으면 null |
| `execution` | Y | `allOf<OrderExecution>` | - | - | 체결 결과. 체결 내역이 없으면 filledQuantity=0 |

### OrderCreateRequest

- 공식 모델 Markdown: [OrderCreateRequest](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderCreateRequest.md)
- 타입: `oneOf<object | object>`

- 형태: `oneOf` 중 하나
  - Variant 1: `object`
  | 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
  |---|---:|---|---|---|---|
  | `clientOrderId` | N | `string` | - | maxLen=36, pattern=^[a-zA-Z0-9\-_]+$ | 클라이언트 지정 주문 식별자. 멱등성 키로 사용됩니다. - 미전달: 멱등성 미적용. 매 요청을 별개 주문으로 처리합니다. - 전달: 동일 값으로 재요청 시 이전 주문 결과를 그대로 재반환합니다. 서버는 자동 생성하지 않습니다. 최대 36자, 영숫자 및 `-`, `_` 허용. 멱등성 키는 10분간 유효하며, 이후 동일 값으로 재요청 시 새 주문으로 처리됩니다. |
  | `symbol` | Y | `string` | - | - | 종목 심볼. KRX: 6자리 숫자, US: 영문 티커 |
  | `side` | Y | `string` | BUY, SELL | - | 주문 방향 |
  | `orderType` | Y | `string` | LIMIT, MARKET | - | 호가 유형. - `LIMIT`: 지정가 - `MARKET`: 시장가 |
  | `timeInForce` | N | `string` | DAY, CLS | default=DAY | 주문 유효 조건 (Time In Force). 미전달 시 `DAY`. `orderType` 과 결합되어 주문 방식이 결정됩니다 (예: `LIMIT` + `CLS` = LOC). - `DAY`: 당일 유효 (Day). 정규장 종료까지 미체결분은 자동 취소됩니다. - `CLS`: 장 마감 주문 (At the Close). 현재 미국 주식 + `orderType=LIMIT` 조합만 지원합니다. |
  | `quantity` | Y | `string(decimal)` | - | maxLen=30, pattern=^\d+$ | 주문 수량 (주 단위). 지정한 수량만큼 주문합니다. 정수만 가능합니다. (소수점 불가능. 소수점 주문 시 Amount-based variant 의 `orderAmount` 를 사용해야 합니다.) |
  | `price` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 주문 가격. `orderType`이 `LIMIT` 일 때만 사용합니다. - `LIMIT`: 필수. 미전달 시 `400 invalid-request`. - `MARKET`: 전달 불가. 전달 시 `400 invalid-request`. KR: 정수 (원 단위). 호가 단위에 맞아야 합니다 (예: 50,000~200,000원 구간은 100원 단위). KR 은 호가 단위에 맞지 않으면 `400 i... |
  | `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. |
  - Variant 2: `object`
  | 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
  |---|---:|---|---|---|---|
  | `clientOrderId` | N | `string` | - | maxLen=36, pattern=^[a-zA-Z0-9\-_]+$ | 클라이언트 지정 주문 식별자. 멱등성 키로 사용됩니다. - 미전달: 멱등성 미적용. 매 요청을 별개 주문으로 처리합니다. - 전달: 동일 값으로 재요청 시 이전 주문 결과를 그대로 재반환합니다. 서버는 자동 생성하지 않습니다. 최대 36자, 영숫자 및 `-`, `_` 허용. 멱등성 키는 10분간 유효하며, 이후 동일 값으로 재요청 시 새 주문으로 처리됩니다. |
  | `symbol` | Y | `string` | - | - | US 종목 심볼 (영문 티커). 금액 기반 주문은 US MARKET 전용입니다. |
  | `side` | Y | `string` | BUY, SELL | - | 주문 방향 |
  | `orderType` | Y | `string` | MARKET | - | 호가 유형. 금액 기반 주문은 `MARKET` 만 허용합니다. |
  | `orderAmount` | Y | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 주문 금액 (달러). 지정한 금액만큼 주문합니다. 체결 수량은 체결 시점의 시장가에 따라 결정됩니다. Quantity-based 와의 차이: quantity 는 수량을 확정하고 비용이 변동하며, orderAmount 는 금액을 확정하고 수량이 변동합니다. 정규장 시간에만 접수 가능합니다. 정규장 시간 외 요청 시 `422 amount-order-outside-regular-hours` 에러를... |
  | `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. |

### OrderExecution

- 공식 모델 Markdown: [OrderExecution](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderExecution.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `filledQuantity` | Y | `string(decimal)` | - | maxLen=30 | 체결 수량 |
| `averageFilledPrice` | Y | `string(decimal) | null` | - | maxLen=30 | 평균 체결 가격 (native currency). 부분 체결 시 체결된 건의 평균 |
| `filledAmount` | Y | `string(decimal) | null` | - | maxLen=30 | 총 체결 금액 (native currency) |
| `commission` | Y | `string(decimal) | null` | - | maxLen=30 | 총 체결 수수료 (native currency) |
| `tax` | Y | `string(decimal) | null` | - | maxLen=30 | 총 체결 세금 (native currency) |
| `filledAt` | Y | `string(date-time) | null` | - | - | 최종 체결 시간 (ISO 8601, KST) |
| `settlementDate` | Y | `string(date) | null` | - | - | 결제 예정일 (YYYY-MM-DD, KST 기준). 미결제 시 null |

### OrderModifyRequest

- 공식 모델 Markdown: [OrderModifyRequest](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderModifyRequest.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orderType` | Y | `string` | LIMIT, MARKET | - | 변경할 호가 유형. - `LIMIT`: 지정가 - `MARKET`: 시장가 |
| `quantity` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+$ | 변경할 수량. **KR 주식: 필수.** 양의 정수만 허용합니다 (미전달/0/음수/소수점은 `400 invalid-request`). US 주식: 전달 불가. 제공 시 `400 us-modify-quantity-not-supported` 에러. |
| `price` | N | `string(decimal)` | - | maxLen=30, pattern=^\d+(\.\d+)?$ | 변경할 가격. `orderType`이 `LIMIT` 일 때만 사용합니다. - `LIMIT`: 필수. 미전달 시 `400 invalid-request`. - `MARKET`: 전달 불가. 전달 시 `400 invalid-request`. KR: 정수 (원 단위). 호가 단위에 맞아야 합니다. 맞지 않으면 `400 invalid-request` 에러. US: 소수점 (달러 단위). - $1 미만... |
| `confirmHighValueOrder` | N | `boolean` | - | default=False | 착오주문 방지를 위한 주문 확인 플래그. 기본값 `false`. 1억원 이상의 주문 시 `true`가 아니면 `400 confirm-high-value-required` 에러를 반환합니다. 사용자가 해당 주문의 금액을 인지하고 있음을 표시하기 위한 필드입니다. 30억원 이상의 주문은 본 플래그와 무관하게 `422 max-order-amount-exceeded` 에러를 반환합니다. |

### OrderOperationResponse

- 공식 모델 Markdown: [OrderOperationResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderOperationResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orderId` | Y | `string` | - | - | 정정/취소로 새로 발급된 주문 식별자. 원주문의 orderId 와 다릅니다. |

### OrderResponse

- 공식 모델 Markdown: [OrderResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orderId` | Y | `string` | - | - | 서버 생성 주문 식별자. 정정/취소 시 사용 |
| `clientOrderId` | N | `string | null` | - | - | 요청 시 전달한 값 그대로 반환. 미전달 시 `null`. |

### OrderStatus

- 공식 모델 Markdown: [OrderStatus](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderStatus.md)
- 타입: `string`
- 설명: 주문 상태. - `PENDING`: 체결 대기. 주문이 접수되어 체결을 대기 중인 상태 - `PENDING_CANCEL`: 취소 대기. 취소 요청이 접수되어 브로커 응답을 대기 중인 상태 - `PENDING_REPLACE`: 정정 대기. 정정 요청이 접수되어 브로커 응답을 대기 중인 상태 - `PARTIAL_FILLED`: 부분 체결. 주문 수량 중 일부만 체결된 상태 - `FILLED`: 체결 완료. 주문 수량이 전량 체결된 상태 - `CANCELED`: 취소 완료. execution.filledQuantity를 통해 부분 체결 여부를 확인할 수 있음 - `REJECTED`: 거부됨. 브로커가 주문을 거부한 상태. execution.filledQuantity를 통해 부분 체결 여부를 확인할 수 있음 - `CANCEL_REJECTED`: 취소...
- Enum/Const: PENDING, PENDING_CANCEL, PENDING_REPLACE, PARTIAL_FILLED, FILLED, CANCELED, REJECTED, CANCEL_REJECTED, REPLACE_REJECTED, REPLACED

- 속성 없음 또는 primitive/enum 모델

### OrderbookEntry

- 공식 모델 Markdown: [OrderbookEntry](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderbookEntry.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `price` | Y | `string(decimal)` | - | maxLen=30 | 호가 |
| `volume` | Y | `string(decimal)` | - | maxLen=30 | 잔량 |

### OrderbookResponse

- 공식 모델 Markdown: [OrderbookResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OrderbookResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `timestamp` | N | `string(date-time) | null` | - | - | 데이터 시각. 데이터 미제공 시 null |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `asks` | Y | `array<OrderbookEntry>` | - | - | 매도호가 목록 (낮은 가격순) |
| `bids` | Y | `array<OrderbookEntry>` | - | - | 매수호가 목록 (높은 가격순) |

### OverviewDailyProfitLoss

- 공식 모델 Markdown: [OverviewDailyProfitLoss](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OverviewDailyProfitLoss.md)
- 타입: `object`
- 설명: 일간 손익. 전체 보유 종목의 통화별 합산

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `amount` | Y | `allOf<Price>` | - | - | 일간 손익금액 |
| `rate` | Y | `string(decimal)` | - | maxLen=30 | 일간 손익률 (소수비율). 전체 자산을 현재 환율로 원화 환산한 기준. 0.0185 = 1.85% |

### OverviewMarketValue

- 공식 모델 Markdown: [OverviewMarketValue](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OverviewMarketValue.md)
- 타입: `object`
- 설명: 시장 평가금액. 전체 보유 종목의 통화별 합산

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `amount` | Y | `allOf<Price>` | - | - | 시장 평가금액 |
| `amountAfterCost` | Y | `allOf<Price>` | - | - | 세금/수수료 공제 후 평가금액 |

### OverviewProfitLoss

- 공식 모델 Markdown: [OverviewProfitLoss](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/OverviewProfitLoss.md)
- 타입: `object`
- 설명: 손익. 전체 보유 종목의 통화별 합산

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `amount` | Y | `allOf<Price>` | - | - | 손익금액 |
| `amountAfterCost` | Y | `allOf<Price>` | - | - | 세금/수수료 공제 후 손익금액 |
| `rate` | Y | `string(decimal)` | - | maxLen=30 | 손익률 (소수비율). 전체 자산을 현재 환율로 원화 환산한 기준. 0.1516 = 15.16% |
| `rateAfterCost` | Y | `string(decimal)` | - | maxLen=30 | 세금/수수료 공제 후 손익률 (소수비율). 전체 자산을 현재 환율로 원화 환산한 기준. 0.1406 = 14.06% |

### PaginatedOrderResponse

- 공식 모델 Markdown: [PaginatedOrderResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/PaginatedOrderResponse.md)
- 타입: `object`
- 설명: 주문 목록 페이징 응답. - `status=OPEN`: 모든 대기 중 주문을 반환합니다. `nextCursor`는 항상 `null`, `hasNext`는 항상 `false`. - `status=CLOSED`: 현재 호출 시 `400 closed-not-supported` 를 반환합니다.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `orders` | Y | `array<Order>` | - | - | 주문 목록 |
| `nextCursor` | Y | `string | null` | - | - | 다음 페이지 커서. 다음 페이지가 없으면 null |
| `hasNext` | Y | `boolean` | - | - | 다음 페이지 존재 여부 |

### PreMarketSession

- 공식 모델 Markdown: [PreMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/PreMarketSession.md)
- 타입: `object`
- 설명: 프리마켓 세션

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 프리마켓 시작 |
| `singlePriceAuctionStartTime` | N | `oneOf<string(date-time) | null>` | - | - | 프리마켓 내 시가단일가 구간 시작 (NXT 프리마켓 접속매매 종료). 단일가 정보 결손 시 null |
| `endTime` | Y | `string(date-time)` | - | - | 프리마켓 종료 (시가단일가 종료) |

### Price

- 공식 모델 Markdown: [Price](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Price.md)
- 타입: `object`
- 설명: 통화별 합산 금액. 각 통화 필드는 해당 통화로 거래된 종목의 합만 포함합니다 (환율 환산을 통한 통화 간 합산 미포함).

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `krw` | Y | `string(decimal)` | - | maxLen=30 | KRW로 거래되는 국내 종목의 합산 금액. 국내 종목이 없으면 0 |
| `usd` | N | `string(decimal) | null` | - | maxLen=30 | USD로 거래되는 해외 종목의 합산 금액. 해외 종목이 없으면 null |

### PriceLimitResponse

- 공식 모델 Markdown: [PriceLimitResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/PriceLimitResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `timestamp` | Y | `string(date-time)` | - | - | 데이터 시각 |
| `upperLimitPrice` | N | `string(decimal) | null` | - | maxLen=30 | 상한가. 미국 주식 등 가격제한이 없는 시장에서는 null |
| `lowerLimitPrice` | N | `string(decimal) | null` | - | maxLen=30 | 하한가. 미국 주식 등 가격제한이 없는 시장에서는 null |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |

### PriceResponse

- 공식 모델 Markdown: [PriceResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/PriceResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `symbol` | Y | `string` | - | - | 종목 심볼 |
| `timestamp` | N | `string(date-time) | null` | - | - | 데이터 시각. 체결 미발생 등으로 시각이 없을 경우 null |
| `lastPrice` | Y | `string(decimal)` | - | maxLen=30 | 현재가 |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |

### ProfitLoss

- 공식 모델 Markdown: [ProfitLoss](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/ProfitLoss.md)
- 타입: `object`
- 설명: 손익. 거래 통화(currency) 기준

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `amount` | Y | `string(decimal)` | - | maxLen=30 | 손익금액 |
| `amountAfterCost` | Y | `string(decimal)` | - | maxLen=30 | 세금/수수료 공제 후 손익금액 |
| `rate` | Y | `string(decimal)` | - | maxLen=30 | 손익률. 소수비율 (0.1077 = 10.77%) |
| `rateAfterCost` | Y | `string(decimal)` | - | maxLen=30 | 세금/수수료 공제 후 손익률. 소수비율 (0.0846 = 8.46%) |

### RegularMarketSession

- 공식 모델 Markdown: [RegularMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/RegularMarketSession.md)
- 타입: `object`
- 설명: 정규장 세션. KRX·NXT 정규장의 합집합(가장 이른 시작 ~ 가장 늦은 종료). 종가단일가 구간을 포함

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 정규장 시작. 가장 이른 KRX/NXT 정규장 시작 시각 |
| `singlePriceAuctionStartTime` | N | `oneOf<string(date-time) | null>` | - | - | 정규장 내 종가단일가 구간 시작 (KRX 기준). KRX 휴장이면 null |
| `endTime` | Y | `string(date-time)` | - | - | 정규장 종료 (종가단일가 종료) |

### SellableQuantityResponse

- 공식 모델 Markdown: [SellableQuantityResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/SellableQuantityResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `sellableQuantity` | Y | `string(decimal)` | - | maxLen=30 | 판매 가능 수량. KR: 정수 (주 단위). US: 소수점 포함 가능 (주 단위). |

### StockInfo

- 공식 모델 Markdown: [StockInfo](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/StockInfo.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `symbol` | Y | `string` | - | - | 종목 심볼. |
| `name` | Y | `string` | - | - | 종목명 (한글) |
| `englishName` | Y | `string` | - | - | 영문 종목명 |
| `isinCode` | Y | `string` | - | - | 국제증권식별번호 (ISO 6166) |
| `market` | Y | `string` | KOSPI, KOSDAQ, NYSE, NASDAQ, AMEX, KR_ETC, US_ETC | - | 상장 시장. warnings API의 exchange(거래소 단위)와 달리 시장 세그먼트 단위로 구분 |
| `securityType` | Y | `string` | STOCK, FOREIGN_STOCK, DEPOSITARY_RECEIPT, INFRASTRUCTURE_FUND, REIT, ETF, FOREIGN_ETF, ETN, STOCK_WARRANTS | - | 종목 유형 |
| `isCommonShare` | Y | `boolean` | - | - | 보통주 여부. 우선주인 경우 false |
| `status` | Y | `string` | SCHEDULED, ACTIVE, DELISTED | - | 상장 상태 |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |
| `listDate` | N | `string(date) | null` | - | - | 상장일 (YYYY-MM-DD, KST 기준). 정보 미제공 시 null |
| `delistDate` | N | `string(date) | null` | - | - | 상장폐지일 (YYYY-MM-DD, KST 기준). 활성 종목은 null |
| `sharesOutstanding` | Y | `string(decimal)` | - | maxLen=30 | 발행주식수 |
| `leverageFactor` | N | `string(decimal) | null` | - | maxLen=30 | 레버리지 배수. ETF/ETN에만 적용 (1.0, 2.0, -1.0 등). 일반 주식 등 해당 없는 종목은 null |
| `koreanMarketDetail` | N | `oneOf<KrMarketDetail | null>` | - | - | 국내 시장 상세 정보. 국내 종목(KOSPI, KOSDAQ, KR_ETC)에만 제공되며, 해외 종목은 null |

### StockWarning

- 공식 모델 Markdown: [StockWarning](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/StockWarning.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `warningType` | Y | `string` | LIQUIDATION_TRADING, OVERHEATED, INVESTMENT_WARNING, INVESTMENT_RISK, VI_STATIC_AND_DYNAMIC, VI_STATIC, VI_DYNAMIC, STOCK_WARRANTS | - | 유의사항 유형. 클라이언트는 unknown code 를 허용하도록 구현해야 합니다. \| 값 \| 의미 \| \|------\|------\| \| `LIQUIDATION_TRADING` \| 정리매매 (상장폐지 절차 진행 중) \| \| `OVERHEATED` \| 단기과열종목 지정 \| \| `INVESTMENT_WARNING` \| 투자경고종목 지정 \| \| `INVESTMENT_RI... |
| `exchange` | N | `string | null` | - | - | 거래소 코드 (KRX, NXT 등 물리적 거래소 단위). stocks API의 market(상장 시장 단위)과 추상화 수준이 다름. 거래소 무관 경고는 null |
| `startDate` | N | `string(date) | null` | - | - | 적용 시작일 (inclusive, YYYY-MM-DD, KST 기준). 시작일 미정 시 null |
| `endDate` | N | `string(date) | null` | - | - | 적용 종료일 (inclusive, YYYY-MM-DD, KST 기준). 진행 중이거나 미정 시 null |

### Trade

- 공식 모델 Markdown: [Trade](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/Trade.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `price` | Y | `string(decimal)` | - | maxLen=30 | 체결가 |
| `volume` | Y | `string(decimal)` | - | maxLen=30 | 체결 수량 |
| `timestamp` | Y | `string(date-time)` | - | - | 체결 시각 |
| `currency` | Y | `Currency` | KRW, USD | - | 통화 코드. - KRW: 한국 원화 - USD: 미국 달러 클라이언트는 unknown enum 값을 허용하도록 구현해야 합니다. |

### UsAfterMarketSession

- 공식 모델 Markdown: [UsAfterMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsAfterMarketSession.md)
- 타입: `object`
- 설명: 애프터마켓 세션

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 애프터마켓 시작 |
| `endTime` | Y | `string(date-time)` | - | - | 애프터마켓 종료 |

### UsDayMarketSession

- 공식 모델 Markdown: [UsDayMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsDayMarketSession.md)
- 타입: `object`
- 설명: 데이마켓 세션 (토스증권)

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 데이마켓 시작 |
| `endTime` | Y | `string(date-time)` | - | - | 데이마켓 종료 |

### UsMarketCalendarResponse

- 공식 모델 Markdown: [UsMarketCalendarResponse](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsMarketCalendarResponse.md)
- 타입: `object`

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `today` | Y | `UsMarketDay` | - | - | 미국 시장 영업일 정보. 4 세션(`dayMarket`, `preMarket`, `regularMarket`, `afterMarket`) 각각 nullable. 휴장일이면 4 세션 모두 null. |
| `previousBusinessDay` | Y | `UsMarketDay` | - | - | 미국 시장 영업일 정보. 4 세션(`dayMarket`, `preMarket`, `regularMarket`, `afterMarket`) 각각 nullable. 휴장일이면 4 세션 모두 null. |
| `nextBusinessDay` | Y | `UsMarketDay` | - | - | 미국 시장 영업일 정보. 4 세션(`dayMarket`, `preMarket`, `regularMarket`, `afterMarket`) 각각 nullable. 휴장일이면 4 세션 모두 null. |

### UsMarketDay

- 공식 모델 Markdown: [UsMarketDay](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsMarketDay.md)
- 타입: `object`
- 설명: 미국 시장 영업일 정보. 4 세션(`dayMarket`, `preMarket`, `regularMarket`, `afterMarket`) 각각 nullable. 휴장일이면 4 세션 모두 null.

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `date` | Y | `string(date)` | - | - | 영업일 (미국 현지 기준) |
| `dayMarket` | N | `oneOf<UsDayMarketSession | null>` | - | - | 데이마켓 세션 (토스증권). 휴장이면 null |
| `preMarket` | N | `oneOf<UsPreMarketSession | null>` | - | - | 프리마켓 세션. 휴장이면 null |
| `regularMarket` | N | `oneOf<UsRegularMarketSession | null>` | - | - | 정규장 세션. 휴장이면 null |
| `afterMarket` | N | `oneOf<UsAfterMarketSession | null>` | - | - | 애프터마켓 세션. 휴장이면 null |

### UsPreMarketSession

- 공식 모델 Markdown: [UsPreMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsPreMarketSession.md)
- 타입: `object`
- 설명: 프리마켓 세션

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 프리마켓 시작 |
| `endTime` | Y | `string(date-time)` | - | - | 프리마켓 종료 |

### UsRegularMarketSession

- 공식 모델 Markdown: [UsRegularMarketSession](https://openapi.tossinvest.com/openapi-docs/latest/api-reference/Models/UsRegularMarketSession.md)
- 타입: `object`
- 설명: 정규장 세션

| 필드 | 필수 | 타입 | Enum/Const | 제약 | 설명 |
|---|---:|---|---|---|---|
| `startTime` | Y | `string(date-time)` | - | - | 정규장 시작 |
| `endTime` | Y | `string(date-time)` | - | - | 정규장 종료 |

## 표준 에러 처리

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "요청 값이 올바르지 않습니다.",
    "data": {
      "field": "side",
      "allowedValues": [
        "BUY",
        "SELL"
      ]
    }
  }
}
```

| HTTP | code | 구현상 처리 힌트 |
|---:|---|---|
| `400` | `invalid-request` | 호가 유형, 주문 방향, 수량/금액, 필수 파라미터 등 요청 값 오류 |
| `400` | `confirm-high-value-required` | 1억원 이상 주문에서 고액 주문 확인 플래그 누락 |
| `400` | `closed-not-supported` | 종료 주문 조회(status=CLOSED)는 현재 미지원 |
| `400` | `account-header-required` | 계좌 헤더 X-Tossinvest-Account 누락 |
| `401` | `invalid-token` | 토큰 형식 또는 값 오류 |
| `401` | `edge-blocked` | Authorization 헤더 누락 또는 엣지 인증 차단 |
| `401` | `expired-token` | 액세스 토큰 만료 |
| `401` | `login-user-not-found` | 토큰에 대응하는 로그인 사용자 없음 |
| `403` | `edge-blocked` | 허용되지 않은 요청 |
| `403` | `forbidden` | 권한 부족 |
| `404` | `edge-blocked` | 지원하지 않는 API 경로 |
| `404` | `stock-not-found` | 종목 없음 |
| `404` | `exchange-rate-not-found` | 환율 정보 없음 |
| `404` | `account-not-found` | 계좌 없음 |
| `404` | `order-not-found` | 주문 없음 |
| `409` | `request-in-progress` | 동일 clientOrderId 주문 생성 처리 중 |
| `409` | `already-filled` | 정정/취소 대상 주문 이미 체결 |
| `409` | `already-canceled` | 정정/취소 대상 주문 이미 취소 |
| `409` | `already-modified` | 정정/취소 대상 주문 이미 정정 |
| `409` | `already-rejected` | 정정/취소 대상 주문 이미 거부 |
| `409` | `already-processing` | 동일 주문 정정/취소 처리 중 |
| `422` | `insufficient-buying-power` | 주문 가능 금액 부족 |
| `422` | `order-hours-closed` | 주문 접수 불가 시간 |
| `422` | `stock-restricted` | 거래 제한 종목 |
| `422` | `price-out-of-range` | 주문 가격이 허용 범위 밖 |
| `422` | `opposite-pending-order-exists` | 동일 종목 반대 방향 대기 주문 존재 |
| `422` | `order-type-not-allowed` | 현재 사용할 수 없는 호가 유형 |
| `422` | `prerequisite-required` | 약관 동의/위험 고지 등 사전 요건 미충족 |
| `422` | `market-not-supported-for-stock` | 해당 종목은 요청 시장에서 거래 불가(KR) |
| `422` | `investor-exchange-not-integrated` | 투자자지시 거래소 설정이 통합(SOR)이 아님(KR) |
| `422` | `amount-order-outside-regular-hours` | 미국 금액 주문은 정규장에만 가능 |
| `422` | `modify-restricted` | 정정 제한 주문 |
| `422` | `cancel-restricted` | 취소 제한 주문 |
| `429` | `edge-rate-limit-exceeded` | 엣지 레이트 리밋 초과 |
| `429` | `rate-limit-exceeded` | 서비스 레이트 리밋 초과 |
| `500` | `internal-error` | 서버 일시 장애 |
| `500` | `maintenance` | 시스템 점검 |

## AI 에이전트 구현 체크리스트

- 환경 변수: `TOSSINVEST_CLIENT_ID`, `TOSSINVEST_CLIENT_SECRET`, 선택적으로 기본 `TOSSINVEST_ACCOUNT_SEQ`를 사용하세요.
- 토큰 캐시: `expires_in`을 기준으로 만료 전 갱신하고, 401/expired-token에서는 재발급 후 1회만 재시도하세요.
- 계좌 헤더: 계좌/주문 관련 API 래퍼에는 accountSeq를 필수 인자로 두고 누락 시 API 호출 전에 실패시키세요.
- 주문 생성: `clientOrderId`를 사용하면 중복 요청과 재시도 제어가 쉬워집니다.
- 429 처리: `Retry-After`를 우선하고, 없으면 `X-RateLimit-Reset` 또는 지수 백오프를 사용하세요.
- 숫자 처리: 금액/가격/수량은 부동소수점 대신 decimal 문자열 또는 Decimal 계열 타입으로 다루세요.
- 날짜/시간: 문서의 KST 기준 필터와 미국장 세션을 혼동하지 않도록 API별 파라미터 설명을 확인하세요.
- unknown enum: 경고 유형 등 일부 값은 확장 가능하므로 알 수 없는 문자열을 허용하는 파서를 권장합니다.
