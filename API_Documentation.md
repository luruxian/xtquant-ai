# XtQuant AI Backend - Complete API Reference

## 1. REST API Endpoints

### Asset Management (`/api/v1/asset`)

| Method | Path | Parameters | Description |
|--------|------|-----------|-------------|
| GET | `/api/v1/asset` | `account_id` (query) | Query single account asset |
| GET | `/api/v1/asset/batch` | `account_ids` (query, comma-separated) | Batch query multiple accounts |
| GET | `/api/v1/asset/accounts` | - | Get list of all account information |

**Response (AssetResponse)**:
```json
{
  "account_type": 0,
  "account_id": "1000000365",
  "cash": 100000.50,
  "frozen_cash": 5000.00,
  "market_value": 50000.00,
  "total_asset": 155000.50
}
```

---

### Position Management (`/api/v1/position`)

| Method | Path | Parameters | Description |
|--------|------|-----------|-------------|
| GET | `/api/v1/position` | `account_id` (query) | Query all open positions |
| GET | `/api/v1/position/{stock_code}` | `stock_code` (path), `account_id` (query) | Query position for specific stock |

**Response (PositionResponse)**:
```json
{
  "account_type": 0,
  "account_id": "1000000365",
  "stock_code": "600000.SH",
  "volume": 1000,
  "can_use_volume": 900,
  "open_price": 10.5,
  "market_value": 10500.00,
  "frozen_volume": 100,
  "on_road_volume": 0,
  "yesterday_volume": 1000,
  "avg_price": 10.45,
  "direction": 1
}
```

---

### Trade (Execution) Query (`/api/v1/trade`)

| Method | Path | Parameters | Description |
|--------|------|-----------|-------------|
| GET | `/api/v1/trade` | `account_id` (query) | Query all trades for today |

**Response (TradeResponse)**:
```json
{
  "account_type": 0,
  "account_id": "1000000365",
  "stock_code": "600000.SH",
  "order_type": 23,
  "traded_id": "12345",
  "traded_time": 150000,
  "traded_price": 10.50,
  "traded_volume": 100,
  "traded_amount": 1050.00,
  "order_id": 1,
  "order_sysid": "SYS001",
  "strategy_name": "test_strategy",
  "order_remark": "test",
  "direction": 1,
  "offset_flag": 0
}
```

---

### Order Management (`/api/v1/order`)

| Method | Path | Parameters | Description |
|--------|------|-----------|-------------|
| GET | `/api/v1/order` | `account_id` (query), `cancelable_only` (query, optional) | Query all orders |
| GET | `/api/v1/order/{order_id}` | `order_id` (path), `account_id` (query) | Query single order |
| POST | `/api/v1/order/stock` | Body: StockOrderRequest | **Synchronous** place stock order |
| POST | `/api/v1/order/cancel` | Body: StockCancelOrderRequest | **Synchronous** cancel order |

**POST /api/v1/order/stock (StockOrderRequest)**:
```json
{
  "account": "1000000365",
  "stock_code": "600000.SH",
  "order_type": 23,
  "order_volume": 100,
  "price_type": 11,
  "price": 10.50,
  "strategy_name": "test_strategy",
  "order_remark": "test order"
}
```

**Response (StockOrderResponse)**:
```json
{
  "order_id": 123,
  "message": "委托成功"
}
```

**POST /api/v1/order/cancel (StockCancelOrderRequest)**:
```json
{
  "account": "1000000365",
  "order_id": 123
}
```

**Response (StockCancelOrderResponse)**:
```json
{
  "result": 0,
  "message": "撤单成功"
}
```

---

### Quote Management (`/api/v1/quote`)

| Method | Path | Parameters | Description |
|--------|------|-----------|-------------|
| POST | `/api/v1/quote/subscribe` | Body: QuoteSubscribeRequest | Subscribe to stock quote |
| POST | `/api/v1/quote/unsubscribe` | Body: QuoteUnsubscribeRequest | Unsubscribe from quote |
| GET | `/api/v1/quote/supported-periods` | - | Get supported K-line periods |
| GET | `/api/v1/quote/subscriptions` | - | Get all active subscriptions |
| GET | `/api/v1/quote/test/{stock_code}` | `stock_code` (path) | Test quote endpoint |

**POST /api/v1/quote/subscribe (QuoteSubscribeRequest)**:
```json
{
  "stock_code": "600000.SH",
  "period": "1d",
  "start_time": "20260101",
  "end_time": "20260301",
  "count": 100
}
```

**Response (QuoteSubscribeResponse)**:
```json
{
  "subscription_id": 1,
  "message": "订阅成功",
  "stock_code": "600000.SH",
  "period": "1d"
}
```

**Supported Periods**: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1w`, `1M`

---

## 2. WebSocket Endpoints

### Order WebSocket (`/ws/order/{client_id}`)

- **Connection**: `ws://localhost:8000/ws/order/{client_id}`
- **Client ID**: Usually the account_id (e.g., `1000000365`)
- **Auto-subscribed**: Order events are automatically pushed to this channel
- **Supported Messages**:
  - `ping` → Server responds with `pong`
  - `subscribe` → Auto-subscribes to order channel

**Order Result Message** (pushed after order placement):
```json
{
  "type": "order_result",
  "timestamp": "2026-03-21T12:00:00.000000",
  "channel": "order",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    "stock_code": "600000.SH",
    "order_type": 23,
    "order_volume": 100,
    "price_type": 11,
    "price": 10.50,
    "success": true,
    "message": "委托成功"
  }
}
```

**Cancel Result Message** (pushed after order cancellation):
```json
{
  "type": "cancel_result",
  "timestamp": "2026-03-21T12:00:00.000000",
  "channel": "order",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    "result": 0,
    "success": true,
    "message": "撤单成功"
  }
}
```

---

### Quote WebSocket (`/ws/quote/{client_id}`)

- **Connection**: `ws://localhost:8000/ws/quote/{client_id}`
- **Client ID**: Usually the account_id (e.g., `1000000365`)

**Supported Client Messages**:

1. **Ping** (keep-alive):
```json
{
  "type": "ping"
}
```

2. **Subscribe to Quote**:
```json
{
  "type": "subscribe",
  "data": {
    "stock_code": "600000.SH",
    "period": "1d",
    "start_time": "20260101",
    "end_time": "20260301",
    "count": 100
  }
}
```

3. **Unsubscribe from Quote**:
```json
{
  "type": "unsubscribe",
  "data": {
    "subscription_id": 1
  }
}
```

**Server Responses**:

- **Subscription Confirmed**:
```json
{
  "type": "subscription_confirmed",
  "timestamp": "2026-03-21T12:00:00.000000",
  "channel": "quote",
  "data": {
    "subscription_id": 1,
    "stock_code": "600000.SH",
    "period": "1d",
    "message": "行情订阅成功"
  }
}
```

- **Quote Data** (pushed on new data):
```json
{
  "type": "quote_data",
  "timestamp": "2026-03-21T12:00:00.000000",
  "channel": "quote",
  "data": {
    "subscription_id": 1,
    "stock_code": "600000.SH",
    "period": "1d",
    "time": 1676793600,
    "open": 10.40,
    "high": 10.60,
    "low": 10.30,
    "close": 10.50,
    "volume": 5000000,
    "amount": 52500000,
    "pre_close": 10.35,
    "change": 0.15,
    "change_rate": 1.45,
    "turnover_rate": 2.3
  }
}
```

- **Heartbeat**:
```json
{
  "type": "heartbeat",
  "timestamp": "2026-03-21T12:00:00.000000",
  "channel": "quote"
}
```

---

## 3. Data Structures & Schemas

### Request Models

| Model | Fields |
|-------|--------|
| **StockOrderRequest** | `account`, `stock_code`, `order_type`, `order_volume`, `price_type`, `price`, `strategy_name`, `order_remark` |
| **StockCancelOrderRequest** | `account`, `order_id` |
| **QuoteSubscribeRequest** | `stock_code`, `period`, `start_time`, `end_time`, `count` |
| **QuoteUnsubscribeRequest** | `subscription_id` |

### Response Models

| Model | Key Fields |
|-------|-----------|
| **AssetResponse** | `account_id`, `account_type`, `cash`, `frozen_cash`, `market_value`, `total_asset` |
| **PositionResponse** | `account_id`, `stock_code`, `volume`, `can_use_volume`, `open_price`, `market_value`, `avg_price` |
| **TradeResponse** | `account_id`, `stock_code`, `traded_price`, `traded_volume`, `traded_amount`, `order_id`, `traded_time` |
| **OrderResponse** | `account_id`, `stock_code`, `order_id`, `order_volume`, `price`, `order_status`, `traded_volume` |
| **StockOrderResponse** | `order_id`, `message` |
| **StockCancelOrderResponse** | `result`, `message` |

---

## 4. Authentication & Configuration

**Environment Variables** (`backend/utils/config.py`):

| Variable | Purpose | Default |
|----------|---------|---------|
| `QMT_PATH` | QMT client path | `C:\Users\...\迅投极速策略交易系统...` |
| `SESSION_ID` | Trading session ID | Generated from current timestamp |

**Example .env**:
```
QMT_PATH=D:\迅投极速交易终端\userdata_mini
SESSION_ID=123456
```

---

## 5. Key Service Architecture

**Global Trader Singleton** (`services/trader_singleton.py`):
- Thread-safe lazy initialization
- Persistent subscription management
- Automatic account subscription handling

**WebSocket Manager** (`services/websocket_manager.py`):
- Dual-channel support (order + quote)
- Per-client message routing
- Standardized message format with timestamps

**QMT Service** (`services/qmt_service.py`):
- Unified query interface
- Automatic account subscription
- Batch query optimization

---

## 6. Error Responses

All endpoints return error responses in format:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Error description"
  }
}
```

**Common Error Codes**:
- `PATH_NOT_FOUND` - QMT client path invalid
- `TRADER_NOT_AVAILABLE` - Trading instance unavailable
- `SUBSCRIBE_FAILED` - Account subscription failed
- `ORDER_FAILED` - Order placement failed
- `INTERNAL_ERROR` - Server error

---

## 7. Documentation References

- [API Summary](backend/api_summary.md)
- [WebSocket Documentation](backend/WEBSOCKET_README.md)  
- [WebSocket Migration Guide](backend/WEBSOCKET_MIGRATION.md)
- [Requirements](backend/requirements.txt)

**Key Dependencies**:
- FastAPI 0.115.0
- Uvicorn 0.33.0
- Pydantic 2.10.0
- XtQuant 250516.1.1

This comprehensive API reference covers all endpoints, message formats, authentication, and data structures used in the XtQuant AI backend system.