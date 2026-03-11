# QMT回调处理系统设计文档

## 概述

本设计文档描述了在XTQuant AI后端系统中添加QMT交易回调处理功能的方案。基于用户需求，采用"简单日志回调"模式，实现完整的官方示例回调功能，将所有回调数据记录到系统日志中。

## 设计决策

### 选择的方法：方法1 - 简单日志回调

**理由**：
1. 完全符合用户"仅日志记录"的需求
2. 实现简单，风险低，不影响现有系统稳定性
3. 便于调试和监控交易状态
4. 符合YAGNI原则，不添加不必要功能
5. 未来可轻松扩展为其他模式

### 功能范围
- 实现官方示例中的所有回调类型
- 仅日志记录，不推送给客户端
- 支持多客户端广播模式（日志对所有客户端可见）

## 架构设计

### 系统架构

```
现有系统架构：
┌─────────────────┐
│   FastAPI应用   │
├─────────────────┤
│   routes/       │ - API路由层
│   services/     │ - 业务逻辑层
│   schemas/      │ - 数据模型层
│   utils/        │ - 工具函数层
└─────────────────┘

新增组件：
┌─────────────────┐
│ services/       │
│   qmt_callback.py│ ← 新增：QMT回调处理器
│   trader_singleton.py│ ← 修改：注册回调实例
└─────────────────┘
```

### 回调类设计

**类名**：`QMTCallback`
**位置**：`services/qmt_callback.py`
**继承**：`XtQuantTraderCallback`

**实现方法**（覆盖所有官方示例回调）：
1. `on_stock_order()` - 委托回报推送
2. `on_stock_trade()` - 成交变动推送
3. `on_order_error()` - 委托失败推送
4. `on_cancel_error()` - 撤单失败推送
5. `on_order_stock_async_response()` - 异步下单回报推送
6. `on_cancel_order_stock_async_response()` - 异步撤单回报推送
7. `on_account_status()` - 账户状态推送
8. `on_disconnected()` - 连接断开回调

## 详细设计

### 1. 回调类实现

```python
# services/qmt_callback.py
from xtquant.xttrader import XtQuantTraderCallback
import logging

logger = logging.getLogger(__name__)

class QMTCallback(XtQuantTraderCallback):
    """QMT交易回调处理器"""

    def on_stock_order(self, order):
        """委托回报推送"""
        try:
            logger.info(
                f"委托回调 - 账户: {order.account_id}, "
                f"订单ID: {order.order_id}, "
                f"股票: {order.stock_code}, "
                f"委托类型: {order.order_type}, "
                f"委托数量: {order.order_volume}, "
                f"价格类型: {order.price_type}, "
                f"价格: {order.price}, "
                f"状态: {order.order_status}, "
                f"状态消息: {order.status_msg}, "
                f"策略名称: {order.strategy_name}, "
                f"投资备注: {order.order_remark}, "
                f"方向: {order.direction}, "
                f"开平标志: {order.offset_flag}"
            )
        except Exception as e:
            logger.error(f"处理委托回调时出错: {e}")

    def on_stock_trade(self, trade):
        """成交变动推送"""
        try:
            logger.info(
                f"成交回调 - 账户: {trade.account_id}, "
                f"订单ID: {trade.order_id}, "
                f"股票: {trade.stock_code}, "
                f"成交价格: {trade.traded_price}, "
                f"成交数量: {trade.traded_volume}, "
                f"成交金额: {trade.traded_price * trade.traded_volume}, "
                f"投资备注: {trade.order_remark}, "
                f"委托方向: {trade.offset_flag} "
                f"(48=买, 49=卖)"
            )
        except Exception as e:
            logger.error(f"处理成交回调时出错: {e}")

    # ... 其他回调方法类似实现
```

### 2. 日志格式规范

**日志级别**：
- `INFO`：正常回调事件
- `ERROR`：回调处理异常
- `WARNING`：需要注意但不影响运行的情况

**日志字段**：
- 时间戳（自动添加）
- 日志级别
- 回调类型（如`QMTCallback.on_stock_order`）
- 账户信息
- 订单/成交详情
- 状态/错误信息

**示例输出**：
```
[2026-03-11 10:30:25] [INFO] [QMTCallback.on_stock_order] 委托回调 - 账户: 2000128, 订单ID: 1001, 股票: 600000.SH, 状态: 已报, 备注: strategy_name
```

### 3. 集成到现有系统

**修改 `trader_singleton.py`**：
```python
# 在适当位置导入
from .qmt_callback import QMTCallback

# 修改初始化方法中的回调注册
# 替换：self._trader.register_callback(XtQuantTraderCallback())
# 改为：self._trader.register_callback(QMTCallback())
```

### 4. 错误处理策略

1. **回调方法内部错误**：每个方法都有try-except包装，记录错误但不影响其他回调
2. **数据格式错误**：记录原始异常信息，便于调试
3. **系统级错误**：由上层系统处理，回调类只负责记录

### 5. 线程安全考虑

- QMT回调在专用线程中执行
- 日志记录器是线程安全的
- 不需要额外的同步机制

## 数据模型

### 回调数据类型

基于官方示例，需要处理的数据类型：

1. **XtOrder** - 委托对象
2. **XtTrade** - 成交对象
3. **XtOrderError** - 委托错误对象
4. **XtCancelError** - 撤单错误对象
5. **XtOrderResponse** - 异步委托响应对象
6. **XtCancelOrderResponse** - 异步撤单响应对象
7. **XtAccountStatus** - 账户状态对象

### 日志数据结构

每个回调日志包含：
- **元数据**：时间戳、日志级别、回调类型
- **账户信息**：account_id, account_type
- **交易信息**：stock_code, order_id, volume, price等
- **状态信息**：order_status, status_msg, error_msg等
- **业务信息**：strategy_name, order_remark等

## 配置要求

### 日志配置
- 使用项目现有的日志配置
- 确保回调日志能正确输出到文件和控制台
- 建议日志级别设置为INFO或DEBUG以查看详细回调信息

### 系统配置
- 不需要额外配置项
- 回调自动启用，无需手动开关

## 测试策略

### 单元测试
1. 测试每个回调方法的日志记录功能
2. 测试异常情况下的错误处理
3. 测试日志格式的正确性

### 集成测试
1. 测试与交易系统的集成
2. 测试在实际交易场景下的回调触发
3. 测试日志输出的完整性和准确性

### 测试用例示例
```python
def test_on_stock_order():
    """测试委托回调日志记录"""
    callback = QMTCallback()
    mock_order = MockOrder(
        account_id="2000128",
        order_id=1001,
        stock_code="600000.SH",
        order_type=23,  # 买入
        order_volume=1000,
        price_type=0,   # 限价
        price=10.5,
        order_status=1, # 已报
        status_msg="已报",
        strategy_name="test_strategy",
        order_remark="test_order"
    )

    # 执行回调
    callback.on_stock_order(mock_order)

    # 验证日志输出
    assert "委托回调" in caplog.text
    assert "账户: 2000128" in caplog.text
    assert "股票: 600000.SH" in caplog.text
```

## 部署计划

### 阶段1：开发与测试
1. 实现 `QMTCallback` 类
2. 编写单元测试
3. 集成到现有系统
4. 本地测试验证

### 阶段2：集成测试
1. 在实际交易环境中测试
2. 验证回调触发和日志记录
3. 性能测试（确保不影响交易性能）

### 阶段3：生产部署
1. 部署到测试环境
2. 监控日志输出
3. 验证系统稳定性
4. 部署到生产环境

## 风险与缓解

### 风险1：回调处理影响交易性能
- **缓解**：回调处理只记录日志，操作轻量
- **监控**：监控系统性能指标，确保无影响

### 风险2：日志输出过大
- **缓解**：使用适当的日志级别（INFO）
- **监控**：监控日志文件大小，设置轮转策略

### 风险3：回调数据格式变化
- **缓解**：使用try-except包装，记录原始异常
- **监控**：定期检查日志中的异常信息

## 未来扩展性

### 扩展点1：WebSocket推送
- 可在 `QMTCallback` 中添加WebSocket广播功能
- 需要集成现有的 `QuoteSubscriptionManager`

### 扩展点2：数据库存储
- 可添加数据库存储回调数据的功能
- 需要设计回调数据表结构

### 扩展点3：回调过滤
- 可添加回调类型过滤配置
- 支持只记录特定类型的回调

### 扩展点4：回调统计分析
- 可添加回调数据统计分析功能
- 提供交易行为分析报告

## 成功标准

1. **功能完整性**：实现所有官方示例回调方法
2. **日志准确性**：回调数据正确记录到日志
3. **系统稳定性**：不影响现有交易功能
4. **性能影响**：回调处理不显著影响系统性能
5. **可维护性**：代码清晰，易于理解和扩展

## 附录

### 官方示例回调方法参考

```python
# 官方示例中的回调类
class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        print(datetime.datetime.now(), '连接断开回调')

    def on_stock_order(self, order):
        print(datetime.datetime.now(), '委托回调 投资备注', order.order_remark)

    def on_stock_trade(self, trade):
        print(datetime.datetime.now(), '成交回调', trade.order_remark)

    def on_order_error(self, order_error):
        print(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        print(datetime.datetime.now(), 'on_cancel_error')

    def on_order_stock_async_response(self, response):
        print(f"异步委托回调 投资备注: {response.order_remark}")

    def on_cancel_order_stock_async_response(self, response):
        print(datetime.datetime.now(), 'on_cancel_order_stock_async_response')

    def on_account_status(self, status):
        print(datetime.datetime.now(), 'on_account_status')
```

### 相关文件列表

1. `services/qmt_callback.py` - 新增：回调处理器实现
2. `services/trader_singleton.py` - 修改：注册回调实例
3. `tests/test_qmt_callback.py` - 新增：回调测试
4. `docs/superpowers/specs/2026-03-11-qmt-callback-design.md` - 本设计文档

---

**文档版本**：1.0
**创建日期**：2026-03-11
**最后更新**：2026-03-11
**状态**：已批准 ✅