# 行情WebSocket客户端接入要求

## 连接地址
```
ws://{host}:{port}/ws/quote/{client_id}
```

- `{host}`: 服务器地址
- `{port}`: 服务器端口（默认8000）
- `{client_id}`: 客户端唯一标识

## 消息类型限制

客户端发送的消息类型**只能是以下三种之一**：

### 1. 心跳消息 (ping)
```json
{
  "type": "ping"
}
```
**作用**：保持WebSocket连接活跃
**响应**：服务器会返回"pong"消息

### 2. 订阅行情消息 (subscribe)
```json
{
  "type": "subscribe",
  "data": {
    "stock_code": "600000.SH",      // 必填：股票代码
    "period": "1d",                 // 可选：周期，默认"1d"
    "start_time": "20240101",       // 可选：起始时间
    "end_time": "20240131",         // 可选：结束时间
    "count": 100                    // 可选：数据个数，默认0
  }
}
```

**必填字段**：
- `stock_code`: 股票代码，格式如 '600000.SH'

**可选字段**：
- `period`: 周期，默认'1d'，可选值：
  - 'tick': 分笔成交
  - '1m': 1分钟
  - '5m': 5分钟
  - '15m': 15分钟
  - '30m': 30分钟
  - '1h': 60分钟
  - '1d': 日线
  - '1w': 周线
  - '1M': 月线
- `start_time`: 起始时间，格式 'YYYYMMDD' 或 'YYYYMMDDHHMMSS'
- `end_time`: 结束时间，格式 'YYYYMMDD' 或 'YYYYMMDDHHMMSS'
- `count`: 数据个数，0表示不请求历史数据

### 3. 取消订阅消息 (unsubscribe)
```json
{
  "type": "unsubscribe",
  "data": {
    "subscription_id": 12345  // 必填：订阅ID
  }
}
```

**必填字段**：
- `subscription_id`: 订阅ID（从订阅成功响应中获取）

## 错误处理

### 错误消息格式
```json
{
  "type": "error",
  "channel": "quote",
  "data": {
    "error": "错误代码",
    "message": "错误描述"
  },
  "timestamp": "2024-01-01T12:00:00",
  "client_id": "your_client_id"
}
```

### 常见错误代码

| 错误代码 | 描述 | 可能原因 |
|---------|------|---------|
| `UNSUPPORTED_MESSAGE_TYPE` | 不支持的消息类型 | 发送了不是"ping"、"subscribe"或"unsubscribe"的消息 |
| `INVALID_SUBSCRIPTION` | 无效的订阅请求 | 订阅请求缺少股票代码参数 |
| `SUBSCRIPTION_FAILED` | 订阅失败 | 调用xtquant订阅接口失败 |
| `INVALID_UNSUBSCRIPTION` | 无效的取消订阅请求 | 取消订阅请求缺少订阅ID参数 |
| `UNSUBSCRIPTION_FAILED` | 取消订阅失败 | 取消订阅过程失败 |

## 成功响应

### 订阅成功响应
```json
{
  "type": "subscription_confirmed",
  "channel": "quote",
  "data": {
    "subscription_id": 12345,
    "stock_code": "600000.SH",
    "period": "1d",
    "message": "行情订阅成功"
  },
  "timestamp": "2024-01-01T12:00:00",
  "client_id": "your_client_id"
}
```

### 取消订阅成功响应
```json
{
  "type": "unsubscription_confirmed",
  "channel": "quote",
  "data": {
    "subscription_id": 12345,
    "message": "取消订阅成功"
  },
  "timestamp": "2024-01-01T12:00:00",
  "client_id": "your_client_id"
}
```

### 心跳响应
```json
{
  "type": "pong",
  "channel": "quote",
  "data": {
    "timestamp": 1704096000.123
  },
  "timestamp": "2024-01-01T12:00:00",
  "client_id": "your_client_id"
}
```

## 行情数据推送

订阅成功后，服务器会推送行情数据：

```json
{
  "type": "quote_data",
  "channel": "quote",
  "data": {
    "stock_code": "600000.SH",
    "period": "1d",
    "data": {
      "time": 1704096000000,
      "open": 10.5,
      "high": 11.2,
      "low": 10.3,
      "close": 10.8,
      "volume": 1000000,
      "amount": 10000000
    },
    "timestamp": 1704096000.123
  },
  "timestamp": "2024-01-01T12:00:00",
  "client_id": "your_client_id"
}
```

## 连接管理

### 连接超时
- 服务器会在30秒内等待客户端消息
- 如果30秒内没有收到任何消息，服务器会发送心跳
- 客户端应定期发送"ping"消息保持连接

### 重连机制
- 客户端应实现自动重连逻辑
- 重连时使用相同的`client_id`
- 重连后需要重新订阅行情

## 示例代码

### Python客户端示例
```python
import asyncio
import websockets
import json

async def quote_client():
    client_id = "test_client_001"
    uri = f"ws://localhost:8000/ws/quote/{client_id}"

    async with websockets.connect(uri) as websocket:
        # 订阅行情
        subscribe_msg = {
            "type": "subscribe",
            "data": {
                "stock_code": "600000.SH",
                "period": "1d"
            }
        }
        await websocket.send(json.dumps(subscribe_msg))

        # 接收消息
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data.get("type") == "quote_data":
                print(f"收到行情数据: {data['data']['stock_code']}")
            elif data.get("type") == "error":
                print(f"错误: {data['data']['message']}")

# 运行客户端
asyncio.run(quote_client())
```

## 注意事项

1. **消息格式**：所有消息必须是有效的JSON格式
2. **字段类型**：确保字段类型正确（如stock_code是字符串，count是整数）
3. **必填字段**：订阅请求必须包含`stock_code`字段
4. **错误处理**：客户端应正确处理错误消息
5. **连接保持**：定期发送"ping"消息避免连接断开
6. **资源清理**：不再需要行情数据时发送"unsubscribe"消息