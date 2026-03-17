# miniqmt-trading

管理 MiniQMT 迅投的 AI 量化交易后端 API，包括查询 API 定义、账户信息、持仓、委托、成交等。

## 快速开始

**基础地址**: `http://129.211.50.62`

### 1. 查询 API 定义

获取完整的 OpenAPI 定义文档：

```bash
curl http://129.211.50.62/openapi.json
```

### 2. 获取账户信息

```bash
# 查询所有资金账号
curl http://129.211.50.62/api/v1/asset/accounts

# 查询单个账户资产
curl "http://129.211.50.62/api/v1/asset?account_id=99158392"
```

### 3. 查询持仓

```bash
# 查询所有持仓
curl "http://129.211.50.62/api/v1/position?account_id=99158392"

# 查询特定股票持仓
curl "http://129.211.50.62/api/v1/position/603019.SH?account_id=99158392"
```

### 4. 查询委托和成交

```bash
# 查询当日所有委托
curl "http://129.211.50.62/api/v1/order?account_id=99158392"

# 查询当日所有成交
curl "http://129.211.50.62/api/v1/trade?account_id=99158392"
```

## API 端点速查

| 功能 | 端点 | 方法 |
|------|------|------|
| API 定义 | `/openapi.json` | GET |
| 账户列表 | `/api/v1/asset/accounts` | GET |
| 账户资产 | `/api/v1/asset?account_id=xxx` | GET |
| 所有持仓 | `/api/v1/position?account_id=xxx` | GET |
| 单只持仓 | `/api/v1/position/{stock_code}?account_id=xxx` | GET |
| 当日委托 | `/api/v1/order?account_id=xxx` | GET |
| 当日成交 | `/api/v1/trade?account_id=xxx` | GET |
| 股票下单 | `/api/v1/order/stock` | POST |
| 股票撤单 | `/api/v1/order/cancel` | POST |

## 常用参数

- **account_id**: 资金账号，如 `99158392`
- **stock_code**: 证券代码，格式 `600000.SH`（上海）、`000001.SZ`（深圳）
- **order_type**: 委托类型 - `23` 买入，`24` 卖出
- **price_type**: 报价类型 - `5` 市价，`11` 限价

### 5. WebSocket 订单推送

**WebSocket 地址**:
- 订单推送: `ws://129.211.50.62/ws/order/{account_id}`
- 行情推送: `ws://129.211.50.62/ws/quote/{client_id}`

**JavaScript 连接示例**:
```javascript
// 订单WebSocket
const orderWs = new WebSocket('ws://129.211.50.62/ws/order/99158392');
orderWs.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('订单推送:', data);
};

// 行情WebSocket
const quoteWs = new WebSocket('ws://129.211.50.62/ws/quote/test_client_001');
quoteWs.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('行情推送:', data);
};
```

**推送消息类型**:

| type | 频道 | 说明 |
|------|------|------|
| `order_result` | order | 订单成交回报 |
| `cancel_result` | order | 撤单结果 |
| `quote_data` | quote | 实时行情 |
| `subscription_confirmed` | quote | 订阅确认 |
| `unsubscription_confirmed` | quote | 取消订阅确认 |
| `connection_established` | all | 连接建立 |
| `heartbeat` | all | 心跳 |

**消息格式**:
```json
{
  "type": "order_result",
  "channel": "order",
  "data": {
    "success": true,
    "order_id": 123456,
    "message": "委托成功"
  },
  "timestamp": "2026-03-15T10:00:00Z"
}
```

### 6. 行情订阅

连接行情WebSocket后，发送订阅消息：

**订阅请求**:
```javascript
quoteWs.send(JSON.stringify({
    "type": "subscribe",
    "data": {
        "stock_code": "600000.SH",
        "period": "1d"  // 1d, 1m, 5m, 15m, 30m, 60m
    }
}));
```

**取消订阅**:
```javascript
quoteWs.send(JSON.stringify({
    "type": "unsubscribe",
    "data": {
        "subscription_id": 1000
    }
}));
```

**支持的周期**: `1m`, `5m`, `15m`, `30m`, `60m`, `1d`

**行情返回字段**: open, high, low, close, volume, amount, preClose, change, change_rate 等

## 使用场景

当用户提到以下内容时激活此 skill：
- MiniQMT、迅投、量化交易
- A股交易、持仓查询、委托下单
- 129.211.50.62 这个地址
- 资金账号、账户资产
- WebSocket 订单推送
