"""行情WebSocket路由"""
import json
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import websocket_manager

# 导入行情订阅管理器
from routes.quote import subscription_manager
from schemas.quote import QuoteSubscribeRequest
from routes.quote import subscribe_quote

router = APIRouter()

# WebSocket专用日志器
logger = logging.getLogger("app.websocket")


@router.websocket("/ws/quote/{client_id}")
async def quote_websocket_endpoint(websocket: WebSocket, client_id: str):
    """行情WebSocket连接端点

    客户端接入参数要求：
    1. 消息类型限制：客户端发送的消息类型只能是以下三种之一：
       - "ping": 心跳消息，用于保持连接
       - "subscribe": 订阅行情消息
       - "unsubscribe": 取消订阅消息

    2. 订阅请求格式：当消息类型为"subscribe"时，必须包含以下字段：
       {
         "type": "subscribe",
         "data": {
           "stock_code": "股票代码，如'600000.SH'",  # 必填字段
           "period": "周期，默认'1d'，可选值：'1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M'",
           "start_time": "起始时间，格式'YYYYMMDD'或'YYYYMMDDHHMMSS'",
           "end_time": "结束时间，格式'YYYYMMDD'或'YYYYMMDDHHMMSS'",
           "count": "数据个数，0表示不请求历史数据"
         }
       }

    3. 取消订阅请求格式：当消息类型为"unsubscribe"时，必须包含以下字段：
       {
         "type": "unsubscribe",
         "data": {
           "subscription_id": "订阅ID"  # 必填字段
         }
       }

    Args:
        websocket: WebSocket连接对象
        client_id: 客户端ID
    """
    # 连接到行情频道
    await websocket_manager.connect(websocket, client_id, channel="quote")

    try:
        while True:
            # 接收客户端消息
            try:
                # 使用 asyncio.wait_for 实现超时
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                # 记录客户端发送的原始消息
                logger.info(f"收到客户端 {client_id} 的原始消息: {data}")

                # 处理客户端消息
                # 注意：客户端消息类型只能是 "ping"、"subscribe" 或 "unsubscribe"
                message_type = data.get("type")

                if message_type == "ping":
                    # 响应心跳
                    await websocket_manager.send_personal_message({
                        "type": "pong",
                        "data": {"timestamp": asyncio.get_event_loop().time()}
                    }, client_id, channel="quote")

                elif message_type == "subscribe":
                    # 处理行情订阅请求
                    await _handle_quote_subscription(client_id, data)

                elif message_type == "unsubscribe":
                    # 处理取消订阅请求
                    await _handle_quote_unsubscription(client_id, data)

                else:
                    # 其他消息类型 - 客户端消息类型只能是 "ping"、"subscribe" 或 "unsubscribe"
                    error_msg = f"不支持的消息类型: {message_type}"
                    logger.warning(f"客户端 {client_id} 发送了不支持的消息类型: {message_type}, 完整消息: {data}")
                    await websocket_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "error": "UNSUPPORTED_MESSAGE_TYPE",
                            "message": error_msg
                        }
                    }, client_id, channel="quote")

            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket_manager.send_heartbeat(websocket, client_id, channel="quote")

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, client_id)
        logger.info(f"行情WebSocket连接断开: client_id={client_id}")
    except Exception as e:
        websocket_manager.disconnect(websocket, client_id)
        logger.error(f"行情WebSocket连接错误: client_id={client_id}, error={e}")


async def _handle_quote_subscription(client_id: str, data: Dict[str, Any]):
    """处理行情订阅请求

    订阅请求必须包含以下字段：
    - stock_code: 股票代码（必填），如 '600000.SH'
    - period: 周期（可选，默认'1d'）
    - start_time: 起始时间（可选）
    - end_time: 结束时间（可选）
    - count: 数据个数（可选，默认0）
    """
    try:
        subscription_data = data.get("data", {})
        stock_code = subscription_data.get("stock_code")  # 必填字段
        period = subscription_data.get("period", "1d")
        start_time = subscription_data.get("start_time", "")
        end_time = subscription_data.get("end_time", "")
        count = subscription_data.get("count", 0)

        # 检查必填字段：股票代码
        if not stock_code:
            error_msg = "缺少股票代码参数"
            logger.warning(f"客户端 {client_id} 订阅请求缺少股票代码参数，订阅数据: {subscription_data}")
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {
                    "error": "INVALID_SUBSCRIPTION",
                    "message": error_msg
                }
            }, client_id, channel="quote")
            return

        # 创建订阅请求对象
        request = QuoteSubscribeRequest(
            stock_code=stock_code,
            period=period,
            start_time=start_time,
            end_time=end_time,
            count=count
        )

        # 调用quote.py中的订阅逻辑
        try:
            response = await subscribe_quote(request)
            
            # 记录客户端订阅了行情频道
            websocket_manager.subscribe_channel(client_id, "quote")

            await websocket_manager.send_personal_message({
                "type": "subscription_confirmed",
                "data": {
                    "subscription_id": response.subscription_id,
                    "stock_code": stock_code,
                    "period": period,
                    "message": "行情订阅成功"
                }
            }, client_id, channel="quote")

            logger.info(f"客户端 {client_id} 订阅了行情: stock_code={stock_code}, period={period}")
        except Exception as sub_error:
            error_msg = f"订阅失败: {str(sub_error)}"
            logger.error(f"客户端 {client_id} 订阅行情失败: stock_code={stock_code}, period={period}, 错误: {sub_error}")
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {
                    "error": "SUBSCRIPTION_FAILED",
                    "message": error_msg
                }
            }, client_id, channel="quote")

    except Exception as e:
        error_msg = f"订阅失败: {str(e)}"
        logger.error(f"客户端 {client_id} 处理订阅请求时发生异常: {e}")
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {
                "error": "SUBSCRIPTION_FAILED",
                "message": error_msg
            }
        }, client_id, channel="quote")


async def _handle_quote_unsubscription(client_id: str, data: Dict[str, Any]):
    """处理取消订阅请求

    取消订阅请求必须包含以下字段：
    - subscription_id: 订阅ID（必填）
    """
    try:
        subscription_data = data.get("data", {})
        subscription_id = subscription_data.get("subscription_id")  # 必填字段

        # 检查必填字段：订阅ID
        if not subscription_id:
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {
                    "error": "INVALID_UNSUBSCRIPTION",
                    "message": "缺少订阅ID参数"
                }
            }, client_id, channel="quote")
            return

        # 这里需要调用quote.py中的取消订阅逻辑
        # 实际集成时需要调用quote.py的unsubscribe_quote函数

        # 模拟取消订阅成功
        websocket_manager.unsubscribe_channel(client_id, "quote")

        await websocket_manager.send_personal_message({
            "type": "unsubscription_confirmed",
            "data": {
                "subscription_id": subscription_id,
                "message": "取消订阅成功"
            }
        }, client_id, channel="quote")

        logger.info(f"客户端 {client_id} 取消了订阅: subscription_id={subscription_id}")

    except Exception as e:
        error_msg = f"取消订阅失败: {str(e)}"
        logger.error(f"客户端 {client_id} 取消订阅失败: subscription_id={subscription_id}, 错误: {e}")
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {
                "error": "UNSUBSCRIPTION_FAILED",
                "message": error_msg
            }
        }, client_id, channel="quote")