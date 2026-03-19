# 日志系统设计文档

## 概述
为xtquant-ai后端项目添加集中式日志系统，实现按日期轮转的日志输出功能。

## 需求
1. 日志输出到`backend/logs`目录
2. 每天自动轮转日志文件
3. 日志级别：INFO及以上（INFO, WARNING, ERROR, CRITICAL）
4. 日志格式：基础格式（时间戳、日志级别、模块名、消息）
5. 替换所有现有`print`语句为`logger`调用

## 架构设计

### 目录结构
```
backend/
├── logs/                    # 日志目录（自动创建）
│   ├── app.log              # 当前应用日志文件
│   ├── app.log.2026-03-18   # 轮转后的日志文件（日期后缀）
│   ├── websocket.log        # WebSocket专用日志
│   ├── error.log            # 错误日志
│   └── error.log.2026-03-18 # 轮转后的错误日志
├── utils/
│   └── logging_config.py    # 日志配置模块
├── main.py                  # 修改应用启动
└── routes/                  # 各路由模块
```

### 组件设计

#### 1. 日志配置模块 (`utils/logging_config.py`)
- **功能**：集中管理日志配置
- **配置项**：
  - 日志级别：INFO
  - 轮转策略：每天午夜轮转
  - 文件命名：`{module_name}_{date}.log`
  - 日志格式：`%(asctime)s - %(levelname)s - %(name)s - %(message)s`
  - 保留天数：30天
- **处理器**：
  - FileHandler：按日期轮转的文件日志
  - StreamHandler：控制台输出（可选）
  - 错误日志单独文件

#### 2. 应用启动修改 (`main.py`)
- 在FastAPI应用启动时初始化日志系统
- 确保所有模块使用统一的日志配置

#### 3. 模块更新
- 更新所有现有模块的`print`语句为`logger`调用
- 保持现有的`logger = logging.getLogger(__name__)`模式

## 详细设计

### 日志配置实现

```python
# utils/logging_config.py
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any

def setup_logging():
    """设置模块化日志配置"""

    # 创建日志目录
    log_dir = Path("backend/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日志配置字典
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "app_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "INFO",
                "formatter": "standard",
                "filename": str(log_dir / "app.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "encoding": "utf-8"
            },
            "websocket_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": str(log_dir / "websocket.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8"
            },
            "error_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": str(log_dir / "error.log"),
                "when": "midnight",
                "interval": 1,
                "backupCount": 90,  # 错误日志保留更久
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["app_file", "console"],
                "propagate": False
            },
            "app.websocket": {
                "level": "INFO",
                "handlers": ["websocket_file"],
                "propagate": False
            },
            "app.trade": {
                "level": "INFO",
                "handlers": ["app_file"],
                "propagate": False
            },
            "app.quote": {
                "level": "INFO",
                "handlers": ["app_file"],
                "propagate": False
            },
            "xtquant": {
                "level": "WARNING",
                "propagate": False
            },
            "uvicorn": {
                "level": "WARNING",
                "propagate": False
            },
            "fastapi": {
                "level": "WARNING",
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",  # 根日志器只处理WARNING及以上
            "handlers": ["console"]
        }
    }

    # 应用配置
    logging.config.dictConfig(config)
```

### 应用启动修改

```python
# main.py
from fastapi import FastAPI
from utils.logging_config import setup_logging

# 初始化日志系统
setup_logging()

app = FastAPI(
    title="MiniQMT AI Backend",
    description="后端 API 服务",
    version="1.0.0"
)

# ... 其余代码不变
```

### 模块日志更新示例

```python
# routes/websocket_quote.py
import logging

# 使用适当的日志器名称
logger = logging.getLogger("app.websocket")

# 替换前
print(f"收到客户端 {client_id} 的原始消息: {data}")

# 替换后
logger.info(f"收到客户端 {client_id} 的原始消息: {data}")
```

## 实施计划

### 阶段1：基础架构（修正配置问题）
1. 创建`utils/logging_config.py`（使用模块化配置）
2. 修改`main.py`初始化日志
3. 创建日志目录结构
4. 修正根日志器配置问题

### 阶段2：模块化改造（按功能域分离日志）
1. 更新`routes/websocket_quote.py`（使用`app.websocket`日志器）
2. 更新`routes/websocket_order.py`（使用`app.websocket`日志器）
3. 更新`routes/quote.py`（使用`app.quote`日志器）
4. 更新其他路由模块（使用相应的功能域日志器）
5. 更新服务模块（使用`app`日志器）

### 阶段3：验证测试
1. 启动应用验证日志输出
2. 测试日志轮转功能
3. 验证日志级别过滤
4. 测试不同模块的日志分离
5. 验证第三方库日志级别控制

## 验收标准

1. ✅ 日志文件正确创建在`backend/logs`目录
2. ✅ 每天自动创建新的日志文件（按日期轮转）
3. ✅ 日志级别正确过滤（INFO及以上）
4. ✅ 所有`print`语句已替换为`logger`调用
5. ✅ 日志格式符合要求
6. ✅ 错误日志单独记录在error.log
7. ✅ 不同模块的日志级别可独立配置
8. ✅ WebSocket日志单独记录在websocket.log
9. ✅ 第三方库日志级别正确控制（WARNING及以上）
10. ✅ 根日志器配置正确（不接收应用模块日志）

## 风险与缓解

### 技术风险

#### 风险1：根日志器配置问题
- **问题**：错误的根日志器配置导致日志传播失控、性能下降
- **缓解**：使用模块化配置，为应用创建专用日志器，设置`propagate=False`

#### 风险2：并发写入冲突
- **问题**：多进程/多线程环境下的日志文件锁竞争
- **缓解**：考虑使用`ConcurrentRotatingFileHandler`或异步日志处理

#### 风险3：磁盘I/O瓶颈
- **问题**：高频日志写入导致磁盘I/O饱和
- **缓解**：实施异步日志、批量写入、日志频率限制

#### 风险4：内存泄漏
- **问题**：日志处理器未正确关闭导致资源泄漏
- **缓解**：添加资源清理机制，确保处理器正确关闭

### 运维风险

#### 风险5：日志文件膨胀
- **问题**：单个日志文件过大影响查看和分析
- **缓解**：结合大小和时间双重轮转策略，设置单个文件大小限制

#### 风险6：日志丢失
- **问题**：应用崩溃时缓冲区日志丢失
- **缓解**：同步写入关键日志，实现WAL（Write-Ahead Logging）模式

#### 风险7：时区问题
- **问题**：`TimedRotatingFileHandler`使用UTC时间，在中国时区可能不准确
- **缓解**：考虑时区处理或使用本地时间轮转

### 业务风险

#### 风险8：故障排查效率低
- **问题**：所有模块日志混在一起影响排查效率
- **缓解**：按功能域分离日志，添加结构化日志支持

#### 风险9：敏感信息泄露
- **问题**：日志中可能包含密码、token等敏感信息
- **缓解**：添加敏感信息过滤机制

#### 风险10：监控盲点
- **问题**：日志系统自身的故障无法被监控
- **缓解**：添加心跳检测和自监控机制

## 后续扩展

1. **日志监控**：集成日志监控工具
2. **结构化日志**：支持JSON格式输出
3. **远程日志**：支持发送到远程日志服务
4. **性能监控**：添加请求耗时等性能指标

---
**创建日期**：2026-03-19
**最后更新**：2026-03-19
**状态**：设计完成，通过两次审查，待用户批准