"""거래 서비스"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.transaction import Transaction
from app.models.ledger import UserChainHash
from app.domain.points.schemas.points import ChainVerificationResult

logger = logging.getLogger(__name__)


class TransactionService:
    """거래 조회 및 체인 검증 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_chain(self, user_id: UUID, skip: int = 0, limit: int = 20) -> list[Transaction]:
        """사용자의 거래 체인 조회 (가장 오래된 순서)

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 개수
            limit: 조회 제한 개수

        Returns:
            거래 목록 (체인 순서)
        """
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_transactions(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[Transaction], int]:
        """사용자의 거래 내역 조회 (최신순)

        Args:
            user_id: 사용자 ID
            skip: 건너뛸 개수
            limit: 조회 제한 개수

        Returns:
            (거래 목록, 총 개수)
        """
        # 총 개수 조회
        count_stmt = select(func.count()).select_from(Transaction).where(
            Transaction.user_id == user_id
        )
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar()

        # 거래 조회
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        return transactions, total_count

    async def verify_user_chain(self, user_id: UUID) -> ChainVerificationResult:
        """사용자의 거래 체인 검증

        모든 거래의 해시를 재계산하고 체인 순서를 확인합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            ChainVerificationResult
        """
        import hashlib
        import json

        # 체인 순서대로 모든 거래 조회
        transactions = await self.get_user_chain(user_id, skip=0, limit=10000)

        errors = []
        prev_hash = None

        for tx in transactions:
            # 해시 재계산
            tx_data_dict = json.loads(tx.tx_data)
            tx_data_json = json.dumps(tx_data_dict, sort_keys=True)
            computed_hash = hashlib.sha256(tx_data_json.encode()).hexdigest()

            # 해시 확인
            if computed_hash != tx.current_hash:
                errors.append(
                    f"Hash mismatch at transaction {tx.id}: "
                    f"computed={computed_hash}, stored={tx.current_hash}"
                )

            # 이전 해시 확인
            if tx.prev_hash != prev_hash:
                errors.append(
                    f"Chain broken at transaction {tx.id}: "
                    f"expected prev_hash={prev_hash}, got {tx.prev_hash}"
                )

            prev_hash = tx.current_hash

        # 최종 체인 해시 (마지막 거래의 해시)
        chain_hash = prev_hash if transactions else None

        status = "valid" if not errors else "invalid"

        logger.info(
            f"🔗 체인 검증 완료: user_id={user_id}, "
            f"status={status}, tx_count={len(transactions)}"
        )

        return ChainVerificationResult(
            status=status,
            user_id=str(user_id),
            transaction_count=len(transactions),
            chain_hash=chain_hash,
            errors=errors,
        )
