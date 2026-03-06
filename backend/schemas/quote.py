"""行情相关的数据模型"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime


class QuoteSubscribeRequest(BaseModel):
    """订阅行情请求模型"""
    stock_code: str
    period: str = "1d"  # 周期，默认日线
    start_time: str = ""  # 起始时间
    end_time: str = ""  # 结束时间
    count: int = 0  # 数据个数
    # callback参数在Web API中不直接传递，而是通过WebSocket或其他方式处理


class QuoteSubscribeResponse(BaseModel):
    """订阅行情响应模型"""
    subscription_id: int  # 订阅号
    message: str
    stock_code: str
    period: str


class QuoteData(BaseModel):
    """行情数据模型"""
    # 基础字段
    time: int  # 时间戳
    open: float  # 开盘价
    high: float  # 最高价
    low: float  # 最低价
    close: float  # 收盘价
    volume: float  # 成交量
    amount: float  # 成交额

    # 扩展字段
    pre_close: Optional[float] = None  # 前收盘价
    change: Optional[float] = None  # 涨跌额
    change_rate: Optional[float] = None  # 涨跌幅
    turnover_rate: Optional[float] = None  # 换手率
    pe_ratio: Optional[float] = None  # 市盈率
    pb_ratio: Optional[float] = None  # 市净率
    market_value: Optional[float] = None  # 市值

    # 买卖盘信息
    bid_price: Optional[List[float]] = None  # 买盘价格
    bid_volume: Optional[List[float]] = None  # 买盘数量
    ask_price: Optional[List[float]] = None  # 卖盘价格
    ask_volume: Optional[List[float]] = None  # 卖盘数量


class QuoteDataResponse(BaseModel):
    """行情数据响应模型"""
    stock_code: str
    period: str
    data: List[QuoteData]


class QuoteUnsubscribeRequest(BaseModel):
    """取消订阅请求模型"""
    subscription_id: int


class QuoteUnsubscribeResponse(BaseModel):
    """取消订阅响应模型"""
    subscription_id: int
    message: str
    success: bool


class QuoteCallbackData(BaseModel):
    """行情回调数据模型（用于WebSocket推送）"""
    subscription_id: int
    stock_code: str
    period: str
    data: QuoteData
    timestamp: datetime = datetime.now()


class QuotePeriodInfo(BaseModel):
    """行情周期信息"""
    period: str
    description: str
    supported: bool


class QuoteSupportedPeriodsResponse(BaseModel):
    """支持的行情周期响应"""
    periods: List[QuotePeriodInfo]