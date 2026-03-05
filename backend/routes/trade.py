"""成交查询路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from schemas.asset import TradeResponse, ErrorResponse, QueryTradesRequest
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

router = APIRouter(
    prefix="/api/v1/trade",
    tags=["trade"],
    responses={404: {"model": ErrorResponse, "description": "成交或路径未找到"}}
)


@router.get("", response_model=List[TradeResponse])
async def query_trades(
    account_id: str = Query(..., description="资金账号")
):
    """
    查询当日所有成交
    
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
        
        qmt_service.start(trader)
        
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
        
        trades = trader.query_stock_trades(acc)
        
        qmt_service.disconnect(trader)
        
        if trades is None:
            return []
        
        return [
            TradeResponse(
                account_type=trade.account_type,
                account_id=trade.account_id,
                stock_code=trade.stock_code,
                order_type=trade.order_type,
                traded_id=trade.traded_id,
                traded_time=trade.traded_time,
                traded_price=trade.traded_price,
                traded_volume=trade.traded_volume,
                traded_amount=trade.traded_amount,
                order_id=trade.order_id,
                order_sysid=trade.order_sysid,
                strategy_name=trade.strategy_name,
                order_remark=trade.order_remark,
                direction=trade.direction,
                offset_flag=trade.offset_flag
            )
            for trade in trades
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
