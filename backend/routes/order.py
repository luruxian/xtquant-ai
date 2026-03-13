"""订单管理路由"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from datetime import datetime
from schemas.asset import OrderResponse, ErrorResponse, OrderRequest, CancelOrderRequest, QueryOrdersRequest, AsyncOrderResponse, AsyncCancelOrderRequest, AsyncCancelOrderResponse, StockOrderRequest, StockOrderResponse, StockCancelOrderRequest, StockCancelOrderResponse
from services.qmt_service import QMTService
from services.websocket_manager import websocket_manager
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
    - **order_type**: 委托类型（买入23，卖出24）
    - **volume**: 委托数量
    - **price_type**: 报价类型（市价设定5，限价指定11）
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
                ).dict()
            )
        
        session_id = get_session_id()
        
        from xtquant.xttype import StockAccount
        from xtquant import xtconstant

        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        # 创建账户对象，明确指定账户类型为STOCK
        acc = StockAccount(request.account_id, 'STOCK')

        # 确保账户已订阅
        if not qmt_service.ensure_account_subscribed(request.account_id):
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message=f"订阅账户失败: {request.account_id}"
                ).dict()
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
                ).dict()
            )

        order = trader.query_stock_order(acc, order_id)

        if order is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ORDER_NOT_FOUND",
                    message=f"订单 {order_id} 不存在"
                ).dict()
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
            ).dict()
        )


@router.post("/async", response_model=AsyncOrderResponse)
async def create_order_async(request: OrderRequest):
    """
    创建异步订单（异步下单）

    - **account_id**: 资金账号
    - **stock_code**: 证券代码，如 '600000.SH'
    - **order_type**: 委托类型（买入23，卖出24）
    - **volume**: 委托数量
    - **price_type**: 报价类型（市价设定5，限价指定11）
    - **price**: 委托价格
    - **strategy_name**: 策略名称（可选）
    - **remark**: 备注（可选）

    示例：
    股票资金账号99158392对浦发银行买入1000股，使用限价价格10.5元，委托备注为'order_test'
    注意：order_type和price_type参数需要传入对应的整数值，例如：
    - order_type: 23 (买入), 24 (卖出) 等
    - price_type: 5 (市价), 11 (限价) 等
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        from xtquant.xttype import StockAccount
        from xtquant import xtconstant

        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        acc = StockAccount(request.account_id)

        # 确保账户已订阅
        if not qmt_service.ensure_account_subscribed(request.account_id):
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message=f"订阅账户失败: {request.account_id}"
                ).dict()
            )

        # 调用异步下单接口
        seq = trader.order_stock_async(
            acc,
            request.stock_code,
            request.order_type,
            request.volume,
            request.price_type,
            request.price,
            request.strategy_name,
            request.remark
        )

        if seq == -1:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="ASYNC_ORDER_FAILED",
                    message="异步下单失败，seq为-1"
                ).dict()
            )

        # 返回异步下单响应
        return AsyncOrderResponse(
            seq=seq,
            message="异步下单请求已提交",
            account_id=request.account_id,
            stock_code=request.stock_code,
            order_type=request.order_type,
            order_volume=request.volume,
            price_type=request.price_type,
            price=request.price,
            strategy_name=request.strategy_name,
            order_remark=request.remark
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )


# @router.delete("/async", response_model=AsyncCancelOrderResponse)
# async def cancel_order_async(request: AsyncCancelOrderRequest):
#     """
#     异步取消订单（异步撤单）
#
#     - **account_id**: 资金账号
#     - **order_id**: 订单编号
#
#     示例：
#     股票资金账号99158392对订单编号为order_id的委托进行异步撤单
#     account = StockAccount('99158392', 'STOCK')
#     order_id = 100
#     cancel_result = xt_trader.cancel_order_stock_async(account, order_id)
#     """
#     try:
#         qmt_path = get_qmt_path()
#
#         if not validate_qmt_path(qmt_path):
#             raise HTTPException(
#                 status_code=404,
#                 detail=ErrorResponse(
#                     error="PATH_NOT_FOUND",
#                     message=f"QMT 客户端路径不存在: {qmt_path}"
#                 ).dict()
#             )
#
#         session_id = get_session_id()
#
#         from xtquant.xttype import StockAccount
#
#         qmt_service = QMTService(qmt_path, session_id)
#         trader = qmt_service.get_shared_trader()
#         if not trader:
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="TRADER_NOT_AVAILABLE",
#                     message="获取全局交易实例失败"
#                 ).dict()
#             )
#
#         # 创建账户对象，明确指定账户类型为STOCK
#         acc = StockAccount(request.account_id, 'STOCK')
#
#         # 确保账户已订阅
#         if not qmt_service.ensure_account_subscribed(request.account_id):
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="SUBSCRIBE_FAILED",
#                     message=f"订阅账户失败: {request.account_id}"
#                 ).dict()
#             )
#
#         # 调用异步撤单接口
#         cancel_seq = trader.cancel_order_stock_async(acc, request.order_id)
#
#         if cancel_seq == -1:
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="ASYNC_CANCEL_FAILED",
#                     message="异步撤单失败，cancel_seq为-1"
#                 ).dict()
#             )
#
#         # 返回异步撤单响应
#         return AsyncCancelOrderResponse(
#             cancel_seq=cancel_seq,
#             message="异步撤单请求已提交",
#             account_id=request.account_id,
#             order_id=request.order_id
#         )
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=ErrorResponse(
#                 error="INTERNAL_ERROR",
#                 message=str(e)
#             ).dict()
#         )


# @router.delete("", response_model=dict)
# async def cancel_order(request: CancelOrderRequest):
#     """
#     取消订单（撤单）
#
#     - **account_id**: 资金账号
#     - **order_id**: 订单编号
#     """
#     try:
#         qmt_path = get_qmt_path()
#
#         if not validate_qmt_path(qmt_path):
#             raise HTTPException(
#                 status_code=404,
#                 detail=ErrorResponse(
#                     error="PATH_NOT_FOUND",
#                     message=f"QMT 客户端路径不存在: {qmt_path}"
#                 ).dict()
#             )
#
#         session_id = get_session_id()
#
#         from xtquant.xttype import StockAccount
#
#         qmt_service = QMTService(qmt_path, session_id)
#         trader = qmt_service.get_shared_trader()
#         if not trader:
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="TRADER_NOT_AVAILABLE",
#                     message="获取全局交易实例失败"
#                 ).dict()
#             )
#
#         # 创建账户对象，明确指定账户类型为STOCK
#         acc = StockAccount(request.account_id, 'STOCK')
#
#         # 确保账户已订阅
#         if not qmt_service.ensure_account_subscribed(request.account_id):
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="SUBSCRIBE_FAILED",
#                     message=f"订阅账户失败: {request.account_id}"
#                 ).dict()
#             )
#
#         result = trader.cancel_order_stock(acc, request.order_id)
#
#         if result is None:
#             raise HTTPException(
#                 status_code=500,
#                 detail=ErrorResponse(
#                     error="CANCEL_FAILED",
#                     message=f"撤单失败，订单 {request.order_id} 可能不存在或已撤销"
#                 ).dict()
#             )
#
#         return {"message": "撤单成功", "order_id": request.order_id, "result": result}
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=ErrorResponse(
#                 error="INTERNAL_ERROR",
#                 message=str(e)
#             ).dict()
#         )


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
                ).dict()
            )

        session_id = get_session_id()

        # 使用新的查询方法
        qmt_service = QMTService(qmt_path, session_id)

        # 定义查询函数
        def query_order_func(trader, account):
            return trader.query_stock_order(account, order_id)

        # 执行查询（自动处理账户订阅）
        order = qmt_service.query_with_account(account_id, query_order_func)

        if order is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ORDER_NOT_FOUND",
                    message=f"订单 {order_id} 不存在"
                ).dict()
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
            ).dict()
        )


@router.get("", response_model=List[OrderResponse])
async def query_orders(
    account_id: str = Query(..., description="资金账号"),
    cancelable_only: bool = Query(False, description="仅查询可撤委托，默认为False")
):
    """
    查询当日所有委托

    - **account_id**: 资金账号
    - **cancelable_only**: 仅查询可撤委托，默认为False

    示例：
    查询股票资金账号99158392对应的当日所有委托
    account = StockAccount('99158392', 'STOCK')
    orders = xt_trader.query_stock_orders(account, False)
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        # 使用新的查询方法
        qmt_service = QMTService(qmt_path, session_id)

        # 定义查询函数
        def query_orders_func(trader, account):
            return trader.query_stock_orders(account, cancelable_only)

        # 执行查询（自动处理账户订阅）
        orders = qmt_service.query_with_account(account_id, query_orders_func)

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
            ).dict()
        )


@router.post("/stock", response_model=StockOrderResponse)
async def order_stock(request: StockOrderRequest):
    """
    股票同步报单

    对股票进行下单操作

    - **account**: 资金账号
    - **stock_code**: 证券代码，如'600000.SH'
    - **order_type**: 委托类型（买入23，卖出24）
    - **order_volume**: 委托数量，股票以'股'为单位，债券以'张'为单位
    - **price_type**: 报价类型（市价设定5，限价指定11）
    - **price**: 委托价格
    - **strategy_name**: 策略名称
    - **order_remark**: 委托备注

    返回：
    系统生成的订单编号，成功委托后的订单编号为大于0的正整数，如果为-1表示委托失败

    示例：
    股票资金账号99158392对浦发银行买入1000股，使用限价价格10.5元, 委托备注为'order_test'
    注意：price_type参数需要传入对应的整数值，例如：
    - price_type: 5 (市价), 11 (限价) 等
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        from xtquant.xttype import StockAccount
        from xtquant import xtconstant

        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        # 创建账户对象，明确指定账户类型为STOCK
        acc = StockAccount(request.account, 'STOCK')

        # 确保账户已订阅
        if not qmt_service.ensure_account_subscribed(request.account):
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message=f"订阅账户失败: {request.account}"
                ).dict()
            )

        # 调用同步下单接口
        order_id = trader.order_stock(
            acc,
            request.stock_code,
            request.order_type,
            request.order_volume,
            request.price_type,
            request.price,
            request.strategy_name,
            request.order_remark
        )

        # 根据文档要求，返回订单编号
        # 如果order_id为None或小于等于0，表示失败
        if order_id is None or order_id <= 0:
            # 推送失败消息（使用标准化格式）
            error_message = {
                "type": "order_result",
                "data": {
                    "order_id": -1,
                    "account": request.account,
                    "stock_code": request.stock_code,
                    "order_type": request.order_type,
                    "order_volume": request.order_volume,
                    "price_type": request.price_type,
                    "price": request.price,
                    "success": False,
                    "message": "委托失败"
                }
            }
            # 推送给客户端（使用账户ID作为客户端ID，指定order频道）
            await websocket_manager.send_personal_message(error_message, request.account, channel="order")

            return StockOrderResponse(
                order_id=-1,
                message="委托失败"
            )

        # 推送成功消息（使用标准化格式）
        success_message = {
            "type": "order_result",
            "data": {
                "order_id": order_id,
                "account": request.account,
                "stock_code": request.stock_code,
                "order_type": request.order_type,
                "order_volume": request.order_volume,
                "price_type": request.price_type,
                "price": request.price,
                "success": True,
                "message": "委托成功"
            }
        }

        # 推送给客户端（指定order频道）
        await websocket_manager.send_personal_message(success_message, request.account, channel="order")

        return StockOrderResponse(
            order_id=order_id,
            message="委托成功"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )


@router.post("/cancel", response_model=StockCancelOrderResponse)
async def cancel_order_stock(request: StockCancelOrderRequest):
    """
    股票同步撤单

    根据订单编号对委托进行撤单操作

    - **account**: 资金账号
    - **order_id**: 同步下单接口返回的订单编号,对于期货来说，是order结构中的order_sysid字段

    返回：
    返回是否成功发出撤单指令，0: 成功, -1: 表示撤单失败

    示例：
    股票资金账号99158392对订单编号为order_id的委托进行撤单

    account = StockAccount('99158392')
    order_id = 100
    #xt_trader为XtQuant API实例对象
    cancel_result = xt_trader.cancel_order_stock(account, order_id)
    """
    try:
        qmt_path = get_qmt_path()

        if not validate_qmt_path(qmt_path):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PATH_NOT_FOUND",
                    message=f"QMT 客户端路径不存在: {qmt_path}"
                ).dict()
            )

        session_id = get_session_id()

        from xtquant.xttype import StockAccount

        qmt_service = QMTService(qmt_path, session_id)
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        # 创建账户对象，明确指定账户类型为STOCK
        acc = StockAccount(request.account, 'STOCK')

        # 确保账户已订阅
        if not qmt_service.ensure_account_subscribed(request.account):
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="SUBSCRIBE_FAILED",
                    message=f"订阅账户失败: {request.account}"
                ).dict()
            )

        # 调用同步撤单接口
        result = trader.cancel_order_stock(acc, request.order_id)

        # 根据文档要求，返回撤单结果
        # 如果result为None，表示撤单失败
        if result is None:
            # 推送撤单失败消息
            cancel_error_message = {
                "type": "cancel_result",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "order_id": request.order_id,
                    "account": request.account,
                    "result": -1,
                    "success": False,
                    "message": "撤单失败"
                }
            }
            await websocket_manager.send_personal_message(cancel_error_message, request.account, channel="order")

            return StockCancelOrderResponse(
                result=-1,
                message="撤单失败"
            )

        # 检查result是否为0（成功）
        if result == 0:
            # 推送撤单成功消息
            cancel_success_message = {
                "type": "cancel_result",
                "data": {
                    "order_id": request.order_id,
                    "account": request.account,
                    "result": 0,
                    "success": True,
                    "message": "撤单成功"
                }
            }
            await websocket_manager.send_personal_message(cancel_success_message, request.account, channel="order")

            return StockCancelOrderResponse(
                result=0,
                message="撤单成功"
            )
        else:
            # 如果result不是0，也视为失败
            # 推送撤单失败消息
            cancel_fail_message = {
                "type": "cancel_result",
                "data": {
                    "order_id": request.order_id,
                    "account": request.account,
                    "result": result,
                    "success": False,
                    "message": f"撤单失败，返回码: {result}"
                }
            }
            await websocket_manager.send_personal_message(cancel_fail_message, request.account, channel="order")

            return StockCancelOrderResponse(
                result=-1,
                message=f"撤单失败，返回码: {result}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message=str(e)
            ).dict()
        )
