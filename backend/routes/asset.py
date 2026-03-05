"""账户资产查询路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from schemas.asset import AssetResponse, ErrorResponse, AccountInfoResponse
from services.qmt_service import QMTService
from utils.config import get_qmt_path, get_session_id, validate_qmt_path

router = APIRouter(
    prefix="/api/v1/asset",
    tags=["asset"],
    responses={404: {"model": ErrorResponse, "description": "资产或路径未找到"}}
)


@router.get("", response_model=AssetResponse)
async def query_asset(
    account_id: str = Query(..., description="资金账号，如 '1000000365'")
):
    """
    查询账户资产

    - **account_id**: 资金账号，如 '1000000365'
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
        def query_asset_func(trader, account):
            return trader.query_stock_asset(account)

        # 执行查询（自动处理账户订阅）
        asset = qmt_service.query_with_account(account_id, query_asset_func)

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ASSET_NOT_FOUND",
                    message=f"账户 {account_id} 的资产信息不存在"
                ).dict()
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
            ).dict()
        )


@router.get("/accounts", response_model=List[AccountInfoResponse])
async def query_accounts():
    """
    查询所有账户信息
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

        # 获取全局交易实例
        trader = qmt_service.get_shared_trader()
        if not trader:
            raise HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error="TRADER_NOT_AVAILABLE",
                    message="获取全局交易实例失败"
                ).dict()
            )

        # 获取所有账号列表
        account_list = trader.query_account_infos()

        if not account_list:
            return []

        # 转换为响应模型
        accounts = []
        for acc_info in account_list:
            accounts.append(AccountInfoResponse(
                account_id=acc_info.account_id,
                account_type=acc_info.account_type
            ))

        return accounts

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


@router.get("/batch", response_model=list)
async def query_assets(
    account_ids: str = Query(..., description="资金账号列表，用逗号分隔，如 '1000000365,1000000366'")
):
    """
    批量查询账户资产（多个账号用逗号分隔）

    - **account_ids**: 资金账号列表，如 '1000000365,1000000366'
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

        # 使用新的批量查询方法
        qmt_service = QMTService(qmt_path, session_id)

        # 解析账户列表
        accounts = [acc.strip() for acc in account_ids.split(',')]

        # 定义查询函数
        def query_asset_func(trader, account):
            return trader.query_stock_asset(account)

        # 执行批量查询
        results = qmt_service.batch_query_accounts(accounts, query_asset_func)

        # 转换结果为标准格式
        formatted_results = []
        for account_id, result in results.items():
            if isinstance(result, dict) and "error" in result:
                formatted_results.append({
                    "account_id": account_id,
                    "error": result["error"]
                })
            else:
                # result 是 XtAsset 对象
                formatted_results.append({
                    "account_type": result.account_type,
                    "account_id": result.account_id,
                    "cash": result.cash,
                    "frozen_cash": result.frozen_cash,
                    "market_value": result.market_value,
                    "total_asset": result.total_asset
                })

        return formatted_results

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