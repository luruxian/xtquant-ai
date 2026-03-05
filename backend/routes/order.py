"""订单管理路由"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from schemas.asset import OrderResponse, ErrorResponse, OrderRequest, CancelOrderRequest, QueryOrdersRequest
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

router = APIRouter(
    prefix="/api/v1/order",
    tags=["order"],
    responses={404: {"model": ErrorResponse, "description": "订单或路径未找到"}}
)


@router.post("", response_model=OrderResponse)
async def create_order(request: OrderRequest):
    """
    创建订单（下单）
    
    - **account_id**: 资金账号
    - **stock_code**: 证券代码，如 '600000.SH'
    - **order_type**: 委托类型
    - **volume**: 委托数量
    - **price_type**: 报价类型
    - **price**: 委托价格
    - **strategy_name**: 策略名称（可选）
    - **remark**: 备注（可选）
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
        from xtquant import xtconstant
        
        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.create_trader()
        
        acc = StockAccount(request.account_id)
        
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
        
        order_id = trader.order_stock(
            acc,
            request.stock_code,
            request.order_type,
            request.volume,
            request.price_type,
            request.price,
            request.strategy_name,
            request.remark
        )
        
        if order_id is None:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="ORDER_FAILED",
                    message="下单失败"
                )
            )
        
        order = trader.query_stock_order(acc, order_id)
        
        qmt_service.disconnect(trader)
        
        if order is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ORDER_NOT_FOUND",
                    message=f"订单 {order_id} 不存在"
                )
            )
        
        return OrderResponse(
            account_type=order.account_type,
            account_id=order.account_id,
            stock_code=order.stock_code,
            order_id=order.order_id,
            order_sysid=order.order_sysid,
            order_time=order.order_time,
            order_type=order.order_type,
            order_volume=order.order_volume,
            price_type=order.price_type,
            price=order.price,
            traded_volume=order.traded_volume,
            traded_price=order.traded_price,
            order_status=order.order_status,
            status_msg=order.status_msg,
            strategy_name=order.strategy_name,
            order_remark=order.order_remark,
            direction=order.direction,
            offset_flag=order.offset_flag
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


@router.delete("", response_model=dict)
async def cancel_order(request: CancelOrderRequest):
    """
    取消订单（撤单）
    
    - **account_id**: 资金账号
    - **order_id**: 订单编号
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
        
        acc = StockAccount(request.account_id)
        
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
        
        result = trader.cancel_order_stock(acc, request.order_id)
        
        qmt_service.disconnect(trader)
        
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="CANCEL_FAILED",
                    message=f"撤单失败，订单 {request.order_id} 可能不存在或已撤销"
                )
            )
        
        return {"message": "撤单成功", "order_id": request.order_id, "result": result}
        
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


@router.get("/{order_id}", response_model=OrderResponse)
async def query_order(
    order_id: int = Path(..., description="订单编号"),
    account_id: str = Query(..., description="资金账号")
):
    """
    查询订单
    
    - **order_id**: 订单编号
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
        
        order = trader.query_stock_order(acc, order_id)
        
        qmt_service.disconnect(trader)
        
        if order is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ORDER_NOT_FOUND",
                    message=f"订单 {order_id} 不存在"
                )
            )
        
        return OrderResponse(
            account_type=order.account_type,
            account_id=order.account_id,
            stock_code=order.stock_code,
            order_id=order.order_id,
            order_sysid=order.order_sysid,
            order_time=order.order_time,
            order_type=order.order_type,
            order_volume=order.order_volume,
            price_type=order.price_type,
            price=order.price,
            traded_volume=order.traded_volume,
            traded_price=order.traded_price,
            order_status=order.order_status,
            status_msg=order.status_msg,
            strategy_name=order.strategy_name,
            order_remark=order.order_remark,
            direction=order.direction,
            offset_flag=order.offset_flag
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


@router.get("", response_model=List[OrderResponse])
async def query_orders(
    account_id: str = Query(..., description="资金账号"),
    order_type: Optional[int] = Query(None, description="委托类型，可选")
):
    """
    查询当日所有订单
    
    - **account_id**: 资金账号
    - **order_type**: 委托类型，可选
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
        
        orders = trader.query_stock_orders(acc, order_type)
        
        qmt_service.disconnect(trader)
        
        if orders is None:
            return []
        
        return [
            OrderResponse(
                account_type=order.account_type,
                account_id=order.account_id,
                stock_code=order.stock_code,
                order_id=order.order_id,
                order_sysid=order.order_sysid,
                order_time=order.order_time,
                order_type=order.order_type,
                order_volume=order.order_volume,
                price_type=order.price_type,
                price=order.price,
                traded_volume=order.traded_volume,
                traded_price=order.traded_price,
                order_status=order.order_status,
                status_msg=order.status_msg,
                strategy_name=order.strategy_name,
                order_remark=order.order_remark,
                direction=order.direction,
                offset_flag=order.offset_flag
            )
            for order in orders
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
