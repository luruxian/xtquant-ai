"""账户资产查询路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from schemas.asset import AssetResponse, ErrorResponse
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

router = APIRouter(
    prefix="/api/v1/asset",
    tags=["asset"],
    responses={404: {"model": ErrorResponse, "description": "资产或路径未找到"}}
)


@router.get("", response_model=AssetResponse)
async def query_asset(
    account_id: str = Query(..., description="资金账号，如 '1000000365'"),
    account_type: Optional[str] = Query("STOCK", description="账号类型，默认为 'STOCK'（股票）")
):
    """
    查询账户资产
    
    - **account_id**: 资金账号，如 '1000000365'
    - **account_type**: 账号类型，默认为 'STOCK'（股票）
      可选值: STOCK, FUTURE, CREDIT, FUTURE_OPTION, STOCK_OPTION, HUGANGTONG, SHENGANGTONG
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
        
        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.create_trader()
        
        from xtquant.xttype import StockAccount
        acc = StockAccount(account_id, account_type)
        
        trader.start()
        
        connect_result = qmt_service.connect(trader)
        if connect_result != 0:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="CONNECT_FAILED",
                    message=f"连接 QMT 失败，错误码: {connect_result}"
                )
            )
        
        subscribe_result = qmt_service.subscribe(trader, acc)
        if subscribe_result != 0:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message=f"订阅交易回调失败，错误码: {subscribe_result}"
                )
            )
        
        asset = trader.query_stock_asset(acc)
        
        qmt_service.disconnect(trader)
        
        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ASSET_NOT_FOUND",
                    message=f"账户 {account_id} 的资产信息不存在"
                )
            )
        
        return AssetResponse(
            account_type=asset.account_type,
            account_id=asset.account_id,
            cash=asset.cash,
            frozen_cash=asset.frozen_cash,
            market_value=asset.market_value,
            total_asset=asset.total_asset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )


@router.get("/batch", response_model=list)
async def query_assets(
    account_ids: str = Query(..., description="资金账号列表，用逗号分隔，如 '1000000365,1000000366'"),
    account_type: Optional[str] = Query("STOCK", description="账号类型，默认为 'STOCK'（股票）")
):
    """
    批量查询账户资产（多个账号用逗号分隔）
    
    - **account_ids**: 资金账号列表，如 '1000000365,1000000366'
    - **account_type**: 账号类型，默认为 'STOCK'（股票）
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
        
        from xtquant.xttype import StockAccount
        from services.qmt_service import QMTService
        
        accounts = [acc.strip() for acc in account_ids.split(',')]
        results = []
        
        for account_id in accounts:
            try:
                qmt_service = QMTService(qmt_path, session_id)
                trader = qmt_service.create_trader()
                acc = StockAccount(account_id, account_type)
                
                trader.start()
                connect_result = qmt_service.connect(trader)
                
                if connect_result != 0:
                    results.append({
                        "account_id": account_id,
                        "error": f"连接失败，错误码: {connect_result}"
                    })
                    continue
                
                subscribe_result = qmt_service.subscribe(trader, acc)
                if subscribe_result != 0:
                    results.append({
                        "account_id": account_id,
                        "error": f"订阅失败，错误码: {subscribe_result}"
                    })
                    continue
                
                asset = trader.query_stock_asset(acc)
                qmt_service.disconnect(trader)
                
                if asset:
                    results.append({
                        "account_type": asset.account_type,
                        "account_id": asset.account_id,
                        "cash": asset.cash,
                        "frozen_cash": asset.frozen_cash,
                        "market_value": asset.market_value,
                        "total_asset": asset.total_asset
                    })
                else:
                    results.append({
                        "account_id": account_id,
                        "error": "资产信息不存在"
                    })
                    
            except Exception as e:
                results.append({
                    "account_id": account_id,
                    "error": str(e)
                })
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            )
        )
