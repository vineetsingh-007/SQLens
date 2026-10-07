import os
import pandas as pd
import logging
from typing import Set
from sqlalchemy import Engine
from app.services.ingestion.normalizer import sanitize_identifier, sanitize_dataframe

logger = logging.getLogger("sqlens.excel_service")

class ExcelProcessor:
    @staticmethod
    def process_excel(file_path: str, original_filename: str, schema_name: str, engine: Engine) -> list[dict]:
        """
        Process an Excel workbook (.xlsx, .xls) and import usable sheets into database schema.
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            raise ValueError("This Excel file is empty or does not exist.")

        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
        except Exception as e:
            logger.error(f"Failed to open Excel file: {e}")
            raise ValueError("Unable to read this Excel file. The file may be corrupted or invalid.")

        if not sheet_names:
            raise ValueError("This Excel file contains no worksheets.")

        tables_metadata = []
        seen_table_names: Set[str] = set()

        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
            except Exception as e:
                logger.warning(f"Could not read sheet '{sheet_name}': {e}")
                continue

            # Skip empty sheet
            if df.empty and len(df.columns) == 0:
                logger.info(f"Skipping empty sheet '{sheet_name}'")
                continue

            # Remove entirely empty rows and columns
            df = df.dropna(how="all").dropna(axis=1, how="all")

            if df.empty or len(df.columns) == 0:
                logger.info(f"Skipping sheet '{sheet_name}' - no usable data after dropping blank rows/columns")
                continue

            # Clean dataframe and columns
            df, col_metadata = sanitize_dataframe(df)

            # Derive table name from sheet_name
            clean_table_name = sanitize_identifier(sheet_name, is_table=True)
            
            # Deduplicate table names in workbook
            candidate = clean_table_name
            counter = 2
            while candidate in seen_table_names:
                candidate = f"{clean_table_name}_{counter}"
                counter += 1
            seen_table_names.add(candidate)
            table_name = candidate

            row_count = len(df)
            col_count = len(col_metadata)

            # Import into database
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
                    "display_name": sheet_name,
                    "row_count": row_count,
                    "column_count": col_count,
                    "columns_json": col_metadata
                })
            except Exception as e:
                logger.error(f"Failed to write Excel sheet '{sheet_name}' to database: {e}")

        if not tables_metadata:
            raise ValueError("No usable tables were found in this Excel file.")

        return tables_metadata
