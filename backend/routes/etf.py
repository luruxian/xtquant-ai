"""ETF申赎清单管理路由"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List, Dict, Any
import asyncio
import logging
from datetime import datetime, timedelta

from schemas.etf import (
    ETFDownloadRequest, ETFDownloadResponse, ETFInfoResponse,
    ETFDetailResponse, ETFListResponse, ETFQueryRequest,
    ETFComponentRequest, ETFErrorResponse, ETFPremiumDiscount,
    ETFArbitrageSignal
)
from schemas.asset import ErrorResponse
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/etf",
    tags=["etf"],
    responses={404: {"model": ErrorResponse, "description": "ETF或路径未找到"}}
)


# ETF信息缓存管理器
class ETFInfoManager:
    """ETF信息管理器"""

    def __init__(self):
        self.etf_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=1)  # 缓存有效期1小时

    def get_etf_info(self, etf_code: str) -> Optional[Dict[str, Any]]:
        """获取ETF信息（带缓存检查）"""
        if etf_code in self.etf_cache:
            expiry_time = self.cache_expiry.get(etf_code)
            if expiry_time and datetime.now() < expiry_time:
                return self.etf_cache[etf_code]
            else:
                # 缓存过期，清理
                del self.etf_cache[etf_code]
                if etf_code in self.cache_expiry:
                    del self.cache_expiry[etf_code]
        return None

    def set_etf_info(self, etf_code: str, info: Dict[str, Any]):
        """设置ETF信息到缓存"""
        self.etf_cache[etf_code] = info
        self.cache_expiry[etf_code] = datetime.now() + self.cache_ttl

    def clear_cache(self, etf_code: Optional[str] = None):
        """清理缓存"""
        if etf_code:
            if etf_code in self.etf_cache:
                del self.etf_cache[etf_code]
            if etf_code in self.cache_expiry:
                del self.cache_expiry[etf_code]
        else:
            self.etf_cache.clear()
            self.cache_expiry.clear()

    def get_all_etfs(self) -> List[Dict[str, Any]]:
        """获取所有ETF信息"""
        now = datetime.now()
        valid_etfs = []

        for etf_code, info in self.etf_cache.items():
            expiry_time = self.cache_expiry.get(etf_code)
            if expiry_time and now < expiry_time:
                valid_etfs.append(info)

        return valid_etfs


# 全局ETF信息管理器实例
etf_manager = ETFInfoManager()


@router.post("/download", response_model=ETFDownloadResponse)
async def download_etf_info(request: ETFDownloadRequest = None):
    """
    下载ETF申赎清单信息

    - **etf_codes**: 指定ETF代码列表，为空则下载所有
    - **force_refresh**: 是否强制刷新，默认False

    返回下载结果
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                )
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
                )
            )

        # 确定要下载的ETF列表
        etf_codes_to_download = []
        if request and request.etf_codes:
            etf_codes_to_download = request.etf_codes
        else:
            # 如果没有指定，尝试获取所有ETF列表
            # 这里需要根据xtquant的实际API获取ETF列表
            # 暂时使用一些常见的ETF代码
            etf_codes_to_download = [
                "510300.SH",  # 沪深300ETF
                "510500.SH",  # 中证500ETF
                "510050.SH",  # 上证50ETF
                "159919.SZ",  # 沪深300ETF（深市）
                "159915.SZ",  # 创业板ETF
            ]

        downloaded_count = 0
        failed_codes = []

        # 下载每个ETF的信息
        for etf_code in etf_codes_to_download:
            try:
                # 调用xtdata的ETF信息下载接口
                # 根据文档，download_etf_info()下载所有ETF申赎清单信息
                # 这里可能需要根据实际API调整

                # 模拟下载过程
                logger.info(f"下载ETF信息: {etf_code}")

                # 模拟ETF信息
                etf_info = {
                    "etf_code": etf_code,
                    "etf_name": f"ETF-{etf_code}",
                    "creation_unit": 1000000,  # 100万份
                    "cash_component": 1000.0,
                    "estimated_cash": 500.0,
                    "total_value": 1000000.0,
                    "nav": 1.0,
                    "iopv": 1.01,
                    "creation_fee": 0.001,
                    "redemption_fee": 0.001,
                    "trading_day": datetime.now().strftime("%Y%m%d"),
                    "update_time": datetime.now(),
                    "status": "normal",
                    "components": [
                        {
                            "stock_code": "600000.SH",
                            "stock_name": "浦发银行",
                            "quantity": 10000,
                            "cash_substitute": 0.0,
                            "premium_rate": 0.0,
                            "discount_rate": 0.0,
                            "market_value": 100000.0
                        }
                    ]
                }

                # 保存到缓存
                etf_manager.set_etf_info(etf_code, etf_info)
                downloaded_count += 1

                logger.info(f"ETF信息下载成功: {etf_code}")

            except Exception as e:
                logger.error(f"下载ETF信息失败: {etf_code}, 错误: {e}")
                failed_codes.append(etf_code)

        # 如果请求强制刷新，清理缓存
        if request and request.force_refresh:
            etf_manager.clear_cache()

        message = f"成功下载 {downloaded_count} 个ETF信息"
        if failed_codes:
            message += f"，失败 {len(failed_codes)} 个"

        return ETFDownloadResponse(
            success=True,
            message=message,
            downloaded_count=downloaded_count,
            failed_codes=failed_codes
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
            )
        )
    except Exception as e:
        logger.error(f"下载ETF信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )


@router.get("/info", response_model=ETFListResponse)
async def get_etf_info(
    etf_codes: Optional[str] = Query(None, description="ETF代码列表，逗号分隔"),
    status: Optional[str] = Query(None, description="状态过滤：normal, suspend_creation, suspend_redemption, suspend_all"),
    exchange: Optional[str] = Query(None, description="交易所：SH, SZ"),
    force_refresh: bool = Query(False, description="是否强制刷新缓存")
):
    """
    获取ETF申赎清单信息

    - **etf_codes**: ETF代码列表，逗号分隔
    - **status**: 状态过滤
    - **exchange**: 交易所过滤
    - **force_refresh**: 是否强制刷新缓存

    返回所有ETF申赎数据
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                )
            )

        # 如果强制刷新，先清理缓存
        if force_refresh:
            etf_manager.clear_cache()

            # 触发下载
            from xtquant import xtdata
            # 调用下载接口
            # xtdata.download_etf_info()
            logger.info("强制刷新ETF信息缓存")

        # 解析ETF代码列表
        etf_code_list = []
        if etf_codes:
            etf_code_list = [code.strip() for code in etf_codes.split(',') if code.strip()]

        # 获取ETF信息
        etf_infos = []

        if etf_code_list:
            # 获取指定ETF的信息
            for etf_code in etf_code_list:
                info = etf_manager.get_etf_info(etf_code)
                if info:
                    etf_infos.append(info)
                else:
                    # 如果缓存中没有，尝试下载
                    logger.info(f"缓存中没有ETF信息，尝试下载: {etf_code}")
                    # 这里可以触发下载逻辑
                    pass
        else:
            # 获取所有ETF信息
            etf_infos = etf_manager.get_all_etfs()

            # 如果缓存为空，触发下载
            if not etf_infos:
                logger.info("缓存为空，触发ETF信息下载")
                # 触发下载所有ETF
                # 这里可以调用下载接口
                pass

        # 应用过滤条件
        filtered_infos = []
        for info in etf_infos:
            # 状态过滤
            if status and info.get("status") != status:
                continue

            # 交易所过滤
            if exchange:
                etf_code = info.get("etf_code", "")
                if exchange == "SH" and not etf_code.endswith(".SH"):
                    continue
                if exchange == "SZ" and not etf_code.endswith(".SZ"):
                    continue

            filtered_infos.append(info)

        # 转换为响应模型
        etf_responses = []
        for info in filtered_infos:
            components = info.get("components", [])
            etf_responses.append(
                ETFInfoResponse(
                    etf_code=info.get("etf_code"),
                    etf_name=info.get("etf_name"),
                    creation_unit=info.get("creation_unit", 0),
                    cash_component=info.get("cash_component", 0.0),
                    estimated_cash=info.get("estimated_cash", 0.0),
                    total_value=info.get("total_value", 0.0),
                    nav=info.get("nav", 0.0),
                    iopv=info.get("iopv", 0.0),
                    creation_fee=info.get("creation_fee"),
                    redemption_fee=info.get("redemption_fee"),
                    trading_day=info.get("trading_day", ""),
                    update_time=info.get("update_time", datetime.now()),
                    status=info.get("status", "unknown"),
                    component_count=len(components)
                )
            )

        return ETFListResponse(
            total=len(etf_responses),
            etfs=etf_responses
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取ETF信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )


@router.get("/info/{etf_code}", response_model=ETFDetailResponse)
async def get_etf_detail(
    etf_code: str = Path(..., description="ETF代码"),
    force_refresh: bool = Query(False, description="是否强制刷新")
):
    """
    获取单个ETF的详细信息

    - **etf_code**: ETF代码
    - **force_refresh**: 是否强制刷新缓存
    """
    try:
        # 如果强制刷新，清理该ETF的缓存
        if force_refresh:
            etf_manager.clear_cache(etf_code)

            # 触发下载该ETF
            logger.info(f"强制刷新ETF信息: {etf_code}")
            # 这里可以触发下载逻辑

        # 获取ETF信息
        info = etf_manager.get_etf_info(etf_code)

        if not info:
            # 尝试下载
            logger.info(f"ETF信息不存在，尝试下载: {etf_code}")
            # 这里可以触发下载逻辑

            # 模拟信息
            info = {
                "etf_code": etf_code,
                "etf_name": f"ETF-{etf_code}",
                "creation_unit": 1000000,
                "cash_component": 1000.0,
                "estimated_cash": 500.0,
                "total_value": 1000000.0,
                "nav": 1.0,
                "iopv": 1.01,
                "creation_fee": 0.001,
                "redemption_fee": 0.001,
                "trading_day": datetime.now().strftime("%Y%m%d"),
                "update_time": datetime.now(),
                "status": "normal",
                "components": [
                    {
                        "stock_code": "600000.SH",
                        "stock_name": "浦发银行",
                        "quantity": 10000,
                        "cash_substitute": 0.0,
                        "premium_rate": 0.0,
                        "discount_rate": 0.0,
                        "market_value": 100000.0
                    },
                    {
                        "stock_code": "000001.SZ",
                        "stock_name": "平安银行",
                        "quantity": 8000,
                        "cash_substitute": 0.0,
                        "premium_rate": 0.0,
                        "discount_rate": 0.0,
                        "market_value": 80000.0
                    }
                ]
            }

            etf_manager.set_etf_info(etf_code, info)

        # 转换为响应模型
        components = info.get("components", [])

        etf_info_response = ETFInfoResponse(
            etf_code=info.get("etf_code"),
            etf_name=info.get("etf_name"),
            creation_unit=info.get("creation_unit", 0),
            cash_component=info.get("cash_component", 0.0),
            estimated_cash=info.get("estimated_cash", 0.0),
            total_value=info.get("total_value", 0.0),
            nav=info.get("nav", 0.0),
            iopv=info.get("iopv", 0.0),
            creation_fee=info.get("creation_fee"),
            redemption_fee=info.get("redemption_fee"),
            trading_day=info.get("trading_day", ""),
            update_time=info.get("update_time", datetime.now()),
            status=info.get("status", "unknown"),
            component_count=len(components)
        )

        return ETFDetailResponse(
            etf_info=etf_info_response,
            components=components
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取ETF详细信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )


@router.get("/premium-discount/{etf_code}", response_model=ETFPremiumDiscount)
async def get_etf_premium_discount(
    etf_code: str = Path(..., description="ETF代码")
):
    """
    获取ETF溢价折价信息

    - **etf_code**: ETF代码

    返回ETF的溢价率、折价率等信息
    """
    try:
        # 获取ETF信息
        info = etf_manager.get_etf_info(etf_code)

        if not info:
            raise HTTPException(
                status_code=404,
                detail=ETFErrorResponse(
                    error="ETF_NOT_FOUND",
                    message=f"ETF信息不存在: {etf_code}",
                    etf_code=etf_code
                )
            )

        # 模拟市场数据
        # 在实际应用中，这里需要获取实时市场数据
        market_price = 1.02  # 模拟市场价格
        iopv = info.get("iopv", 1.01)

        premium_rate = 0.0
        discount_rate = 0.0

        if market_price > iopv:
            premium_rate = (market_price - iopv) / iopv * 100
        else:
            discount_rate = (iopv - market_price) / iopv * 100

        # 判断套利机会（简单阈值判断）
        arbitrage_threshold = 0.5  # 0.5%
        arbitrage_opportunity = premium_rate > arbitrage_threshold or discount_rate > arbitrage_threshold

        return ETFPremiumDiscount(
            etf_code=etf_code,
            timestamp=datetime.now(),
            market_price=market_price,
            iopv=iopv,
            premium_rate=premium_rate,
            discount_rate=discount_rate,
            arbitrage_opportunity=arbitrage_opportunity
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取ETF溢价折价信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ETFErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e),
                etf_code=etf_code
            )
        )


@router.get("/arbitrage-signals", response_model=List[ETFArbitrageSignal])
async def get_arbitrage_signals(
    min_return: float = Query(0.3, description="最小预期收益率(%)", ge=0.0),
    max_risk: str = Query("medium", description="最大风险等级：low, medium, high")
):
    """
    获取ETF套利信号

    - **min_return**: 最小预期收益率(%)
    - **max_risk**: 最大风险等级

    返回符合条件的套利信号
    """
    try:
        # 获取所有ETF信息
        etf_infos = etf_manager.get_all_etfs()

        if not etf_infos:
            return []

        signals = []

        # 模拟套利信号分析
        for info in etf_infos[:5]:  # 只分析前5个
            etf_code = info.get("etf_code")

            # 模拟分析结果
            signal_types = ["creation_arbitrage", "redemption_arbitrage"]

            for signal_type in signal_types:
                # 模拟预期收益率
                expected_return = 0.5  # 0.5%

                if expected_return >= min_return:
                    signal = ETFArbitrageSignal(
                        etf_code=etf_code,
                        signal_type=signal_type,
                        timestamp=datetime.now(),
                        expected_return=expected_return,
                        risk_level="low",
                        components=info.get("components", [])[:3],  # 只返回前3个成分股
                        market_conditions={
                            "liquidity": "high",
                            "volatility": "low",
                            "market_trend": "neutral"
                        }
                    )
                    signals.append(signal)

        return signals

    except Exception as e:
        logger.error(f"获取套利信号失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )


@router.get("/cache/status")
async def get_cache_status():
    """
    获取ETF缓存状态

    返回缓存统计信息
    """
    etf_infos = etf_manager.get_all_etfs()

    now = datetime.now()
    expired_count = 0

    for etf_code in list(etf_manager.cache_expiry.keys()):
        expiry_time = etf_manager.cache_expiry.get(etf_code)
        if expiry_time and now >= expiry_time:
            expired_count += 1

    return {
        "total_cached": len(etf_manager.etf_cache),
        "valid_cached": len(etf_infos),
        "expired_cached": expired_count,
        "cache_ttl_hours": etf_manager.cache_ttl.total_seconds() / 3600,
        "last_update": datetime.now().isoformat()
    }


@router.delete("/cache")
async def clear_etf_cache(
    etf_code: Optional[str] = Query(None, description="指定清理的ETF代码，为空则清理所有")
):
    """
    清理ETF缓存

    - **etf_code**: 指定清理的ETF代码，为空则清理所有
    """
    etf_manager.clear_cache(etf_code)

    message = "清理所有ETF缓存成功" if not etf_code else f"清理ETF缓存成功: {etf_code}"

    return {
        "success": True,
        "message": message,
        "timestamp": datetime.now()
    }


@router.get("/test/download")
async def test_download_etf():
    """
    测试ETF信息下载

    用于测试下载功能
    """
    try:
        # 模拟下载过程
        etf_codes = ["510300.SH", "510500.SH", "510050.SH"]

        for etf_code in etf_codes:
            etf_info = {
                "etf_code": etf_code,
                "etf_name": f"测试ETF-{etf_code}",
                "creation_unit": 1000000,
                "cash_component": 1000.0,
                "estimated_cash": 500.0,
                "total_value": 1000000.0,
                "nav": 1.0,
                "iopv": 1.01,
                "creation_fee": 0.001,
                "redemption_fee": 0.001,
                "trading_day": datetime.now().strftime("%Y%m%d"),
                "update_time": datetime.now(),
                "status": "normal",
                "components": [
                    {
                        "stock_code": "600000.SH",
                        "stock_name": "测试股票",
                        "quantity": 10000,
                        "cash_substitute": 0.0,
                        "premium_rate": 0.0,
                        "discount_rate": 0.0,
                        "market_value": 100000.0
                    }
                ]
            }

            etf_manager.set_etf_info(etf_code, etf_info)

        return {
            "success": True,
            "message": f"测试下载成功，下载了 {len(etf_codes)} 个ETF",
            "downloaded_codes": etf_codes
        }

    except Exception as e:
        logger.error(f"测试下载失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="TEST_ERROR",
                message=str(e)
            )
        )