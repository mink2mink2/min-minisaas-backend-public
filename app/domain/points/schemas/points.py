"""포인트 시스템 스키마"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from uuid import UUID


class BalanceResponse(BaseModel):
    """잔액 조회 응답"""
    balance: int = Field(..., description="현재 포인트")
    user_id: str = Field(..., description="사용자 ID")


class ChargeRequest(BaseModel):
    """포인트 충전 요청"""
    amount: int = Field(..., gt=0, description="충전할 포인트")
    description: str = Field(..., description="설명")
    idempotency_key: str = Field(..., description="중복 방지 키")


class ConsumeRequest(BaseModel):
    """포인트 사용 요청"""
    amount: int = Field(..., gt=0, description="사용할 포인트")
    description: str = Field(..., description="설명")
    idempotency_key: str = Field(..., description="중복 방지 키")


class RefundRequest(BaseModel):
    """포인트 환급 요청"""
    amount: int = Field(..., gt=0, description="환급할 포인트")
    description: str = Field(..., description="설명")
    idempotency_key: str = Field(..., description="중복 방지 키")


class TransactionItem(BaseModel):
    """거래 아이템"""
    id: str = Field(..., description="거래 ID")
    type: str = Field(..., description="거래 타입 (charge, consume, refund)")
    amount: int = Field(..., description="거래 포인트")
    balance_after: int = Field(..., description="거래 후 잔액")
    description: str = Field(..., description="설명")
    prev_hash: Optional[str] = Field(None, description="이전 해시")
    current_hash: str = Field(..., description="현재 해시")
    created_at: str = Field(..., description="생성 시간")

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    """거래 내역 조회 응답"""
    status: str = Field("success", description="상태")
    user_id: str = Field(..., description="사용자 ID")
    total_count: int = Field(..., description="총 거래 수")
    items: List[TransactionItem] = Field(..., description="거래 목록")
    skip: int = Field(0, description="건너뛴 개수")
    limit: int = Field(20, description="제한 개수")


class ChainVerificationResult(BaseModel):
    """체인 검증 결과"""
    status: str = Field(..., description="검증 결과 (valid, invalid)")
    user_id: str = Field(..., description="사용자 ID")
    transaction_count: int = Field(..., description="거래 개수")
    chain_hash: Optional[str] = Field(None, description="체인 마지막 해시")
    errors: List[str] = Field(default_factory=list, description="오류 목록")
