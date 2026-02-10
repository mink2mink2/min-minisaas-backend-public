"""트랜잭션 모델 (해시 체인 포함)"""
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.models.base import BaseModel

class TransactionType(enum.Enum):
    CHARGE = "charge"      # 충전
    CONSUME = "consume"    # 사용
    REFUND = "refund"      # 환급

class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)  # 거래 후 잔액
    description = Column(String(255))
    idempotency_key = Column(String(64), unique=True)  # 중복 방지

    # 🔗 Hash Chain (완전 투명성)
    prev_hash = Column(String(64), nullable=True)  # 이전 거래의 해시
    current_hash = Column(String(64), nullable=False, index=True)  # 현재 거래의 해시
    tx_data = Column(Text, nullable=False)  # 거래 데이터 (해시 생성용)

    def __repr__(self):
        return f"<Transaction {self.id} user_id={self.user_id} amount={self.amount}>"
