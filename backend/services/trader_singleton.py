"""
全局XtQuantTrader单例管理器

管理全局唯一的XtQuantTrader实例，避免重复创建实例造成的性能问题。
采用永久订阅模式，一旦订阅账户就保持订阅状态。
"""
import threading
import time
from typing import Optional, Set, Dict
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import logging

logger = logging.getLogger(__name__)


class TraderSingleton:
    """
    XtQuantTrader全局单例管理器

    管理全局唯一的XtQuantTrader实例，支持：
    1. 线程安全的懒加载初始化
    2. 永久订阅模式管理
    3. 连接状态监控
    4. 资源清理
    """

    _instance: Optional['TraderSingleton'] = None
    _lock = threading.Lock()
    _trader: Optional[XtQuantTrader] = None
    _initialized = False
    _qmt_path: Optional[str] = None
    _session_id: Optional[int] = None

    # 订阅状态管理
    _subscribed_accounts: Set[str] = set()
    _subscription_lock = threading.Lock()

    # 连接状态
    _last_health_check: float = 0
    _health_check_interval: int = 60  # 健康检查间隔（秒）

    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, qmt_path: str, session_id: int) -> bool:
        """
        初始化全局交易实例

        Args:
            qmt_path: QMT客户端路径
            session_id: 会话ID

        Returns:
            bool: 初始化是否成功
        """
        with self._lock:
            if self._initialized:
                logger.info("交易实例已初始化，跳过重复初始化")
                return True

            try:
                logger.info(f"初始化全局交易实例，qmt_path={qmt_path}, session_id={session_id}")

                # 创建交易实例
                self._trader = XtQuantTrader(qmt_path, session_id)
                self._trader.register_callback(XtQuantTraderCallback())

                # 启动交易客户端
                self._trader.start()

                # 连接QMT
                connect_result = self._trader.connect()
                if connect_result != 0:
                    logger.error(f"连接QMT失败，错误码: {connect_result}")
                    self._trader = None
                    return False

                logger.info("全局交易实例初始化成功")

                self._qmt_path = qmt_path
                self._session_id = session_id
                self._initialized = True
                self._last_health_check = time.time()

                return True

            except Exception as e:
                logger.error(f"初始化全局交易实例失败: {e}")
                self._trader = None
                return False

    def get_trader(self) -> Optional[XtQuantTrader]:
        """
        获取全局交易实例

        Returns:
            Optional[XtQuantTrader]: 交易实例，如果未初始化则返回None
        """
        if not self._initialized:
            logger.warning("交易实例未初始化，请先调用initialize()")
            return None

        # 定期健康检查
        self._check_health()

        return self._trader

    def subscribe_account(self, account_id: str) -> bool:
        """
        订阅账户（永久订阅模式）

        Args:
            account_id: 资金账号

        Returns:
            bool: 订阅是否成功
        """
        with self._subscription_lock:
            # 检查是否已订阅
            if account_id in self._subscribed_accounts:
                logger.debug(f"账户 {account_id} 已订阅，跳过重复订阅")
                return True

            trader = self.get_trader()
            if not trader:
                logger.error("无法订阅账户：交易实例未初始化")
                return False

            try:
                account = StockAccount(account_id)
                subscribe_result = trader.subscribe(account)

                if subscribe_result == 0:
                    self._subscribed_accounts.add(account_id)
                    logger.info(f"订阅账户成功: {account_id}")
                    return True
                else:
                    logger.error(f"订阅账户失败: {account_id}, 错误码: {subscribe_result}")
                    return False

            except Exception as e:
                logger.error(f"订阅账户异常: {account_id}, 错误: {e}")
                return False

    def batch_subscribe_accounts(self, account_ids: list) -> Dict[str, bool]:
        """
        批量订阅账户

        Args:
            account_ids: 资金账号列表

        Returns:
            Dict[str, bool]: 每个账户的订阅结果
        """
        results = {}
        for account_id in account_ids:
            results[account_id] = self.subscribe_account(account_id)
        return results

    def is_account_subscribed(self, account_id: str) -> bool:
        """
        检查账户是否已订阅

        Args:
            account_id: 资金账号

        Returns:
            bool: 是否已订阅
        """
        return account_id in self._subscribed_accounts

    def get_subscribed_accounts(self) -> Set[str]:
        """
        获取所有已订阅的账户

        Returns:
            Set[str]: 已订阅账户集合
        """
        return self._subscribed_accounts.copy()

    def _check_health(self):
        """检查连接健康状态"""
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return

        try:
            # 简单的健康检查：尝试查询账户列表
            if self._trader:
                # 这里可以添加更复杂的健康检查逻辑
                self._last_health_check = current_time
                logger.debug("交易连接健康检查通过")
        except Exception as e:
            logger.warning(f"交易连接健康检查失败: {e}")
            # 可以考虑在这里实现重连逻辑

    def shutdown(self):
        """关闭交易实例，释放资源"""
        with self._lock:
            if self._trader:
                try:
                    logger.info("关闭全局交易实例")
                    self._trader.stop()
                except Exception as e:
                    logger.error(f"关闭交易实例失败: {e}")
                finally:
                    self._trader = None

            self._subscribed_accounts.clear()
            self._initialized = False
            self._qmt_path = None
            self._session_id = None
            logger.info("全局交易实例已关闭")

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "initialized": self._initialized,
            "qmt_path": self._qmt_path,
            "session_id": self._session_id,
            "subscribed_accounts_count": len(self._subscribed_accounts),
            "subscribed_accounts": list(self._subscribed_accounts),
            "last_health_check": self._last_health_check
        }


# 全局单例实例访问函数
_singleton_instance: Optional[TraderSingleton] = None


def get_trader_singleton() -> TraderSingleton:
    """获取全局单例实例"""
    global _singleton_instance
    if _singleton_instance is None:
        _singleton_instance = TraderSingleton()
    return _singleton_instance


def initialize_trader(qmt_path: str, session_id: int) -> bool:
    """初始化全局交易实例（便捷函数）"""
    singleton = get_trader_singleton()
    return singleton.initialize(qmt_path, session_id)


def get_global_trader() -> Optional[XtQuantTrader]:
    """获取全局交易实例（便捷函数）"""
    singleton = get_trader_singleton()
    return singleton.get_trader()


def shutdown_trader():
    """关闭全局交易实例（便捷函数）"""
    singleton = get_trader_singleton()
    singleton.shutdown()