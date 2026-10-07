import os
import pandas as pd
import logging
from sqlalchemy import Engine
from app.services.ingestion.normalizer import sanitize_identifier, sanitize_dataframe

logger = logging.getLogger("sqlens.csv_service")

class CSVProcessor:
    @staticmethod
    def process_csv(file_path: str, original_filename: str, schema_name: str, engine: Engine) -> list[dict]:
        """
        Process a CSV file and load it into an isolated database schema.
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise ValueError("This CSV file is empty or does not exist.")

        # Try common encodings
        df = None
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        last_err = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, low_memory=False)
                break
            except Exception as e:
                last_err = e
                continue

        if df is None:
            raise ValueError(f"Unable to read CSV file: {last_err or 'Format unreadable'}")

        if df.empty and len(df.columns) == 0:
            raise ValueError("This CSV file does not contain usable tabular data.")

        # Clean dataframe and extract column metadata
        df, columns_metadata = sanitize_dataframe(df)
        
        # Derive table name from filename
        file_stem = os.path.splitext(original_filename)[0]
        table_name = sanitize_identifier(file_stem, is_table=True)

        row_count = len(df)
        col_count = len(columns_metadata)

        # Write to PostgreSQL isolated schema
        try:
            if engine.name == "postgresql":
                df.to_sql(
                    name=table_name,
                    con=engine,
                    schema=schema_name,
                    if_exists="replace",
                    index=False
                )
            else:
                # SQLite fallback for testing environments
                sqlite_table_name = f"{schema_name}__{table_name}"
                df.to_sql(
                    name=sqlite_table_name,
                    con=engine,
                    if_exists="replace",
                    index=False
                )
        except Exception as e:
            logger.error(f"Failed to write CSV data to database: {e}")
            raise RuntimeError(f"Database import failed: {e}")

        return [{
            "table_name": table_name,
            "display_name": file_stem,
            "row_count": row_count,
            "column_count": col_count,
            "columns_json": columns_metadata
        }]
