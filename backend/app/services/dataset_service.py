import os
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from app.core.database import engine, drop_dataset_schema
from app.models.dataset import Dataset, DatasetTable

logger = logging.getLogger("sqlens.dataset_service")

class DatasetService:
    @staticmethod
    def get_datasets(db: Session, session_id: Optional[str] = None) -> List[Dataset]:
        """Fetch all datasets stored in the database."""
        query = db.query(Dataset)
        if session_id:
            query = query.filter((Dataset.session_id == session_id) | (Dataset.session_id.is_(None)))
        return query.order_by(Dataset.created_at.desc()).all()

    @staticmethod
    def get_dataset_by_id(dataset_id: str, db: Session, session_id: Optional[str] = None) -> Dataset:
        """Fetch a single dataset by ID."""
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset with ID '{dataset_id}' not found."
            )
        return dataset

    @staticmethod
    def get_dataset_tables(dataset_id: str, db: Session, session_id: Optional[str] = None) -> List[DatasetTable]:
        """Fetch tables for a specific dataset."""
        dataset = DatasetService.get_dataset_by_id(dataset_id, db)
        return dataset.tables

    @staticmethod
    def get_table_preview(
        dataset_id: str,
        table_name: str,
        limit: int,
        offset: int,
        db: Session,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch a paginated row preview from the dataset's isolated PostgreSQL/SQLite schema table.
        Safe against JSON serialization crashes.
        """
        dataset = DatasetService.get_dataset_by_id(dataset_id, db)
        
        if dataset.status != "READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dataset is not ready. Current status: {dataset.status}"
            )

        # Find table record in metadata
        table_record = db.query(DatasetTable).filter(
            DatasetTable.dataset_id == dataset_id,
            DatasetTable.table_name == table_name
        ).first()

        if not table_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table '{table_name}' not found in dataset '{dataset_id}'."
            )

        safe_limit = min(max(1, limit), 100)
        safe_offset = max(0, offset)
        schema_name = dataset.schema_name

        try:
            with engine.connect() as conn:
                if engine.name == "postgresql":
                    query_str = f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {safe_limit} OFFSET {safe_offset}'
                else:
                    query_str = f'SELECT * FROM "{schema_name}__{table_name}" LIMIT {safe_limit} OFFSET {safe_offset}'
                
                result = conn.execute(text(query_str))
                columns = list(result.keys())
                rows = []
                for row in result.fetchall():
                    row_dict = {}
                    for col, val in zip(columns, row):
                        if isinstance(val, (bytes, bytearray)):
                            val = f"<binary {len(val)} bytes>"
                        elif hasattr(val, "isoformat"):
                            val = val.isoformat()
                        elif val is None:
                            val = None
                        row_dict[col] = val
                    rows.append(row_dict)
        except Exception as e:
            logger.error(f"Error querying table preview for {schema_name}.{table_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch table data preview: {str(e)}"
            )

        return {
            "dataset_id": dataset_id,
            "table_name": table_name,
            "total_rows": table_record.row_count,
            "columns": table_record.columns_json,
            "rows": rows,
            "limit": safe_limit,
            "offset": safe_offset
        }

    @staticmethod
    def delete_dataset(dataset_id: str, db: Session, session_id: Optional[str] = None) -> bool:
        """
        Safely delete a dataset:
        1. Drop isolated PostgreSQL/SQLite schema tables
        2. Delete stored physical source file
        3. Delete associated query history records
        4. Delete metadata record
        """
        dataset = DatasetService.get_dataset_by_id(dataset_id, db)

        try:
            drop_dataset_schema(dataset.schema_name)
        except Exception as e:
            logger.error(f"Error dropping database schema '{dataset.schema_name}': {e}")

        if dataset.storage_path and os.path.exists(dataset.storage_path):
            try:
                os.remove(dataset.storage_path)
            except Exception as e:
                logger.error(f"Error removing source file '{dataset.storage_path}': {e}")

        try:
            from app.models.query_history import QueryHistory
            db.query(QueryHistory).filter(QueryHistory.dataset_id == dataset_id).delete(synchronize_session=False)
        except Exception as e:
            logger.error(f"Error deleting query history for dataset {dataset_id}: {e}")

        db.delete(dataset)
        db.commit()

        return True
