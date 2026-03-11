# QMT回调处理系统实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在XTQuant AI后端系统中实现QMT交易回调处理功能，采用简单日志回调模式，记录所有交易回调数据到系统日志。

**Architecture:** 创建独立的QMTCallback类继承XtQuantTraderCallback，实现官方示例中的所有回调方法，每个方法记录结构化日志。在trader_singleton.py中注册回调实例。

**Tech Stack:** Python 3.13, FastAPI, XTQuant SDK, pytest, logging

---

## 文件结构

### 新增文件
1. `backend/services/qmt_callback.py` - QMT回调处理器实现
2. `backend/tests/test_qmt_callback.py` - 回调处理器测试

### 修改文件
1. `backend/services/trader_singleton.py:72` - 注册QMTCallback实例
2. `backend/services/__init__.py` - 导出QMTCallback类（可选）

### 文件职责
- `qmt_callback.py`: 实现所有回调方法，处理日志记录
- `trader_singleton.py`: 管理交易实例和回调注册
- `test_qmt_callback.py`: 验证回调功能和日志输出

---

## Chunk 1: 创建回调处理器基础结构

### Task 1: 创建QMTCallback类文件

**Files:**
- Create: `backend/services/qmt_callback.py`

- [ ] **Step 1: 创建文件并导入依赖**

```python
"""
QMT交易回调处理器

实现XTQuantTraderCallback的所有回调方法，将回调数据记录到系统日志。
"""
from xtquant.xttrader import XtQuantTraderCallback
import logging

logger = logging.getLogger(__name__)


class QMTCallback(XtQuantTraderCallback):
    """QMT交易回调处理器"""

    def __init__(self):
        """初始化回调处理器"""
        super().__init__()
        logger.info("QMTCallback初始化完成")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交基础文件**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 创建QMTCallback基础类文件"
```

---

### Task 2: 实现连接断开回调

**Files:**
- Modify: `backend/services/qmt_callback.py:15-30`

- [ ] **Step 1: 添加on_disconnected方法**

```python
    def on_disconnected(self):
        """
        连接断开回调

        当交易连接断开时调用
        """
        try:
            logger.warning("交易连接断开回调")
        except Exception as e:
            logger.error(f"处理连接断开回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交连接断开回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现连接断开回调方法"
```

---

### Task 3: 实现委托回报回调

**Files:**
- Modify: `backend/services/qmt_callback.py:32-60`

- [ ] **Step 1: 添加on_stock_order方法**

```python
    def on_stock_order(self, order):
        """
        委托回报推送

        :param order: XtOrder对象
        """
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
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交委托回报回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现委托回报回调方法"
```

---

## Chunk 2: 实现核心交易回调

### Task 4: 实现成交变动回调

**Files:**
- Modify: `backend/services/qmt_callback.py:62-90`

- [ ] **Step 1: 添加on_stock_trade方法**

```python
    def on_stock_trade(self, trade):
        """
        成交变动推送

        :param trade: XtTrade对象
        """
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
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交成交变动回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现成交变动回调方法"
```

---

### Task 5: 实现委托错误回调

**Files:**
- Modify: `backend/services/qmt_callback.py:92-110`

- [ ] **Step 1: 添加on_order_error方法**

```python
    def on_order_error(self, order_error):
        """
        委托失败推送

        :param order_error: XtOrderError对象
        """
        try:
            logger.error(
                f"委托报错回调 - 账户: {order_error.account_id}, "
                f"订单ID: {order_error.order_id}, "
                f"错误ID: {order_error.error_id}, "
                f"错误消息: {order_error.error_msg}, "
                f"投资备注: {order_error.order_remark}"
            )
        except Exception as e:
            logger.error(f"处理委托错误回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交委托错误回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现委托错误回调方法"
```

---

### Task 6: 实现撤单错误回调

**Files:**
- Modify: `backend/services/qmt_callback.py:112-130`

- [ ] **Step 1: 添加on_cancel_error方法**

```python
    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送

        :param cancel_error: XtCancelError对象
        """
        try:
            logger.error(
                f"撤单报错回调 - 账户: {cancel_error.account_id}, "
                f"订单ID: {cancel_error.order_id}, "
                f"错误ID: {cancel_error.error_id}, "
                f"错误消息: {cancel_error.error_msg}"
            )
        except Exception as e:
            logger.error(f"处理撤单错误回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交撤单错误回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现撤单错误回调方法"
```

---

## Chunk 3: 实现异步回调和其他回调

### Task 7: 实现异步委托响应回调

**Files:**
- Modify: `backend/services/qmt_callback.py:132-150`

- [ ] **Step 1: 添加on_order_stock_async_response方法**

```python
    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送

        :param response: XtOrderResponse对象
        """
        try:
            logger.info(
                f"异步委托回调 - 序列号: {response.seq}, "
                f"账户: {response.account_id}, "
                f"订单ID: {response.order_id}, "
                f"错误ID: {response.error_id}, "
                f"错误消息: {response.error_msg}, "
                f"投资备注: {response.order_remark}"
            )
        except Exception as e:
            logger.error(f"处理异步委托回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交异步委托响应回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现异步委托响应回调方法"
```

---

### Task 8: 实现异步撤单响应回调

**Files:**
- Modify: `backend/services/qmt_callback.py:152-170`

- [ ] **Step 1: 添加on_cancel_order_stock_async_response方法**

```python
    def on_cancel_order_stock_async_response(self, response):
        """
        异步撤单回报推送

        :param response: XtCancelOrderResponse对象
        """
        try:
            logger.info(
                f"异步撤单回调 - 序列号: {response.seq}, "
                f"账户: {response.account_id}, "
                f"订单ID: {response.order_id}, "
                f"错误ID: {response.error_id}, "
                f"错误消息: {response.error_msg}"
            )
        except Exception as e:
            logger.error(f"处理异步撤单回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交异步撤单响应回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现异步撤单响应回调方法"
```

---

### Task 9: 实现账户状态回调

**Files:**
- Modify: `backend/services/qmt_callback.py:172-190`

- [ ] **Step 1: 添加on_account_status方法**

```python
    def on_account_status(self, status):
        """
        账户状态推送

        :param status: XtAccountStatus对象
        """
        try:
            logger.info(
                f"账户状态回调 - 账户: {status.account_id}, "
                f"状态: {status.status}, "
                f"消息: {status.msg}"
            )
        except Exception as e:
            logger.error(f"处理账户状态回调时出错: {e}")
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交账户状态回调**

```bash
git add backend/services/qmt_callback.py
git commit -m "feat: 实现账户状态回调方法"
```

---

## Chunk 4: 集成到现有系统

### Task 10: 修改trader_singleton.py注册回调

**Files:**
- Modify: `backend/services/trader_singleton.py:10,72`

- [ ] **Step 1: 导入QMTCallback类**

在文件顶部添加导入：
```python
from .qmt_callback import QMTCallback
```

- [ ] **Step 2: 修改回调注册**

找到第72行左右：
```python
self._trader.register_callback(XtQuantTraderCallback())
```
修改为：
```python
self._trader.register_callback(QMTCallback())
```

- [ ] **Step 3: 运行语法检查**

Run: `python -m py_compile backend/services/trader_singleton.py`
Expected: 无输出（语法正确）

- [ ] **Step 4: 提交集成修改**

```bash
git add backend/services/trader_singleton.py
git commit -m "feat: 集成QMTCallback到交易单例"
```

---

### Task 11: 添加服务导出（可选）

**Files:**
- Modify: `backend/services/__init__.py`

- [ ] **Step 1: 添加QMTCallback导出**

如果文件存在，添加：
```python
from .qmt_callback import QMTCallback

__all__ = [
    # ... 现有导出
    'QMTCallback',
]
```

如果文件不存在，创建：
```python
"""
服务模块
"""
from .qmt_callback import QMTCallback
from .qmt_service import QMTService
from .trader_singleton import TraderSingleton

__all__ = [
    'QMTCallback',
    'QMTService',
    'TraderSingleton',
]
```

- [ ] **Step 2: 运行语法检查**

Run: `python -m py_compile backend/services/__init__.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交服务导出**

```bash
git add backend/services/__init__.py
git commit -m "feat: 添加QMTCallback到服务导出"
```

---

## Chunk 5: 创建单元测试

### Task 12: 创建测试文件

**Files:**
- Create: `backend/tests/test_qmt_callback.py`

- [ ] **Step 1: 创建测试文件基础结构**

```python
"""
QMTCallback单元测试
"""
import pytest
import logging
from unittest.mock import Mock, patch
from services.qmt_callback import QMTCallback


class TestQMTCallback:
    """QMTCallback测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.callback = QMTCallback()
        self.log_capture = []

        # 创建日志处理器捕获日志
        class LogHandler(logging.Handler):
            def emit(self, record):
                self.log_capture.append(record.getMessage())

        self.log_handler = LogHandler()
        logging.getLogger('services.qmt_callback').addHandler(self.log_handler)
        self.log_handler.log_capture = self.log_capture

    def teardown_method(self):
        """每个测试方法后执行"""
        logging.getLogger('services.qmt_callback').removeHandler(self.log_handler)
```

- [ ] **Step 2: 运行测试文件检查**

Run: `python -m py_compile backend/tests/test_qmt_callback.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 提交测试基础文件**

```bash
git add backend/tests/test_qmt_callback.py
git commit -m "test: 创建QMTCallback测试基础文件"
```

---

### Task 13: 测试on_stock_order方法

**Files:**
- Modify: `backend/tests/test_qmt_callback.py:30-60`

- [ ] **Step 1: 添加on_stock_order测试**

```python
    def test_on_stock_order(self):
        """测试委托回调日志记录"""
        # 创建模拟订单对象
        mock_order = Mock()
        mock_order.account_id = "2000128"
        mock_order.order_id = 1001
        mock_order.stock_code = "600000.SH"
        mock_order.order_type = 23  # 买入
        mock_order.order_volume = 1000
        mock_order.price_type = 0   # 限价
        mock_order.price = 10.5
        mock_order.order_status = 1  # 已报
        mock_order.status_msg = "已报"
        mock_order.strategy_name = "test_strategy"
        mock_order.order_remark = "test_order"
        mock_order.direction = 0
        mock_order.offset_flag = 0

        # 执行回调
        self.callback.on_stock_order(mock_order)

        # 验证日志输出
        assert len(self.log_capture) > 0
        log_message = self.log_capture[-1]
        assert "委托回调" in log_message
        assert "账户: 2000128" in log_message
        assert "股票: 600000.SH" in log_message
        assert "订单ID: 1001" in log_message
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest backend/tests/test_qmt_callback.py::TestQMTCallback::test_on_stock_order -v`
Expected: 测试通过（因为回调方法已实现）

- [ ] **Step 3: 提交委托回调测试**

```bash
git add backend/tests/test_qmt_callback.py
git commit -m "test: 添加委托回调测试"
```

---

### Task 14: 测试on_stock_trade方法

**Files:**
- Modify: `backend/tests/test_qmt_callback.py:62-90`

- [ ] **Step 1: 添加on_stock_trade测试**

```python
    def test_on_stock_trade(self):
        """测试成交回调日志记录"""
        # 创建模拟成交对象
        mock_trade = Mock()
        mock_trade.account_id = "2000128"
        mock_trade.order_id = 1001
        mock_trade.stock_code = "600000.SH"
        mock_trade.traded_price = 10.5
        mock_trade.traded_volume = 500
        mock_trade.order_remark = "test_trade"
        mock_trade.offset_flag = 48  # 买入

        # 执行回调
        self.callback.on_stock_trade(mock_trade)

        # 验证日志输出
        assert len(self.log_capture) > 0
        log_message = self.log_capture[-1]
        assert "成交回调" in log_message
        assert "账户: 2000128" in log_message
        assert "股票: 600000.SH" in log_message
        assert "成交价格: 10.5" in log_message
        assert "成交数量: 500" in log_message
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest backend/tests/test_qmt_callback.py::TestQMTCallback::test_on_stock_trade -v`
Expected: 测试通过

- [ ] **Step 3: 提交成交回调测试**

```bash
git add backend/tests/test_qmt_callback.py
git commit -m "test: 添加成交回调测试"
```

---

### Task 15: 测试错误处理

**Files:**
- Modify: `backend/tests/test_qmt_callback.py:92-120`

- [ ] **Step 1: 添加错误处理测试**

```python
    def test_on_order_error(self):
        """测试委托错误回调日志记录"""
        # 创建模拟错误对象
        mock_error = Mock()
        mock_error.account_id = "2000128"
        mock_error.order_id = 1001
        mock_error.error_id = 10001
        mock_error.error_msg = "委托失败: 资金不足"
        mock_error.order_remark = "test_error"

        # 执行回调
        self.callback.on_order_error(mock_error)

        # 验证日志输出
        assert len(self.log_capture) > 0
        log_message = self.log_capture[-1]
        assert "委托报错回调" in log_message
        assert "账户: 2000128" in log_message
        assert "错误ID: 10001" in log_message
        assert "错误消息: 委托失败: 资金不足" in log_message

    def test_exception_handling(self):
        """测试异常情况下的错误处理"""
        # 创建会引发异常的对象
        mock_broken_order = Mock()
        mock_broken_order.account_id = "2000128"
        # 设置属性访问引发异常
        mock_broken_order.order_id = Mock(side_effect=AttributeError("测试异常"))

        # 执行回调，应该捕获异常并记录错误日志
        self.callback.on_stock_order(mock_broken_order)

        # 验证错误日志被记录
        assert len(self.log_capture) > 0
        log_message = self.log_capture[-1]
        assert "处理委托回调时出错" in log_message
```

- [ ] **Step 2: 运行错误处理测试**

Run: `pytest backend/tests/test_qmt_callback.py::TestQMTCallback::test_on_order_error -v`
Expected: 测试通过

- [ ] **Step 3: 提交错误处理测试**

```bash
git add backend/tests/test_qmt_callback.py
git commit -m "test: 添加错误回调和异常处理测试"
```

---

## Chunk 6: 集成测试和验证

### Task 16: 运行完整测试套件

**Files:**
- 所有相关文件

- [ ] **Step 1: 运行所有QMTCallback测试**

Run: `pytest backend/tests/test_qmt_callback.py -v`
Expected: 所有测试通过

- [ ] **Step 2: 运行服务模块测试**

Run: `pytest backend/tests/ -k "callback" -v`
Expected: 找到并运行回调相关测试

- [ ] **Step 3: 验证语法和导入**

Run: `python -c "from services.qmt_callback import QMTCallback; print('QMTCallback导入成功')"`
Expected: 输出 "QMTCallback导入成功"

- [ ] **Step 4: 提交测试验证**

```bash
git add backend/tests/
git commit -m "test: 完成QMTCallback测试套件验证"
```

---

### Task 17: 验证与现有系统集成

**Files:**
- `backend/services/trader_singleton.py`
- `backend/main.py`

- [ ] **Step 1: 验证trader_singleton导入**

Run: `python -c "from services.trader_singleton import TraderSingleton; print('TraderSingleton导入成功')"`
Expected: 输出 "TraderSingleton导入成功"

- [ ] **Step 2: 验证FastAPI应用启动**

Run: `cd backend && python -c "from main import app; print('FastAPI应用导入成功')"`
Expected: 输出 "FastAPI应用导入成功"

- [ ] **Step 3: 检查日志配置**

Run: `cd backend && python -c "import logging; logger = logging.getLogger('services.qmt_callback'); print(f'QMTCallback日志器: {logger}')"`
Expected: 输出日志器对象信息

- [ ] **Step 4: 提交集成验证**

```bash
git add backend/services/ backend/main.py
git commit -m "chore: 验证QMTCallback与系统集成"
```

---

### Task 18: 创建使用示例文档

**Files:**
- Create: `docs/qmt-callback-usage.md`

- [ ] **Step 1: 创建使用文档**

```markdown
# QMT回调处理系统使用指南

## 概述

QMT回调处理系统实现了XTQuant交易系统的完整回调功能，将所有交易回调数据记录到系统日志中。

## 功能特性

- 支持所有官方示例回调类型
- 结构化日志记录，便于查询和分析
- 自动错误处理，不影响系统稳定性
- 与现有交易系统无缝集成

## 回调类型

### 1. 委托回报 (on_stock_order)
当订单状态发生变化时触发，记录：
- 账户信息
- 订单详情
- 委托状态
- 策略信息

### 2. 成交回报 (on_stock_trade)
当订单成交时触发，记录：
- 成交价格和数量
- 成交金额
- 买卖方向

### 3. 错误回调 (on_order_error, on_cancel_error)
当委托或撤单失败时触发，记录：
- 错误代码
- 错误消息
- 失败原因

### 4. 异步响应 (on_order_stock_async_response, on_cancel_order_stock_async_response)
异步操作响应时触发，记录：
- 序列号
- 操作结果
- 错误信息（如果有）

### 5. 账户状态 (on_account_status)
账户状态变化时触发，记录：
- 账户状态
- 状态消息

### 6. 连接断开 (on_disconnected)
交易连接断开时触发，记录警告信息。

## 日志查看

### 日志位置
回调日志输出到项目配置的日志文件中，默认位置：
- 控制台输出（开发环境）
- 日志文件（生产环境）

### 日志格式
```
[时间戳] [日志级别] [QMTCallback.方法名] 回调信息 - 字段1: 值1, 字段2: 值2, ...
```

### 示例日志
```
[2026-03-11 10:30:25] [INFO] [QMTCallback.on_stock_order] 委托回调 - 账户: 2000128, 订单ID: 1001, 股票: 600000.SH, 状态: 已报, 备注: strategy_name
[2026-03-11 10:30:26] [INFO] [QMTCallback.on_stock_trade] 成交回调 - 账户: 2000128, 订单ID: 1001, 股票: 600000.SH, 成交价格: 10.5, 成交数量: 500
```

## 配置说明

### 日志级别
在日志配置中设置 `services.qmt_callback` 的日志级别：
- `INFO`: 记录所有回调信息（推荐）
- `DEBUG`: 记录详细调试信息
- `WARNING`: 只记录警告和错误
- `ERROR`: 只记录错误

### 启用/禁用
回调系统自动启用，无需额外配置。如需禁用，可修改 `trader_singleton.py` 中的回调注册。

## 故障排除

### 问题1: 没有回调日志
1. 检查交易连接是否正常
2. 验证账户是否已订阅
3. 检查日志级别设置
4. 查看是否有异常日志

### 问题2: 日志格式不正确
1. 检查日志配置
2. 验证回调数据对象结构
3. 查看异常处理日志

### 问题3: 回调处理异常
1. 查看错误日志中的异常信息
2. 检查回调方法实现
3. 验证数据对象属性

## 扩展开发

### 添加新的回调处理
如需添加新的回调处理方式（如WebSocket推送）：
1. 继承 `QMTCallback` 类
2. 重写需要扩展的回调方法
3. 在 `trader_singleton.py` 中注册新的回调实例

### 自定义日志格式
修改 `QMTCallback` 类中的日志记录逻辑，使用自定义格式。

## 相关文件
- `services/qmt_callback.py` - 回调处理器实现
- `services/trader_singleton.py` - 回调注册
- `tests/test_qmt_callback.py` - 单元测试
```

- [ ] **Step 2: 提交使用文档**

```bash
git add docs/qmt-callback-usage.md
git commit -m "docs: 添加QMT回调处理系统使用指南"
```

---

### Task 19: 最终验证和总结

**Files:**
- 所有修改的文件

- [ ] **Step 1: 运行完整测试套件**

Run: `cd backend && pytest tests/ -v`
Expected: 所有测试通过

- [ ] **Step 2: 检查代码风格**

Run: `cd backend && python -m black --check services/ tests/`
Expected: 代码格式正确（或使用项目代码风格工具）

- [ ] **Step 3: 验证导入和依赖**

Run: `cd backend && python -c "import sys; from services.qmt_callback import QMTCallback; from services.trader_singleton import TraderSingleton; print('所有导入成功')"`
Expected: 输出 "所有导入成功"

- [ ] **Step 4: 创建最终提交**

```bash
git add .
git commit -m "feat: 完成QMT回调处理系统实现

- 实现完整官方示例回调功能
- 所有回调数据记录到系统日志
- 包含完整的单元测试
- 添加使用文档和示例
- 与现有系统无缝集成

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 实施后验证清单

完成所有任务后，验证以下项目：

### 功能验证
- [ ] 所有回调方法已实现
- [ ] 回调数据正确记录到日志
- [ ] 错误处理正常工作
- [ ] 与交易系统集成正常

### 测试验证
- [ ] 所有单元测试通过
- [ ] 测试覆盖主要功能
- [ ] 异常情况测试通过

### 代码质量
- [ ] 代码符合项目规范
- [ ] 文档完整准确
- [ ] 导入和依赖正确

### 系统集成
- [ ] 不影响现有功能
- [ ] 日志输出符合预期
- [ ] 性能影响可接受

---

**计划完成时间估计**：2-3小时（包含测试和验证）

**关键风险**：
1. XTQuant SDK回调数据格式变化
2. 日志输出影响系统性能
3. 与现有系统的兼容性问题

**缓解措施**：
1. 使用try-except包装所有回调处理
2. 监控日志文件大小和系统性能
3. 充分测试与现有功能的集成