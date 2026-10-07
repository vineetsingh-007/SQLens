import os
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Header, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.core.config import settings
from app.schemas.dataset import (
    DatasetResponse,
    DatasetTableResponse,
    UploadResponse,
    PaginatedPreviewResponse,
    DatasetSchemaResponse,
    RelationshipSchema,
    TableStatisticsSchema
)
from app.services.ingestion.ingestion_service import IngestionService
from app.services.dataset_service import DatasetService
from app.services.schema.schema_service import SchemaService
from app.services.schema.statistics_service import StatisticsService

router = APIRouter()

@router.post("/datasets/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Upload a CSV, Excel, or SQLite file for processing, dataset schema import, and relationship discovery."""
    dataset = await IngestionService.process_file_upload(file, db, session_id=x_session_id)
    table_names = [t.table_name for t in dataset.tables]

    return UploadResponse(
        success=True,
        dataset_id=dataset.id,
        filename=dataset.original_filename,
        file_type=dataset.file_type,
        status=dataset.status,
        number_of_tables=dataset.number_of_tables,
        tables=table_names,
        message="Dataset created, tables imported, and relationships discovered successfully."
    )

@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve all uploaded datasets for the current session."""
    return DatasetService.get_datasets(db, session_id=x_session_id)

@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve metadata and table summary for a specific dataset."""
    return DatasetService.get_dataset_by_id(dataset_id, db, session_id=x_session_id)

@router.get("/datasets/{dataset_id}/schema", response_model=DatasetSchemaResponse)
def get_dataset_schema(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve full schema metadata including tables, columns, primary keys, foreign keys, and relationships."""
    DatasetService.get_dataset_by_id(dataset_id, db, session_id=x_session_id)
    schema_data = SchemaService.get_full_schema(dataset_id, db)
    return DatasetSchemaResponse(**schema_data)

@router.post("/datasets/{dataset_id}/schema/refresh", response_model=DatasetSchemaResponse)
def refresh_dataset_schema(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Re-inspect the database schema, update metadata cache, relationships, and return the refreshed schema."""
    DatasetService.get_dataset_by_id(dataset_id, db, session_id=x_session_id)
    SchemaService.discover_and_cache_schema(dataset_id, db)
    schema_data = SchemaService.get_full_schema(dataset_id, db)
    return DatasetSchemaResponse(**schema_data)

@router.get("/datasets/{dataset_id}/tables", response_model=List[DatasetTableResponse])
def get_dataset_tables(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve table metadata for a dataset."""
    return DatasetService.get_dataset_tables(dataset_id, db, session_id=x_session_id)

@router.get("/datasets/{dataset_id}/tables/{table_name}", response_model=DatasetTableResponse)
def get_table_details(
    dataset_id: str,
    table_name: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve detailed column and key definitions for a single table."""
    tables = DatasetService.get_dataset_tables(dataset_id, db, session_id=x_session_id)
    for tbl in tables:
        if tbl.table_name == table_name:
            return tbl
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Table '{table_name}' not found in dataset '{dataset_id}'."
    )

@router.get("/datasets/{dataset_id}/tables/{table_name}/statistics", response_model=TableStatisticsSchema)
def get_table_statistics(
    dataset_id: str,
    table_name: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Calculate data quality metrics and column-level statistics for a table."""
    dataset = DatasetService.get_dataset_by_id(dataset_id, db, session_id=x_session_id)
    tbl = get_table_details(dataset_id, table_name, x_session_id, db)

    stats = StatisticsService.calculate_table_statistics(
        schema_name=dataset.schema_name,
        table_name=table_name,
        columns_meta=tbl.columns_json,
        engine=engine
    )
    return TableStatisticsSchema(**stats)

@router.get("/datasets/{dataset_id}/relationships", response_model=List[RelationshipSchema])
def get_dataset_relationships(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Retrieve confirmed foreign keys and inferred relationships for a dataset."""
    schema_data = SchemaService.get_full_schema(dataset_id, db)
    return schema_data["relationships"]

@router.get("/datasets/{dataset_id}/preview/{table_name}", response_model=PaginatedPreviewResponse)
def preview_table(
    dataset_id: str,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Fetch paginated preview of data rows for a specific table."""
    offset = (page - 1) * page_size
    preview_data = DatasetService.get_table_preview(
        dataset_id=dataset_id,
        table_name=table_name,
        limit=page_size,
        offset=offset,
        db=db,
        session_id=x_session_id
    )

    total_rows = preview_data["total_rows"]
    total_pages = max(1, math.ceil(total_rows / page_size))

    return PaginatedPreviewResponse(
        dataset_id=dataset_id,
        table_name=table_name,
        total_rows=total_rows,
        total_pages=total_pages,
        page=page,
        page_size=page_size,
        columns=preview_data["columns"],
        rows=preview_data["rows"]
    )

@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Delete a dataset, dropping its isolated database schema, files, and metadata."""
    success = DatasetService.delete_dataset(dataset_id, db, session_id=x_session_id)
    return {"success": success, "message": f"Dataset '{dataset_id}' deleted successfully."}

@router.post("/datasets/sample", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def load_sample_dataset(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """Quickly ingest the built-in multi-sheet sample dataset (sample_sales.xlsx)."""
    sample_file = os.path.join(settings.SAMPLE_DATA_DIRECTORY, "sample_sales.xlsx")
    if not os.path.exists(sample_file):
        sample_file = os.path.join(settings.SAMPLE_DATA_DIRECTORY, "sample_customers.csv")

    if not os.path.exists(sample_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample dataset file not found on server."
        )

    with open(sample_file, "rb") as f:
        content = f.read()

    from io import BytesIO
    filename = os.path.basename(sample_file)
    upload_file = UploadFile(filename=filename, file=BytesIO(content))
    
    dataset = await IngestionService.process_file_upload(upload_file, db, session_id=x_session_id)
    table_names = [t.table_name for t in dataset.tables]

    return UploadResponse(
        success=True,
        dataset_id=dataset.id,
        filename=dataset.original_filename,
        file_type=dataset.file_type,
        status=dataset.status,
        number_of_tables=dataset.number_of_tables,
        tables=table_names,
        message="Sample dataset imported successfully."
    )
