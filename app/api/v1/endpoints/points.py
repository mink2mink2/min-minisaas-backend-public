"""포인트 API"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.v1.dependencies.auth import verify_any_platform
from app.api.v1.dependencies.api_key import verify_api_key
from app.core.auth import AuthResult
from app.domain.points.services.point_service import PointService, InsufficientPointsError
from app.domain.points.services.transaction_service import TransactionService
from app.domain.points.schemas.points import (
    BalanceResponse,
    ChargeRequest,
    ConsumeRequest,
    RefundRequest,
    TransactionListResponse,
    TransactionItem,
)

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """잔액 조회

    Args:
        current_user: 인증된 사용자
        api_key: API 키
        db: 데이터베이스 세션

    Returns:
        BalanceResponse: 현재 포인트
    """
    try:
        service = PointService(db)
        balance = await service.get_balance(current_user.user_id)
        return BalanceResponse(
            balance=balance,
            user_id=str(current_user.user_id),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/charge")
async def charge(
    request: ChargeRequest,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """포인트 충전

    Args:
        request: ChargeRequest
        current_user: 인증된 사용자
        api_key: API 키
        db: 데이터베이스 세션

    Returns:
        거래 정보
    """
    try:
        service = PointService(db)
        transaction = await service.charge(
            user_id=current_user.user_id,
            amount=request.amount,
            description=request.description,
            idempotency_key=request.idempotency_key,
        )
        return {
            "status": "success",
            "transaction_id": str(transaction.id),
            "amount": transaction.amount,
            "balance_after": transaction.balance_after,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/consume")
async def consume(
    request: ConsumeRequest,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """포인트 사용

    Args:
        request: ConsumeRequest
        current_user: 인증된 사용자
        api_key: API 키
        db: 데이터베이스 세션

    Returns:
        거래 정보
    """
    try:
        service = PointService(db)
        transaction = await service.consume(
            user_id=current_user.user_id,
            amount=request.amount,
            description=request.description,
            idempotency_key=request.idempotency_key,
        )
        return {
            "status": "success",
            "transaction_id": str(transaction.id),
            "amount": transaction.amount,
            "balance_after": transaction.balance_after,
        }
    except InsufficientPointsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refund")
async def refund(
    request: RefundRequest,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """포인트 환급 (어드민 전용)

    Args:
        request: RefundRequest
        current_user: 인증된 사용자 (어드민)
        api_key: API 키
        db: 데이터베이스 세션

    Returns:
        거래 정보
    """
    try:
        service = PointService(db)
        transaction = await service.refund(
            user_id=current_user.user_id,
            amount=request.amount,
            description=request.description,
            idempotency_key=request.idempotency_key,
        )
        return {
            "status": "success",
            "transaction_id": str(transaction.id),
            "amount": transaction.amount,
            "balance_after": transaction.balance_after,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=TransactionListResponse)
async def get_history(
    skip: int = 0,
    limit: int = 20,
    current_user: AuthResult = Depends(verify_any_platform),
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """거래 내역 조회

    Args:
        skip: 건너뛸 개수
        limit: 조회 제한 개수
        current_user: 인증된 사용자
        api_key: API 키
        db: 데이터베이스 세션

    Returns:
        TransactionListResponse: 거래 목록
    """
    try:
        service = TransactionService(db)
        transactions, total_count = await service.get_user_transactions(
            user_id=current_user.user_id,
            skip=skip,
            limit=limit,
        )

        items = [
            TransactionItem(
                id=str(tx.id),
                type=tx.type.value,
                amount=tx.amount,
                balance_after=tx.balance_after,
                description=tx.description,
                prev_hash=tx.prev_hash,
                current_hash=tx.current_hash,
                created_at=tx.created_at.isoformat(),
            )
            for tx in transactions
        ]

        return TransactionListResponse(
            user_id=str(current_user.user_id),
            total_count=total_count,
            items=items,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))