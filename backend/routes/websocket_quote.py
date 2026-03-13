"""行情WebSocket路由"""
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import websocket_manager

router = APIRouter()

# 导入行情订阅管理器
from routes.quote import subscription_manager


@router.websocket("/ws/quote/{client_id}")
async def quote_websocket_endpoint(websocket: WebSocket, client_id: str):
    """行情WebSocket连接端点

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

                # 处理客户端消息
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
                    # 其他消息类型
                    await websocket_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "error": "UNSUPPORTED_MESSAGE_TYPE",
                            "message": f"不支持的消息类型: {message_type}"
                        }
                    }, client_id, channel="quote")

            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket_manager.send_heartbeat(websocket, client_id, channel="quote")

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, client_id)
        print(f"行情WebSocket连接断开: client_id={client_id}")
    except Exception as e:
        websocket_manager.disconnect(websocket, client_id)
        print(f"行情WebSocket连接错误: client_id={client_id}, error={e}")


async def _handle_quote_subscription(client_id: str, data: Dict[str, Any]):
    """处理行情订阅请求"""
    try:
        subscription_data = data.get("data", {})
        stock_code = subscription_data.get("stock_code")
        period = subscription_data.get("period", "1d")
        start_time = subscription_data.get("start_time", "")
        end_time = subscription_data.get("end_time", "")
        count = subscription_data.get("count", 0)

        if not stock_code:
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {
                    "error": "INVALID_SUBSCRIPTION",
                    "message": "缺少股票代码参数"
                }
            }, client_id, channel="quote")
            return

        # 导入必要的模块
        from schemas.quote import QuoteSubscribeRequest
        from routes.quote import subscribe_quote

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

            print(f"客户端 {client_id} 订阅了行情: stock_code={stock_code}, period={period}")
        except Exception as sub_error:
            await websocket_manager.send_personal_message({
                "type": "error",
                "data": {
                    "error": "SUBSCRIPTION_FAILED",
                    "message": f"订阅失败: {str(sub_error)}"
                }
            }, client_id, channel="quote")

    except Exception as e:
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {
                "error": "SUBSCRIPTION_FAILED",
                "message": f"订阅失败: {str(e)}"
            }
        }, client_id, channel="quote")


async def _handle_quote_unsubscription(client_id: str, data: Dict[str, Any]):
    """处理取消订阅请求"""
    try:
        subscription_data = data.get("data", {})
        subscription_id = subscription_data.get("subscription_id")

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

        print(f"客户端 {client_id} 取消了订阅: subscription_id={subscription_id}")

    except Exception as e:
        await websocket_manager.send_personal_message({
            "type": "error",
            "data": {
                "error": "UNSUBSCRIPTION_FAILED",
                "message": f"取消订阅失败: {str(e)}"
            }
        }, client_id, channel="quote")