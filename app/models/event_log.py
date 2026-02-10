# api/app/models/event_log.py
from sqlalchemy import Column, BigInteger, String, JSON, DateTime, Index
from app.models.base import BaseModel

class EventLog(BaseModel):
    """모든 이벤트의 불변 기록"""
    __tablename__ = "event_logs"
    
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), index=True)
    payload = Column(JSON, nullable=False)
    
    # 이벤트 처리 결과
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1000), nullable=True)
    
    # 인덱스: 고속 쿼리
    __table_args__ = (
        Index('idx_event_type_created', 'event_type', 'created_at'),
        Index('idx_aggregate_id_created', 'aggregate_id', 'created_at'),
        Index('idx_user_id_created', 'user_id', 'created_at'),
    )