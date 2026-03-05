"""服务层 - 包含业务逻辑（优化版，使用全局单例）"""
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from typing import Optional, Callable, Any
from .trader_singleton import get_trader_singleton, initialize_trader
import logging

logger = logging.getLogger(__name__)


class QMTService:
    """QMT 服务类（优化版，使用全局单例）"""

    def __init__(self, qmt_path: str, session_id: int):
        """
        初始化 QMT 服务

        :param qmt_path: QMT 客户端路径
        :param session_id: 会话 ID
        """
        self.qmt_path = qmt_path
        self.session_id = session_id
        self.trader: Optional[XtQuantTrader] = None
        self._singleton = get_trader_singleton()

        # 初始化全局单例（如果尚未初始化）
        if not self._singleton.is_initialized():
            logger.info(f"初始化全局交易实例: qmt_path={qmt_path}, session_id={session_id}")
            if not initialize_trader(qmt_path, session_id):
                logger.error("全局交易实例初始化失败")

    # ==================== 新接口：使用全局单例 ====================

    def get_shared_trader(self) -> Optional[XtQuantTrader]:
        """
        获取全局共享的XtQuantTrader实例

        :return: XtQuantTrader实例，如果未初始化则返回None
        """
        trader = self._singleton.get_trader()
        if trader:
            self.trader = trader  # 更新本地引用以保持兼容性
        return trader

    def ensure_account_subscribed(self, account_id: str) -> bool:
        """
        确保账户已订阅（如果未订阅则订阅）

        :param account_id: 资金账号
        :return: 订阅是否成功
        """
        return self._singleton.subscribe_account(account_id)

    def query_with_account(self, account_id: str, query_func: Callable, *args, **kwargs) -> Any:
        """
        通用查询方法（带账户订阅）

        :param account_id: 资金账号
        :param query_func: 查询函数，格式为 func(trader, account, *args, **kwargs)
        :return: 查询结果
        """
        # 获取全局交易实例
        trader = self.get_shared_trader()
        if not trader:
            raise Exception("获取全局交易实例失败")

        # 确保账户已订阅
        if not self.ensure_account_subscribed(account_id):
            raise Exception(f"订阅账户失败: {account_id}")

        # 创建账户对象
        account = StockAccount(account_id)

        # 执行查询
        try:
            return query_func(trader, account, *args, **kwargs)
        except Exception as e:
            logger.error(f"查询失败，account_id={account_id}, 错误: {e}")
            raise

    def batch_query_accounts(self, account_ids: list, query_func: Callable, *args, **kwargs) -> dict:
        """
        批量查询多个账户

        :param account_ids: 资金账号列表
        :param query_func: 查询函数，格式为 func(trader, account, *args, **kwargs)
        :return: 字典，key为account_id，value为查询结果或错误信息
        """
        results = {}

        # 先批量订阅所有账户
        subscription_results = self._singleton.batch_subscribe_accounts(account_ids)

        # 获取全局交易实例
        trader = self.get_shared_trader()
        if not trader:
            for account_id in account_ids:
                results[account_id] = {"error": "获取全局交易实例失败"}
            return results

        # 逐个执行查询
        for account_id in account_ids:
            try:
                # 检查订阅状态
                if not subscription_results.get(account_id, False):
                    results[account_id] = {"error": "订阅账户失败"}
                    continue

                # 创建账户对象并执行查询
                account = StockAccount(account_id)
                result = query_func(trader, account, *args, **kwargs)
                results[account_id] = result

            except Exception as e:
                logger.error(f"批量查询失败，account_id={account_id}, 错误: {e}")
                results[account_id] = {"error": str(e)}

        return results

    # ==================== 兼容性接口：保持原有API不变 ====================

    def create_trader(self) -> XtQuantTrader:
        """
        创建 XtQuantTrader 实例（兼容性方法）

        注意：实际上返回全局共享实例，避免重复创建

        :return: XtQuantTrader 实例
        """
        trader = self.get_shared_trader()
        if not trader:
            raise Exception("创建交易实例失败：全局实例未初始化")
        return trader

    def start(self, trader: XtQuantTrader) -> None:
        """
        启动交易客户端（兼容性方法）

        注意：全局实例已启动，此方法为空实现

        :param trader: XtQuantTrader 实例
        """
        pass  # 全局实例已启动

    def connect(self, trader: XtQuantTrader) -> int:
        """
        连接 QMT（兼容性方法）

        注意：全局实例已连接，此方法始终返回成功

        :param trader: XtQuantTrader 实例
        :return: 连接结果，0 表示成功
        """
        return 0  # 全局实例已连接

    def subscribe(self, trader: XtQuantTrader, account: StockAccount) -> int:
        """
        订阅交易回调（兼容性方法）

        :param trader: XtQuantTrader 实例
        :param account: 账号对象
        :return: 订阅结果，0 表示成功
        """
        if self.ensure_account_subscribed(account.account_id):
            return 0
        return -1

    def disconnect(self, trader: XtQuantTrader) -> None:
        """
        断开连接（兼容性方法）

        注意：全局实例不断开连接，此方法为空实现

        :param trader: XtQuantTrader 实例
        """
        pass  # 全局实例不断开连接

    # ==================== 工具方法 ====================

    def get_status(self) -> dict:
        """
        获取服务状态

        :return: 状态字典
        """
        return {
            "qmt_path": self.qmt_path,
            "session_id": self.session_id,
            "singleton_initialized": self._singleton.is_initialized(),
            "singleton_status": self._singleton.get_status()
        }

    def is_account_subscribed(self, account_id: str) -> bool:
        """
        检查账户是否已订阅

        :param account_id: 资金账号
        :return: 是否已订阅
        """
        return self._singleton.is_account_subscribed(account_id)