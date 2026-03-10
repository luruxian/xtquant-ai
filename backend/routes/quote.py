"""行情管理路由"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional, Dict, List, Any
import asyncio
import json
import logging

from schemas.quote import (
    QuoteSubscribeRequest, QuoteSubscribeResponse, QuoteDataResponse,
    QuoteUnsubscribeRequest, QuoteUnsubscribeResponse, QuoteCallbackData,
    QuoteSupportedPeriodsResponse, QuotePeriodInfo
)
from schemas.asset import ErrorResponse
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/quote",
    tags=["quote"],
    responses={404: {"model": ErrorResponse, "description": "行情或路径未找到"}}
)


# 全局订阅管理器
class QuoteSubscriptionManager:
    """行情订阅管理器"""

    def __init__(self):
        self.subscriptions: Dict[int, Dict[str, Any]] = {}
        self.next_subscription_id = 1
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.callback_handlers: Dict[int, Any] = {}
        self.main_event_loop = None  # 保存主事件循环

    def generate_subscription_id(self) -> int:
        """生成订阅ID"""
        subscription_id = self.next_subscription_id
        self.next_subscription_id += 1
        return subscription_id

    def add_subscription(self, subscription_data: Dict[str, Any]) -> int:
        """添加订阅"""
        subscription_id = self.generate_subscription_id()
        self.subscriptions[subscription_id] = subscription_data
        return subscription_id

    def remove_subscription(self, subscription_id: int) -> bool:
        """移除订阅"""
        if subscription_id in self.subscriptions:
            # 清理回调处理器
            if subscription_id in self.callback_handlers:
                del self.callback_handlers[subscription_id]
            del self.subscriptions[subscription_id]
            return True
        return False

    def get_subscription(self, subscription_id: int) -> Optional[Dict[str, Any]]:
        """获取订阅信息"""
        return self.subscriptions.get(subscription_id)

    def add_websocket_connection(self, client_id: str, websocket: WebSocket):
        """添加WebSocket连接"""
        self.websocket_connections[client_id] = websocket

    def remove_websocket_connection(self, client_id: str):
        """移除WebSocket连接"""
        if client_id in self.websocket_connections:
            del self.websocket_connections[client_id]

    def broadcast_to_websockets(self, data: Dict[str, Any]):
        """广播数据到所有WebSocket连接"""
        disconnected_clients = []

        for client_id, websocket in self.websocket_connections.items():
            try:
                # 使用保存的主事件循环
                if self.main_event_loop is None:
                    logger.error("主事件循环未设置，无法发送WebSocket消息")
                    continue

                asyncio.run_coroutine_threadsafe(
                    websocket.send_json(data),
                    self.main_event_loop
                )
            except Exception as e:
                logger.error(f"向客户端 {client_id} 发送数据失败: {e}")
                disconnected_clients.append(client_id)

        # 清理断开的连接
        for client_id in disconnected_clients:
            self.remove_websocket_connection(client_id)


# 全局订阅管理器实例
subscription_manager = QuoteSubscriptionManager()


@router.post("/subscribe", response_model=QuoteSubscribeResponse)
async def subscribe_quote(request: QuoteSubscribeRequest):
    """
    订阅单股行情

    - **stock_code**: 合约代码，如 '600000.SH'
    - **period**: 周期，默认 '1d'（日线），可选值：'1m', '5m', '15m', '30m', '1h', '1d', '1w', '1M'
    - **start_time**: 起始时间，格式 'YYYYMMDD' 或 'YYYYMMDDHHMMSS'
    - **end_time**: 结束时间，格式 'YYYYMMDD' 或 'YYYYMMDDHHMMSS'
    - **count**: 数据个数，0表示不请求历史数据

    返回订阅号，订阅成功返回大于0，失败返回-1
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        # 导入xtquant相关模块
        from xtquant import xtdata

        # 创建QMT服务实例
        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        # 定义回调函数
        def quote_callback(datas):
            """行情数据回调函数"""
            try:
                import time
                for stock_code in datas:
                    data_list = datas[stock_code]
                    if data_list:
                        # 将数据转换为可序列化的格式
                        for data in data_list:
                            # 这里可以根据实际的数据结构进行调整
                            quote_data = {
                                "stock_code": stock_code,
                                "period": request.period,
                                "data": data,
                                "timestamp": time.time()  # 使用time.time()而不是asyncio的事件循环
                            }

                            # 广播到WebSocket连接
                            subscription_manager.broadcast_to_websockets({
                                "type": "quote_data",
                                "data": quote_data
                            })

                            logger.debug(f"收到行情数据: {stock_code}, 数据长度: {len(data_list)}")
            except Exception as e:
                logger.error(f"行情回调处理失败: {e}")

        # 调用xtdata的订阅接口
        # 注意：xtdata.subscribe_quote的具体参数需要根据xtquant的实际API调整
        subscription_id = xtdata.subscribe_quote(
            stock_code=request.stock_code,
            period=request.period,
            start_time=request.start_time,
            end_time=request.end_time,
            count=request.count,
            callback=quote_callback
        )

        if subscription_id == -1:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message="订阅行情失败"
                ).dict()
            )

        # 保存订阅信息
        subscription_data = {
            "stock_code": request.stock_code,
            "period": request.period,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "count": request.count,
            "subscription_id": subscription_id,
            "callback": quote_callback
        }

        # 使用我们自己的订阅管理器生成ID（用于API管理）
        api_subscription_id = subscription_manager.add_subscription(subscription_data)

        # 保存回调处理器引用
        subscription_manager.callback_handlers[api_subscription_id] = quote_callback

        # 设置主事件循环（如果还没有设置）
        if subscription_manager.main_event_loop is None:
            subscription_manager.main_event_loop = asyncio.get_event_loop()

        logger.info(f"订阅行情成功: stock_code={request.stock_code}, period={request.period}, "
                   f"subscription_id={subscription_id}, api_subscription_id={api_subscription_id}")

        return QuoteSubscribeResponse(
            subscription_id=api_subscription_id,
            message="订阅成功",
            stock_code=request.stock_code,
            period=request.period
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"导入xtquant模块失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MODULE_IMPORT_ERROR",
                message=f"导入xtquant模块失败: {str(e)}"
            ).dict()
        )
    except Exception as e:
        logger.error(f"订阅行情失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )


@router.post("/unsubscribe", response_model=QuoteUnsubscribeResponse)
async def unsubscribe_quote(request: QuoteUnsubscribeRequest):
    """
    取消订阅行情

    - **subscription_id**: 订阅号
    """
    try:
        # 获取订阅信息
        subscription_data = subscription_manager.get_subscription(request.subscription_id)
        if not subscription_data:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="SUBSCRIPTION_NOT_FOUND",
                    message=f"订阅号 {request.subscription_id} 不存在"
                ).dict()
            )

        # 导入xtquant相关模块
        from xtquant import xtdata

        # 调用xtdata的取消订阅接口
        xtdata_subscription_id = subscription_data.get("subscription_id")
        if xtdata_subscription_id:
            # 这里需要根据xtquant的实际API调用取消订阅
            # xtdata.unsubscribe_quote(xtdata_subscription_id)
            pass

        # 从订阅管理器中移除
        success = subscription_manager.remove_subscription(request.subscription_id)

        if success:
            logger.info(f"取消订阅成功: subscription_id={request.subscription_id}")
            return QuoteUnsubscribeResponse(
                subscription_id=request.subscription_id,
                message="取消订阅成功",
                success=True
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="UNSUBSCRIBE_FAILED",
                    message="取消订阅失败"
                ).dict()
            )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"导入xtquant模块失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MODULE_IMPORT_ERROR",
                message=f"导入xtquant模块失败: {str(e)}"
            ).dict()
        )
    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )


@router.get("/supported-periods", response_model=QuoteSupportedPeriodsResponse)
async def get_supported_periods():
    """
    获取支持的行情周期

    返回系统支持的所有行情周期
    """
    periods = [
        QuotePeriodInfo(period="tick", description="分笔成交", supported=True),
        QuotePeriodInfo(period="1m", description="1分钟", supported=True),
        QuotePeriodInfo(period="5m", description="5分钟", supported=True),
        QuotePeriodInfo(period="15m", description="15分钟", supported=True),
        QuotePeriodInfo(period="30m", description="30分钟", supported=True),
        QuotePeriodInfo(period="60m", description="60分钟", supported=True),
        QuotePeriodInfo(period="1d", description="日线", supported=True),
        QuotePeriodInfo(period="1w", description="周线", supported=True),
        QuotePeriodInfo(period="1M", description="月线", supported=True),
    ]

    return QuoteSupportedPeriodsResponse(periods=periods)


@router.get("/subscriptions")
async def get_active_subscriptions():
    """
    获取当前活跃的订阅

    返回所有活跃的行情订阅信息
    """
    subscriptions = []
    for sub_id, sub_data in subscription_manager.subscriptions.items():
        subscriptions.append({
            "subscription_id": sub_id,
            "stock_code": sub_data.get("stock_code"),
            "period": sub_data.get("period"),
            "start_time": sub_data.get("start_time"),
            "end_time": sub_data.get("end_time"),
            "count": sub_data.get("count")
        })

    return {
        "total": len(subscriptions),
        "subscriptions": subscriptions
    }


@router.websocket("/ws/{client_id}")
async def quote_websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket端点，用于实时接收行情数据

    - **client_id**: 客户端ID，用于标识连接
    """
    await websocket.accept()
    subscription_manager.add_websocket_connection(client_id, websocket)

    logger.info(f"WebSocket连接建立: client_id={client_id}")

    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "message": "WebSocket连接已建立"
        })

        # 保持连接活跃
        while True:
            # 接收客户端消息（心跳或控制消息）
            try:
                data = await websocket.receive_json(timeout=30.0)

                # 处理客户端消息
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                elif data.get("type") == "subscribe":
                    # 客户端可以通过WebSocket订阅特定股票
                    # 这里可以扩展功能
                    pass

            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": asyncio.get_event_loop().time()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: client_id={client_id}")
    except Exception as e:
        logger.error(f"WebSocket连接错误: client_id={client_id}, error={e}")
    finally:
        subscription_manager.remove_websocket_connection(client_id)


@router.get("/test/{stock_code}")
async def test_quote(stock_code: str, period: str = "1d", count: int = 10, fields: str = ""):
    """
    测试获取行情数据（不订阅）

    - **stock_code**: 合约代码，格式如 '600000.SH'
    - **period**: 周期，默认 '1d'，可选：tick, 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1mon, 1q, 1hy, 1y
    - **count**: 数据个数，默认 10
    - **fields**: 返回字段列表，逗号分隔，为空则返回全部字段
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        # 导入xtquant相关模块
        from xtquant import xtdata

        # 解析字段列表
        field_list = []
        if fields:
            field_list = [f.strip() for f in fields.split(',') if f.strip()]

        # 根据API文档，对于数据获取接口，需要先确保MiniQmt已有所需数据
        # 如果本地没有数据，先调用download_history_data补充数据
        # 下载历史行情数据，增量下载
        xtdata.download_history_data(
            stock_code=stock_code,
            period=period,
            start_time='',
            end_time='',
            incrementally=True
        )

        # 使用get_market_data从缓存获取行情数据
        # 根据API文档，get_market_data是从缓存获取行情数据的主动接口
        data_dict = xtdata.get_market_data(
            field_list=field_list,
            stock_list=[stock_code],
            period=period,
            start_time='',
            end_time='',
            count=count,
            dividend_type='none',
            fill_data=True
        )

        # 处理返回数据
        # 根据period不同，返回格式不同
        # K线周期(1m, 5m, 1d等)返回dict { field1 : pd.DataFrame, ... }
        # tick分笔周期返回dict { stock1 : np.ndarray, ... }
        
        result_data = []
        
        if period == 'tick':
            # tick分笔数据
            if stock_code in data_dict:
                tick_data = data_dict[stock_code]
                # tick数据是np.ndarray，按时间戳升序排列
                for item in tick_data:
                    result_data.append(dict(item))
        else:
            # K线数据
            # data_dict格式: { field1 : pd.DataFrame, field2 : pd.DataFrame, ... }
            # DataFrame的index为stock_list，columns为time_list
            if field_list:
                # 有指定字段
                for field in field_list:
                    if field in data_dict:
                        df = data_dict[field]
                        if stock_code in df.index:
                            series = df.loc[stock_code]
                            # 将每列数据转换为字典列表
                            for time_idx in series.index:
                                record = {
                                    "time": str(time_idx),
                                    "stock_code": stock_code,
                                    "period": period
                                }
                                for f in field_list:
                                    if f in data_dict and stock_code in data_dict[f].index:
                                        record[f] = data_dict[f].loc[stock_code, time_idx]
                                result_data.append(record)
            else:
                # 返回全部字段
                for field, df in data_dict.items():
                    if stock_code in df.index:
                        series = df.loc[stock_code]
                        for time_idx in series.index:
                            record = {
                                "time": str(time_idx),
                                "stock_code": stock_code,
                                "period": period
                            }
                            for f, f_df in data_dict.items():
                                if stock_code in f_df.index:
                                    record[f] = f_df.loc[stock_code, time_idx]
                            result_data.append(record)

        return QuoteDataResponse(
            stock_code=stock_code,
            period=period,
            data=result_data
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"导入xtquant模块失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MODULE_IMPORT_ERROR",
                message=f"导入xtquant模块失败: {str(e)}"
            ).dict()
        )
    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )