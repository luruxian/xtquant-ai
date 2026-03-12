"""WebSocket功能测试脚本"""
import asyncio
import websockets
import json
import time


async def test_websocket_client():
    """测试WebSocket客户端"""
    client_id = "test_account_123"
    uri = f"ws://localhost:8000/ws/{client_id}"

    print(f"连接WebSocket服务器: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket连接成功!")

            # 发送测试消息
            test_message = {"type": "test", "message": "Hello from client"}
            await websocket.send(json.dumps(test_message))
            print(f"发送消息: {test_message}")

            # 接收服务器响应
            response = await websocket.recv()
            print(f"收到服务器响应: {response}")

            # 等待接收推送消息
            print("等待接收推送消息...")
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    print(f"收到推送消息: {data}")

                    if data.get("type") == "order_result":
                        order_data = data.get("data", {})
                        if order_data.get("success"):
                            print(f"✅ 订单成功: 订单号 {order_data.get('order_id')}")
                        else:
                            print(f"❌ 订单失败: {order_data.get('message')}")

                    elif data.get("type") == "cancel_result":
                        cancel_data = data.get("data", {})
                        if cancel_data.get("success"):
                            print(f"✅ 撤单成功: 订单号 {cancel_data.get('order_id')}")
                        else:
                            print(f"❌ 撤单失败: {cancel_data.get('message')}")

            except asyncio.TimeoutError:
                print("等待超时，未收到推送消息")

    except Exception as e:
        print(f"连接失败: {e}")


async def test_order_api():
    """测试订单API（模拟下单）"""
    import requests
    import random

    # 模拟下单请求
    order_data = {
        "account": "test_account_123",
        "stock_code": "600000.SH",
        "order_type": 23,  # 买入
        "order_volume": 100,
        "price_type": 0,  # 限价
        "price": 10.5,
        "strategy_name": "test_strategy",
        "order_remark": "websocket_test"
    }

    print(f"模拟下单请求: {order_data}")

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/order/stock",
            json=order_data,
            timeout=10
        )
        print(f"API响应: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"API调用失败: {e}")


async def main():
    """主测试函数"""
    print("=== WebSocket功能测试 ===")

    # 启动WebSocket客户端
    websocket_task = asyncio.create_task(test_websocket_client())

    # 等待连接建立
    await asyncio.sleep(2)

    # 测试订单API
    await test_order_api()

    # 等待WebSocket客户端完成
    await websocket_task


if __name__ == "__main__":
    asyncio.run(main())