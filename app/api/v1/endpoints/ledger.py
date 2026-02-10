"""공개 원장 API 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.ledger_service import LedgerService
from features.points.backend.services.transaction_service import TransactionService
from datetime import date

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/my-chain")
async def verify_my_chain(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    자신의 거래 체인 검증

    응답:
    - status: "valid" 또는 "invalid"
    - transaction_count: 거래 개수
    - chain_hash: 최종 체인 해시
    """
    try:
        tx_service = TransactionService(db)
        result = await tx_service.verify_user_chain(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-transactions")
async def get_my_transactions(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    자신의 거래 내역 조회 (해시 포함)
    """
    try:
        tx_service = TransactionService(db)
        transactions = await tx_service.get_user_chain(user_id)

        return {
            "status": "success",
            "user_id": str(user_id),
            "transaction_count": len(transactions),
            "transactions": [
                {
                    "id": str(tx.id),
                    "type": tx.type.value,
                    "amount": tx.amount,
                    "balance_after": tx.balance_after,
                    "description": tx.description,
                    "prev_hash": tx.prev_hash,
                    "current_hash": tx.current_hash,
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in transactions
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/integrity/{date_str}")
async def verify_system_integrity(
    date_str: str,
    db: AsyncSession = Depends(get_db)
):
    """
    시스템 무결성 검증 (특정 날짜)

    응답:
    - status: "valid" 또는 "invalid"
    - system_hash: 시스템 해시
    """
    try:
        ledger_service = LedgerService(db)
        result = await ledger_service.verify_system_integrity(date_str)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/root/{date_str}")
async def get_ledger_root(
    date_str: str,
    db: AsyncSession = Depends(get_db)
):
    """
    공개 원장 조회 (누구든 볼 수 있음)

    응답:
    - date: 날짜
    - system_hash: 시스템 전체 해시
    - user_hashes: {user_id: hash, ...} (모든 사용자의 체인 해시)
    - transaction_count: 그날의 거래 수
    """
    try:
        ledger_service = LedgerService(db)
        result = await ledger_service.get_ledger_by_date(date_str)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-daily/{date_str}")
async def generate_daily_ledger(
    date_str: str,
    db: AsyncSession = Depends(get_db)
):
    """
    일일 공개 원장 생성 (관리자용)

    날짜 형식: YYYY-MM-DD
    """
    try:
        # 날짜 파싱
        target_date = date.fromisoformat(date_str)

        ledger_service = LedgerService(db)
        ledger = await ledger_service.generate_daily_ledger(target_date)

        await db.commit()

        return {
            "status": "success",
            "date": ledger.date,
            "system_hash": ledger.system_hash,
            "transaction_count": ledger.transaction_count,
            "user_count": len(ledger.user_hashes),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/today")
async def get_today_ledger(db: AsyncSession = Depends(get_db)):
    """
    오늘의 공개 원장 조회
    """
    try:
        ledger_service = LedgerService(db)
        today = date.today().strftime("%Y-%m-%d")
        result = await ledger_service.get_ledger_by_date(today)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
