# WebSocket URL 迁移指南

## 变更概述
为了统一WebSocket URL管理，我们对WebSocket端点进行了重构：

### 旧的URL结构：
- 订单WebSocket: `/ws/{client_id}`
- 行情WebSocket: `/api/v1/quote/ws/{client_id}`

### 新的URL结构：
- 订单WebSocket: `/ws/order/{client_id}`
- 行情WebSocket: `/ws/quote/{client_id}`

## 主要变更

### 1. URL前缀统一
所有WebSocket URL现在都以`/ws`开头，功能通过子路径区分：
- `/ws/order/{client_id}` - 订单结果和撤单结果推送
- `/ws/quote/{client_id}` - 实时行情数据推送

### 2. 消息格式标准化
新的消息格式采用统一结构：
```json
{
  "type": "message_type",
  "channel": "order|quote",
  "data": {},
  "timestamp": "2024-01-01T00:00:00",
  "client_id": "client_001"
}
```

### 3. 功能分离
- **订单WebSocket**：专门处理订单相关消息（order_result, cancel_result）
- **行情WebSocket**：专门处理行情相关消息（quote_data, subscription_confirmed等）

## 客户端迁移步骤

### 步骤1：更新连接URL
```javascript
// 旧的连接方式
const orderWs = new WebSocket('ws://localhost:8000/ws/account_123');
const quoteWs = new WebSocket('ws://localhost:8000/api/v1/quote/ws/client_001');

// 新的连接方式
const orderWs = new WebSocket('ws://localhost:8000/ws/order/account_123');
const quoteWs = new WebSocket('ws://localhost:8000/ws/quote/client_001');
```

### 步骤2：更新消息处理
```javascript
// 旧的消息格式（订单结果）
{
  "type": "order_result",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    // ... 其他字段
  }
}

// 新的消息格式（订单结果）
{
  "type": "order_result",
  "channel": "order",
  "data": {
    "order_id": 123,
    "account": "1000000365",
    // ... 其他字段
  },
  "timestamp": "2024-01-01T12:00:00.000000",
  "client_id": "account_123"
}
```

### 步骤3：更新订阅逻辑
```javascript
// 旧的行情订阅（通过HTTP API）
// POST /api/v1/quote/subscribe

// 新的行情订阅（通过WebSocket）
// 连接到 /ws/quote/{client_id} 后发送：
{
  "type": "subscribe",
  "stock_code": "600000.SH",
  "period": "1d"
}
```

## 向后兼容性

### 已移除的功能
1. 旧的订单WebSocket端点 (`/ws/{client_id}`) 已移除
2. 旧的行情WebSocket端点 (`/api/v1/quote/ws/{client_id}`) 已移除

### 保持的功能
1. 所有HTTP API接口保持不变
2. 订单和撤单的HTTP API接口仍然工作
3. 行情订阅的HTTP API接口仍然工作

## 测试新端点

### 测试订单WebSocket
```bash
# 使用websocat或其他WebSocket客户端测试
websocat ws://localhost:8000/ws/order/test_account
```

### 测试行情WebSocket
```bash
# 连接行情WebSocket
websocat ws://localhost:8000/ws/quote/test_client

# 发送订阅请求
{"type": "subscribe", "stock_code": "600000.SH", "period": "1d"}
```

## 故障排除

### 常见问题
1. **连接失败**：检查URL是否正确，确保使用新的URL格式
2. **收不到消息**：检查客户端ID是否正确，确保已订阅相应频道
3. **消息格式错误**：检查消息处理代码是否支持新的标准化格式

### 调试建议
1. 查看服务器日志，确认连接建立
2. 使用WebSocket测试工具验证连接
3. 检查客户端ID和频道设置

## 相关文件
- `backend/services/websocket_manager.py` - 统一的WebSocket管理器
- `backend/routes/websocket_order.py` - 订单WebSocket路由
- `backend/routes/websocket_quote.py` - 行情WebSocket路由
- `backend/routes/websocket_legacy.py` - 旧的WebSocket路由（已备份）