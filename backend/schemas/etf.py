"""ETF申赎清单相关的数据模型"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ETFComponent(BaseModel):
    """ETF成分股信息"""
    stock_code: str  # 股票代码
    stock_name: str  # 股票名称
    quantity: int  # 数量
    cash_substitute: Optional[float] = None  # 现金替代金额
    premium_rate: Optional[float] = None  # 溢价率
    discount_rate: Optional[float] = None  # 折价率
    market_value: Optional[float] = None  # 市值


class ETFInfo(BaseModel):
    """ETF申赎清单信息"""
    etf_code: str  # ETF代码
    etf_name: str  # ETF名称
    creation_unit: int  # 最小申赎单位（份）
    cash_component: float  # 现金差额
    estimated_cash: float  # 预估现金
    total_value: float  # 一篮子股票总市值
    nav: float  # 基金净值
    iopv: float  # 参考单位净值
    creation_fee: Optional[float] = None  # 申购费用
    redemption_fee: Optional[float] = None  # 赎回费用
    trading_day: str  # 交易日，格式：YYYYMMDD
    update_time: datetime  # 更新时间
    components: List[ETFComponent]  # 成分股列表
    status: str  # 状态：正常、暂停申购、暂停赎回、暂停申赎


class ETFDownloadRequest(BaseModel):
    """ETF信息下载请求模型"""
    etf_codes: Optional[List[str]] = None  # 指定ETF代码列表，为空则下载所有
    force_refresh: bool = False  # 是否强制刷新


class ETFDownloadResponse(BaseModel):
    """ETF信息下载响应模型"""
    success: bool
    message: str
    downloaded_count: int
    failed_codes: List[str] = []
    timestamp: datetime = datetime.now()


class ETFInfoResponse(BaseModel):
    """ETF信息响应模型"""
    etf_code: str
    etf_name: str
    creation_unit: int
    cash_component: float
    estimated_cash: float
    total_value: float
    nav: float
    iopv: float
    creation_fee: Optional[float] = None
    redemption_fee: Optional[float] = None
    trading_day: str
    update_time: datetime
    status: str
    component_count: int


class ETFDetailResponse(BaseModel):
    """ETF详细信息响应模型"""
    etf_info: ETFInfoResponse
    components: List[ETFComponent]


class ETFListResponse(BaseModel):
    """ETF列表响应模型"""
    total: int
    etfs: List[ETFInfoResponse]


class ETFQueryRequest(BaseModel):
    """ETF查询请求模型"""
    etf_codes: Optional[List[str]] = None  # 指定ETF代码列表，为空则查询所有
    status_filter: Optional[str] = None  # 状态过滤：normal, suspend_creation, suspend_redemption, suspend_all
    min_creation_unit: Optional[int] = None  # 最小申赎单位过滤
    exchange: Optional[str] = None  # 交易所过滤：SH, SZ


class ETFComponentRequest(BaseModel):
    """ETF成分股查询请求模型"""
    etf_code: str
    stock_codes: Optional[List[str]] = None  # 指定成分股代码，为空则返回所有


class ETFMarketData(BaseModel):
    """ETF市场数据"""
    etf_code: str
    timestamp: datetime
    last_price: float  # 最新价
    bid_price: float  # 买一价
    ask_price: float  # 卖一价
    volume: int  # 成交量
    amount: float  # 成交额
    bid_volume: int  # 买一量
    ask_volume: int  # 卖一量
    open_interest: Optional[int] = None  # 持仓量（期权）
    implied_volatility: Optional[float] = None  # 隐含波动率（期权）


class ETFPremiumDiscount(BaseModel):
    """ETF溢价折价信息"""
    etf_code: str
    timestamp: datetime
    market_price: float  # 市场价格
    iopv: float  # 参考净值
    premium_rate: float  # 溢价率 = (市价 - IOPV) / IOPV * 100%
    discount_rate: float  # 折价率 = (IOPV - 市价) / IOPV * 100%
    arbitrage_opportunity: bool  # 是否存在套利机会


class ETFArbitrageSignal(BaseModel):
    """ETF套利信号"""
    etf_code: str
    signal_type: str  # creation_arbitrage, redemption_arbitrage
    timestamp: datetime
    expected_return: float  # 预期收益率
    risk_level: str  # 风险等级：low, medium, high
    components: List[Dict[str, Any]]  # 相关成分股信息
    market_conditions: Dict[str, Any]  # 市场条件


class ETFErrorResponse(BaseModel):
    """ETF错误响应模型"""
    error: str
    message: str
    etf_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None