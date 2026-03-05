"""持仓查询路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from schemas.asset import PositionResponse, ErrorResponse, QueryPositionsRequest
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

router = APIRouter(
    prefix="/api/v1/position",
    tags=["position"],
    responses={404: {"model": ErrorResponse, "description": "持仓或路径未找到"}}
)


@router.get("/{stock_code}", response_model=PositionResponse)
async def query_position(
    stock_code: str = Query(..., description="证券代码，如 '600000.SH'"),
    account_id: str = Query(..., description="资金账号")
):
    """
    根据股票代码查询持仓
    
    - **stock_code**: 证券代码
    - **account_id**: 资金账号
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
        
        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.create_trader()
        
        acc = StockAccount(account_id)
        
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
        
        position = trader.query_stock_position(acc, stock_code)
        
        qmt_service.disconnect(trader)
        
        if position is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="POSITION_NOT_FOUND",
                    message=f"股票 {stock_code} 的持仓信息不存在"
                )
            )
        
        return PositionResponse(
            account_type=position.account_type,
            account_id=position.account_id,
            stock_code=position.stock_code,
            volume=position.volume,
            can_use_volume=position.can_use_volume,
            open_price=position.open_price,
            market_value=position.market_value,
            frozen_volume=position.frozen_volume,
            on_road_volume=position.on_road_volume,
            yesterday_volume=position.yesterday_volume,
            avg_price=position.avg_price,
            direction=position.direction
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


@router.get("", response_model=list[PositionResponse])
async def query_positions(
    account_id: str = Query(..., description="资金账号")
):
    """
    查询当日所有持仓
    
    - **account_id**: 资金账号
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
        
        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.create_trader()
        
        acc = StockAccount(account_id)
        
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
        
        positions = trader.query_stock_positions(acc)
        
        qmt_service.disconnect(trader)
        
        if positions is None:
            return []
        
        return [
            PositionResponse(
                account_type=position.account_type,
                account_id=position.account_id,
                stock_code=position.stock_code,
                volume=position.volume,
                can_use_volume=position.can_use_volume,
                open_price=position.open_price,
                market_value=position.market_value,
                frozen_volume=position.frozen_volume,
                on_road_volume=position.on_road_volume,
                yesterday_volume=position.yesterday_volume,
                avg_price=position.avg_price,
                direction=position.direction
            )
            for position in positions
        ]
        
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
