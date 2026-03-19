"""日志配置模块"""
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logging() -> bool:
    """设置模块化日志配置，返回是否成功

    支持的环境变量：
    - LOG_DIR: 日志目录路径（默认：backend/logs）
    - LOG_LEVEL: 日志级别（默认：INFO）
    - LOG_CONSOLE: 是否输出到控制台（默认：true）
    - LOG_BACKUP_COUNT: 日志文件保留天数（默认：30）
    - LOG_MAX_BYTES: WebSocket日志最大字节数（默认：10MB）
    """
    try:
        # 从环境变量获取配置
        import os
        log_dir_env = os.getenv("LOG_DIR", "backend/logs")
        log_level_env = os.getenv("LOG_LEVEL", "INFO")
        console_output = os.getenv("LOG_CONSOLE", "true").lower() == "true"
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "30"))
        max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB

        # 创建日志目录
        log_dir = Path(log_dir_env)
        log_dir.mkdir(parents=True, exist_ok=True)

        # 构建处理器列表
        handlers = {}

        # 控制台处理器（可选）
        if console_output:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "level": log_level_env,
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            }

        # 文件处理器
        handlers["app_file"] = {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": log_level_env,
            "formatter": "standard",
            "filename": str(log_dir / "app.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": backup_count,
            "encoding": "utf-8"
        }

        handlers["websocket_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level_env,
            "formatter": "detailed",
            "filename": str(log_dir / "websocket.log"),
            "maxBytes": max_bytes,
            "backupCount": 10,
            "encoding": "utf-8"
        }

        handlers["error_file"] = {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": str(log_dir / "error.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": backup_count,
            "encoding": "utf-8"
        }

        # 构建日志器处理器列表
        app_handlers = ["app_file"]
        if console_output:
            app_handlers.append("console")

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
            "handlers": handlers,
            "loggers": {
                "app": {
                    "level": log_level_env,
                    "handlers": app_handlers,
                    "propagate": False
                },
                "app.websocket": {
                    "level": log_level_env,
                    "handlers": ["websocket_file"],
                    "propagate": False
                },
                "app.trade": {
                    "level": log_level_env,
                    "handlers": ["app_file"],
                    "propagate": False
                },
                "app.quote": {
                    "level": log_level_env,
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
                "handlers": ["console"] if console_output else []
            }
        }

        # 应用配置
        logging.config.dictConfig(config)

        # 记录初始化成功
        init_logger = logging.getLogger(__name__)
        init_logger.info("日志系统初始化成功")
        return True

    except Exception as e:
        # 回退到基础日志配置
        try:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            logging.error(f"日志系统配置失败，使用基础配置: {e}")
        except Exception as fallback_error:
            # 最终回退：静默失败，至少应用能启动
            print(f"严重：日志系统完全失败: {fallback_error}")

        return False


def get_logger(name: str) -> logging.Logger:
    """获取配置好的日志器"""
    return logging.getLogger(name)