import os
import sqlite3
import pandas as pd
import logging
from typing import Set
from sqlalchemy import Engine
from app.services.ingestion.normalizer import sanitize_identifier, sanitize_dataframe

logger = logging.getLogger("sqlens.sqlite_service")

class SQLiteProcessor:
    @staticmethod
    def process_sqlite(file_path: str, original_filename: str, schema_name: str, engine: Engine) -> list[dict]:
        """
        Process a SQLite database (.db, .sqlite) safely in read-only mode,
        extracting all user tables and importing them into the target database schema.
        Original SQLite file is NOT modified.
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise ValueError("This SQLite file is empty or does not exist.")

        # Open SQLite in read-only mode
        abs_path = os.path.abspath(file_path)
        sqlite_uri = f"file:{abs_path}?mode=ro"

        try:
            conn = sqlite3.connect(sqlite_uri, uri=True)
            cursor = conn.cursor()
            
            # Fetch user table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to open SQLite database: {e}")
            raise ValueError("Unable to read this SQLite file. The file may be corrupted or invalid.")

        if not tables:
            conn.close()
            raise ValueError("No user tables were found in this SQLite database.")

        tables_metadata = []
        seen_table_names: Set[str] = set()

        for raw_table_name in tables:
            try:
                # Read table into dataframe using parameterized/quoted table name
                query = f'SELECT * FROM "{raw_table_name}"'
                df = pd.read_sql_query(query, conn)
            except Exception as e:
                logger.warning(f"Could not read SQLite table '{raw_table_name}': {e}")
                continue

            if df.empty and len(df.columns) == 0:
                logger.info(f"Skipping empty SQLite table '{raw_table_name}'")
                continue

            # Sanitize dataframe and column names
            df, col_metadata = sanitize_dataframe(df)

            clean_table_name = sanitize_identifier(raw_table_name, is_table=True)
            
            candidate = clean_table_name
            counter = 2
            while candidate in seen_table_names:
                candidate = f"{clean_table_name}_{counter}"
                counter += 1
            seen_table_names.add(candidate)
            table_name = candidate

            row_count = len(df)
            col_count = len(col_metadata)

            # Import to target DB schema
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
                    sqlite_table_name = f"{schema_name}__{table_name}"
                    df.to_sql(
                        name=sqlite_table_name,
                        con=engine,
                        if_exists="replace",
                        index=False
                    )

                tables_metadata.append({
                    "table_name": table_name,
                    "display_name": raw_table_name,
                    "row_count": row_count,
                    "column_count": col_count,
                    "columns_json": col_metadata
                })
            except Exception as e:
                logger.error(f"Failed to write SQLite table '{raw_table_name}' to database: {e}")

        conn.close()

        if not tables_metadata:
            raise ValueError("No usable data tables were found in this SQLite file.")

        return tables_metadata
