"""订单WebSocket路由"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import websocket_manager

router = APIRouter()


@router.websocket("/ws/order/{client_id}")
async def order_websocket_endpoint(websocket: WebSocket, client_id: str):
    """订单WebSocket连接端点

    Args:
        websocket: WebSocket连接对象
        client_id: 客户端ID，通常使用账户ID
    """
    # 连接到订单频道
    await websocket_manager.connect(websocket, client_id, channel="order")

    try:
        while True:
            # 接收客户端消息（心跳或控制消息）
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
                    }, client_id, channel="order")

                elif message_type == "subscribe":
                    # 订单WebSocket自动订阅，无需客户端显式订阅
                    await websocket_manager.send_personal_message({
                        "type": "subscription_confirmed",
                        "data": {
                            "channel": "order",
                            "message": "订单频道已自动订阅"
                        }
                    }, client_id, channel="order")

                else:
                    # 其他消息类型
                    await websocket_manager.send_personal_message({
                        "type": "error",
                        "data": {
                            "error": "UNSUPPORTED_MESSAGE_TYPE",
                            "message": f"不支持的消息类型: {message_type}"
                        }
                    }, client_id, channel="order")

            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket_manager.send_heartbeat(websocket, client_id, channel="order")

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, client_id)
        print(f"订单WebSocket连接断开: client_id={client_id}")
    except Exception as e:
        websocket_manager.disconnect(websocket, client_id)
        print(f"订单WebSocket连接错误: client_id={client_id}, error={e}")