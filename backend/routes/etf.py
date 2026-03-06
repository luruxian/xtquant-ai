"""ETF申赎清单信息管理路由"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse

from schemas.etf import (
    ETFDownloadRequest, ETFDownloadResponse, ETFInfoResponse,
    ETFDetailResponse, ETFListResponse, ETFQueryRequest,
    ETFComponentRequest, ETFErrorResponse
)
from schemas.asset import ErrorResponse

# 创建路由器
router = APIRouter(
    prefix="/api/v1/etf",
    tags=["etf"],
    responses={404: {"model": ErrorResponse, "description": "ETF信息未找到"}}
)

# 配置日志
logger = logging.getLogger(__name__)


def parse_etf_data(etf_code: str, etf_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    解析ETF数据，处理中文和英文键名

    Args:
        etf_code: ETF代码
        etf_data: 原始ETF数据

    Returns:
        解析后的ETF信息字典
    """
    try:
        # 处理中文键名
        etf_info = {
            "etf_code": etf_code,
            "etf_name": etf_data.get("基金名称") or etf_data.get("fund_name") or "",
            "creation_unit": etf_data.get("最小申赎单位") or etf_data.get("creation_unit") or 0,
            "cash_component": etf_data.get("现金差额") or etf_data.get("cash_component") or 0.0,
            "estimated_cash": etf_data.get("预估现金") or etf_data.get("estimated_cash") or 0.0,
            "total_value": etf_data.get("一篮子股票总市值") or etf_data.get("total_value") or 0.0,
            "nav": etf_data.get("基金净值") or etf_data.get("nav") or 0.0,
            "iopv": etf_data.get("参考单位净值") or etf_data.get("iopv") or 0.0,
            "creation_fee": etf_data.get("申购费用") or etf_data.get("creation_fee"),
            "redemption_fee": etf_data.get("赎回费用") or etf_data.get("redemption_fee"),
            "trading_day": etf_data.get("交易日") or etf_data.get("trading_day") or "",
            "update_time": datetime.now(),
            "status": etf_data.get("状态") or etf_data.get("status") or "normal",
            "components": []
        }

        # 解析成分股信息
        components_data = etf_data.get("成份股信息") or etf_data.get("components") or []
        if isinstance(components_data, list):
            for comp in components_data:
                if isinstance(comp, dict):
                    component = {
                        "stock_code": comp.get("股票代码") or comp.get("stock_code") or "",
                        "stock_name": comp.get("股票名称") or comp.get("stock_name") or "",
                        "quantity": comp.get("数量") or comp.get("quantity") or 0,
                        "cash_substitute": comp.get("现金替代金额") or comp.get("cash_substitute"),
                        "premium_rate": comp.get("溢价率") or comp.get("premium_rate"),
                        "discount_rate": comp.get("折价率") or comp.get("discount_rate"),
                        "market_value": comp.get("市值") or comp.get("market_value")
                    }
                    etf_info["components"].append(component)

        return etf_info
    except Exception as e:
        logger.error(f"解析ETF数据失败: {etf_code}, 错误: {e}")
        return None


class ETFInfoManager:
    """ETF信息缓存管理器"""

    def __init__(self, cache_ttl_hours: int = 24):
        self.etf_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

    def get_etf_info(self, etf_code: str) -> Optional[Dict[str, Any]]:
        """获取ETF信息，检查缓存是否过期"""
        if etf_code not in self.etf_cache:
            return None

        expiry_time = self.cache_expiry.get(etf_code)
        if expiry_time and datetime.now() >= expiry_time:
            # 缓存过期，清除
            del self.etf_cache[etf_code]
            if etf_code in self.cache_expiry:
                del self.cache_expiry[etf_code]
            return None

        return self.etf_cache.get(etf_code)

    def set_etf_info(self, etf_code: str, etf_info: Dict[str, Any]):
        """设置ETF信息到缓存"""
        self.etf_cache[etf_code] = etf_info
        self.cache_expiry[etf_code] = datetime.now() + self.cache_ttl

    def clear_cache(self, etf_code: Optional[str] = None):
        """清理缓存"""
        if etf_code:
            if etf_code in self.etf_cache:
                del self.etf_cache[etf_code]
            if etf_code in self.cache_expiry:
                del self.cache_expiry[etf_code]
            logger.info(f"清理ETF缓存: {etf_code}")
        else:
            self.etf_cache.clear()
            self.cache_expiry.clear()
            logger.info("清理所有ETF缓存")

    def get_all_etfs(self) -> List[Dict[str, Any]]:
        """获取所有有效的ETF信息"""
        valid_etfs = []
        now = datetime.now()

        for etf_code, expiry_time in list(self.cache_expiry.items()):
            if expiry_time and now < expiry_time:
                etf_info = self.etf_cache.get(etf_code)
                if etf_info:
                    valid_etfs.append(etf_info)

        return valid_etfs


# 创建全局ETF管理器实例
etf_manager = ETFInfoManager()


@router.post("/download", response_model=ETFDownloadResponse)
async def download_etf_info(
    request: ETFDownloadRequest = Body(..., description="下载请求参数")
):
    """
    下载ETF申赎清单信息

    - **etf_codes**: 指定ETF代码列表，为空则下载所有
    - **force_refresh**: 是否强制刷新缓存
    """
    try:
        from xtquant import xtdata

        # 下载所有ETF信息
        xtdata.download_etf_info()
        logger.info("下载ETF信息完成")

        # 获取所有ETF信息
        all_etf_info = xtdata.get_etf_info()

        if not all_etf_info:
            return ETFDownloadResponse(
                success=False,
                message="未获取到ETF信息",
                downloaded_count=0
            )

        # 如果指定了ETF代码，只处理指定的ETF
        etf_codes_to_process = request.etf_codes or list(all_etf_info.keys())
        downloaded_count = 0
        failed_codes = []

        for etf_code in etf_codes_to_process:
            try:
                etf_data = all_etf_info.get(etf_code)
                if etf_data:
                    # 解析ETF数据
                    parsed_info = parse_etf_data(etf_code, etf_data)
                    if parsed_info:
                        etf_manager.set_etf_info(etf_code, parsed_info)
                        downloaded_count += 1
                        logger.info(f"下载ETF信息成功: {etf_code}")
                    else:
                        failed_codes.append(etf_code)
                        logger.warning(f"解析ETF数据失败: {etf_code}")
                else:
                    failed_codes.append(etf_code)
                    logger.warning(f"ETF信息不存在: {etf_code}")
            except Exception as e:
                failed_codes.append(etf_code)
                logger.error(f"处理ETF信息失败: {etf_code}, 错误: {e}")

        message = f"成功下载 {downloaded_count} 个ETF信息"
        if failed_codes:
            message += f"，失败 {len(failed_codes)} 个: {', '.join(failed_codes)}"

        return ETFDownloadResponse(
            success=True,
            message=message,
            downloaded_count=downloaded_count,
            failed_codes=failed_codes
        )

    except Exception as e:
        logger.error(f"下载ETF信息失败: {e}")
        return ETFDownloadResponse(
            success=False,
            message=f"下载ETF信息失败: {str(e)}",
            downloaded_count=0
        )


@router.get("/info", response_model=ETFListResponse)
async def get_etf_info(
    status_filter: Optional[str] = Query(None, description="状态过滤"),
    min_creation_unit: Optional[int] = Query(None, description="最小申赎单位过滤"),
    exchange: Optional[str] = Query(None, description="交易所过滤: SH, SZ")
):
    """
    获取ETF列表信息

    - **status_filter**: 状态过滤
    - **min_creation_unit**: 最小申赎单位过滤
    - **exchange**: 交易所过滤
    """
    try:
        etf_infos = etf_manager.get_all_etfs()

        # 应用过滤器
        filtered_etfs = []
        for etf_info in etf_infos:
            # 状态过滤
            if status_filter and etf_info.get("status") != status_filter:
                continue

            # 最小申赎单位过滤
            if min_creation_unit is not None:
                creation_unit = etf_info.get("creation_unit", 0)
                if creation_unit < min_creation_unit:
                    continue

            # 交易所过滤（通过ETF代码前缀判断）
            if exchange:
                etf_code = etf_info.get("etf_code", "")
                if exchange == "SH" and not etf_code.startswith("51"):
                    continue
                if exchange == "SZ" and not etf_code.startswith("15"):
                    continue

            components = etf_info.get("components", [])

            etf_response = ETFInfoResponse(
                etf_code=etf_info.get("etf_code"),
                etf_name=etf_info.get("etf_name"),
                creation_unit=etf_info.get("creation_unit", 0),
                cash_component=etf_info.get("cash_component", 0.0),
                estimated_cash=etf_info.get("estimated_cash", 0.0),
                total_value=etf_info.get("total_value", 0.0),
                nav=etf_info.get("nav", 0.0),
                iopv=etf_info.get("iopv", 0.0),
                creation_fee=etf_info.get("creation_fee"),
                redemption_fee=etf_info.get("redemption_fee"),
                trading_day=etf_info.get("trading_day", ""),
                update_time=etf_info.get("update_time", datetime.now()),
                status=etf_info.get("status", "unknown"),
                component_count=len(components)
            )
            filtered_etfs.append(etf_response)

        return ETFListResponse(
            total=len(filtered_etfs),
            etfs=filtered_etfs
        )

    except Exception as e:
        logger.error(f"获取ETF列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=f"获取ETF列表失败: {str(e)}"
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

                # 下载所有ETF信息
                xtdata.download_etf_info()
                logger.info(f"强制刷新ETF信息: {etf_code}")
            except Exception as e:
                logger.error(f"强制刷新ETF信息失败: {etf_code}, 错误: {e}")

        info = etf_manager.get_etf_info(etf_code)

        if not info:
            try:
                from xtquant import xtdata

                # 下载所有ETF信息
                xtdata.download_etf_info()
                # 获取所有ETF信息
                all_etf_info = xtdata.get_etf_info()
                etf_data = all_etf_info.get(etf_code) if all_etf_info else None

                logger.info(f"ETF信息不存在，已下载: {etf_code}")

                if etf_data:
                    # 使用辅助函数解析ETF数据
                    info = parse_etf_data(etf_code, etf_data)
                    if info:
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