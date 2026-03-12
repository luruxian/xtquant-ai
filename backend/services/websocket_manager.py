"""WebSocket连接管理器"""
import json
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        """连接WebSocket"""
        await websocket.accept()
        async with self.lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = set()
            self.active_connections[client_id].add(websocket)
            print(f"客户端 {client_id} 已连接，当前连接数: {len(self.active_connections[client_id])}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
            print(f"客户端 {client_id} 已断开，剩余连接数: {len(self.active_connections.get(client_id, []))}")

    async def send_personal_message(self, message: dict, client_id: str):
        """向特定客户端发送消息"""
        if client_id in self.active_connections:
            message_json = json.dumps(message, ensure_ascii=False)
            connections = list(self.active_connections[client_id])
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                    print(f"消息已发送到客户端 {client_id}")
                except Exception as e:
                    print(f"发送消息到客户端 {client_id} 失败: {e}")
                    # 移除失效的连接
                    self.active_connections[client_id].discard(connection)
        else:
            print(f"客户端 {client_id} 未连接，无法发送消息")

    async def broadcast(self, message: dict):
        """广播消息到所有客户端"""
        message_json = json.dumps(message, ensure_ascii=False)
        for client_id, connections in list(self.active_connections.items()):
            for connection in list(connections):
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    print(f"广播消息到客户端 {client_id} 失败: {e}")
                    connections.discard(connection)
            if not connections:
                del self.active_connections[client_id]


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()