"""服务层 - 包含业务逻辑"""
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from typing import Optional


class QMTService:
    """QMT 服务类"""
    
    def __init__(self, qmt_path: str, session_id: int):
        """
        初始化 QMT 服务
        
        :param qmt_path: QMT 客户端路径
        :param session_id: 会话 ID
        """
        self.qmt_path = qmt_path
        self.session_id = session_id
        self.trader: Optional[XtQuantTrader] = None
    
    def create_trader(self) -> XtQuantTrader:
        """
        创建 XtQuantTrader 实例
        
        :return: XtQuantTrader 实例
        """
        self.trader = XtQuantTrader(self.qmt_path, self.session_id)
        self.trader.register_callback(XtQuantTraderCallback())
        return self.trader
    
    def start(self, trader: XtQuantTrader) -> None:
        """
        启动交易客户端
        
        :param trader: XtQuantTrader 实例
        """
        trader.start()
    
    def connect(self, trader: XtQuantTrader) -> int:
        """
        连接 QMT
        
        :param trader: XtQuantTrader 实例
        :return: 连接结果，0 表示成功
        """
        return trader.connect()
    
    def subscribe(self, trader: XtQuantTrader, account: StockAccount) -> int:
        """
        订阅交易回调
        
        :param trader: XtQuantTrader 实例
        :param account: 账号对象
        :return: 订阅结果，0 表示成功
        """
        return trader.subscribe(account)
    
    def disconnect(self, trader: XtQuantTrader) -> None:
        """
        断开连接
        
        :param trader: XtQuantTrader 实例
        """
        if trader:
            trader.stop()
