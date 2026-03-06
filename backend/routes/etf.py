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