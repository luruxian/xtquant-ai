# WebSocket 数据推送处理流程梳理

## 1. 系统架构概述

本项目使用 FastAPI 框架实现 WebSocket 实时数据推送功能，支持两种类型的推送通道：
- **订单通道 (order)**：用于推送订单下单和撤单结果
- **行情通道 (quote)**：用于推送实时行情数据

### 1.1 核心组件

| 组件 | 文件路径 | 职责 |
|------|---------|------|
| WebSocket 连接管理器 | `backend/services/websocket_manager.py` | 统一管理所有 WebSocket 连接 |
| 订单 WebSocket 路由 | `backend/routes/websocket_order.py` | 处理订单通道连接和消息 |
| 行情 WebSocket 路由 | `backend/routes/websocket_quote.py` | 处理行情通道连接和消息 |
| 订单 API 路由 | `backend/routes/order.py` | 处理下单/撤单请求并触发推送 |
| 行情 API 路由 | `backend/routes/quote.py` | 处理行情订阅并推送行情数据 |

---

## 2. WebSocket 连接建立流程

### 2.1 客户端连接

#### 2.1.1 订单通道连接

```
客户端 → ws://localhost:8000/ws/order/{client_id}
```

**流程步骤：**

1. **客户端发起 WebSocket 连接**
   - URL: `ws://localhost:8000/ws/order/{client_id}`
   - `{client_id}` 通常使用账户 ID（如 `1000000365`）

2. **服务端接受连接**
   ```python
   # websocket_order.py
   @router.websocket("/ws/order/{client_id}")
   async def order_websocket_endpoint(websocket: WebSocket, client_id: str):
       await websocket_manager.connect(websocket, client_id, channel="order")
   ```

3. **WebSocketManager 处理连接**
   ```python
   # websocket_manager.py
   async def connect(self, websocket: WebSocket, client_id: str, channel: Optional[str] = None):
       await websocket.accept()  # 接受连接

       # 存储连接：active_connections[client_id] = {websocket1, websocket2, ...}
       if client_id not in self.active_connections:
           self.active_connections[client_id] = set()
       self.active_connections[client_id].add(websocket)

       # 记录频道
       if channel:
           if client_id not in self.connection_channels:
               self.connection_channels[client_id] = set()
           self.connection_channels[client_id].add(channel)

       # 发送连接确认消息
       await self._send_connection_confirmation(websocket, client_id, channel)
   ```

4. **发送连接确认**
   ```json
   {
     "type": "connection_established",
     "channel": "order",
     "data": {
       "client_id": "1000000365",
       "channel": "order",
       "message": "WebSocket连接已建立"
     },
     "timestamp": "2024-01-01T12:00:00.000000",
     "client_id": "1000000365"
   }
   ```

5. **进入消息循环**
   - 监听客户端消息（ping/subscribe 等）
   - 超时 30 秒自动发送心跳
   - 处理断开连接事件

#### 2.1.2 行情通道连接

```
客户端 → ws://localhost:8000/ws/quote/{client_id}
```

**流程步骤：**

1. **客户端发起连接**
   - URL: `ws://localhost:8000/ws/quote/{client_id}`

2. **服务端接受连接**
   ```python
   # websocket_quote.py
   @router.websocket("/ws/quote/{client_id}")
   async def quote_websocket_endpoint(websocket: WebSocket, client_id: str):
       await websocket_manager.connect(websocket, client_id, channel="quote")
   ```

3. **后续处理与订单通道类似**

### 2.2 连接管理数据结构

```python
# websocket_manager.py
class WebSocketManager:
    def __init__(self):
        # 活跃连接：{client_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # 频道订阅：{client_id: {"order", "quote", ...}}
        self.connection_channels: Dict[str, Set[str]] = {}

        # 异步锁
        self.lock = asyncio.Lock()
```

---

## 3. 消息推送流程

### 3.1 订单结果推送流程

#### 3.1.1 下单推送流程

```
HTTP 请求 → 订单 API → QMT 交易接口 → 推送订单结果到 WebSocket
```

**详细步骤：**

1. **客户端提交 HTTP 下单请求**
   ```bash
   POST /api/v1/order/stock
   {
     "account": "1000000365",
     "stock_code": "600000.SH",
     "order_type": 23,
     "order_volume": 100,
     "price_type": 0,
     "price": 10.5,
     "strategy_name": "test",
     "order_remark": "websocket_test"
   }
   ```

2. **订单 API 处理请求**
   ```python
   # order.py
   @router.post("/stock", response_model=StockOrderResponse)
   async def order_stock(request: StockOrderRequest):
       # 1. 获取 QMT 交易实例
       qmt_service = QMTService(qmt_path, session_id)
       trader = qmt_service.get_shared_trader()

       # 2. 调用 QMT 下单接口
       order_id = trader.order_stock(acc, request.stock_code, ...)

       # 3. 判断订单是否成功
       if order_id is None or order_id <= 0:
           # 3a. 下单失败：推送失败消息
           error_message = {
               "type": "order_result",
               "data": {
                   "order_id": -1,
                   "account": request.account,
                   "stock_code": request.stock_code,
                   "success": False,
                   "message": "委托失败"
               }
           }
           await websocket_manager.send_personal_message(error_message, request.account, channel="order")
           return StockOrderResponse(order_id=-1, message="委托失败")

       # 3b. 下单成功：推送成功消息
       success_message = {
           "type": "order_result",
           "data": {
               "order_id": order_id,
               "account": request.account,
               "stock_code": request.stock_code,
               "success": True,
               "message": "委托成功"
           }
       }
       await websocket_manager.send_personal_message(success_message, request.account, channel="order")
       return StockOrderResponse(order_id=order_id, message="委托成功")
   ```

3. **WebSocketManager 发送消息**
   ```python
   # websocket_manager.py
   async def send_personal_message(self, message: dict, client_id: str, channel: Optional[str] = None):
       # 1. 查找客户端的所有连接
       if client_id in self.active_connections:
           # 2. 转换为标准化消息格式（如果需要）
           if "timestamp" not in message or "channel" not in message:
               standard_message = self._create_standard_message(
                   message_type=message.get("type", "data"),
                   data=message.get("data", message),
                   channel=channel,
                   client_id=client_id
               )
           else:
               standard_message = message

           # 3. 序列化为 JSON
           message_json = json.dumps(standard_message, ensure_ascii=False)

           # 4. 发送到该客户端的所有 WebSocket 连接
           for connection in self.active_connections[client_id]:
               try:
                   await connection.send_text(message_json)
               except Exception as e:
                   # 移除失效的连接
                   self.active_connections[client_id].discard(connection)
   ```

4. **客户端接收订单结果消息**
   ```json
   {
     "type": "order_result",
     "channel": "order",
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
     },
     "timestamp": "2024-01-01T12:00:00.000000",
     "client_id": "1000000365"
   }
   ```

#### 3.1.2 撤单推送流程

撤单推送流程与下单类似：

```python
# order.py
@router.post("/cancel", response_model=StockCancelOrderResponse)
async def cancel_order_stock(request: StockCancelOrderRequest):
    # 1. 调用 QMT 撤单接口
    result = trader.cancel_order_stock(acc, request.order_id)

    # 2. 判断撤单结果
    if result == 0:  # 撤单成功
        cancel_success_message = {
            "type": "cancel_result",
            "data": {
                "order_id": request.order_id,
                "account": request.account,
                "result": 0,
                "success": True,
                "message": "撤单成功"
            }
        }
        await websocket_manager.send_personal_message(cancel_success_message, request.account, channel="order")
    else:  # 撤单失败
        cancel_fail_message = {
            "type": "cancel_result",
            "data": {
                "order_id": request.order_id,
                "account": request.account,
                "result": result,
                "success": False,
                "message": "撤单失败"
            }
        }
        await websocket_manager.send_personal_message(cancel_fail_message, request.account, channel="order")
```

---

### 3.2 行情数据推送流程

#### 3.2.1 订阅行情流程

```
客户端订阅 → 注册回调 → xtquant 推送数据 → 回调函数处理 → 广播到所有订阅客户端
```

**详细步骤：**

1. **客户端通过 WebSocket 发送订阅请求**
   ```json
   {
     "type": "subscribe",
     "data": {
       "stock_code": "600000.SH",
       "period": "1d",
       "start_time": "",
       "end_time": "",
       "count": 0
     }
   }
   ```

2. **服务端处理订阅请求**
   ```python
   # websocket_quote.py
   @router.websocket("/ws/quote/{client_id}")
   async def quote_websocket_endpoint(websocket: WebSocket, client_id: str):
       await websocket_manager.connect(websocket, client_id, channel="quote")

       while True:
           data = await websocket.receive_json()
           message_type = data.get("type")

           if message_type == "subscribe":
               await _handle_quote_subscription(client_id, data)
   ```

3. **调用行情订阅接口**
   ```python
   async def _handle_quote_subscription(client_id: str, data: Dict[str, Any]):
       # 1. 提取订阅参数
       subscription_data = data.get("data", {})
       stock_code = subscription_data.get("stock_code")  # 必填
       period = subscription_data.get("period", "1d")
       # ... 其他参数

       # 2. 创建订阅请求对象
       request = QuoteSubscribeRequest(
           stock_code=stock_code,
           period=period,
           # ...
       )

       # 3. 调用 quote.py 中的订阅逻辑
       response = await subscribe_quote(request)

       # 4. 记录客户端订阅了行情频道
       websocket_manager.subscribe_channel(client_id, "quote")

       # 5. 发送订阅确认
       await websocket_manager.send_personal_message({
           "type": "subscription_confirmed",
           "data": {
               "subscription_id": response.subscription_id,
               "stock_code": stock_code,
               "period": period,
               "message": "行情订阅成功"
           }
       }, client_id, channel="quote")
   ```

4. **注册行情回调函数**
   ```python
   # quote.py
   @router.post("/subscribe")
   async def subscribe_quote(request: QuoteSubscribeRequest):
       # 定义回调函数
       def quote_callback(datas):
           """xtquant 行情数据回调函数"""
           try:
               for stock_code in datas:
                   data_list = datas[stock_code]
                   if data_list:
                       for data in data_list:
                           # 数据验证和清洗
                           if not isinstance(data, dict):
                               continue
                           if 'time' not in data or data['time'] is None:
                               continue

                           # 数值范围检查
                           numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
                           for field in numeric_fields:
                               if field in data:
                                   if isinstance(value := data[field], (int, float)):
                                       if not (value >= 0 and value < 1e15):
                                           data[field] = 0.0

                           # 构造行情数据
                           quote_data = {
                               "stock_code": stock_code,
                               "period": request.period,
                               "data": data,
                               "timestamp": time.time()
                           }

                           # 广播到 quote 频道（异步调用）
                           async def broadcast_quote():
                               await websocket_manager.broadcast({
                                   "type": "quote_data",
                                   "data": quote_data
                               }, channel="quote")

                           # 在事件循环中运行异步函数
                           if subscription_manager.main_event_loop:
                               asyncio.run_coroutine_threadsafe(
                                   broadcast_quote(),
                                   subscription_manager.main_event_loop
                               )
           except Exception as e:
               logger.error(f"行情回调处理失败: {e}")

       # 调用 xtquant 订阅接口
       subscription_id = xtdata.subscribe_quote(
           stock_code=request.stock_code,
           period=request.period,
           # ...
           callback=quote_callback
       )

       # 保存订阅信息和回调引用
       subscription_data = {
           "stock_code": request.stock_code,
           "period": request.period,
           "subscription_id": subscription_id,
           "callback": quote_callback
       }
       api_subscription_id = subscription_manager.add_subscription(subscription_data)
       subscription_manager.callback_handlers[api_subscription_id] = quote_callback

       # 保存主事件循环引用
       if subscription_manager.main_event_loop is None:
           subscription_manager.main_event_loop = asyncio.get_event_loop()
   ```

5. **xtquant 推送行情数据**
   - QMT/xtquant 后台检测到行情更新
   - 调用注册的 `quote_callback` 回调函数
   - 回调函数接收行情数据字典

6. **回调函数处理并广播**
   ```python
   # 构造标准化消息
   quote_message = {
       "type": "quote_data",
       "channel": "quote",
       "data": {
           "stock_code": "600000.SH",
           "period": "1d",
           "data": {
               "time": "2024-01-01 15:00:00",
               "open": 10.5,
               "high": 10.8,
               "low": 10.3,
               "close": 10.7,
               "volume": 100000,
               "amount": 1070000.0
           },
           "timestamp": 1704067200.0
       },
       "timestamp": "2024-01-01T15:00:00.000000",
       "client_id": null
   }
   ```

7. **WebSocketManager 广播到所有订阅客户端**
   ```python
   # websocket_manager.py
   async def broadcast(self, message: dict, channel: Optional[str] = None):
       message_json = json.dumps(standard_message, ensure_ascii=False)

       for client_id, connections in list(self.active_connections.items()):
           # 频道过滤：只发送给订阅了该频道的客户端
           if channel and client_id in self.connection_channels:
               if channel not in self.connection_channels[client_id]:
                   continue

           for connection in list(connections):
               try:
                   await connection.send_text(message_json)
               except Exception as e:
                   connections.discard(connection)
   ```

8. **客户端接收行情数据**
   ```json
   {
     "type": "quote_data",
     "channel": "quote",
     "data": {
       "stock_code": "600000.SH",
       "period": "1d",
       "data": {
         "time": "2024-01-01 15:00:00",
         "open": 10.5,
         "high": 10.8,
         "low": 10.3,
         "close": 10.7,
         "volume": 100000,
         "amount": 1070000.0
       },
       "timestamp": 1704067200.0
     },
     "timestamp": "2024-01-01T15:00:00.000000",
     "client_id": null
   }
   ```

---

## 4. 消息格式标准化

### 4.1 标准消息结构

```typescript
interface StandardMessage {
  type: string;              // 消息类型
  channel: string | null;     // 频道名称（order/quote）
  data: any;                 // 消息数据
  timestamp: string;          // ISO 格式时间戳
  client_id: string | null;   // 客户端 ID（广播消息为 null）
}
```

### 4.2 消息类型汇总

| 类型 | 频道 | 用途 | 触发条件 |
|------|------|------|---------|
| `connection_established` | order/quote | 连接确认 | WebSocket 连接成功 |
| `heartbeat` | order/quote | 心跳保持 | 超时 30 秒无消息 |
| `pong` | order/quote | 心跳响应 | 客户端发送 ping |
| `subscription_confirmed` | quote | 订阅确认 | 行情订阅成功 |
| `unsubscription_confirmed` | quote | 取消订阅确认 | 取消订阅成功 |
| `order_result` | order | 订单结果 | 下单/撤单完成 |
| `cancel_result` | order | 撤单结果 | 撤单完成 |
| `quote_data` | quote | 行情数据 | xtquant 推送行情 |
| `error` | order/quote | 错误消息 | 操作失败或异常 |

### 4.3 消息示例

#### 订单结果
```json
{
  "type": "order_result",
  "channel": "order",
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
  },
  "timestamp": "2024-01-01T12:00:00.000000",
  "client_id": "1000000365"
}
```

#### 撤单结果
```json
{
  "type": "cancel_result",
  "channel": "order",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    "result": 0,
    "success": true,
    "message": "撤单成功",
    "timestamp": "2024-01-01T12:00:00.000000"
  },
  "timestamp": "2024-01-01T12:00:00.000000",
  "client_id": "1000000365"
}
```

#### 行情数据
```json
{
  "type": "quote_data",
  "channel": "quote",
  "data": {
    "stock_code": "600000.SH",
    "period": "1d",
    "data": {
      "time": "2024-01-01 15:00:00",
      "open": 10.5,
      "high": 10.8,
      "low": 10.3,
      "close": 10.7,
      "volume": 100000,
      "amount": 1070000.0
    },
    "timestamp": 1704067200.0
  },
  "timestamp": "2024-01-01T15:00:00.000000",
  "client_id": null
}
```

#### 错误消息
```json
{
  "type": "error",
  "channel": "quote",
  "data": {
    "error": "SUBSCRIPTION_FAILED",
    "message": "订阅失败: 股票代码无效"
  },
  "timestamp": "2024-01-01T12:00:00.000000",
  "client_id": "client_001"
}
```

---

## 5. 心跳和断线处理

### 5.1 心跳机制

#### 服务器端心跳
- **触发条件**: 客户端 30 秒内未发送任何消息
- **心跳消息**:
  ```json
  {
    "type": "heartbeat",
    "channel": "order",
    "data": {"timestamp": "2024-01-01T12:00:00.000000"},
    "timestamp": "2024-01-01T12:00:00.000000",
    "client_id": "1000000365"
  }
  ```

#### 客户端心跳
- **触发条件**: 客户端主动发送 ping 保持连接
- **ping 消息**:
  ```json
  {
    "type": "ping"
  }
  ```
- **pong 响应**:
  ```json
  {
    "type": "pong",
    "data": {"timestamp": 1704067200.123456}
  }
  ```

### 5.2 断线处理

```python
# 两种断开连接情况：
# 1. 正常断开（客户端主动关闭）
except WebSocketDisconnect:
    websocket_manager.disconnect(websocket, client_id)
    logger.info(f"WebSocket连接断开: client_id={client_id}")

# 2. 异常断开（网络错误等）
except Exception as e:
    websocket_manager.disconnect(websocket, client_id)
    logger.error(f"WebSocket连接错误: client_id={client_id}, error={e}")
```

**disconnect 方法清理逻辑：**
```python
def disconnect(self, websocket: WebSocket, client_id: str):
    # 1. 从连接池中移除该 WebSocket
    if client_id in self.active_connections:
        self.active_connections[client_id].discard(websocket)

        # 2. 如果该客户端没有其他连接，清理所有相关数据
        if not self.active_connections[client_id]:
            del self.active_connections[client_id]

            # 3. 清理频道订阅信息
            if client_id in self.connection_channels:
                del self.connection_channels[client_id]
```

---

## 6. 关键技术点

### 6.1 异步回调处理

行情数据来自 xtquant 的同步回调，需要在异步环境中广播：

```python
def quote_callback(datas):
    # ... 处理数据 ...

    # 定义异步广播函数
    async def broadcast_quote():
        await websocket_manager.broadcast({
            "type": "quote_data",
            "data": quote_data
        }, channel="quote")

    # 在主事件循环中执行异步函数
    if subscription_manager.main_event_loop:
        asyncio.run_coroutine_threadsafe(
            broadcast_quote(),
            subscription_manager.main_event_loop
        )
```

**关键点：**
- 保存主事件循环引用：`subscription_manager.main_event_loop = asyncio.get_event_loop()`
- 使用 `asyncio.run_coroutine_threadsafe()` 在同步回调中调度异步任务

### 6.2 消息标准化转换

```python
async def send_personal_message(self, message: dict, client_id: str, channel: Optional[str] = None):
    # 自动检测并转换为标准化格式
    if "timestamp" not in message or "channel" not in message:
        standard_message = self._create_standard_message(
            message_type=message.get("type", "data"),
            data=message.get("data", message),
            channel=channel,
            client_id=client_id
        )
    else:
        standard_message = message

    # 发送标准化消息
    await connection.send_text(json.dumps(standard_message, ensure_ascii=False))
```

### 6.3 频道过滤

广播消息时只发送给订阅了特定频道的客户端：

```python
async def broadcast(self, message: dict, channel: Optional[str] = None):
    for client_id, connections in list(self.active_connections.items()):
        # 检查频道过滤
        if channel and client_id in self.connection_channels:
            if channel not in self.connection_channels[client_id]:
                continue  # 跳过未订阅该频道的客户端

        # 发送消息
        for connection in list(connections):
            await connection.send_text(message_json)
```

### 6.4 数据验证和清洗

行情回调中的数据验证：

```python
# 1. 类型检查
if not isinstance(data, dict):
    logger.warning(f"跳过无效数据格式: {type(data)}")
    continue

# 2. 字段存在性检查
if 'time' not in data or data['time'] is None:
    logger.warning(f"跳过缺少time字段的数据")
    continue

# 3. 数值范围检查（避免 bson 序列化问题）
numeric_fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
for field in numeric_fields:
    if field in data:
        value = data[field]
        if isinstance(value, (int, float)):
            if not (value >= 0 and value < 1e15):  # 合理范围
                data[field] = 0.0  # 设置为默认值
```

---

## 7. 完整数据流图

```
┌─────────────┐
│   客户端    │
└──────┬──────┘
       │
       │ 1. WebSocket 连接
       │    ws://localhost:8000/ws/order/{account_id}
       │    ws://localhost:8000/ws/quote/{client_id}
       ↓
┌─────────────────────────────────────────┐
│  FastAPI Application (main.py)         │
│  - 路由注册                            │
│  - 中间件                              │
└─────────────────────────────────────────┘
       │
       ├─────────────────┬──────────────────┐
       ↓                 ↓                  ↓
┌──────────────────┐ ┌─────────────┐ ┌─────────────────┐
│ websocket_order  │ │ order.py    │ │ websocket_quote │
│ (订单连接路由)    │ │ (订单API)   │ │ (行情连接路由)   │
└────────┬─────────┘ └──────┬──────┘ └────────┬────────┘
         │                  │                   │
         │                  │                   │
         ↓                  ↓                   ↓
┌──────────────────────────────────────────────────┐
│       WebSocketManager (统一连接管理)              │
│  - active_connections: {client_id: {ws1, ws2}}    │
│  - connection_channels: {client_id: {channel}}    │
└───────────────────┬──────────────────────────────┘
                    │
                    │
         ┌──────────┴──────────┐
         ↓                     ↓
┌────────────────┐    ┌────────────────┐
│   订单推送      │    │   行情推送      │
└────────┬───────┘    └────────┬───────┘
         │                     │
         ↓                     ↓
┌────────────────┐    ┌────────────────┐
│ HTTP 请求      │    │ xtquant 回调   │
│ /order/stock   │    │ quote_callback │
│ /order/cancel  │    │                │
└────────┬───────┘    └────────┬───────┘
         │                     │
         ↓                     ↓
┌────────────────┐    ┌────────────────┐
│ QMT 交易接口   │    │ xtdata         │
│ trader.order   │    │ .subscribe_    │
│ _stock()       │    │ quote()        │
└────────┬───────┘    └────────┬───────┘
         │                     │
         │                     │ 行情数据推送
         │                     │ ↓
         │                     │ 回调处理
         │                     │ ↓
         │                     │ broadcast()
         │                     │ ↓
         └──────────┬──────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  所有已连接的客户端  │
         │  (按频道过滤)        │
         └──────────────────────┘
```

---

## 8. 使用示例

### 8.1 客户端 JavaScript 示例

```javascript
// 订单 WebSocket 连接
const orderWs = new WebSocket('ws://localhost:8000/ws/order/1000000365');

orderWs.onopen = () => {
    console.log('订单 WebSocket 连接已建立');
};

orderWs.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);

    switch (message.type) {
        case 'order_result':
            if (message.data.success) {
                console.log(`订单成功: 订单号 ${message.data.order_id}`);
            } else {
                console.log(`订单失败: ${message.data.message}`);
            }
            break;
        case 'cancel_result':
            if (message.data.success) {
                console.log(`撤单成功: 订单号 ${message.data.order_id}`);
            } else {
                console.log(`撤单失败: ${message.data.message}`);
            }
            break;
        case 'heartbeat':
            // 心跳消息，无需处理
            break;
    }
};

orderWs.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

orderWs.onclose = () => {
    console.log('WebSocket 连接已关闭');
};

// 行情 WebSocket 连接
const quoteWs = new WebSocket('ws://localhost:8000/ws/quote/client_001');

quoteWs.onopen = () => {
    console.log('行情 WebSocket 连接已建立');

    // 订阅行情
    quoteWs.send(JSON.stringify({
        type: 'subscribe',
        data: {
            stock_code: '600000.SH',
            period: '1d',
            count: 0
        }
    }));
};

quoteWs.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === 'quote_data') {
        const data = message.data;
        console.log(`行情更新: ${data.stock_code}`, data.data);
    } else if (message.type === 'subscription_confirmed') {
        console.log('行情订阅成功:', message.data.subscription_id);
    }
};
```

### 8.2 客户端 Python 示例

```python
import asyncio
import websockets
import json

async def order_websocket_client():
    client_id = "1000000365"
    uri = f"ws://localhost:8000/ws/order/{client_id}"

    async with websockets.connect(uri) as websocket:
        print("订单 WebSocket 连接成功!")

        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"收到消息: {data}")

            if data['type'] == 'order_result':
                if data['data']['success']:
                    print(f"订单成功: 订单号 {data['data']['order_id']}")
                else:
                    print(f"订单失败: {data['data']['message']}")

async def quote_websocket_client():
    client_id = "client_001"
    uri = f"ws://localhost:8000/ws/quote/{client_id}"

    async with websockets.connect(uri) as websocket:
        print("行情 WebSocket 连接成功!")

        # 发送订阅请求
        subscribe_msg = {
            "type": "subscribe",
            "data": {
                "stock_code": "600000.SH",
                "period": "1d",
                "count": 0
            }
        }
        await websocket.send(json.dumps(subscribe_msg))

        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"收到消息: {data}")

            if data['type'] == 'quote_data':
                print(f"行情更新: {data['data']['stock_code']}")

# 运行客户端
asyncio.run(order_websocket_client())
# asyncio.run(quote_websocket_client())
```

---

## 9. 注意事项

### 9.1 客户端 ID 使用
- **订单通道**: 建议使用账户 ID（如 `1000000365`），确保每个账户只能收到自己的订单消息
- **行情通道**: 可以使用任意唯一标识（如 `client_001`），用于区分不同客户端

### 9.2 连接管理
- 客户端断开连接后需要重新连接
- 同一个客户端可以有多个连接（多标签页、多设备）
- 连接断开时服务端会自动清理连接和频道信息

### 9.3 错误处理
- WebSocket 推送失败时会记录日志，但不会影响 HTTP 响应
- 失效的连接会自动从连接池中移除

### 9.4 性能考虑
- 大量并发连接时需要考虑服务器性能
- 行情数据高频推送时可能需要节流控制
- 建议使用心跳机制检测连接状态

### 9.5 安全性
- 生产环境应考虑添加身份验证
- 建议使用 WSS (WebSocket Secure) 加密连接
- 需要添加访问控制和频率限制

---

## 10. 扩展功能建议

1. **重连机制**: 客户端连接断开时自动重连
2. **消息确认**: 客户端收到消息后发送确认
3. **历史消息**: 连接时推送未读的历史消息
4. **多类型推送**: 添加成交、持仓等更多类型的推送
5. **心跳优化**: 客户端和服务器双向心跳，更快检测断线
6. **消息压缩**: 大数据量时启用消息压缩
7. **订阅管理**: 支持批量订阅、取消订阅
8. **消息优先级**: 重要消息优先发送

---

## 11. 相关文件清单

| 文件 | 说明 |
|------|------|
| `backend/services/websocket_manager.py` | WebSocket 连接管理器 |
| `backend/routes/websocket_order.py` | 订单 WebSocket 路由 |
| `backend/routes/websocket_quote.py` | 行情 WebSocket 路由 |
| `backend/routes/order.py` | 订单 API 路由（触发推送） |
| `backend/routes/quote.py` | 行情 API 路由（订阅管理） |
| `backend/schemas/websocket.py` | WebSocket 消息模型 |
| `backend/main.py` | 主应用（路由注册） |
| `backend/WEBSOCKET_README.md` | WebSocket 功能说明 |
| `backend/WEBSOCKET_MIGRATION.md` | WebSocket URL 迁移指南 |
| `backend/websocket_test.html` | WebSocket 测试页面 |

---

**文档版本**: v1.0
**最后更新**: 2025-03-21
**作者**: WorkBuddy AI Assistant
