"""路由模块"""
from routes.asset import router as asset_router
from routes.order import router as order_router
from routes.position import router as position_router
from routes.trade import router as trade_router

__all__ = ['asset_router', 'order_router', 'position_router', 'trade_router']
