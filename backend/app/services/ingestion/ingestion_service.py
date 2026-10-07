import os
import uuid
import logging
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import engine, create_dataset_schema, drop_dataset_schema
from app.models.dataset import Dataset, DatasetTable
from app.services.ingestion.csv_service import CSVProcessor
from app.services.ingestion.excel_service import ExcelProcessor
from app.services.ingestion.sqlite_service import SQLiteProcessor
from app.services.schema.schema_service import SchemaService

logger = logging.getLogger("sqlens.ingestion_service")

ALLOWED_EXTENSIONS = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
    ".sqlite": "sqlite",
    ".db": "sqlite"
}

class IngestionService:
    @staticmethod
    def validate_file(file: UploadFile) -> Tuple[str, str]:
        """
        Validate file extension and file size.
        Returns (ext, file_type).
        """
        original_filename = os.path.basename(file.filename or "")
        ext = os.path.splitext(original_filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Please upload CSV, Excel (.xlsx, .xls), or SQLite (.db, .sqlite)."
            )

        file_type = ALLOWED_EXTENSIONS[ext]
        return ext, file_type

    @staticmethod
    async def process_file_upload(file: UploadFile, db: Session, session_id: str = None) -> Dataset:
        """
        Complete pipeline: validate, store, create isolated DB schema, ingest tables, record metadata, and discover schema relationships.
        """
        ext, file_type = IngestionService.validate_file(file)
        
        # Prevent path traversal: strip directory components
        raw_filename = os.path.basename(file.filename or "uploaded_data")
        display_name = os.path.splitext(raw_filename)[0]

        # Generate unique IDs
        dataset_id = str(uuid.uuid4())
        schema_name = f"ds_{uuid.uuid4().hex}"

        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
        stored_filename = f"{dataset_id}{ext}"
        storage_path = os.path.join(settings.UPLOAD_DIRECTORY, stored_filename)

        # Read file contents and check file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        contents = await file.read()
        file_size = len(contents)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File is too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # Save file to disk
        with open(storage_path, "wb") as f:
            f.write(contents)

        # Create initial metadata record with status PROCESSING
        dataset = Dataset(
            id=dataset_id,
            original_filename=raw_filename,
            display_name=display_name,
            file_type=file_type,
            file_size=file_size,
            status="PROCESSING",
            schema_name=schema_name,
            storage_path=storage_path,
            session_id=session_id
        )
        db.add(dataset)
        db.commit()

        # Ingestion phase with schema cleanup on failure
        try:
            # 1. Create dataset-isolated database schema
            create_dataset_schema(schema_name)

            # 2. Process file based on format and populate database tables
            if file_type == "csv":
                tables_metadata = CSVProcessor.process_csv(
                    storage_path, raw_filename, schema_name, engine
                )
            elif file_type == "excel":
                tables_metadata = ExcelProcessor.process_excel(
                    storage_path, raw_filename, schema_name, engine
                )
            elif file_type == "sqlite":
                tables_metadata = SQLiteProcessor.process_sqlite(
                    storage_path, raw_filename, schema_name, engine
                )
            else:
                raise ValueError(f"Unsupported file type '{file_type}'")

            # 3. Discover schema metadata, PKs, FKs, relationships and cache summary
            dataset = SchemaService.discover_and_cache_schema(dataset_id, db)

            return dataset

        except Exception as e:
            logger.error(f"Ingestion failed for dataset {dataset_id}: {e}", exc_info=True)
            
            # Clean up PostgreSQL/SQLite schema & file if needed
            try:
                drop_dataset_schema(schema_name)
            except Exception as cleanup_err:
                logger.error(f"Error dropping schema {schema_name} during cleanup: {cleanup_err}")

            dataset.status = "FAILED"
            dataset.error_message = str(e)
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ingestion failed: {str(e)}"
            )
