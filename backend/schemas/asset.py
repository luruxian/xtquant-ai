from pydantic import BaseModel
from typing import Optional, List


class AssetResponse(BaseModel):
    """资产响应模型"""
    account_type: int
    account_id: str
    cash: float
    frozen_cash: float
    market_value: float
    total_asset: float


class AssetDetailResponse(BaseModel):
    """资产详情响应模型"""
    account_type: int
    account_id: str
    cash: float
    frozen_cash: float
    market_value: float
    total_asset: float


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    message: str


class BatchAssetResponse(BaseModel):
    """批量资产响应模型"""
    results: List[dict]


class OrderResponse(BaseModel):
    """订单响应模型"""
    account_type: int
    account_id: str
    stock_code: str
    order_id: int
    order_sysid: str
    order_time: int
    order_type: int
    order_volume: int
    price_type: int
    price: float
    traded_volume: int
    traded_price: float
    order_status: int
    status_msg: str
    strategy_name: str
    order_remark: str
    direction: int
    offset_flag: int


class TradeResponse(BaseModel):
    """成交响应模型"""
    account_type: int
    account_id: str
    stock_code: str
    order_type: int
    traded_id: str
    traded_time: int
    traded_price: float
    traded_volume: int
    traded_amount: float
    order_id: int
    order_sysid: str
    strategy_name: str
    order_remark: str
    direction: int
    offset_flag: int


class PositionResponse(BaseModel):
    """持仓响应模型"""
    account_type: int
    account_id: str
    stock_code: str
    volume: int
    can_use_volume: int
    open_price: float
    market_value: float
    frozen_volume: int
    on_road_volume: int
    yesterday_volume: int
    avg_price: float
    direction: int


class PositionStatisticsResponse(BaseModel):
    """期货持仓统计响应模型"""
    account_id: str
    exchange_id: str
    exchange_name: str
    product_id: str
    instrument_id: str
    instrument_name: str
    direction: int
    hedge_flag: int
    position: int
    yesterday_position: int
    today_position: int
    can_close_vol: int
    position_cost: float
    avg_price: float
    position_profit: float
    float_profit: float
    open_price: float
    open_cost: float
    used_margin: float
    used_commission: float
    frozen_margin: float
    frozen_commission: float
    instrument_value: float
    cancel_times: int
    last_price: float
    rise_ratio: float
    product_name: str
    royalty: float
    expire_date: str


class OrderRequest(BaseModel):
    """下单请求模型"""
    account_id: str
    stock_code: str
    order_type: int
    volume: int
    price_type: int
    price: float
    strategy_name: Optional[str] = ""
    remark: Optional[str] = ""


class CancelOrderRequest(BaseModel):
    """撤单请求模型"""
    account_id: str
    order_id: int


class QueryOrdersRequest(BaseModel):
    """查询订单请求模型"""
    account_id: str
    order_type: Optional[int] = None


class QueryPositionsRequest(BaseModel):
    """查询持仓请求模型"""
    account_id: str


class QueryTradesRequest(BaseModel):
    """查询成交请求模型"""
    account_id: str


class AccountInfoResponse(BaseModel):
    """账户信息响应模型"""
    account_id: str
    account_type: int


class AsyncOrderResponse(BaseModel):
    """异步报单响应模型"""
    seq: int
    message: str
    account_id: str
    stock_code: str
    order_type: int
    order_volume: int
    price_type: int
    price: float
    strategy_name: str
    order_remark: str


class AsyncCancelOrderRequest(BaseModel):
    """异步撤单请求模型"""
    account_id: str
    order_id: int


class AsyncCancelOrderResponse(BaseModel):
    """异步撤单响应模型"""
    cancel_seq: int
    message: str
    account_id: str
    order_id: int


class StockOrderRequest(BaseModel):
    """股票同步报单请求模型"""
    account: str
    stock_code: str
    order_type: int
    order_volume: int
    price_type: int
    price: float
    strategy_name: str
    order_remark: str


class StockOrderResponse(BaseModel):
    """股票同步报单响应模型"""
    order_id: int
    message: str
