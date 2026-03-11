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