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

        from xtquant import xtdata

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

        etf_codes_to_download = []
        if request and request.etf_codes:
            etf_codes_to_download = request.etf_codes
        else:
            try:
                all_etf_info = xtdata.get_etf_info()
                if all_etf_info:
                    etf_codes_to_download = list(all_etf_info.keys())
                else:
                    etf_codes_to_download = [
                        "510300.SH", "510500.SH", "510050.SH",
                        "159919.SZ", "159915.SZ"
                    ]
            except Exception:
                etf_codes_to_download = [
                    "510300.SH", "510500.SH", "510050.SH",
                    "159919.SZ", "159915.SZ"
                ]

        downloaded_count = 0
        failed_codes = []

        for etf_code in etf_codes_to_download:
            try:
                logger.info(f"下载ETF信息: {etf_code}")

                xtdata.download_etf_info([etf_code])

                etf_data = xtdata.get_etf_info(etf_code)

                if etf_data:
                    etf_info = {
                        "etf_code": etf_code,
                        "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                        "creation_unit": etf_data.get("creation_unit", 1000000),
                        "cash_component": etf_data.get("cash_component", 0.0),
                        "estimated_cash": etf_data.get("estimated_cash", 0.0),
                        "total_value": etf_data.get("total_value", 0.0),
                        "nav": etf_data.get("nav", 0.0),
                        "iopv": etf_data.get("iopv", 0.0),
                        "creation_fee": etf_data.get("creation_fee", 0.001),
                        "redemption_fee": etf_data.get("redemption_fee", 0.001),
                        "trading_day": etf_data.get("trading_day", ""),
                        "update_time": etf_data.get("update_time", datetime.now()),
                        "status": etf_data.get("status", "normal"),
                        "components": []
                    }

                    components_data = etf_data.get("components", [])
                    for comp in components_data:
                        component = {
                            "stock_code": comp.get("stock_code", ""),
                            "stock_name": comp.get("stock_name", ""),
                            "quantity": comp.get("quantity", 0),
                            "cash_substitute": comp.get("cash_substitute", 0.0),
                            "premium_rate": comp.get("premium_rate", 0.0),
                            "discount_rate": comp.get("discount_rate", 0.0),
                            "market_value": comp.get("market_value", 0.0)
                        }
                        etf_info["components"].append(component)

                    etf_manager.set_etf_info(etf_code, etf_info)
                    downloaded_count += 1

                    logger.info(f"ETF信息下载成功: {etf_code}")
                else:
                    failed_codes.append(etf_code)
                    logger.warning(f"ETF信息为空: {etf_code}")

            except Exception as e:
                logger.error(f"下载ETF信息失败: {etf_code}, 错误: {e}")
                failed_codes.append(etf_code)

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

        if force_refresh:
            etf_manager.clear_cache()

            from xtquant import xtdata

            try:
                all_etf_info = xtdata.get_etf_info()
                if all_etf_info:
                    for etf_code in all_etf_info.keys():
                        try:
                            xtdata.download_etf_info([etf_code])
                        except Exception:
                            pass
                logger.info("强制刷新ETF信息缓存")
            except Exception as e:
                logger.error(f"强制刷新ETF信息失败: {e}")

        etf_code_list = []
        if etf_codes:
            etf_code_list = [code.strip() for code in etf_codes.split(',') if code.strip()]

        etf_infos = []

        if etf_code_list:
            for etf_code in etf_code_list:
                info = etf_manager.get_etf_info(etf_code)
                if info:
                    etf_infos.append(info)
                else:
                    try:
                        from xtquant import xtdata

                        xtdata.download_etf_info([etf_code])
                        etf_data = xtdata.get_etf_info(etf_code)

                        if etf_data:
                            etf_info = {
                                "etf_code": etf_code,
                                "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                                "creation_unit": etf_data.get("creation_unit", 1000000),
                                "cash_component": etf_data.get("cash_component", 0.0),
                                "estimated_cash": etf_data.get("estimated_cash", 0.0),
                                "total_value": etf_data.get("total_value", 0.0),
                                "nav": etf_data.get("nav", 0.0),
                                "iopv": etf_data.get("iopv", 0.0),
                                "creation_fee": etf_data.get("creation_fee", 0.001),
                                "redemption_fee": etf_data.get("redemption_fee", 0.001),
                                "trading_day": etf_data.get("trading_day", ""),
                                "update_time": etf_data.get("update_time", datetime.now()),
                                "status": etf_data.get("status", "normal"),
                                "components": []
                            }

                            components_data = etf_data.get("components", [])
                            for comp in components_data:
                                component = {
                                    "stock_code": comp.get("stock_code", ""),
                                    "stock_name": comp.get("stock_name", ""),
                                    "quantity": comp.get("quantity", 0),
                                    "cash_substitute": comp.get("cash_substitute", 0.0),
                                    "premium_rate": comp.get("premium_rate", 0.0),
                                    "discount_rate": comp.get("discount_rate", 0.0),
                                    "market_value": comp.get("market_value", 0.0)
                                }
                                etf_info["components"].append(component)

                            etf_manager.set_etf_info(etf_code, etf_info)
                            etf_infos.append(etf_info)

                            logger.info(f"缓存中没有ETF信息，已下载: {etf_code}")
                    except Exception as e:
                        logger.error(f"下载ETF信息失败: {etf_code}, 错误: {e}")
        else:
            etf_infos = etf_manager.get_all_etfs()

            if not etf_infos:
                try:
                    from xtquant import xtdata

                    all_etf_info = xtdata.get_etf_info()
                    if all_etf_info:
                        for etf_code in all_etf_info.keys():
                            try:
                                xtdata.download_etf_info([etf_code])
                                etf_data = xtdata.get_etf_info(etf_code)

                                if etf_data:
                                    etf_info = {
                                        "etf_code": etf_code,
                                        "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                                        "creation_unit": etf_data.get("creation_unit", 1000000),
                                        "cash_component": etf_data.get("cash_component", 0.0),
                                        "estimated_cash": etf_data.get("estimated_cash", 0.0),
                                        "total_value": etf_data.get("total_value", 0.0),
                                        "nav": etf_data.get("nav", 0.0),
                                        "iopv": etf_data.get("iopv", 0.0),
                                        "creation_fee": etf_data.get("creation_fee", 0.001),
                                        "redemption_fee": etf_data.get("redemption_fee", 0.001),
                                        "trading_day": etf_data.get("trading_day", ""),
                                        "update_time": etf_data.get("update_time", datetime.now()),
                                        "status": etf_data.get("status", "normal"),
                                        "components": []
                                    }

                                    components_data = etf_data.get("components", [])
                                    for comp in components_data:
                                        component = {
                                            "stock_code": comp.get("stock_code", ""),
                                            "stock_name": comp.get("stock_name", ""),
                                            "quantity": comp.get("quantity", 0),
                                            "cash_substitute": comp.get("cash_substitute", 0.0),
                                            "premium_rate": comp.get("premium_rate", 0.0),
                                            "discount_rate": comp.get("discount_rate", 0.0),
                                            "market_value": comp.get("market_value", 0.0)
                                        }
                                        etf_info["components"].append(component)

                                    etf_manager.set_etf_info(etf_code, etf_info)
                                    etf_infos.append(etf_info)
                            except Exception as e:
                                logger.error(f"下载ETF信息失败: {etf_code}, 错误: {e}")

                        logger.info("缓存为空，已触发ETF信息下载")
                except Exception as e:
                    logger.error(f"获取所有ETF信息失败: {e}")

        filtered_infos = []
        for info in etf_infos:
            if status and info.get("status") != status:
                continue

            if exchange:
                etf_code = info.get("etf_code", "")
                if exchange == "SH" and not etf_code.endswith(".SH"):
                    continue
                if exchange == "SZ" and not etf_code.endswith(".SZ"):
                    continue

            filtered_infos.append(info)

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
        if force_refresh:
            etf_manager.clear_cache(etf_code)

            try:
                from xtquant import xtdata

                xtdata.download_etf_info([etf_code])
                logger.info(f"强制刷新ETF信息: {etf_code}")
            except Exception as e:
                logger.error(f"强制刷新ETF信息失败: {etf_code}, 错误: {e}")

        info = etf_manager.get_etf_info(etf_code)

        if not info:
            try:
                from xtquant import xtdata

                xtdata.download_etf_info([etf_code])
                etf_data = xtdata.get_etf_info(etf_code)

                logger.info(f"ETF信息不存在，已下载: {etf_code}")

                if etf_data:
                    info = {
                        "etf_code": etf_code,
                        "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                        "creation_unit": etf_data.get("creation_unit", 1000000),
                        "cash_component": etf_data.get("cash_component", 0.0),
                        "estimated_cash": etf_data.get("estimated_cash", 0.0),
                        "total_value": etf_data.get("total_value", 0.0),
                        "nav": etf_data.get("nav", 0.0),
                        "iopv": etf_data.get("iopv", 0.0),
                        "creation_fee": etf_data.get("creation_fee", 0.001),
                        "redemption_fee": etf_data.get("redemption_fee", 0.001),
                        "trading_day": etf_data.get("trading_day", ""),
                        "update_time": etf_data.get("update_time", datetime.now()),
                        "status": etf_data.get("status", "normal"),
                        "components": []
                    }

                    components_data = etf_data.get("components", [])
                    for comp in components_data:
                        component = {
                            "stock_code": comp.get("stock_code", ""),
                            "stock_name": comp.get("stock_name", ""),
                            "quantity": comp.get("quantity", 0),
                            "cash_substitute": comp.get("cash_substitute", 0.0),
                            "premium_rate": comp.get("premium_rate", 0.0),
                            "discount_rate": comp.get("discount_rate", 0.0),
                            "market_value": comp.get("market_value", 0.0)
                        }
                        info["components"].append(component)

                    etf_manager.set_etf_info(etf_code, info)
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=ETFErrorResponse(
                            error="ETF_NOT_FOUND",
                            message=f"ETF信息不存在: {etf_code}",
                            etf_code=etf_code
                        )
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取ETF信息失败: {etf_code}, 错误: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error="INTERNAL_ERROR",
                        message=f"获取ETF信息失败: {str(e)}"
                    )
                )

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
        info = etf_manager.get_etf_info(etf_code)

        if not info:
            try:
                from xtquant import xtdata

                xtdata.download_etf_info([etf_code])
                etf_data = xtdata.get_etf_info(etf_code)

                if etf_data:
                    etf_info = {
                        "etf_code": etf_code,
                        "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                        "creation_unit": etf_data.get("creation_unit", 1000000),
                        "cash_component": etf_data.get("cash_component", 0.0),
                        "estimated_cash": etf_data.get("estimated_cash", 0.0),
                        "total_value": etf_data.get("total_value", 0.0),
                        "nav": etf_data.get("nav", 0.0),
                        "iopv": etf_data.get("iopv", 0.0),
                        "creation_fee": etf_data.get("creation_fee", 0.001),
                        "redemption_fee": etf_data.get("redemption_fee", 0.001),
                        "trading_day": etf_data.get("trading_day", ""),
                        "update_time": etf_data.get("update_time", datetime.now()),
                        "status": etf_data.get("status", "normal"),
                        "components": []
                    }

                    components_data = etf_data.get("components", [])
                    for comp in components_data:
                        component = {
                            "stock_code": comp.get("stock_code", ""),
                            "stock_name": comp.get("stock_name", ""),
                            "quantity": comp.get("quantity", 0),
                            "cash_substitute": comp.get("cash_substitute", 0.0),
                            "premium_rate": comp.get("premium_rate", 0.0),
                            "discount_rate": comp.get("discount_rate", 0.0),
                            "market_value": comp.get("market_value", 0.0)
                        }
                        etf_info["components"].append(component)

                    etf_manager.set_etf_info(etf_code, etf_info)
                    info = etf_info
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=ETFErrorResponse(
                            error="ETF_NOT_FOUND",
                            message=f"ETF信息不存在: {etf_code}",
                            etf_code=etf_code
                        )
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取ETF信息失败: {etf_code}, 错误: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error="INTERNAL_ERROR",
                        message=f"获取ETF信息失败: {str(e)}"
                    )
                )

        try:
            from xtquant import xtdata

            market_data = xtdata.get_market_data_ex(
                stocks=[etf_code],
                periods=['tick'],
                count=1
            )

            if market_data and len(market_data) > 0:
                tick_data = market_data[0]
                market_price = tick_data.get("last_price", info.get("iopv", 1.0))
            else:
                market_price = info.get("iopv", 1.0)
        except Exception:
            market_price = info.get("iopv", 1.0)

        iopv = info.get("iopv", 1.0)

        premium_rate = 0.0
        discount_rate = 0.0

        if market_price > iopv:
            premium_rate = (market_price - iopv) / iopv * 100
        else:
            discount_rate = (iopv - market_price) / iopv * 100

        arbitrage_threshold = 0.5
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
        etf_infos = etf_manager.get_all_etfs()

        if not etf_infos:
            try:
                from xtquant import xtdata

                all_etf_info = xtdata.get_etf_info()
                if all_etf_info:
                    for etf_code in all_etf_info.keys():
                        try:
                            xtdata.download_etf_info([etf_code])
                            etf_data = xtdata.get_etf_info(etf_code)

                            if etf_data:
                                etf_info = {
                                    "etf_code": etf_code,
                                    "etf_name": etf_data.get("name", f"ETF-{etf_code}"),
                                    "creation_unit": etf_data.get("creation_unit", 1000000),
                                    "cash_component": etf_data.get("cash_component", 0.0),
                                    "estimated_cash": etf_data.get("estimated_cash", 0.0),
                                    "total_value": etf_data.get("total_value", 0.0),
                                    "nav": etf_data.get("nav", 0.0),
                                    "iopv": etf_data.get("iopv", 0.0),
                                    "creation_fee": etf_data.get("creation_fee", 0.001),
                                    "redemption_fee": etf_data.get("redemption_fee", 0.001),
                                    "trading_day": etf_data.get("trading_day", ""),
                                    "update_time": etf_data.get("update_time", datetime.now()),
                                    "status": etf_data.get("status", "normal"),
                                    "components": []
                                }

                                components_data = etf_data.get("components", [])
                                for comp in components_data:
                                    component = {
                                        "stock_code": comp.get("stock_code", ""),
                                        "stock_name": comp.get("stock_name", ""),
                                        "quantity": comp.get("quantity", 0),
                                        "cash_substitute": comp.get("cash_substitute", 0.0),
                                        "premium_rate": comp.get("premium_rate", 0.0),
                                        "discount_rate": comp.get("discount_rate", 0.0),
                                        "market_value": comp.get("market_value", 0.0)
                                    }
                                    etf_info["components"].append(component)

                                etf_manager.set_etf_info(etf_code, etf_info)
                                etf_infos.append(etf_info)
                        except Exception as e:
                            logger.error(f"下载ETF信息失败: {etf_code}, 错误: {e}")
            except Exception as e:
                logger.error(f"获取所有ETF信息失败: {e}")

        if not etf_infos:
            return []

        signals = []

        for info in etf_infos[:5]:
            etf_code = info.get("etf_code")

            signal_types = ["creation_arbitrage", "redemption_arbitrage"]

            for signal_type in signal_types:
                try:
                    from xtquant import xtdata

                    market_data = xtdata.get_market_data_ex(
                        stocks=[etf_code],
                        periods=['tick'],
                        count=1
                    )

                    if market_data and len(market_data) > 0:
                        tick_data = market_data[0]
                        market_price = tick_data.get("last_price", info.get("iopv", 1.0))
                    else:
                        market_price = info.get("iopv", 1.0)
                except Exception:
                    market_price = info.get("iopv", 1.0)

                iopv = info.get("iopv", 1.0)

                premium_rate = 0.0
                discount_rate = 0.0

                if market_price > iopv:
                    premium_rate = (market_price - iopv) / iopv * 100
                else:
                    discount_rate = (iopv - market_price) / iopv * 100

                if signal_type == "creation_arbitrage":
                    expected_return = premium_rate
                else:
                    expected_return = discount_rate

                if expected_return >= min_return:
                    signal = ETFArbitrageSignal(
                        etf_code=etf_code,
                        signal_type=signal_type,
                        timestamp=datetime.now(),
                        expected_return=expected_return,
                        risk_level="low",
                        components=info.get("components", [])[:3],
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