"""WebSocket连接管理器"""
import json
import asyncio
from typing import Dict, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_channels: Dict[str, Set[str]] = {}  # 客户端ID -> 订阅的频道集合
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str, channel: Optional[str] = None):
        """连接WebSocket

        Args:
            websocket: WebSocket连接对象
            client_id: 客户端ID
            channel: 频道名称（order或quote）
        """
        await websocket.accept()
        async with self.lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = set()
            self.active_connections[client_id].add(websocket)

            # 记录频道信息
            if channel:
                if client_id not in self.connection_channels:
                    self.connection_channels[client_id] = set()
                self.connection_channels[client_id].add(channel)

            print(f"客户端 {client_id} 已连接，频道: {channel}, 当前连接数: {len(self.active_connections[client_id])}")

            # 发送连接确认消息
            await self._send_connection_confirmation(websocket, client_id, channel)

    def disconnect(self, websocket: WebSocket, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
                # 清理频道信息
                if client_id in self.connection_channels:
                    del self.connection_channels[client_id]
            print(f"客户端 {client_id} 已断开，剩余连接数: {len(self.active_connections.get(client_id, []))}")

    def _create_standard_message(self, message_type: str, data: dict, channel: Optional[str] = None,
                                client_id: Optional[str] = None) -> dict:
        """创建标准化消息格式

        Args:
            message_type: 消息类型
            data: 消息数据
            channel: 频道名称
            client_id: 客户端ID

        Returns:
            标准化消息字典
        """
        return {
            "type": message_type,
            "channel": channel,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id
        }

    async def send_personal_message(self, message: dict, client_id: str, channel: Optional[str] = None):
        """向特定客户端发送消息

        Args:
            message: 消息字典，可以是原始消息或标准化消息
            client_id: 客户端ID
            channel: 频道名称（可选）
        """
        if client_id in self.active_connections:
            # 如果消息不是标准化格式，转换为标准化格式
            if "timestamp" not in message or "channel" not in message:
                message_type = message.get("type", "data")
                message_data = message.get("data", message)
                standard_message = self._create_standard_message(
                    message_type=message_type,
                    data=message_data,
                    channel=channel,
                    client_id=client_id
                )
            else:
                standard_message = message

            message_json = json.dumps(standard_message, ensure_ascii=False)
            connections = list(self.active_connections[client_id])
            for connection in connections:
                try:
                    await connection.send_text(message_json)
                    msg_type = standard_message.get('type')
                    print(f"消息已发送到客户端 {client_id}, 频道: {channel}, 类型: {msg_type}")

                    # 如果是错误消息，记录更多信息
                    if msg_type == "error":
                        error_data = standard_message.get('data', {})
                        error_code = error_data.get('error', 'UNKNOWN_ERROR')
                        error_msg = error_data.get('message', '未知错误')
                        print(f"错误详情 - 错误码: {error_code}, 错误信息: {error_msg}")
                except Exception as e:
                    print(f"发送消息到客户端 {client_id} 失败: {e}")
                    # 移除失效的连接
                    self.active_connections[client_id].discard(connection)
        else:
            print(f"客户端 {client_id} 未连接，无法发送消息")

    async def broadcast(self, message: dict, channel: Optional[str] = None):
        """广播消息到所有客户端

        Args:
            message: 消息字典
            channel: 频道名称，如果指定则只发送给订阅了该频道的客户端
        """
        # 如果消息不是标准化格式，转换为标准化格式
        if "timestamp" not in message or "channel" not in message:
            message_type = message.get("type", "data")
            message_data = message.get("data", message)
            standard_message = self._create_standard_message(
                message_type=message_type,
                data=message_data,
                channel=channel,
                client_id=None
            )
        else:
            standard_message = message

        message_json = json.dumps(standard_message, ensure_ascii=False)

        for client_id, connections in list(self.active_connections.items()):
            # 检查频道过滤
            if channel and client_id in self.connection_channels:
                if channel not in self.connection_channels[client_id]:
                    continue

            for connection in list(connections):
                try:
                    await connection.send_text(message_json)
                    msg_type = standard_message.get('type')
                    # 如果是错误消息或重要消息，记录日志
                    if msg_type in ["error", "quote_data", "order_result"]:
                        print(f"广播消息到客户端 {client_id}, 频道: {channel}, 类型: {msg_type}")
                except Exception as e:
                    print(f"广播消息到客户端 {client_id} 失败: {e}")
                    connections.discard(connection)

            if not connections:
                del self.active_connections[client_id]
                if client_id in self.connection_channels:
                    del self.connection_channels[client_id]

    async def _send_connection_confirmation(self, websocket: WebSocket, client_id: str, channel: Optional[str] = None):
        """发送连接确认消息"""
        confirmation_message = self._create_standard_message(
            message_type="connection_established",
            data={
                "client_id": client_id,
                "channel": channel,
                "message": "WebSocket连接已建立"
            },
            channel=channel,
            client_id=client_id
        )
        await websocket.send_json(confirmation_message)

    async def send_heartbeat(self, websocket: WebSocket, client_id: str, channel: Optional[str] = None):
        """发送心跳消息"""
        heartbeat_message = self._create_standard_message(
            message_type="heartbeat",
            data={"timestamp": datetime.now().isoformat()},
            channel=channel,
            client_id=client_id
        )
        await websocket.send_json(heartbeat_message)

    def subscribe_channel(self, client_id: str, channel: str):
        """客户端订阅频道"""
        if client_id not in self.connection_channels:
            self.connection_channels[client_id] = set()
        self.connection_channels[client_id].add(channel)
        print(f"客户端 {client_id} 订阅了频道: {channel}")

    def unsubscribe_channel(self, client_id: str, channel: str):
        """客户端取消订阅频道"""
        if client_id in self.connection_channels:
            self.connection_channels[client_id].discard(channel)
            if not self.connection_channels[client_id]:
                del self.connection_channels[client_id]
            print(f"客户端 {client_id} 取消订阅了频道: {channel}")


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()