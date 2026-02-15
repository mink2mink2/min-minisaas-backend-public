"""포인트 서비스 - 모든 포인트 변화는 여기를 통함"""
import hashlib
import json
import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.transaction import Transaction, TransactionType
from app.models.ledger import UserChainHash
from app.domain.auth.models.user import User
from app.core.events import (
    PointsChargedEvent,
    PointsConsumedEvent,
    PointsRefundedEvent,
    event_bus,
)

logger = logging.getLogger(__name__)


class InsufficientPointsError(Exception):
    """포인트 부족 에러"""
    pass


class PointService:
    """포인트 서비스 - ALL point mutations go through here"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: UUID) -> int:
        """사용자의 현재 포인트 잔액 조회

        Args:
            user_id: 사용자 ID

        Returns:
            현재 포인트
        """
        stmt = select(User.points).where(User.id == user_id)
        result = await self.db.execute(stmt)
        points = result.scalar_one_or_none()
        return points if points is not None else 0

    async def charge(
        self,
        user_id: UUID,
        amount: int,
        description: str,
        idempotency_key: str,
    ) -> Transaction:
        """포인트 충전

        Args:
            user_id: 사용자 ID
            amount: 충전할 포인트 (양수)
            description: 설명
            idempotency_key: 중복 방지 키

        Returns:
            생성된 Transaction
        """
        # 1. 멱등성 확인 - 이미 처리된 요청인지
        idempotent_stmt = select(Transaction).where(
            Transaction.idempotency_key == idempotency_key
        )
        existing = await self.db.execute(idempotent_stmt)
        if existing.scalar_one_or_none():
            existing_tx = existing.scalar_one()
            logger.info(
                f"⏮️  이미 처리된 요청: idempotency_key={idempotency_key}, "
                f"transaction_id={existing_tx.id}"
            )
            return existing_tx

        # 2. 사용자 조회 (비관적 잠금)
        user_stmt = select(User).where(User.id == user_id).with_for_update()
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 3. 새로운 잔액 계산
        new_balance = user.points + amount

        # 4. Transaction 생성
        transaction = await self._create_transaction(
            user_id=user_id,
            tx_type=TransactionType.CHARGE,
            amount=amount,
            balance_after=new_balance,
            description=description,
            idempotency_key=idempotency_key,
        )

        # 5. User 포인트 업데이트
        await self.db.execute(
            update(User).where(User.id == user_id).values(points=new_balance)
        )

        # 6. 커밋
        await self.db.commit()

        logger.info(
            f"💰 포인트 충전 완료: user_id={user_id}, "
            f"amount={amount}, balance={new_balance}"
        )

        # 7. 이벤트 발행
        await event_bus.emit(
            PointsChargedEvent(
                user_id=str(user_id),
                amount=amount,
                balance_after=new_balance,
                description=description,
            )
        )

        return transaction

    async def consume(
        self,
        user_id: UUID,
        amount: int,
        description: str,
        idempotency_key: str,
    ) -> Transaction:
        """포인트 사용

        Args:
            user_id: 사용자 ID
            amount: 사용할 포인트 (양수)
            description: 설명
            idempotency_key: 중복 방지 키

        Returns:
            생성된 Transaction

        Raises:
            InsufficientPointsError: 포인트 부족
        """
        # 1. 멱등성 확인
        idempotent_stmt = select(Transaction).where(
            Transaction.idempotency_key == idempotency_key
        )
        existing = await self.db.execute(idempotent_stmt)
        if existing.scalar_one_or_none():
            existing_tx = existing.scalar_one()
            logger.info(
                f"⏮️  이미 처리된 요청: idempotency_key={idempotency_key}, "
                f"transaction_id={existing_tx.id}"
            )
            return existing_tx

        # 2. 사용자 조회 (비관적 잠금)
        user_stmt = select(User).where(User.id == user_id).with_for_update()
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 3. 포인트 부족 확인
        if user.points < amount:
            raise InsufficientPointsError(
                f"Insufficient points: required={amount}, available={user.points}"
            )

        # 4. 새로운 잔액 계산
        new_balance = max(0, user.points - amount)
        actual_deducted = user.points - new_balance

        # 5. Transaction 생성
        transaction = await self._create_transaction(
            user_id=user_id,
            tx_type=TransactionType.CONSUME,
            amount=actual_deducted,
            balance_after=new_balance,
            description=description,
            idempotency_key=idempotency_key,
        )

        # 6. User 포인트 업데이트
        await self.db.execute(
            update(User).where(User.id == user_id).values(points=new_balance)
        )

        # 7. 커밋
        await self.db.commit()

        logger.info(
            f"📉 포인트 사용 완료: user_id={user_id}, "
            f"amount={actual_deducted}, balance={new_balance}"
        )

        # 8. 이벤트 발행
        await event_bus.emit(
            PointsConsumedEvent(
                user_id=str(user_id),
                amount=actual_deducted,
                balance_after=new_balance,
                description=description,
            )
        )

        return transaction

    async def refund(
        self,
        user_id: UUID,
        amount: int,
        description: str,
        idempotency_key: str,
    ) -> Transaction:
        """포인트 환급

        Args:
            user_id: 사용자 ID
            amount: 환급할 포인트 (양수)
            description: 설명
            idempotency_key: 중복 방지 키

        Returns:
            생성된 Transaction
        """
        # 1. 멱등성 확인
        idempotent_stmt = select(Transaction).where(
            Transaction.idempotency_key == idempotency_key
        )
        existing = await self.db.execute(idempotent_stmt)
        if existing.scalar_one_or_none():
            existing_tx = existing.scalar_one()
            logger.info(
                f"⏮️  이미 처리된 요청: idempotency_key={idempotency_key}, "
                f"transaction_id={existing_tx.id}"
            )
            return existing_tx

        # 2. 사용자 조회 (비관적 잠금)
        user_stmt = select(User).where(User.id == user_id).with_for_update()
        user_result = await self.db.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        # 3. 새로운 잔액 계산
        new_balance = user.points + amount

        # 4. Transaction 생성
        transaction = await self._create_transaction(
            user_id=user_id,
            tx_type=TransactionType.REFUND,
            amount=amount,
            balance_after=new_balance,
            description=description,
            idempotency_key=idempotency_key,
        )

        # 5. User 포인트 업데이트
        await self.db.execute(
            update(User).where(User.id == user_id).values(points=new_balance)
        )

        # 6. 커밋
        await self.db.commit()

        logger.info(
            f"🔄 포인트 환급 완료: user_id={user_id}, "
            f"amount={amount}, balance={new_balance}"
        )

        # 7. 이벤트 발행
        await event_bus.emit(
            PointsRefundedEvent(
                user_id=str(user_id),
                amount=amount,
                balance_after=new_balance,
                description=description,
            )
        )

        return transaction

    async def _create_transaction(
        self,
        user_id: UUID,
        tx_type: TransactionType,
        amount: int,
        balance_after: int,
        description: str,
        idempotency_key: str,
    ) -> Transaction:
        """내부: Transaction 레코드 생성 및 해시 체인 업데이트

        Args:
            user_id: 사용자 ID
            tx_type: 거래 타입
            amount: 거래 포인트
            balance_after: 거래 후 잔액
            description: 설명
            idempotency_key: 중복 방지 키

        Returns:
            생성된 Transaction
        """
        # 1. 이전 체인 해시 조회
        prev_chain_stmt = select(UserChainHash).where(
            UserChainHash.user_id == str(user_id)
        )
        prev_chain_result = await self.db.execute(prev_chain_stmt)
        prev_chain = prev_chain_result.scalar_one_or_none()
        prev_hash = prev_chain.current_hash if prev_chain else None

        # 2. 거래 데이터 구성 및 해시 생성
        tx_data_dict = {
            "user_id": str(user_id),
            "type": tx_type.value,
            "amount": amount,
            "balance_after": balance_after,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        }
        tx_data_json = json.dumps(tx_data_dict, sort_keys=True)
        current_hash = hashlib.sha256(tx_data_json.encode()).hexdigest()

        # 3. Transaction 생성
        transaction = Transaction(
            user_id=user_id,
            type=tx_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
            idempotency_key=idempotency_key,
            prev_hash=prev_hash,
            current_hash=current_hash,
            tx_data=tx_data_json,
        )
        self.db.add(transaction)
        await self.db.flush()  # ID 생성을 위해 flush

        # 4. UserChainHash 업데이트 또는 생성
        if prev_chain:
            # 기존 체인 업데이트
            prev_chain.current_hash = current_hash
            prev_chain.transaction_count += 1
            prev_chain.last_transaction_at = datetime.utcnow()
        else:
            # 새로운 체인 생성
            new_chain = UserChainHash(
                user_id=str(user_id),
                current_hash=current_hash,
                transaction_count=1,
                last_transaction_at=datetime.utcnow(),
                chain_started_at=datetime.utcnow(),
            )
            self.db.add(new_chain)

        return transaction
