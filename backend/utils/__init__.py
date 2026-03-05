"""工具模块 - 包含通用工具函数"""
import os
from typing import Optional


def get_qmt_path() -> str:
    """
    获取 QMT 客户端路径
    
    :return: QMT 客户端 userdata_mini 路径
    """
    return os.environ.get('QMT_PATH', 'D:\\迅投极速交易终端 睿智融科版\\userdata_mini')


def get_session_id() -> int:
    """
    获取会话 ID
    
    :return: 会话 ID，默认为 123456
    """
    return int(os.environ.get('SESSION_ID', '123456'))


def validate_qmt_path(path: str) -> bool:
    """
    验证 QMT 路径是否存在
    
    :param path: QMT 客户端路径
    :return: 路径是否存在
    """
    return os.path.exists(path)
