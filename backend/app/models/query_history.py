import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    user_question = Column(Text, nullable=False)
    intent_json = Column(JSON, nullable=True)
    generated_sql = Column(Text, nullable=True)
    execution_status = Column(String(50), nullable=False, default="success")
    row_count = Column(Integer, default=0)
    chart_type = Column(String(50), default="none")
    insight_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    dataset = relationship("Dataset", backref="query_histories")
