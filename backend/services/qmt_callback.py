"""
QMT交易回调处理器

实现XTQuantTraderCallback的所有回调方法，将回调数据记录到系统日志。
按照官方示例风格实现简单日志回调。
"""
from xtquant.xttrader import XtQuantTraderCallback
import logging
import datetime

logger = logging.getLogger(__name__)


class QMTCallback(XtQuantTraderCallback):
    """QMT交易回调处理器"""

    def __init__(self):
        """初始化回调处理器"""
        super().__init__()
        logger.info("QMTCallback初始化完成")

    def on_disconnected(self):
        """
        连接断开回调

        当交易连接断开时调用
        """
        try:
            logger.warning(f"{datetime.datetime.now()} 连接断开回调")
        except Exception as e:
            logger.error(f"处理连接断开回调时出错: {e}")

    def on_stock_order(self, order):
        """
        委托回报推送

        :param order: XtOrder对象
        """
        try:
            logger.info(f"{datetime.datetime.now()} 委托回调 投资备注 {order.order_remark}")
        except Exception as e:
            logger.error(f"处理委托回调时出错: {e}")

    def on_stock_trade(self, trade):
        """
        成交变动推送

        :param trade: XtTrade对象
        """
        try:
            logger.info(f"{datetime.datetime.now()} 成交回调 {trade.order_remark}")
        except Exception as e:
            logger.error(f"处理成交回调时出错: {e}")

    def on_order_error(self, order_error):
        """
        委托失败推送

        :param order_error: XtOrderError对象
        """
        try:
            logger.error(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")
        except Exception as e:
            logger.error(f"处理委托错误回调时出错: {e}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送

        :param cancel_error: XtCancelError对象
        """
        try:
            logger.error(f"{datetime.datetime.now()} on_cancel_error")
        except Exception as e:
            logger.error(f"处理撤单错误回调时出错: {e}")

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送

        :param response: XtOrderResponse对象
        """
        try:
            logger.info(f"异步委托回调 投资备注: {response.order_remark}")
        except Exception as e:
            logger.error(f"处理异步委托回调时出错: {e}")

    def on_cancel_order_stock_async_response(self, response):
        """
        异步撤单回报推送

        :param response: XtCancelOrderResponse对象
        """
        try:
            logger.info(f"{datetime.datetime.now()} on_cancel_order_stock_async_response")
        except Exception as e:
            logger.error(f"处理异步撤单回调时出错: {e}")

    def on_account_status(self, status):
        """
        账户状态推送

        :param status: XtAccountStatus对象
        """
        try:
            logger.info(f"{datetime.datetime.now()} on_account_status")
        except Exception as e:
            logger.error(f"处理账户状态回调时出错: {e}")