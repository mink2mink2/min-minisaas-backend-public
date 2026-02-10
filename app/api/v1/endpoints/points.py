"""포인트 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from features.points.backend.services.point_service import PointService

router = APIRouter()

@router.get("/balance")
async def get_balance(db: AsyncSession = Depends(get_db)):
    """잔액 조회"""
    service = PointService(db)
    balance = await service.get_balance("dummy-user")  # TODO: 실제 user_id
    return {"balance": balance}

@router.post("/charge")
async def charge(amount: int, idempotency_key: str, db: AsyncSession = Depends(get_db)):
    """포인트 충전"""
    service = PointService(db)
    success = await service.charge("dummy-user", amount, idempotency_key)
    if not success:
        return {"error": "이미 처리된 요청"}
    return {"success": True}