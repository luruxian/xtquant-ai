"""路由模块"""
from routes.asset import router as asset_router
from routes.order import router as order_router
from routes.position import router as position_router
from routes.trade import router as trade_router
from routes.quote import router as quote_router

__all__ = ['asset_router', 'order_router', 'position_router', 'trade_router', 'quote_router']
