import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # csv, excel, sqlite
    file_size = Column(BigInteger, nullable=False)  # in bytes
    status = Column(String(50), nullable=False, default="PROCESSING")  # UPLOADING, PROCESSING, READY, FAILED
    schema_name = Column(String(63), nullable=False, unique=True)  # PG schema name
    storage_path = Column(Text, nullable=False)
    number_of_tables = Column(Integer, default=0)
    total_rows = Column(BigInteger, default=0)
    total_columns = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    tables = relationship("DatasetTable", back_populates="dataset", cascade="all, delete-orphan")
    relationships = relationship("DatasetRelationship", back_populates="dataset", cascade="all, delete-orphan")

class DatasetTable(Base):
    __tablename__ = "dataset_tables"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String(63), nullable=False)
    display_name = Column(String(255), nullable=False)
    row_count = Column(BigInteger, default=0)
    column_count = Column(Integer, default=0)
    columns_json = Column(JSON, nullable=False, default=list)
    primary_keys_json = Column(JSON, nullable=False, default=list)
    foreign_keys_json = Column(JSON, nullable=False, default=list)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="tables")

class DatasetRelationship(Base):
    __tablename__ = "dataset_relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_table = Column(String(63), nullable=False)
    source_column = Column(String(63), nullable=False)
    target_table = Column(String(63), nullable=False)
    target_column = Column(String(63), nullable=False)
    relationship_type = Column(String(50), nullable=False, default="many_to_one")
    is_confirmed = Column(Boolean, nullable=False, default=True)  # True = FK constraint, False = Inferred
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    dataset = relationship("Dataset", back_populates="relationships")
