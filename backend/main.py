"""主应用入口"""
from fastapi import FastAPI

# 尝试导入日志配置模块
try:
    from utils.logging_config import setup_logging
    # 初始化日志系统
    setup_logging()
    logging_initialized = True
except ImportError as e:
    # 如果utils模块不存在，尝试相对导入
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from utils.logging_config import setup_logging
        setup_logging()
        logging_initialized = True
    except ImportError:
        # 日志系统初始化失败，但应用仍可启动
        import logging
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"日志系统初始化失败: {e}，使用基础配置")
        logging_initialized = False

from routes import asset, order, position, trade, quote, etf, websocket_order, websocket_quote

app = FastAPI(
    title="MiniQMT AI Backend",
    description="后端 API 服务",
    version="1.0.0"
)

# 在应用启动时预初始化交易实例，确保xtquant信息在启动时显示
try:
    from utils.config import get_qmt_path, get_session_id
    from services.trader_singleton import get_trader_singleton

    qmt_path = get_qmt_path()
    session_id = get_session_id()

    singleton = get_trader_singleton()
    if not singleton.is_initialized():
        import logging
        logger = logging.getLogger("app")
        logger.info("应用启动时预初始化交易实例...")
        if singleton.initialize(qmt_path, session_id):
            logger.info("交易实例预初始化成功")
        else:
            logger.warning("交易实例预初始化失败，将在首次使用时初始化")
    else:
        import logging
        logger = logging.getLogger("app")
        logger.info("交易实例已初始化，跳过预初始化")

except Exception as e:
    import logging
    logger = logging.getLogger("app")
    logger.warning(f"交易实例预初始化异常: {e}，将在首次使用时初始化")


@app.get("/")
async def root():
    return {"message": "Welcome to MiniQMT AI Backend"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(asset.router)
app.include_router(order.router)
app.include_router(position.router)
app.include_router(trade.router)
app.include_router(quote.router)
# app.include_router(etf.router)  # 已注释掉所有 /api/v1/etf/ 接口
app.include_router(websocket_order.router)  # 订单WebSocket路由
app.include_router(websocket_quote.router)  # 行情WebSocket路由
