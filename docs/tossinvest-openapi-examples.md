# 토스증권 Open API 예시 모음

- 생성일: 2026-06-09 18:28:03 KST
- 출처: https://developers.tossinvest.com/docs
- Source of Truth: https://openapi.tossinvest.com/openapi-docs/latest/openapi.json
- 이 파일은 OpenAPI JSON 안의 `example`/`examples` 노드를 개발 참조용으로 추출한 companion 문서입니다.
- 추출 개수: endpoint example 222개, component schema example 139개

## Endpoint Examples

### POST /oauth2/token

- operationId: `issueOAuth2Token`
- 요약: OAuth2 액세스 토큰 발급

#### Request 'application/x-www-form-urlencoded' example 'example'

```json
{
  "grant_type": "client_credentials",
  "client_id": "c_01HXYZABCDEFG123456789",
  "client_secret": "s_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

#### Response '200' 'application/json' example 'example'

```json
{
  "access_token": "eyJraWQiOiIyMDI2LTA0LTAxLWtleSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJjXzAxSFhZWiJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

#### Response '400' 'application/json' example 'invalidRequest'
- label: 필수 파라미터 누락 / 형식 오류

```json
{
  "error": "invalid_request",
  "error_description": "Required parameter is missing."
}
```

#### Response '400' 'application/json' example 'unsupportedGrantType'
- label: 지원하지 않는 grant_type

```json
{
  "error": "unsupported_grant_type",
  "error_description": "Only client_credentials grant type is supported."
}
```

#### Response '401' 'application/json' example 'example'

```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed."
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

### GET /api/v1/orderbook

- operationId: `getOrderbook`
- 요약: 호가 조회

#### Response '200' 'application/json' example 'krStock'
- label: 국내 주식 (삼성전자)

```json
{
  "result": {
    "timestamp": "2026-03-25T09:30:00.123+09:00",
    "currency": "KRW",
    "asks": [
      {
        "price": "72300",
        "volume": "1200"
      },
      {
        "price": "72200",
        "volume": "3400"
      },
      {
        "price": "72100",
        "volume": "8500"
      }
    ],
    "bids": [
      {
        "price": "72000",
        "volume": "5200"
      },
      {
        "price": "71900",
        "volume": "4100"
      },
      {
        "price": "71800",
        "volume": "2700"
      }
    ]
  }
}
```

#### Response '200' 'application/json' example 'usStock'
- label: 해외 주식 (Apple)

```json
{
  "result": {
    "timestamp": "2026-03-25T22:30:00.456+09:00",
    "currency": "USD",
    "asks": [
      {
        "price": "185.75",
        "volume": "250"
      },
      {
        "price": "185.70",
        "volume": "410"
      }
    ],
    "bids": [
      {
        "price": "185.65",
        "volume": "180"
      },
      {
        "price": "185.60",
        "volume": "320"
      }
    ]
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/prices

- operationId: `getPrices`
- 요약: 현재가 조회

#### Response '200' 'application/json' example 'krStock'
- label: 국내 주식 (삼성전자)

```json
{
  "result": [
    {
      "symbol": "005930",
      "timestamp": "2026-03-25T09:30:00.123+09:00",
      "lastPrice": "72000",
      "currency": "KRW"
    }
  ]
}
```

#### Response '200' 'application/json' example 'usStock'
- label: 해외 주식 (Apple)

```json
{
  "result": [
    {
      "symbol": "AAPL",
      "timestamp": "2026-03-25T22:30:00.456+09:00",
      "lastPrice": "185.70",
      "currency": "USD"
    }
  ]
}
```

#### Response '400' 'application/json' example 'invalidBatchSize'
- label: symbols 개수가 허용 범위(1~200) 를 벗어남

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "요청이 올바르지 않습니다.",
    "data": {
      "field": "symbols",
      "constraint": {
        "min": 1,
        "max": 200
      }
    }
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/trades

- operationId: `getTrades`
- 요약: 최근 체결 내역 조회

#### Response '200' 'application/json' example 'krStock'
- label: 국내 주식 (삼성전자)

```json
{
  "result": [
    {
      "price": "72000",
      "volume": "120",
      "timestamp": "2026-03-25T09:30:42.000+09:00",
      "currency": "KRW"
    },
    {
      "price": "71900",
      "volume": "50",
      "timestamp": "2026-03-25T09:30:41.500+09:00",
      "currency": "KRW"
    },
    {
      "price": "72000",
      "volume": "200",
      "timestamp": "2026-03-25T09:30:40.800+09:00",
      "currency": "KRW"
    }
  ]
}
```

#### Response '200' 'application/json' example 'usStock'
- label: 해외 주식 (Apple)

```json
{
  "result": [
    {
      "price": "185.70",
      "volume": "15",
      "timestamp": "2026-03-25T22:30:42.100+09:00",
      "currency": "USD"
    },
    {
      "price": "185.75",
      "volume": "8",
      "timestamp": "2026-03-25T22:30:41.700+09:00",
      "currency": "USD"
    }
  ]
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/price-limits

- operationId: `getPriceLimit`
- 요약: 상/하한가 조회

#### Response '200' 'application/json' example 'krStock'
- label: 국내 주식 (삼성전자)

```json
{
  "result": {
    "timestamp": "2026-03-25T09:30:00.123+09:00",
    "upperLimitPrice": "93000",
    "lowerLimitPrice": "50400",
    "currency": "KRW"
  }
}
```

#### Response '200' 'application/json' example 'usStock'
- label: 해외 주식 (Apple, 가격제한 없음)

```json
{
  "result": {
    "timestamp": "2026-03-25T22:30:00.456+09:00",
    "upperLimitPrice": null,
    "lowerLimitPrice": null,
    "currency": "USD"
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/candles

- operationId: `getCandles`
- 요약: 캔들 차트 조회

#### Response '200' 'application/json' example 'dailyCandles'
- label: 일봉 (1d)

```json
{
  "result": {
    "candles": [
      {
        "timestamp": "2026-03-25T09:00:00+09:00",
        "openPrice": "71600",
        "highPrice": "72300",
        "lowPrice": "71500",
        "closePrice": "72000",
        "volume": "3521000",
        "currency": "KRW"
      },
      {
        "timestamp": "2026-03-24T09:00:00+09:00",
        "openPrice": "71200",
        "highPrice": "71800",
        "lowPrice": "71000",
        "closePrice": "71600",
        "volume": "2984000",
        "currency": "KRW"
      }
    ],
    "nextBefore": "2026-03-24T09:00:00+09:00"
  }
}
```

#### Response '200' 'application/json' example 'minuteCandles'
- label: 분봉 (1m)

```json
{
  "result": {
    "candles": [
      {
        "timestamp": "2026-03-25T09:32:00+09:00",
        "openPrice": "72000",
        "highPrice": "72100",
        "lowPrice": "71950",
        "closePrice": "72050",
        "volume": "15200",
        "currency": "KRW"
      },
      {
        "timestamp": "2026-03-25T09:31:00+09:00",
        "openPrice": "71950",
        "highPrice": "72050",
        "lowPrice": "71900",
        "closePrice": "72000",
        "volume": "18400",
        "currency": "KRW"
      }
    ],
    "nextBefore": "2026-03-25T09:31:00+09:00"
  }
}
```

#### Response '200' 'application/json' example 'lastPage'
- label: 마지막 페이지 (nextBefore null)

```json
{
  "result": {
    "candles": [
      {
        "timestamp": "2026-03-20T09:00:00+09:00",
        "openPrice": "70800",
        "highPrice": "71200",
        "lowPrice": "70500",
        "closePrice": "71000",
        "volume": "2112000",
        "currency": "KRW"
      }
    ],
    "nextBefore": null
  }
}
```

#### Response '400' 'application/json' example 'unsupportedCandleInterval'
- label: 지원하지 않는 캔들 주기

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "지원하지 않는 캔들 주기입니다.",
    "data": {
      "field": "interval",
      "allowedValues": [
        "1m",
        "1d"
      ]
    }
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/stocks

- operationId: `getStocks`
- 요약: 종목 기본 정보 조회

#### Response '200' 'application/json' example 'multiple'
- label: 다건 조회 (국내 + 미국)

```json
{
  "result": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "englishName": "SamsungElec",
      "isinCode": "KR7005930003",
      "market": "KOSPI",
      "securityType": "STOCK",
      "isCommonShare": true,
      "status": "ACTIVE",
      "currency": "KRW",
      "listDate": "1975-06-11",
      "delistDate": null,
      "sharesOutstanding": "5919637922",
      "leverageFactor": null,
      "koreanMarketDetail": {
        "liquidationTrading": false,
        "nxtSupported": true,
        "krxTradingSuspended": false,
        "nxtTradingSuspended": false
      }
    },
    {
      "symbol": "AAPL",
      "name": "애플",
      "englishName": "APPLE INC",
      "isinCode": "US0378331005",
      "market": "NASDAQ",
      "securityType": "STOCK",
      "isCommonShare": true,
      "status": "ACTIVE",
      "currency": "USD",
      "listDate": "1980-12-12",
      "delistDate": null,
      "sharesOutstanding": "14702703000",
      "leverageFactor": null,
      "koreanMarketDetail": null
    }
  ]
}
```

#### Response '200' 'application/json' example 'krxStock'
- label: 국내 주식 (삼성전자)

```json
{
  "result": [
    {
      "symbol": "005930",
      "name": "삼성전자",
      "englishName": "SamsungElec",
      "isinCode": "KR7005930003",
      "market": "KOSPI",
      "securityType": "STOCK",
      "isCommonShare": true,
      "status": "ACTIVE",
      "currency": "KRW",
      "listDate": "1975-06-11",
      "delistDate": null,
      "sharesOutstanding": "5919637922",
      "leverageFactor": null,
      "koreanMarketDetail": {
        "liquidationTrading": false,
        "nxtSupported": true,
        "krxTradingSuspended": false,
        "nxtTradingSuspended": false
      }
    }
  ]
}
```

#### Response '200' 'application/json' example 'usStock'
- label: 미국 주식 (Apple)

```json
{
  "result": [
    {
      "symbol": "AAPL",
      "name": "애플",
      "englishName": "APPLE INC",
      "isinCode": "US0378331005",
      "market": "NASDAQ",
      "securityType": "STOCK",
      "isCommonShare": true,
      "status": "ACTIVE",
      "currency": "USD",
      "listDate": "1980-12-12",
      "delistDate": null,
      "sharesOutstanding": "14702703000",
      "leverageFactor": null,
      "koreanMarketDetail": null
    }
  ]
}
```

#### Response '200' 'application/json' example 'etf'
- label: ETF (KODEX 200)

```json
{
  "result": [
    {
      "symbol": "069500",
      "name": "KODEX 200",
      "englishName": "KODEX 200",
      "isinCode": "KR7069500007",
      "market": "KOSPI",
      "securityType": "ETF",
      "isCommonShare": true,
      "status": "ACTIVE",
      "currency": "KRW",
      "listDate": "2002-10-14",
      "delistDate": null,
      "sharesOutstanding": "208050000",
      "leverageFactor": "1",
      "koreanMarketDetail": {
        "liquidationTrading": false,
        "nxtSupported": false,
        "krxTradingSuspended": false,
        "nxtTradingSuspended": null
      }
    }
  ]
}
```

#### Response '400' 'application/json' example 'tooManySymbols'
- label: 허용 개수 초과 (1~200건)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "요청이 올바르지 않습니다.",
    "data": {
      "field": "symbols",
      "constraint": {
        "min": 1,
        "max": 200
      }
    }
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '403' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "forbidden",
    "message": "요청에 필요한 권한이 부족합니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/stocks/{symbol}/warnings

- operationId: `getStockWarnings`
- 요약: 매수 유의사항 조회

#### Response '200' 'application/json' example 'withWarnings'
- label: 유의사항이 있는 종목

```json
{
  "result": [
    {
      "warningType": "OVERHEATED",
      "exchange": "KRX",
      "startDate": "2026-03-20",
      "endDate": "2026-03-27"
    },
    {
      "warningType": "VI_STATIC",
      "exchange": "KRX",
      "startDate": "2026-03-26",
      "endDate": null
    }
  ]
}
```

#### Response '200' 'application/json' example 'noWarnings'
- label: 유의사항이 없는 종목

```json
{
  "result": []
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '403' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "forbidden",
    "message": "요청에 필요한 권한이 부족합니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/exchange-rate

- operationId: `getExchangeRate`
- 요약: 환율 조회

#### Response '200' 'application/json' example 'usdToKrwUp'
- label: USD→KRW 환율 (상승)

```json
{
  "result": {
    "baseCurrency": "USD",
    "quoteCurrency": "KRW",
    "rate": "1380.5",
    "midRate": "1375",
    "basisPoint": "40",
    "rateChangeType": "UP",
    "validFrom": "2026-03-25T09:30:00+09:00",
    "validUntil": "2026-03-25T09:31:00+09:00"
  }
}
```

#### Response '200' 'application/json' example 'usdToKrwDown'
- label: USD→KRW 환율 (하락)

```json
{
  "result": {
    "baseCurrency": "USD",
    "quoteCurrency": "KRW",
    "rate": "1372.3",
    "midRate": "1375",
    "basisPoint": "-19.6",
    "rateChangeType": "DOWN",
    "validFrom": "2026-03-25T09:30:00+09:00",
    "validUntil": "2026-03-25T09:31:00+09:00"
  }
}
```

#### Response '400' 'application/json' example 'unsupportedCurrency'
- label: 지원하지 않는 통화

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "지원하지 않는 통화입니다.",
    "data": {
      "field": "baseCurrency",
      "allowedValues": [
        "KRW",
        "USD"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'sameCurrency'
- label: 기준 통화와 상대 통화가 같음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "기준 통화와 상대 통화가 같을 수 없습니다.",
    "data": {
      "field": "baseCurrency,quoteCurrency"
    }
  }
}
```

#### Response '404' 'application/json' example 'exchangeRateNotFound'
- label: 요청한 시점의 환율 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "exchange-rate-not-found",
    "message": "요청한 시점의 환율 정보가 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/market-calendar/KR

- operationId: `getKrMarketCalendar`
- 요약: 국내 장 운영 정보 조회

#### Response '200' 'application/json' example 'businessDay'
- label: 영업일 (KRX+NXT 정상 운영)

```json
{
  "result": {
    "today": {
      "date": "2026-03-25",
      "integrated": {
        "preMarket": {
          "startTime": "2026-03-25T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-25T08:50:00+09:00",
          "endTime": "2026-03-25T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-03-25T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-25T15:20:00+09:00",
          "endTime": "2026-03-25T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-25T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-25T15:40:00+09:00",
          "endTime": "2026-03-25T20:00:00+09:00"
        }
      }
    },
    "previousBusinessDay": {
      "date": "2026-03-24",
      "integrated": {
        "preMarket": {
          "startTime": "2026-03-24T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-24T08:50:00+09:00",
          "endTime": "2026-03-24T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-03-24T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-24T15:20:00+09:00",
          "endTime": "2026-03-24T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-24T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-24T15:40:00+09:00",
          "endTime": "2026-03-24T20:00:00+09:00"
        }
      }
    },
    "nextBusinessDay": {
      "date": "2026-03-26",
      "integrated": {
        "preMarket": {
          "startTime": "2026-03-26T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-26T08:50:00+09:00",
          "endTime": "2026-03-26T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-03-26T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-26T15:20:00+09:00",
          "endTime": "2026-03-26T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-26T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-26T15:40:00+09:00",
          "endTime": "2026-03-26T20:00:00+09:00"
        }
      }
    }
  }
}
```

#### Response '200' 'application/json' example 'holidayToday'
- label: 휴장일 (today 만 휴장, integrated null)

```json
{
  "result": {
    "today": {
      "date": "2026-05-05",
      "integrated": null
    },
    "previousBusinessDay": {
      "date": "2026-05-04",
      "integrated": {
        "preMarket": {
          "startTime": "2026-05-04T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-05-04T08:50:00+09:00",
          "endTime": "2026-05-04T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-05-04T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-05-04T15:20:00+09:00",
          "endTime": "2026-05-04T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-05-04T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-05-04T15:40:00+09:00",
          "endTime": "2026-05-04T20:00:00+09:00"
        }
      }
    },
    "nextBusinessDay": {
      "date": "2026-05-06",
      "integrated": {
        "preMarket": {
          "startTime": "2026-05-06T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-05-06T08:50:00+09:00",
          "endTime": "2026-05-06T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-05-06T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-05-06T15:20:00+09:00",
          "endTime": "2026-05-06T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-05-06T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-05-06T15:40:00+09:00",
          "endTime": "2026-05-06T20:00:00+09:00"
        }
      }
    }
  }
}
```

#### Response '200' 'application/json' example 'nxtPreMarketHoliday'
- label: 부분 휴장 (NXT 프리마켓만 휴장, 정규장·애프터마켓은 운영)

```json
{
  "result": {
    "today": {
      "date": "2026-03-25",
      "integrated": {
        "preMarket": null,
        "regularMarket": {
          "startTime": "2026-03-25T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-25T15:20:00+09:00",
          "endTime": "2026-03-25T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-25T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-25T15:40:00+09:00",
          "endTime": "2026-03-25T20:00:00+09:00"
        }
      }
    },
    "previousBusinessDay": {
      "date": "2026-03-24",
      "integrated": {
        "preMarket": {
          "startTime": "2026-03-24T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-24T08:50:00+09:00",
          "endTime": "2026-03-24T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-03-24T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-24T15:20:00+09:00",
          "endTime": "2026-03-24T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-24T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-24T15:40:00+09:00",
          "endTime": "2026-03-24T20:00:00+09:00"
        }
      }
    },
    "nextBusinessDay": {
      "date": "2026-03-26",
      "integrated": {
        "preMarket": {
          "startTime": "2026-03-26T08:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-26T08:50:00+09:00",
          "endTime": "2026-03-26T09:00:00+09:00"
        },
        "regularMarket": {
          "startTime": "2026-03-26T09:00:00+09:00",
          "singlePriceAuctionStartTime": "2026-03-26T15:20:00+09:00",
          "endTime": "2026-03-26T15:30:00+09:00"
        },
        "afterMarket": {
          "startTime": "2026-03-26T15:30:00+09:00",
          "singlePriceAuctionEndTime": "2026-03-26T15:40:00+09:00",
          "endTime": "2026-03-26T20:00:00+09:00"
        }
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'unsupportedDate'
- label: 지원하지 않는 조회 일자

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "unsupported-date",
    "message": "요청한 조회 일자를 지원하지 않습니다.",
    "data": {
      "field": "date"
    }
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/market-calendar/US

- operationId: `getUsMarketCalendar`
- 요약: 해외 장 운영 정보 조회

#### Response '200' 'application/json' example 'businessDay'
- label: 영업일 (데이마켓 포함, 4 세션 nested)

```json
{
  "result": {
    "today": {
      "date": "2026-03-25",
      "dayMarket": {
        "startTime": "2026-03-25T09:00:00+09:00",
        "endTime": "2026-03-25T16:50:00+09:00"
      },
      "preMarket": {
        "startTime": "2026-03-25T17:00:00+09:00",
        "endTime": "2026-03-25T22:30:00+09:00"
      },
      "regularMarket": {
        "startTime": "2026-03-25T22:30:00+09:00",
        "endTime": "2026-03-26T05:00:00+09:00"
      },
      "afterMarket": {
        "startTime": "2026-03-26T05:00:00+09:00",
        "endTime": "2026-03-26T07:00:00+09:00"
      }
    },
    "previousBusinessDay": {
      "date": "2026-03-24",
      "dayMarket": {
        "startTime": "2026-03-24T09:00:00+09:00",
        "endTime": "2026-03-24T16:50:00+09:00"
      },
      "preMarket": {
        "startTime": "2026-03-24T17:00:00+09:00",
        "endTime": "2026-03-24T22:30:00+09:00"
      },
      "regularMarket": {
        "startTime": "2026-03-24T22:30:00+09:00",
        "endTime": "2026-03-25T05:00:00+09:00"
      },
      "afterMarket": {
        "startTime": "2026-03-25T05:00:00+09:00",
        "endTime": "2026-03-25T07:00:00+09:00"
      }
    },
    "nextBusinessDay": {
      "date": "2026-03-26",
      "dayMarket": {
        "startTime": "2026-03-26T09:00:00+09:00",
        "endTime": "2026-03-26T16:50:00+09:00"
      },
      "preMarket": {
        "startTime": "2026-03-26T17:00:00+09:00",
        "endTime": "2026-03-26T22:30:00+09:00"
      },
      "regularMarket": {
        "startTime": "2026-03-26T22:30:00+09:00",
        "endTime": "2026-03-27T05:00:00+09:00"
      },
      "afterMarket": {
        "startTime": "2026-03-27T05:00:00+09:00",
        "endTime": "2026-03-27T07:00:00+09:00"
      }
    }
  }
}
```

#### Response '200' 'application/json' example 'holidayToday'
- label: 휴장일 (today 만 휴장, 4 세션 모두 null)

```json
{
  "result": {
    "today": {
      "date": "2026-07-03",
      "dayMarket": null,
      "preMarket": null,
      "regularMarket": null,
      "afterMarket": null
    },
    "previousBusinessDay": {
      "date": "2026-07-02",
      "dayMarket": {
        "startTime": "2026-07-02T09:00:00+09:00",
        "endTime": "2026-07-02T16:50:00+09:00"
      },
      "preMarket": {
        "startTime": "2026-07-02T17:00:00+09:00",
        "endTime": "2026-07-02T22:30:00+09:00"
      },
      "regularMarket": {
        "startTime": "2026-07-02T22:30:00+09:00",
        "endTime": "2026-07-03T05:00:00+09:00"
      },
      "afterMarket": {
        "startTime": "2026-07-03T05:00:00+09:00",
        "endTime": "2026-07-03T07:00:00+09:00"
      }
    },
    "nextBusinessDay": {
      "date": "2026-07-06",
      "dayMarket": {
        "startTime": "2026-07-06T09:00:00+09:00",
        "endTime": "2026-07-06T16:50:00+09:00"
      },
      "preMarket": {
        "startTime": "2026-07-06T17:00:00+09:00",
        "endTime": "2026-07-06T22:30:00+09:00"
      },
      "regularMarket": {
        "startTime": "2026-07-06T22:30:00+09:00",
        "endTime": "2026-07-07T05:00:00+09:00"
      },
      "afterMarket": {
        "startTime": "2026-07-07T05:00:00+09:00",
        "endTime": "2026-07-07T07:00:00+09:00"
      }
    }
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/accounts

- operationId: `getAccounts`
- 요약: 계좌 목록 조회

#### Response '200' 'application/json' example 'brokerageAccount'
- label: 종합매매 계좌

```json
{
  "result": [
    {
      "accountNo": "12345678901",
      "accountSeq": 1,
      "accountType": "BROKERAGE"
    }
  ]
}
```

#### Response '200' 'application/json' example 'emptyAccounts'
- label: 계좌 없음

```json
{
  "result": []
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/holdings

- operationId: `getHoldings`
- 요약: 보유 주식 조회

#### Response '200' 'application/json' example 'withHoldings'
- label: 보유 종목 있음 (KR + US 혼합)

```json
{
  "result": {
    "totalPurchaseAmount": {
      "krw": "6500000",
      "usd": "1553"
    },
    "marketValue": {
      "amount": {
        "krw": "7200000",
        "usd": "1785"
      },
      "amountAfterCost": {
        "krw": "7050000",
        "usd": "1771.43"
      }
    },
    "profitLoss": {
      "amount": {
        "krw": "700000",
        "usd": "232"
      },
      "amountAfterCost": {
        "krw": "550000",
        "usd": "218.43"
      },
      "rate": "0.1179",
      "rateAfterCost": "0.0983"
    },
    "dailyProfitLoss": {
      "amount": {
        "krw": "100000",
        "usd": "25"
      },
      "rate": "0.0141"
    },
    "items": [
      {
        "symbol": "005930",
        "name": "삼성전자",
        "marketCountry": "KR",
        "currency": "KRW",
        "quantity": "100",
        "lastPrice": "72000",
        "averagePurchasePrice": "65000",
        "marketValue": {
          "purchaseAmount": "6500000",
          "amount": "7200000",
          "amountAfterCost": "7050000"
        },
        "profitLoss": {
          "amount": "700000",
          "amountAfterCost": "550000",
          "rate": "0.1077",
          "rateAfterCost": "0.0846"
        },
        "dailyProfitLoss": {
          "amount": "100000",
          "rate": "0.0141"
        },
        "cost": {
          "commission": "14400",
          "tax": "135600"
        }
      },
      {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "marketCountry": "US",
        "currency": "USD",
        "quantity": "10",
        "lastPrice": "178.5",
        "averagePurchasePrice": "155.3",
        "marketValue": {
          "purchaseAmount": "1553",
          "amount": "1785",
          "amountAfterCost": "1771.43"
        },
        "profitLoss": {
          "amount": "232",
          "amountAfterCost": "218.43",
          "rate": "0.1494",
          "rateAfterCost": "0.1406"
        },
        "dailyProfitLoss": {
          "amount": "25",
          "rate": "0.0142"
        },
        "cost": {
          "commission": "3.57",
          "tax": "10"
        }
      }
    ]
  }
}
```

#### Response '200' 'application/json' example 'filteredBySymbol'
- label: symbol 필터 적용 (005930)

```json
{
  "result": {
    "totalPurchaseAmount": {
      "krw": "6500000",
      "usd": null
    },
    "marketValue": {
      "amount": {
        "krw": "7200000",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "7050000",
        "usd": null
      }
    },
    "profitLoss": {
      "amount": {
        "krw": "700000",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "550000",
        "usd": null
      },
      "rate": "0.1077",
      "rateAfterCost": "0.0846"
    },
    "dailyProfitLoss": {
      "amount": {
        "krw": "100000",
        "usd": null
      },
      "rate": "0.0141"
    },
    "items": [
      {
        "symbol": "005930",
        "name": "삼성전자",
        "marketCountry": "KR",
        "currency": "KRW",
        "quantity": "100",
        "lastPrice": "72000",
        "averagePurchasePrice": "65000",
        "marketValue": {
          "purchaseAmount": "6500000",
          "amount": "7200000",
          "amountAfterCost": "7050000"
        },
        "profitLoss": {
          "amount": "700000",
          "amountAfterCost": "550000",
          "rate": "0.1077",
          "rateAfterCost": "0.0846"
        },
        "dailyProfitLoss": {
          "amount": "100000",
          "rate": "0.0141"
        },
        "cost": {
          "commission": "14400",
          "tax": "135600"
        }
      }
    ]
  }
}
```

#### Response '200' 'application/json' example 'filteredByUsSymbol'
- label: symbol 필터 적용 (AAPL, 해외 종목)

```json
{
  "result": {
    "totalPurchaseAmount": {
      "krw": "0",
      "usd": "1500.00"
    },
    "marketValue": {
      "amount": {
        "krw": "0",
        "usd": "1700.00"
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": "1650.00"
      }
    },
    "profitLoss": {
      "amount": {
        "krw": "0",
        "usd": "200.00"
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": "150.00"
      },
      "rate": "0.1333",
      "rateAfterCost": "0.1000"
    },
    "dailyProfitLoss": {
      "amount": {
        "krw": "0",
        "usd": "20.00"
      },
      "rate": "0.0119"
    },
    "items": [
      {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "marketCountry": "US",
        "currency": "USD",
        "quantity": "10",
        "lastPrice": "170.00",
        "averagePurchasePrice": "150.00",
        "marketValue": {
          "purchaseAmount": "1500.00",
          "amount": "1700.00",
          "amountAfterCost": "1650.00"
        },
        "profitLoss": {
          "amount": "200.00",
          "amountAfterCost": "150.00",
          "rate": "0.1333",
          "rateAfterCost": "0.10"
        },
        "dailyProfitLoss": {
          "amount": "20.00",
          "rate": "0.012"
        },
        "cost": {
          "commission": "2.15",
          "tax": null
        }
      }
    ]
  }
}
```

#### Response '200' 'application/json' example 'filteredBySymbolNotFound'
- label: symbol 필터 적용 — 해당 종목 미보유

```json
{
  "result": {
    "totalPurchaseAmount": {
      "krw": "0",
      "usd": null
    },
    "marketValue": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": null
      }
    },
    "profitLoss": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": null
      },
      "rate": "0",
      "rateAfterCost": "0"
    },
    "dailyProfitLoss": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "rate": "0"
    },
    "items": []
  }
}
```

#### Response '200' 'application/json' example 'emptyHoldings'
- label: 보유 종목 없음

```json
{
  "result": {
    "totalPurchaseAmount": {
      "krw": "0",
      "usd": null
    },
    "marketValue": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": null
      }
    },
    "profitLoss": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "amountAfterCost": {
        "krw": "0",
        "usd": null
      },
      "rate": "0",
      "rateAfterCost": "0"
    },
    "dailyProfitLoss": {
      "amount": {
        "krw": "0",
        "usd": null
      },
      "rate": "0"
    },
    "items": []
  }
}
```

#### Response '400' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/orders

- operationId: `getOrders`
- 요약: 주문 목록 조회

#### Response '200' 'application/json' example 'pendingMixed'
- label: 대기중 주문 — 국내+해외 혼합 (전량 반환)

```json
{
  "result": {
    "orders": [
      {
        "orderId": "bAGzNvMOOTa5Uy0xVzYNbxDJ3Qpobwau4jDF3hyZZGWbpHm7wha8CFZc7aXVOWAl",
        "symbol": "005930",
        "side": "BUY",
        "orderType": "LIMIT",
        "timeInForce": "DAY",
        "status": "PENDING",
        "price": "70000",
        "quantity": "10",
        "orderAmount": null,
        "currency": "KRW",
        "orderedAt": "2026-03-29T09:30:00+09:00",
        "canceledAt": null,
        "execution": {
          "filledQuantity": "0",
          "averageFilledPrice": null,
          "filledAmount": null,
          "commission": null,
          "tax": null,
          "filledAt": null,
          "settlementDate": null
        }
      },
      {
        "orderId": "RpP3_wtsiKe9btBvdendaHoBqOIY_Zb_xPkRfYaqCIvf2FXtMDv_mo7VnD7KB-ia",
        "symbol": "AAPL",
        "side": "SELL",
        "orderType": "LIMIT",
        "timeInForce": "DAY",
        "status": "PARTIAL_FILLED",
        "price": "185.5",
        "quantity": "5",
        "orderAmount": null,
        "currency": "USD",
        "orderedAt": "2026-03-29T10:00:00+09:00",
        "canceledAt": null,
        "execution": {
          "filledQuantity": "2",
          "averageFilledPrice": "185.25",
          "filledAmount": "370.5",
          "commission": "0.66",
          "tax": "0",
          "filledAt": "2026-03-29T10:00:05+09:00",
          "settlementDate": null
        }
      }
    ],
    "nextCursor": null,
    "hasNext": false
  }
}
```

#### Response '200' 'application/json' example 'completedWithNextPage'
- label: 완료된 주문 — 다음 페이지 있음

```json
{
  "result": {
    "orders": [
      {
        "orderId": "0d5QIHjmtksbsmM-hBRAgP-ExI8iodGm9fAR5txelPfnMM8XQ_swoJdwL5RpGWMo",
        "symbol": "005930",
        "side": "BUY",
        "orderType": "LIMIT",
        "timeInForce": "DAY",
        "status": "FILLED",
        "price": "70000",
        "quantity": "10",
        "orderAmount": null,
        "currency": "KRW",
        "orderedAt": "2026-03-28T09:30:00+09:00",
        "canceledAt": null,
        "execution": {
          "filledQuantity": "10",
          "averageFilledPrice": "70000",
          "filledAmount": "700000",
          "commission": "1400",
          "tax": "0",
          "filledAt": "2026-03-28T09:31:15+09:00",
          "settlementDate": "2026-03-30"
        }
      }
    ],
    "nextCursor": "eyJvcmRlcmVkQXQiOiIyMDI2LTAzLTI4VDA5OjMwOjAwKzA5OjAwIiwib3JkZXJJZCI6Ik9SRDIwMjYwMzI4MDAxIn0=",
    "hasNext": true
  }
}
```

#### Response '200' 'application/json' example 'empty'
- label: 주문 없음

```json
{
  "result": {
    "orders": [],
    "nextCursor": null,
    "hasNext": false
  }
}
```

#### Response '400' 'application/json' example 'invalidStatus'
- label: 유효하지 않은 주문 상태 필터

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "유효하지 않은 주문 상태 필터입니다. OPEN 또는 CLOSED 만 허용됩니다.",
    "data": {
      "field": "status",
      "allowedValues": [
        "OPEN",
        "CLOSED"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'closedNotSupported'
- label: CLOSED 상태 조회 미지원

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "closed-not-supported",
    "message": "CLOSED 상태 조회는 아직 지원되지 않습니다.",
    "data": {
      "field": "status"
    }
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### POST /api/v1/orders

- operationId: `createOrder`
- 요약: 주문 생성

#### Request 'application/json' example 'krLimitBuy'
- label: 국내주식 지정가 매수

```json
{
  "clientOrderId": "my-order-001",
  "symbol": "005930",
  "side": "BUY",
  "orderType": "LIMIT",
  "quantity": "10",
  "price": "70000"
}
```

#### Request 'application/json' example 'usMarketBuyAmount'
- label: 해외주식 소수점 시장가 매수 (금액)

```json
{
  "symbol": "AAPL",
  "side": "BUY",
  "orderType": "MARKET",
  "orderAmount": "100.5"
}
```

#### Request 'application/json' example 'usLocBuy'
- label: 해외주식 종가 지정가 매수 (LOC = LIMIT + CLS)

```json
{
  "symbol": "AAPL",
  "side": "BUY",
  "orderType": "LIMIT",
  "timeInForce": "CLS",
  "quantity": "10",
  "price": "185.5"
}
```

#### Response '200' 'application/json' example 'example'

```json
{
  "result": {
    "orderId": "0d5QIHjmtksbsmM-hBRAgP-ExI8iodGm9fAR5txelPfnMM8XQ_swoJdwL5RpGWMo",
    "clientOrderId": "my-order-001"
  }
}
```

#### Response '400' 'application/json' example 'invalidOrderType'
- label: 지원하지 않는 호가 유형

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "호가 유형이 올바르지 않습니다.",
    "data": {
      "field": "orderType",
      "allowedValues": [
        "LIMIT",
        "MARKET"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidTimeInForce'
- label: 지원하지 않는 유효 조건

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 유효 조건이 올바르지 않습니다.",
    "data": {
      "field": "timeInForce",
      "allowedValues": [
        "DAY",
        "CLS"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'clsConditionNotMet'
- label: 종가(CLS) 주문 조건 불충족

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "종가 주문(CLS)은 미국 주식 지정가 주문에만 사용할 수 있습니다.",
    "data": {
      "field": "timeInForce",
      "allowedConditions": {
        "marketCountry": "US",
        "orderType": "LIMIT"
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidSide'
- label: 잘못된 주문 방향

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 방향이 올바르지 않습니다.",
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

#### Response '400' 'application/json' example 'quantityOrAmountRequired'
- label: 수량 또는 금액 미지정

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 수량 또는 금액 중 하나를 지정해야 합니다.",
    "data": {
      "field": "quantity,orderAmount"
    }
  }
}
```

#### Response '400' 'application/json' example 'limitPriceRequired'
- label: 지정가 주문 가격 미지정

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "지정가 주문 시 가격을 지정해야 합니다.",
    "data": {
      "field": "price"
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidTickSize'
- label: 호가 단위 불일치

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 가격이 호가 단위에 맞지 않습니다.",
    "data": {
      "field": "price",
      "tickSize": "100",
      "nearestPrices": [
        "50100",
        "50200"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'confirmHighValueRequired'
- label: 1억원 이상 주문 확인 필요

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "confirm-high-value-required",
    "message": "1억원 이상 주문은 확인이 필요합니다.",
    "data": {
      "field": "confirmHighValueOrder",
      "limits": {
        "threshold": "100000000",
        "currency": "KRW"
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'amountUsMarketOnly'
- label: 금액 주문 조건 불충족

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "금액 주문은 미국 주식 시장가 주문에만 사용할 수 있습니다.",
    "data": {
      "field": "orderAmount",
      "allowedConditions": {
        "marketCountry": "US",
        "orderType": "MARKET"
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidQuantityFormat'
- label: 주문 수량 형식 오류

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 수량이 유효한 숫자가 아닙니다.",
    "data": {
      "field": "quantity",
      "format": "decimal",
      "pattern": "^-?\\d+(\\.\\d+)?$",
      "maxLength": 30
    }
  }
}
```

#### Response '400' 'application/json' example 'fractionalQuantityUsMarketOnly'
- label: 소수점 수량은 US 시장가에만 허용

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "소수점 수량 주문은 미국 주식 시장가 주문에만 사용할 수 있습니다.",
    "data": {
      "field": "quantity",
      "allowedConditions": {
        "marketCountry": "US",
        "orderType": "MARKET"
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '409' 'application/json' example 'requestInProgress'
- label: 동일 주문 키에 대해 처리 중인 요청 있음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "request-in-progress",
    "message": "동일 주문 키에 대해 처리 중인 요청이 있습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '422' 'application/json' example 'insufficientBuyingPower'
- label: 주문 가능 금액 부족

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "insufficient-buying-power",
    "message": "주문 가능 금액이 부족합니다."
  }
}
```

#### Response '422' 'application/json' example 'outsideOrderHours'
- label: 주문 접수 불가 시간

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-hours-closed",
    "message": "현재 해당 주문을 접수할 수 없는 시간입니다.",
    "data": {
      "retryAfterAt": "2026-01-02T09:00:00+09:00"
    }
  }
}
```

#### Response '422' 'application/json' example 'stockRestricted'
- label: 종목 주문 제한

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-restricted",
    "message": "해당 종목은 현재 주문이 제한되어 있습니다."
  }
}
```

#### Response '422' 'application/json' example 'priceOutOfRange'
- label: 주문 가격 허용 범위 초과

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "price-out-of-range",
    "message": "주문 가격이 허용 범위를 벗어났습니다."
  }
}
```

#### Response '422' 'application/json' example 'oppositePendingOrderExists'
- label: 반대 방향 미체결 주문 존재

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "opposite-pending-order-exists",
    "message": "동일 종목에 반대 방향의 체결 대기 주문이 있습니다."
  }
}
```

#### Response '422' 'application/json' example 'orderTypeNotAllowed'
- label: 현재 사용 불가 호가 유형

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-type-not-allowed",
    "message": "현재 사용할 수 없는 호가 유형입니다."
  }
}
```

#### Response '422' 'application/json' example 'prerequisiteRequired'
- label: 사전 자격 요건 미충족 (약관 동의/교육 이수/위험고지 등록)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "prerequisite-required",
    "message": "주문 전 필요한 사전 자격 요건이 충족되지 않았습니다."
  }
}
```

#### Response '422' 'application/json' example 'marketNotSupportedForStock'
- label: 종목-마켓 조합 거래 불가 (KR)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "market-not-supported-for-stock",
    "message": "해당 종목은 이 시장에서 거래할 수 없습니다."
  }
}
```

#### Response '422' 'application/json' example 'investorExchangeNotIntegrated'
- label: 투자자지시 거래소가 통합(SOR)이 아님 (KR)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "investor-exchange-not-integrated",
    "message": "투자자지시 거래소가 통합(SOR) 으로 설정되어 있어야 주문할 수 있습니다."
  }
}
```

#### Response '422' 'application/json' example 'amountOrderOutsideRegularHours'
- label: 정규장 외 시간 금액 주문 불가

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "amount-order-outside-regular-hours",
    "message": "미국 주식 금액 주문은 정규장 시간에만 접수할 수 있습니다.",
    "data": {
      "field": "orderAmount",
      "regularHours": {
        "start": "2026-03-30T09:30:00-04:00",
        "end": "2026-03-30T16:00:00-04:00"
      }
    }
  }
}
```

#### Response '422' 'application/json' example 'accountRestricted'
- label: 계좌 거래 제한 (사고 계좌, 거래 정지 등)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-restricted",
    "message": "계좌 상태가 주문을 허용하지 않습니다."
  }
}
```

#### Response '422' 'application/json' example 'maxOrderAmountExceeded'
- label: 30억원 초과 주문 (KR)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "max-order-amount-exceeded",
    "message": "최대 주문가능금액을 초과하였습니다.",
    "data": {
      "limits": {
        "maxAmount": "3000000000",
        "currency": "KRW"
      }
    }
  }
}
```

#### Response '422' 'application/json' example 'idempotencyKeyConflict'
- label: 동일 clientOrderId 로 이전과 다른 본문 재요청 (멱등성 키 충돌)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "idempotency-key-conflict",
    "message": "동일한 clientOrderId 로 다른 내용의 주문을 요청할 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'internalError'
- label: 주문 처리 중 일시적 오류

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

#### Response '500' 'application/json' example 'maintenance'
- label: 점검 중

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "maintenance",
    "message": "점검 중입니다. 잠시 후 다시 시도해 주세요.",
    "data": {
      "retryAfterSeconds": 600
    }
  }
}
```

### GET /api/v1/orders/{orderId}

- operationId: `getOrder`
- 요약: 주문 상세 조회

#### Response '200' 'application/json' example 'krLimitFilled'
- label: 국내주식 지정가 매수 — 체결 완료

```json
{
  "result": {
    "orderId": "0d5QIHjmtksbsmM-hBRAgP-ExI8iodGm9fAR5txelPfnMM8XQ_swoJdwL5RpGWMo",
    "symbol": "005930",
    "side": "BUY",
    "orderType": "LIMIT",
    "timeInForce": "DAY",
    "status": "FILLED",
    "price": "70000",
    "quantity": "10",
    "orderAmount": null,
    "currency": "KRW",
    "orderedAt": "2026-03-28T09:30:00+09:00",
    "canceledAt": null,
    "execution": {
      "filledQuantity": "10",
      "averageFilledPrice": "70000",
      "filledAmount": "700000",
      "commission": "1400",
      "tax": "0",
      "filledAt": "2026-03-28T09:31:15+09:00",
      "settlementDate": "2026-03-30"
    }
  }
}
```

#### Response '200' 'application/json' example 'usMarketPartialFilled'
- label: 해외주식 시장가 매수 — 부분 체결

```json
{
  "result": {
    "orderId": "J4lDkgVA-pMiRPOqXd2nBjxTj8hsTVhzOhIth7i1Izq14XYxIg1r_QTDEH7RTL8d",
    "symbol": "AAPL",
    "side": "BUY",
    "orderType": "MARKET",
    "timeInForce": "DAY",
    "status": "PARTIAL_FILLED",
    "price": null,
    "quantity": "5",
    "orderAmount": null,
    "currency": "USD",
    "orderedAt": "2026-03-28T23:30:00+09:00",
    "canceledAt": null,
    "execution": {
      "filledQuantity": "3",
      "averageFilledPrice": "185.25",
      "filledAmount": "555.75",
      "commission": "0.99",
      "tax": "0",
      "filledAt": "2026-03-28T23:30:05+09:00",
      "settlementDate": null
    }
  }
}
```

#### Response '200' 'application/json' example 'rejected'
- label: 주문 거부

```json
{
  "result": {
    "orderId": "Oqqsu76YSdwKZsdKbPwy-D7buUwy-RH2xZYbYSzAyAnlPy48Al5Lb7FyMKwibw4i",
    "symbol": "AAPL",
    "side": "BUY",
    "orderType": "MARKET",
    "timeInForce": "DAY",
    "status": "REJECTED",
    "price": null,
    "quantity": "0.5",
    "orderAmount": null,
    "currency": "USD",
    "orderedAt": "2026-03-28T23:30:00+09:00",
    "canceledAt": null,
    "execution": {
      "filledQuantity": "0",
      "averageFilledPrice": null,
      "filledAmount": null,
      "commission": null,
      "tax": null,
      "filledAt": null,
      "settlementDate": null
    }
  }
}
```

#### Response '400' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-not-found",
    "message": "주문을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### POST /api/v1/orders/{orderId}/modify

- operationId: `modifyOrder`
- 요약: 주문 정정

#### Request 'application/json' example 'krModify'
- label: 국내주식 가격+수량 정정

```json
{
  "orderType": "LIMIT",
  "quantity": "15",
  "price": "71000"
}
```

#### Request 'application/json' example 'usModify'
- label: 해외주식 가격 정정

```json
{
  "orderType": "LIMIT",
  "price": "185.5"
}
```

#### Response '200' 'application/json' example 'example'

```json
{
  "result": {
    "orderId": "5nfzdqmzfnAw3LFXWHPRy0UNi7y_WZlphJh5hRIsi25-NIfm_GtQgXima5QD2hUz"
  }
}
```

#### Response '400' 'application/json' example 'invalidPrice'
- label: 지정가 주문 가격 미지정

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "지정가 주문에는 가격이 필요합니다.",
    "data": {
      "field": "price"
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidQuantityKr'
- label: 국내주식 주문 수량 오류

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 수량이 유효하지 않습니다.",
    "data": {
      "field": "quantity",
      "constraint": {
        "min": 1,
        "integerOnly": true
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidTickSize'
- label: 호가 단위 불일치

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "주문 가격이 호가 단위에 맞지 않습니다.",
    "data": {
      "field": "price",
      "tickSize": "100",
      "nearestPrices": [
        "50100",
        "50200"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'invalidParameter'
- label: 주문 파라미터 오류

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "요청이 올바르지 않습니다."
  }
}
```

#### Response '400' 'application/json' example 'usModifyQuantityNotSupported'
- label: 미국 주식 주문 정정은 가격만 지원

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "us-modify-quantity-not-supported",
    "message": "미국 주식 주문 정정은 가격만 지원합니다.",
    "data": {
      "field": "quantity"
    }
  }
}
```

#### Response '400' 'application/json' example 'confirmHighValueRequired'
- label: 정정 후 1억원 이상 주문 확인 필요

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "confirm-high-value-required",
    "message": "1억원 이상 주문은 확인이 필요합니다.",
    "data": {
      "field": "confirmHighValueOrder",
      "limits": {
        "threshold": "100000000",
        "currency": "KRW"
      }
    }
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'orderNotFound'
- label: 주문을 찾을 수 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-not-found",
    "message": "주문을 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'accountNotFound'
- label: 계좌 부재

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-not-found",
    "message": "계좌를 찾을 수 없습니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyFilled'
- label: 이미 체결된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-filled",
    "message": "이미 체결된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyCanceled'
- label: 이미 취소된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-canceled",
    "message": "이미 취소된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyModified'
- label: 이미 정정된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-modified",
    "message": "이미 정정된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'rejectedOrder'
- label: 거부된 주문 정정 시도

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-rejected",
    "message": "거부된 주문은 정정/취소할 수 없습니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyProcessing'
- label: 주문 처리 중

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-processing",
    "message": "주문이 처리 중입니다. 잠시 후 다시 시도해 주세요.",
    "data": {
      "retryAfterSeconds": 1
    }
  }
}
```

#### Response '422' 'application/json' example 'modifyRestricted'
- label: 정정 불가 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "modify-restricted",
    "message": "해당 주문은 정정할 수 없습니다."
  }
}
```

#### Response '422' 'application/json' example 'outsideOrderHours'
- label: 주문 접수 불가 시간

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-hours-closed",
    "message": "현재 해당 주문을 접수할 수 없는 시간입니다.",
    "data": {
      "retryAfterAt": "2026-01-02T09:00:00+09:00"
    }
  }
}
```

#### Response '422' 'application/json' example 'investorExchangeNotIntegrated'
- label: 투자자지시 거래소가 통합(SOR)이 아님 (KR)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "investor-exchange-not-integrated",
    "message": "투자자지시 거래소가 통합(SOR) 으로 설정되어 있어야 주문할 수 있습니다."
  }
}
```

#### Response '422' 'application/json' example 'prerequisiteRequired'
- label: 사전 자격 요건 미충족 (약관 동의/교육 이수/위험고지 등록)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "prerequisite-required",
    "message": "주문 전 필요한 사전 자격 요건이 충족되지 않았습니다."
  }
}
```

#### Response '422' 'application/json' example 'amountOrderOutsideRegularHours'
- label: 정규장 외 시간 금액 주문 정정 불가

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "amount-order-outside-regular-hours",
    "message": "미국 주식 금액 주문은 정규장 시간에만 접수할 수 있습니다.",
    "data": {
      "field": "orderAmount",
      "regularHours": {
        "start": "2026-03-30T09:30:00-04:00",
        "end": "2026-03-30T16:00:00-04:00"
      }
    }
  }
}
```

#### Response '422' 'application/json' example 'accountRestricted'
- label: 계좌 정정 제한 (사고 계좌 등)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-restricted",
    "message": "계좌 상태가 주문을 허용하지 않습니다."
  }
}
```

#### Response '422' 'application/json' example 'maxOrderAmountExceeded'
- label: 30억원 초과 정정 (KR)

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "max-order-amount-exceeded",
    "message": "최대 주문가능금액을 초과하였습니다.",
    "data": {
      "limits": {
        "maxAmount": "3000000000",
        "currency": "KRW"
      }
    }
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### POST /api/v1/orders/{orderId}/cancel

- operationId: `cancelOrder`
- 요약: 주문 취소

#### Request 'application/json' example 'example'

```json
{}
```

#### Response '200' 'application/json' example 'example'

```json
{
  "result": {
    "orderId": "Kx9mTqR2vLwE7oPn3YhBjCf1dAsU6gZi8rNk4bWcXeJtMlSyDuQaHp5oVzI0FvRw"
  }
}
```

#### Response '400' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-not-found",
    "message": "주문을 찾을 수 없습니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyFilled'
- label: 이미 체결된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-filled",
    "message": "이미 체결된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyCanceled'
- label: 이미 취소된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-canceled",
    "message": "이미 취소된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyModified'
- label: 이미 정정된 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-modified",
    "message": "이미 정정된 주문입니다."
  }
}
```

#### Response '409' 'application/json' example 'rejectedOrder'
- label: 거부된 주문 취소 시도

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-rejected",
    "message": "거부된 주문은 정정/취소할 수 없습니다."
  }
}
```

#### Response '409' 'application/json' example 'alreadyProcessing'
- label: 주문 처리 중

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "already-processing",
    "message": "주문이 처리 중입니다. 잠시 후 다시 시도해 주세요.",
    "data": {
      "retryAfterSeconds": 1
    }
  }
}
```

#### Response '422' 'application/json' example 'cancelRestricted'
- label: 취소 불가 주문

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "cancel-restricted",
    "message": "해당 주문은 취소할 수 없습니다."
  }
}
```

#### Response '422' 'application/json' example 'outsideOrderHours'
- label: 취소 접수 불가 시간

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "order-hours-closed",
    "message": "현재 해당 주문을 접수할 수 없는 시간입니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/buying-power

- operationId: `getBuyingPower`
- 요약: 매수 가능 금액 조회

#### Response '200' 'application/json' example 'krw'
- label: 원화 응답

```json
{
  "result": {
    "currency": "KRW",
    "cashBuyingPower": "5000000"
  }
}
```

#### Response '200' 'application/json' example 'usd'
- label: 달러 응답

```json
{
  "result": {
    "currency": "USD",
    "cashBuyingPower": "3500.5"
  }
}
```

#### Response '400' 'application/json' example 'unsupportedCurrency'
- label: 지원하지 않는 통화

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-request",
    "message": "지원하지 않는 통화입니다.",
    "data": {
      "field": "currency",
      "allowedValues": [
        "KRW",
        "USD"
      ]
    }
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'accountNotFound'
- label: 계좌 부재

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-not-found",
    "message": "계좌를 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/sellable-quantity

- operationId: `getSellableQuantity`
- 요약: 판매 가능 수량 조회

#### Response '200' 'application/json' example 'kr'
- label: 국내주식 응답

```json
{
  "result": {
    "sellableQuantity": "100"
  }
}
```

#### Response '200' 'application/json' example 'us'
- label: 해외주식 응답

```json
{
  "result": {
    "sellableQuantity": "5.5"
  }
}
```

#### Response '400' 'application/json' example 'accountNotFound'
- label: 조회 가능한 계좌가 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-not-found",
    "message": "계좌를 찾을 수 없습니다."
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '404' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "stock-not-found",
    "message": "종목을 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

### GET /api/v1/commissions

- operationId: `getCommissions`
- 요약: 매매 수수료 조회

#### Response '200' 'application/json' example 'standard'
- label: 국내 + 해외 수수료

```json
{
  "result": [
    {
      "marketCountry": "KR",
      "commissionRate": "0.015",
      "startDate": "2026-01-01",
      "endDate": "2026-12-31"
    },
    {
      "marketCountry": "US",
      "commissionRate": "0.1",
      "startDate": null,
      "endDate": "2026-06-30"
    }
  ]
}
```

#### Response '200' 'application/json' example 'unlimited'
- label: 무기한 수수료

```json
{
  "result": [
    {
      "marketCountry": "KR",
      "commissionRate": "0.015",
      "startDate": "2026-01-01",
      "endDate": null
    },
    {
      "marketCountry": "US",
      "commissionRate": "0.25",
      "startDate": null,
      "endDate": null
    }
  ]
}
```

#### Response '400' 'application/json' example 'accountNotFound'
- label: 조회 가능한 계좌가 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-not-found",
    "message": "계좌를 찾을 수 없습니다."
  }
}
```

#### Response '400' 'application/json' example 'accountHeaderRequired'
- label: X-Tossinvest-Account 헤더 누락

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "account-header-required",
    "message": "x-tossinvest-account 헤더가 필요합니다."
  }
}
```

#### Response '401' 'application/json' example 'invalidToken'
- label: 유효하지 않은 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "invalid-token",
    "message": "유효하지 않은 토큰입니다."
  }
}
```

#### Response '401' 'application/json' example 'expiredToken'
- label: 만료된 토큰

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "expired-token",
    "message": "토큰이 만료되었습니다."
  }
}
```

#### Response '401' 'application/json' example 'loginUserNotFound'
- label: 로그인 정보 없음

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "login-user-not-found",
    "message": "로그인 정보를 찾을 수 없습니다."
  }
}
```

#### Response '429' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "rate-limit-exceeded",
    "message": "요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
  }
}
```

#### Response '500' 'application/json' example 'example'

```json
{
  "error": {
    "requestId": "01HXYZABCDEFG123456789",
    "code": "internal-error",
    "message": "처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요."
  }
}
```

## Component Schema Examples

### Account

#### `#/components/schemas/Account/properties/accountNo/example`

```json
"12345678901"
```

#### `#/components/schemas/Account/properties/accountSeq/example`

```json
1
```

#### `#/components/schemas/Account/properties/accountType/example`

```json
"BROKERAGE"
```

### AfterMarketSession

#### `#/components/schemas/AfterMarketSession/properties/startTime/example`

```json
"2026-03-25T15:30:00+09:00"
```

#### `#/components/schemas/AfterMarketSession/properties/singlePriceAuctionEndTime/example`

```json
"2026-03-25T15:40:00+09:00"
```

#### `#/components/schemas/AfterMarketSession/properties/endTime/example`

```json
"2026-03-25T20:00:00+09:00"
```

### ApiError

#### `#/components/schemas/ApiError/properties/requestId/example`

```json
"01HXYZABCDEFG123456789"
```

#### `#/components/schemas/ApiError/properties/code/example`

```json
"order-not-found"
```

#### `#/components/schemas/ApiError/properties/message/example`

```json
"주문 방향이 올바르지 않습니다."
```

### BuyingPowerResponse

#### `#/components/schemas/BuyingPowerResponse/properties/cashBuyingPower/example`

```json
"5000000"
```

### Candle

#### `#/components/schemas/Candle/properties/timestamp/example`

```json
"2026-03-25T09:00:00+09:00"
```

#### `#/components/schemas/Candle/properties/openPrice/example`

```json
"71600"
```

#### `#/components/schemas/Candle/properties/highPrice/example`

```json
"72300"
```

#### `#/components/schemas/Candle/properties/lowPrice/example`

```json
"71500"
```

#### `#/components/schemas/Candle/properties/closePrice/example`

```json
"72000"
```

#### `#/components/schemas/Candle/properties/volume/example`

```json
"3521000"
```

### Commission

#### `#/components/schemas/Commission/properties/commissionRate/example`

```json
"0.015"
```

#### `#/components/schemas/Commission/properties/startDate/example`

```json
"2026-01-01"
```

#### `#/components/schemas/Commission/properties/endDate/example`

```json
"2026-12-31"
```

### Cost

#### `#/components/schemas/Cost/properties/commission/example`

```json
"14400"
```

#### `#/components/schemas/Cost/properties/tax/example`

```json
"135600"
```

### DailyProfitLoss

#### `#/components/schemas/DailyProfitLoss/properties/amount/example`

```json
"100000"
```

#### `#/components/schemas/DailyProfitLoss/properties/rate/example`

```json
"0.0141"
```

### ExchangeRateResponse

#### `#/components/schemas/ExchangeRateResponse/properties/rate/example`

```json
"1380.5"
```

#### `#/components/schemas/ExchangeRateResponse/properties/midRate/example`

```json
"1375"
```

#### `#/components/schemas/ExchangeRateResponse/properties/basisPoint/example`

```json
"40"
```

#### `#/components/schemas/ExchangeRateResponse/properties/rateChangeType/example`

```json
"UP"
```

#### `#/components/schemas/ExchangeRateResponse/properties/validFrom/example`

```json
"2026-03-25T09:30:00+09:00"
```

#### `#/components/schemas/ExchangeRateResponse/properties/validUntil/example`

```json
"2026-03-25T09:31:00+09:00"
```

### HoldingsItem

#### `#/components/schemas/HoldingsItem/properties/symbol/example`

```json
"005930"
```

#### `#/components/schemas/HoldingsItem/properties/name/example`

```json
"삼성전자"
```

#### `#/components/schemas/HoldingsItem/properties/quantity/example`

```json
"100"
```

#### `#/components/schemas/HoldingsItem/properties/lastPrice/example`

```json
"72000"
```

#### `#/components/schemas/HoldingsItem/properties/averagePurchasePrice/example`

```json
"65000"
```

### KrMarketDay

#### `#/components/schemas/KrMarketDay/properties/date/example`

```json
"2026-03-25"
```

### KrMarketDetail

#### `#/components/schemas/KrMarketDetail/properties/liquidationTrading/example`

```json
false
```

#### `#/components/schemas/KrMarketDetail/properties/nxtSupported/example`

```json
true
```

#### `#/components/schemas/KrMarketDetail/properties/krxTradingSuspended/example`

```json
false
```

#### `#/components/schemas/KrMarketDetail/properties/nxtTradingSuspended/example`

```json
false
```

### MarketValue

#### `#/components/schemas/MarketValue/properties/purchaseAmount/example`

```json
"6500000"
```

#### `#/components/schemas/MarketValue/properties/amount/example`

```json
"7200000"
```

#### `#/components/schemas/MarketValue/properties/amountAfterCost/example`

```json
"7050000"
```

### OAuth2ErrorResponse

#### `#/components/schemas/OAuth2ErrorResponse/properties/error_description/example`

```json
"Client authentication failed."
```

### OAuth2TokenRequest

#### `#/components/schemas/OAuth2TokenRequest/properties/client_id/example`

```json
"c_01HXYZABCDEFG123456789"
```

### OAuth2TokenResponse

#### `#/components/schemas/OAuth2TokenResponse/properties/access_token/example`

```json
"eyJraWQiOiIyMDI2LTA0LTAxLWtleSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiJjXzAxSFhZWiJ9..."
```

#### `#/components/schemas/OAuth2TokenResponse/properties/token_type/example`

```json
"Bearer"
```

#### `#/components/schemas/OAuth2TokenResponse/properties/expires_in/example`

```json
86400
```

### Order

#### `#/components/schemas/Order/properties/orderId/example`

```json
"bAGzNvMOOTa5Uy0xVzYNbxDJ3Qpobwau4jDF3hyZZGWbpHm7wha8CFZc7aXVOWAl"
```

#### `#/components/schemas/Order/properties/symbol/example`

```json
"005930"
```

#### `#/components/schemas/Order/properties/side/example`

```json
"BUY"
```

#### `#/components/schemas/Order/properties/orderType/example`

```json
"LIMIT"
```

#### `#/components/schemas/Order/properties/timeInForce/example`

```json
"DAY"
```

#### `#/components/schemas/Order/properties/price/example`

```json
"70000"
```

#### `#/components/schemas/Order/properties/quantity/example`

```json
"10"
```

#### `#/components/schemas/Order/properties/orderAmount/example`

```json
null
```

#### `#/components/schemas/Order/properties/orderedAt/example`

```json
"2026-03-29T09:30:00+09:00"
```

#### `#/components/schemas/Order/properties/canceledAt/example`

```json
null
```

### OrderCreateRequest

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/clientOrderId/example`

```json
"my-order-001"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/symbol/example`

```json
"005930"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/side/example`

```json
"BUY"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/orderType/example`

```json
"LIMIT"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/timeInForce/example`

```json
"DAY"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/quantity/example`

```json
"10"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/price/example`

```json
"70000"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/0/properties/confirmHighValueOrder/example`

```json
false
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/clientOrderId/example`

```json
"my-order-001"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/symbol/example`

```json
"AAPL"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/side/example`

```json
"BUY"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/orderType/example`

```json
"MARKET"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/orderAmount/example`

```json
"100.5"
```

#### `#/components/schemas/OrderCreateRequest/oneOf/1/properties/confirmHighValueOrder/example`

```json
false
```

### OrderExecution

#### `#/components/schemas/OrderExecution/properties/filledQuantity/example`

```json
"10"
```

#### `#/components/schemas/OrderExecution/properties/averageFilledPrice/example`

```json
"70000"
```

#### `#/components/schemas/OrderExecution/properties/filledAmount/example`

```json
"700000"
```

#### `#/components/schemas/OrderExecution/properties/commission/example`

```json
"1400"
```

#### `#/components/schemas/OrderExecution/properties/tax/example`

```json
"0"
```

#### `#/components/schemas/OrderExecution/properties/filledAt/example`

```json
"2026-03-28T09:31:15+09:00"
```

#### `#/components/schemas/OrderExecution/properties/settlementDate/example`

```json
"2026-03-30"
```

### OrderModifyRequest

#### `#/components/schemas/OrderModifyRequest/properties/orderType/example`

```json
"LIMIT"
```

#### `#/components/schemas/OrderModifyRequest/properties/quantity/example`

```json
"15"
```

#### `#/components/schemas/OrderModifyRequest/properties/price/example`

```json
"71000"
```

#### `#/components/schemas/OrderModifyRequest/properties/confirmHighValueOrder/example`

```json
false
```

### OrderOperationResponse

#### `#/components/schemas/OrderOperationResponse/properties/orderId/example`

```json
"5nfzdqmzfnAw3LFXWHPRy0UNi7y_WZlphJh5hRIsi25-NIfm_GtQgXima5QD2hUz"
```

### OrderResponse

#### `#/components/schemas/OrderResponse/properties/orderId/example`

```json
"0d5QIHjmtksbsmM-hBRAgP-ExI8iodGm9fAR5txelPfnMM8XQ_swoJdwL5RpGWMo"
```

#### `#/components/schemas/OrderResponse/properties/clientOrderId/example`

```json
"my-order-001"
```

### OrderStatus

#### `#/components/schemas/OrderStatus/example`

```json
"FILLED"
```

### OrderbookEntry

#### `#/components/schemas/OrderbookEntry/properties/price/example`

```json
"72100"
```

#### `#/components/schemas/OrderbookEntry/properties/volume/example`

```json
"8500"
```

### OrderbookResponse

#### `#/components/schemas/OrderbookResponse/properties/timestamp/example`

```json
"2026-03-25T09:30:00.123+09:00"
```

### OverviewDailyProfitLoss

#### `#/components/schemas/OverviewDailyProfitLoss/properties/rate/example`

```json
"0.0185"
```

### OverviewProfitLoss

#### `#/components/schemas/OverviewProfitLoss/properties/rate/example`

```json
"0.1516"
```

#### `#/components/schemas/OverviewProfitLoss/properties/rateAfterCost/example`

```json
"0.1406"
```

### PaginatedOrderResponse

#### `#/components/schemas/PaginatedOrderResponse/properties/nextCursor/example`

```json
null
```

#### `#/components/schemas/PaginatedOrderResponse/properties/hasNext/example`

```json
false
```

### PreMarketSession

#### `#/components/schemas/PreMarketSession/properties/startTime/example`

```json
"2026-03-25T08:00:00+09:00"
```

#### `#/components/schemas/PreMarketSession/properties/singlePriceAuctionStartTime/example`

```json
"2026-03-25T08:50:00+09:00"
```

#### `#/components/schemas/PreMarketSession/properties/endTime/example`

```json
"2026-03-25T09:00:00+09:00"
```

### PriceLimitResponse

#### `#/components/schemas/PriceLimitResponse/properties/timestamp/example`

```json
"2026-03-25T09:30:00.123+09:00"
```

#### `#/components/schemas/PriceLimitResponse/properties/upperLimitPrice/example`

```json
"93000"
```

#### `#/components/schemas/PriceLimitResponse/properties/lowerLimitPrice/example`

```json
"50400"
```

### PriceResponse

#### `#/components/schemas/PriceResponse/properties/symbol/example`

```json
"005930"
```

#### `#/components/schemas/PriceResponse/properties/timestamp/example`

```json
"2026-03-25T09:30:00.123+09:00"
```

#### `#/components/schemas/PriceResponse/properties/lastPrice/example`

```json
"72000"
```

### ProfitLoss

#### `#/components/schemas/ProfitLoss/properties/amount/example`

```json
"700000"
```

#### `#/components/schemas/ProfitLoss/properties/amountAfterCost/example`

```json
"550000"
```

#### `#/components/schemas/ProfitLoss/properties/rate/example`

```json
"0.1077"
```

#### `#/components/schemas/ProfitLoss/properties/rateAfterCost/example`

```json
"0.0846"
```

### RegularMarketSession

#### `#/components/schemas/RegularMarketSession/properties/startTime/example`

```json
"2026-03-25T09:00:00+09:00"
```

#### `#/components/schemas/RegularMarketSession/properties/singlePriceAuctionStartTime/example`

```json
"2026-03-25T15:20:00+09:00"
```

#### `#/components/schemas/RegularMarketSession/properties/endTime/example`

```json
"2026-03-25T15:30:00+09:00"
```

### SellableQuantityResponse

#### `#/components/schemas/SellableQuantityResponse/properties/sellableQuantity/example`

```json
"100"
```

### StockInfo

#### `#/components/schemas/StockInfo/properties/symbol/example`

```json
"005930"
```

#### `#/components/schemas/StockInfo/properties/name/example`

```json
"삼성전자"
```

#### `#/components/schemas/StockInfo/properties/englishName/example`

```json
"SamsungElec"
```

#### `#/components/schemas/StockInfo/properties/isinCode/example`

```json
"KR7005930003"
```

#### `#/components/schemas/StockInfo/properties/market/example`

```json
"KOSPI"
```

#### `#/components/schemas/StockInfo/properties/securityType/example`

```json
"STOCK"
```

#### `#/components/schemas/StockInfo/properties/isCommonShare/example`

```json
true
```

#### `#/components/schemas/StockInfo/properties/status/example`

```json
"ACTIVE"
```

#### `#/components/schemas/StockInfo/properties/listDate/example`

```json
"1975-06-11"
```

#### `#/components/schemas/StockInfo/properties/delistDate/example`

```json
null
```

#### `#/components/schemas/StockInfo/properties/sharesOutstanding/example`

```json
"5919637922"
```

#### `#/components/schemas/StockInfo/properties/leverageFactor/example`

```json
null
```

### StockWarning

#### `#/components/schemas/StockWarning/properties/warningType/example`

```json
"VI_STATIC"
```

#### `#/components/schemas/StockWarning/properties/exchange/example`

```json
"KRX"
```

#### `#/components/schemas/StockWarning/properties/startDate/example`

```json
"2026-03-26"
```

#### `#/components/schemas/StockWarning/properties/endDate/example`

```json
"2026-03-27"
```

### Trade

#### `#/components/schemas/Trade/properties/price/example`

```json
"72000"
```

#### `#/components/schemas/Trade/properties/volume/example`

```json
"120"
```

#### `#/components/schemas/Trade/properties/timestamp/example`

```json
"2026-03-25T09:30:42.000+09:00"
```

### UsAfterMarketSession

#### `#/components/schemas/UsAfterMarketSession/properties/startTime/example`

```json
"2026-03-26T05:00:00+09:00"
```

#### `#/components/schemas/UsAfterMarketSession/properties/endTime/example`

```json
"2026-03-26T07:00:00+09:00"
```

### UsDayMarketSession

#### `#/components/schemas/UsDayMarketSession/properties/startTime/example`

```json
"2026-03-25T09:00:00+09:00"
```

#### `#/components/schemas/UsDayMarketSession/properties/endTime/example`

```json
"2026-03-25T16:50:00+09:00"
```

### UsMarketDay

#### `#/components/schemas/UsMarketDay/properties/date/example`

```json
"2026-03-25"
```

### UsPreMarketSession

#### `#/components/schemas/UsPreMarketSession/properties/startTime/example`

```json
"2026-03-25T17:00:00+09:00"
```

#### `#/components/schemas/UsPreMarketSession/properties/endTime/example`

```json
"2026-03-25T22:30:00+09:00"
```

### UsRegularMarketSession

#### `#/components/schemas/UsRegularMarketSession/properties/startTime/example`

```json
"2026-03-25T22:30:00+09:00"
```

#### `#/components/schemas/UsRegularMarketSession/properties/endTime/example`

```json
"2026-03-26T05:00:00+09:00"
```
