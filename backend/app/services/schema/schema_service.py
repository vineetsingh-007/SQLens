import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models.dataset import Dataset, DatasetTable, DatasetRelationship
from app.services.schema.metadata_service import MetadataService
from app.services.schema.relationship_service import RelationshipService
from app.services.schema.statistics_service import StatisticsService

logger = logging.getLogger("sqlens.schema_service")

class SchemaService:
    @staticmethod
    def discover_and_cache_schema(dataset_id: str, db: Session) -> Dataset:
        """
        Extract schema metadata, discover relationships, update DB cache, and compute totals.
        """
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

        # 1. Discover table definitions
        tables_meta = MetadataService.discover_schema(dataset.schema_name, engine)

        # 2. Discover relationships (FK constraints + inferred)
        relationships_meta = RelationshipService.discover_relationships(tables_meta)

        # 3. Clear old cached tables & relationships
        db.query(DatasetTable).filter(DatasetTable.dataset_id == dataset_id).delete()
        db.query(DatasetRelationship).filter(DatasetRelationship.dataset_id == dataset_id).delete()

        # 4. Insert table records
        tot_rows = 0
        tot_cols = 0

        for tbl in tables_meta:
            table_rec = DatasetTable(
                dataset_id=dataset_id,
                table_name=tbl["table_name"],
                display_name=tbl["display_name"],
                row_count=tbl["row_count"],
                column_count=tbl["column_count"],
                columns_json=tbl["columns_json"],
                primary_keys_json=tbl.get("primary_keys_json", []),
                foreign_keys_json=tbl.get("foreign_keys_json", [])
            )
            db.add(table_rec)
            tot_rows += tbl["row_count"]
            tot_cols += tbl["column_count"]

        # 5. Insert relationship records
        for rel in relationships_meta:
            rel_rec = DatasetRelationship(
                dataset_id=dataset_id,
                source_table=rel["source_table"],
                source_column=rel["source_column"],
                target_table=rel["target_table"],
                target_column=rel["target_column"],
                relationship_type=rel.get("relationship_type", "many_to_one"),
                is_confirmed=rel.get("is_confirmed", True)
            )
            db.add(rel_rec)

        # 6. Update Dataset summary
        dataset.number_of_tables = len(tables_meta)
        dataset.total_rows = tot_rows
        dataset.total_columns = tot_cols
        dataset.status = "READY"
        db.commit()
        db.refresh(dataset)

        return dataset

    @staticmethod
    def get_full_schema(dataset_id: str, db: Session) -> Dict[str, Any]:
        """
        Return the cached schema structure for a dataset.
        """
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

        tables = db.query(DatasetTable).filter(DatasetTable.dataset_id == dataset_id).all()
        relationships = db.query(DatasetRelationship).filter(DatasetRelationship.dataset_id == dataset_id).all()

        return {
            "dataset_id": dataset.id,
            "original_filename": dataset.original_filename,
            "schema_name": dataset.schema_name,
            "number_of_tables": dataset.number_of_tables,
            "total_rows": dataset.total_rows,
            "total_columns": dataset.total_columns,
            "tables": tables,
            "relationships": relationships
        }
