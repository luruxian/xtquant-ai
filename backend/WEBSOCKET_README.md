# WebSocket订单推送功能

## 概述

本功能为同步报单接口添加了WebSocket推送能力。当客户端提交订单或撤单请求时，除了返回HTTP响应外，还会通过WebSocket实时推送订单结果给客户端。

## 功能特性

1. **实时推送**：订单结果实时推送给客户端，无需轮询
2. **按账户推送**：每个账户只能收到自己的订单消息
3. **双向通信**：支持客户端与服务器之间的双向通信
4. **错误处理**：推送失败时不会影响主流程
5. **兼容性**：不影响现有的HTTP API接口

## 文件结构

```
backend/
├── services/
│   └── websocket_manager.py    # WebSocket连接管理器
├── schemas/
│   └── websocket.py           # WebSocket消息模型
├── routes/
│   ├── websocket.py           # WebSocket路由
│   └── order.py               # 修改后的订单路由（添加推送功能）
├── main.py                    # 主应用（添加WebSocket路由）
└── websocket_test.html        # WebSocket测试页面
```

## 使用方法

### 1. 启动后端服务

```bash
cd backend
python run.py
```

### 2. 客户端连接WebSocket

#### JavaScript示例

```javascript
const clientId = "your_account_id"; // 使用账户ID作为客户端ID
const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);

    if (message.type === 'order_result') {
        const data = message.data;
        if (data.success) {
            console.log(`订单成功: 订单号 ${data.order_id}, ${data.message}`);
        } else {
            console.log(`订单失败: ${data.message}`);
        }
    } else if (message.type === 'cancel_result') {
        const data = message.data;
        if (data.success) {
            console.log(`撤单成功: 订单号 ${data.order_id}, ${data.message}`);
        } else {
            console.log(`撤单失败: ${data.message}`);
        }
    }
};

ws.onopen = () => {
    console.log('WebSocket连接已建立');
};

ws.onclose = () => {
    console.log('WebSocket连接已关闭');
};
```

#### Python示例

```python
import asyncio
import websockets
import json

async def websocket_client():
    client_id = "your_account_id"
    uri = f"ws://localhost:8000/ws/{client_id}"

    async with websockets.connect(uri) as websocket:
        print("WebSocket连接成功!")

        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"收到消息: {data}")

asyncio.run(websocket_client())
```

### 3. 提交订单

提交订单的方式不变，使用现有的HTTP API接口：

```bash
# 同步报单
curl -X POST "http://localhost:8000/api/v1/order/stock" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "1000000365",
    "stock_code": "600000.SH",
    "order_type": 23,
    "order_volume": 100,
    "price_type": 0,
    "price": 10.5,
    "strategy_name": "test",
    "order_remark": "websocket_test"
  }'

# 同步撤单
curl -X POST "http://localhost:8000/api/v1/order/cancel" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "1000000365",
    "order_id": 123
  }'
```

## 消息格式

### 订单结果消息

```json
{
  "type": "order_result",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    "stock_code": "600000.SH",
    "order_type": 23,
    "order_volume": 100,
    "price_type": 0,
    "price": 10.5,
    "success": true,
    "message": "委托成功",
    "timestamp": "2024-01-01T12:00:00.000000"
  }
}
```

### 撤单结果消息

```json
{
  "type": "cancel_result",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    "result": 0,
    "success": true,
    "message": "撤单成功",
    "timestamp": "2024-01-01T12:00:00.000000"
  }
}
```

## 测试方法

### 方法1：使用测试页面

1. 在浏览器中打开 `websocket_test.html`
2. 输入客户端ID（账户ID）
3. 点击"连接WebSocket"
4. 点击"模拟下单"或"模拟撤单"
5. 查看消息日志中的推送结果

### 方法2：使用Python测试脚本

```bash
cd backend
python test_websocket.py
```

## 注意事项

1. **客户端ID**：建议使用账户ID作为客户端ID，确保每个账户只能收到自己的消息
2. **连接管理**：客户端断开连接后需要重新连接
3. **错误处理**：WebSocket推送失败时会记录日志，但不会影响HTTP响应
4. **安全性**：在生产环境中应考虑添加身份验证和加密
5. **性能**：大量并发连接时需要考虑服务器性能

## 扩展功能

可以根据需要扩展以下功能：

1. **心跳检测**：定期发送心跳包保持连接
2. **重连机制**：连接断开时自动重连
3. **消息确认**：客户端收到消息后发送确认
4. **历史消息**：连接时推送未读的历史消息
5. **多类型推送**：添加成交、持仓等更多类型的推送