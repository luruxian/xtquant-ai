# XtQuant AI 后端 API 总结

## 已完成的工作

### 1. XtQuantTrader 实例优化
- **问题**: 每个API请求都重复创建XtQuantTrader实例，造成性能浪费
- **解决方案**: 实现全局单例模式
- **实现文件**:
  - `services/trader_singleton.py` - 全局单例管理器
  - `services/qmt_service.py` - 修改为使用全局单例
- **优化效果**: 显著提升批量查询性能，减少资源浪费

### 2. 路由文件优化
所有路由文件已优化为使用新的查询方法：

#### `routes/asset.py` - 资产查询
- `GET /api/v1/asset` - 查询单个账户资产
- `GET /api/v1/asset/batch` - 批量查询账户资产
- `GET /api/v1/asset/accounts` - 查询所有账户信息

#### `routes/position.py` - 持仓查询
- `GET /api/v1/position/{stock_code}` - 根据股票代码查询持仓
- `GET /api/v1/position` - 查询当日所有持仓

#### `routes/trade.py` - 成交查询
- `GET /api/v1/trade` - 查询当日所有成交

#### `routes/order.py` - 订单管理
- `GET /api/v1/order` - 查询当日所有委托
- `GET /api/v1/order/{order_id}` - 查询单个订单
- `POST /api/v1/order` - 创建订单（同步下单）
- `DELETE /api/v1/order` - 取消订单（同步撤单）

### 3. 新增异步交易API

#### 异步报单API
- **端点**: `POST /api/v1/order/async`
- **请求模型**: `OrderRequest` (复用现有模型)
- **响应模型**: `AsyncOrderResponse`
  ```json
  {
    "seq": 12345,
    "message": "异步下单请求已提交",
    "account_id": "1000000365",
    "stock_code": "600000.SH",
    "order_type": 23,
    "order_volume": 1000,
    "price_type": 0,
    "price": 10.5,
    "strategy_name": "strategy1",
    "order_remark": "order_test"
  }
  ```

#### 异步撤单API
- **端点**: `DELETE /api/v1/order/async`
- **请求模型**: `AsyncCancelOrderRequest`
  ```json
  {
    "account_id": "1000000365",
    "order_id": 100
  }
  ```
- **响应模型**: `AsyncCancelOrderResponse`
  ```json
  {
    "cancel_seq": 12346,
    "message": "异步撤单请求已提交",
    "account_id": "1000000365",
    "order_id": 100
  }
  ```

### 4. 技术特点

#### 全局单例管理器 (`TraderSingleton`)
- 线程安全的懒加载初始化
- 永久订阅模式管理
- 连接状态监控和健康检查
- 资源清理和优雅关闭

#### 新的查询方法 (`QMTService`)
- `query_with_account()` - 单个账户查询（自动处理订阅）
- `batch_query_accounts()` - 批量账户查询
- `get_shared_trader()` - 获取全局交易实例
- `ensure_account_subscribed()` - 确保账户订阅状态

### 5. 修复的问题
- `utils/config.py` - 修复缺少`import time`的问题
- 所有路由文件 - 消除重复创建实例的问题

## API 端点总览

### 资产相关
- `GET /api/v1/asset` - 查询账户资产
- `GET /api/v1/asset/batch` - 批量查询资产
- `GET /api/v1/asset/accounts` - 查询账户列表

### 持仓相关
- `GET /api/v1/position` - 查询所有持仓
- `GET /api/v1/position/{stock_code}` - 查询特定股票持仓

### 成交相关
- `GET /api/v1/trade` - 查询当日成交

### 订单相关
- `GET /api/v1/order` - 查询所有委托
- `GET /api/v1/order/{order_id}` - 查询单个订单
- `POST /api/v1/order` - 同步下单
- `POST /api/v1/order/async` - 异步下单
- `DELETE /api/v1/order` - 同步撤单
- `DELETE /api/v1/order/async` - 异步撤单

## 性能优化成果
1. **减少实例创建**: 从每次API调用创建实例改为全局单例
2. **批量查询优化**: 批量查询使用共享实例，显著提升性能
3. **永久订阅模式**: 账户订阅后保持订阅状态，减少重复订阅开销
4. **资源管理**: 统一的资源初始化和清理机制

## 下一步建议
1. 添加API文档和示例
2. 实现回调处理机制（用于异步交易结果）
3. 添加更多的错误处理和重试逻辑
4. 实现连接断开自动重连
5. 添加性能监控和日志记录