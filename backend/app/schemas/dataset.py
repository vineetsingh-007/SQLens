from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict

class ColumnInfo(BaseModel):
    name: str
    type: str  # Normalized type for display (e.g. Integer, Text, Decimal, DateTime)
    raw_type: Optional[str] = None  # Actual PG/SQL type (e.g. character varying(255), bigint)
    display_name: str
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    referenced_table: Optional[str] = None
    referenced_column: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RelationshipSchema(BaseModel):
    id: Optional[str] = None
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "many_to_one"
    is_confirmed: bool = True

    model_config = ConfigDict(from_attributes=True)

class DatasetTableResponse(BaseModel):
    id: str
    table_name: str
    display_name: str
    row_count: int
    column_count: int
    columns_json: List[ColumnInfo]
    primary_keys_json: List[str] = []
    foreign_keys_json: List[Dict[str, Any]] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DatasetResponse(BaseModel):
    id: str
    original_filename: str
    display_name: str
    file_type: str
    file_size: int
    status: str
    number_of_tables: int
    total_rows: int
    total_columns: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tables: Optional[List[DatasetTableResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class UploadResponse(BaseModel):
    success: bool
    dataset_id: str
    filename: str
    file_type: str
    status: str
    number_of_tables: int
    tables: List[str]
    message: Optional[str] = None

class PaginatedPreviewResponse(BaseModel):
    dataset_id: str
    table_name: str
    total_rows: int
    total_pages: int
    page: int
    page_size: int
    columns: List[ColumnInfo]
    rows: List[Dict[str, Any]]

class ColumnStatisticsSchema(BaseModel):
    column_name: str
    display_name: str
    data_type: str
    null_count: int
    non_null_count: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    avg_value: Optional[float] = None
    distinct_count: Optional[int] = None
    true_count: Optional[int] = None
    false_count: Optional[int] = None
    sample_values: List[Any] = []

class TableStatisticsSchema(BaseModel):
    table_name: str
    display_name: str
    total_rows: int
    total_columns: int
    total_missing_values: int
    columns_stats: List[ColumnStatisticsSchema]

class DatasetSchemaResponse(BaseModel):
    dataset_id: str
    original_filename: str
    schema_name: str
    number_of_tables: int
    total_rows: int
    total_columns: int
    tables: List[DatasetTableResponse]
    relationships: List[RelationshipSchema]

class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
