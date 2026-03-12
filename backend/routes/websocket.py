"""WebSocket路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import websocket_manager
import uuid

router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点

    Args:
        websocket: WebSocket连接对象
        client_id: 客户端ID，可以使用账户ID或用户ID
    """
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接，等待客户端消息
            data = await websocket.receive_text()
            # 可以处理客户端发送的消息
            print(f"收到来自客户端 {client_id} 的消息: {data}")

            # 可以回复确认消息
            await websocket.send_text(f"收到消息: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, client_id)
        print(f"客户端 {client_id} 断开连接")
    except Exception as e:
        websocket_manager.disconnect(websocket, client_id)
        print(f"客户端 {client_id} 连接异常: {e}")