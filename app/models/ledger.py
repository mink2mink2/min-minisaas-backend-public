"""공개 원장 모델 (Hash Chain Ledger)"""
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from app.models.base import BaseModel

class LedgerRoot(BaseModel):
    """일일 공개 원장 (모든 거래의 무결성 증명)"""
    __tablename__ = "ledger_roots"

    # 일자 (yyyy-mm-dd)
    date = Column(String(10), nullable=False, unique=True, index=True)

    # 🔗 시스템 전체 해시 (모든 사용자의 거래 해시 결합)
    system_hash = Column(String(64), nullable=False, unique=True)

    # 포함된 거래 수
    transaction_count = Column(Integer, default=0)

    # 사용자별 해시 (JSON: {user_id: user_chain_hash, ...})
    user_hashes = Column(JSON, nullable=False)

    # 상세 정보
    description = Column(Text, nullable=True)

    # 공개 여부
    is_published = Column(String(20), default="pending")  # pending, published

    def __repr__(self):
        return f"<LedgerRoot {self.date} tx_count={self.transaction_count}>"


class UserChainHash(BaseModel):
    """사용자별 거래 해시 체인"""
    __tablename__ = "user_chain_hashes"

    user_id = Column(String(36), nullable=False, unique=True, index=True)

    # 현재 체인의 끝 해시
    current_hash = Column(String(64), nullable=False, index=True)

    # 거래 수
    transaction_count = Column(Integer, default=0)

    # 최신 거래 시간
    last_transaction_at = Column(DateTime, default=datetime.utcnow)

    # 체인 시작 시간
    chain_started_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserChainHash {self.user_id} tx_count={self.transaction_count}>"
