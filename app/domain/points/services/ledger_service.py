"""원장 서비스"""
import hashlib
import json
import logging
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ledger import LedgerRoot, UserChainHash

logger = logging.getLogger(__name__)


class LedgerService:
    """일일 공개 원장 생성 및 검증"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_daily_ledger(self, target_date: date) -> LedgerRoot:
        """일일 공개 원장 생성

        모든 사용자의 체인 해시를 수집하여 시스템 해시를 생성합니다.

        Args:
            target_date: 대상 날짜

        Returns:
            생성된 LedgerRoot
        """
        # 1. 모든 사용자의 체인 해시 조회
        stmt = select(UserChainHash)
        result = await self.db.execute(stmt)
        chain_hashes = result.scalars().all()

        # 2. 사용자별 해시 딕셔너리 생성
        user_hashes = {
            ch.user_id: ch.current_hash
            for ch in chain_hashes
        }

        # 3. 시스템 해시 생성
        sorted_user_hashes = json.dumps(user_hashes, sort_keys=True)
        system_hash = hashlib.sha256(sorted_user_hashes.encode()).hexdigest()

        # 4. 거래 수 계산
        transaction_count = sum(ch.transaction_count for ch in chain_hashes)

        # 5. LedgerRoot 생성 또는 업데이트
        date_str = target_date.strftime("%Y-%m-%d")
        ledger_stmt = select(LedgerRoot).where(LedgerRoot.date == date_str)
        ledger_result = await self.db.execute(ledger_stmt)
        ledger = ledger_result.scalar_one_or_none()

        if ledger:
            # 기존 원장 업데이트
            ledger.system_hash = system_hash
            ledger.user_hashes = user_hashes
            ledger.transaction_count = transaction_count
        else:
            # 새로운 원장 생성
            ledger = LedgerRoot(
                date=date_str,
                system_hash=system_hash,
                user_hashes=user_hashes,
                transaction_count=transaction_count,
                description=f"Daily ledger for {date_str}",
                is_published="pending",
            )
            self.db.add(ledger)

        await self.db.flush()

        logger.info(
            f"📊 일일 원장 생성: date={date_str}, "
            f"user_count={len(user_hashes)}, tx_count={transaction_count}"
        )

        return ledger

    async def get_ledger_by_date(self, date_str: str) -> dict:
        """특정 날짜의 공개 원장 조회

        Args:
            date_str: 날짜 (YYYY-MM-DD)

        Returns:
            원장 정보 또는 "not_generated" 상태
        """
        stmt = select(LedgerRoot).where(LedgerRoot.date == date_str)
        result = await self.db.execute(stmt)
        ledger = result.scalar_one_or_none()

        if not ledger:
            return {
                "status": "not_generated",
                "date": date_str,
            }

        return {
            "status": "success",
            "date": ledger.date,
            "system_hash": ledger.system_hash,
            "user_hashes": ledger.user_hashes,
            "transaction_count": ledger.transaction_count,
            "user_count": len(ledger.user_hashes),
            "is_published": ledger.is_published,
            "created_at": ledger.created_at.isoformat() if ledger.created_at else None,
        }

    async def verify_system_integrity(self, date_str: str) -> dict:
        """시스템 무결성 검증

        저장된 시스템 해시와 현재 재계산한 해시를 비교합니다.

        Args:
            date_str: 날짜 (YYYY-MM-DD)

        Returns:
            검증 결과
        """
        # 1. 저장된 원장 조회
        stmt = select(LedgerRoot).where(LedgerRoot.date == date_str)
        result = await self.db.execute(stmt)
        ledger = result.scalar_one_or_none()

        if not ledger:
            return {
                "status": "not_found",
                "date": date_str,
                "message": "Ledger not found for this date",
            }

        # 2. 현재 사용자 체인 해시 조회
        chain_stmt = select(UserChainHash)
        chain_result = await self.db.execute(chain_stmt)
        current_chains = chain_result.scalars().all()

        current_user_hashes = {
            ch.user_id: ch.current_hash
            for ch in current_chains
        }

        # 3. 시스템 해시 재계산
        sorted_current = json.dumps(current_user_hashes, sort_keys=True)
        recomputed_hash = hashlib.sha256(sorted_current.encode()).hexdigest()

        # 4. 검증
        is_valid = recomputed_hash == ledger.system_hash

        return {
            "status": "valid" if is_valid else "invalid",
            "date": date_str,
            "stored_system_hash": ledger.system_hash,
            "recomputed_system_hash": recomputed_hash,
            "user_count": len(ledger.user_hashes),
            "current_user_count": len(current_user_hashes),
            "is_published": ledger.is_published,
        }
