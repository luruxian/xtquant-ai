"""WebSocket消息模型"""
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class WebSocketMessage(BaseModel):
    """WebSocket消息基础模型"""
    type: str  # 消息类型: order_result, cancel_result, error
    timestamp: str
    data: dict


class OrderResultMessage(BaseModel):
    """订单结果消息"""
    order_id: int
    account: str
    stock_code: str
    order_type: int
    order_volume: int
    price_type: int
    price: float
    success: bool
    message: str
    timestamp: str


class CancelResultMessage(BaseModel):
    """撤单结果消息"""
    order_id: int
    account: str
    result: int
    success: bool
    message: str
    timestamp: str


class ErrorMessage(BaseModel):
    """错误消息"""
    error: str
    message: str
    timestamp: str