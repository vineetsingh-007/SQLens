export type FileType = 'csv' | 'excel' | 'sqlite';
export type DatasetStatus = 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED';

export interface ColumnInfo {
  name: string;
  type: string;
  raw_type?: string;
  display_name: string;
  nullable?: boolean;
  default_value?: string | null;
  is_primary_key?: boolean;
  is_foreign_key?: boolean;
  referenced_table?: string | null;
  referenced_column?: string | null;
}

export interface Relationship {
  id?: string;
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  relationship_type: string;
  is_confirmed: boolean;
}

export interface DatasetTable {
  id: string;
  table_name: string;
  display_name: string;
  row_count: number;
  column_count: number;
  columns_json: ColumnInfo[];
  primary_keys_json?: string[];
  foreign_keys_json?: Record<string, any>[];
  created_at: string;
}

export interface ColumnStatistics {
  column_name: string;
  display_name: string;
  data_type: string;
  null_count: number;
  non_null_count: number;
  min_value?: any;
  max_value?: any;
  avg_value?: number | null;
  distinct_count?: number | null;
  true_count?: number | null;
  false_count?: number | null;
  sample_values?: any[];
}

export interface TableStatistics {
  table_name: string;
  display_name: string;
  total_rows: number;
  total_columns: number;
  total_missing_values: number;
  columns_stats: ColumnStatistics[];
}

export interface DatasetSchemaResponse {
  dataset_id: string;
  original_filename: string;
  schema_name: string;
  number_of_tables: number;
  total_rows: number;
  total_columns: number;
  tables: DatasetTable[];
  relationships: Relationship[];
}

export interface Dataset {
  id: string;
  original_filename: string;
  display_name: string;
  file_type: FileType;
  file_size: number;
  status: DatasetStatus;
  number_of_tables: number;
  total_rows: number;
  total_columns: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
  tables?: DatasetTable[];
  relationships?: Relationship[];
}

export interface UploadResponse {
  success: boolean;
  dataset_id: string;
  filename: string;
  file_type: string;
  status: string;
  number_of_tables: number;
  tables: string[];
  message?: string;
}

export interface PaginatedPreviewResponse {
  dataset_id: string;
  table_name: string;
  total_rows: number;
  total_pages: number;
  page: number;
  page_size: number;
  columns: ColumnInfo[];
  rows: Record<string, any>[];
}

export interface HealthResponse {
  status: string;
  service: string;
  database: string;
}
