import logging
from typing import List, Dict, Any

logger = logging.getLogger("sqlens.relationship_service")

class RelationshipService:
    @staticmethod
    def discover_relationships(tables_meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Discover both confirmed database foreign keys and inferred relationships across tables.
        """
        relationships = []
        seen_keys = set()

        # 1. Extract confirmed Foreign Key relationships
        for table in tables_meta:
            src_tbl = table["table_name"]
            for fk in table.get("foreign_keys_json", []):
                src_col = fk["column"]
                tgt_tbl = fk["referenced_table"]
                tgt_col = fk["referenced_column"]

                key = (src_tbl, src_col, tgt_tbl, tgt_col)
                if key not in seen_keys:
                    seen_keys.add(key)
                    relationships.append({
                        "source_table": src_tbl,
                        "source_column": src_col,
                        "target_table": tgt_tbl,
                        "target_column": tgt_col,
                        "relationship_type": "many_to_one",
                        "is_confirmed": True
                    })

        # 2. Extract Inferred relationships for tables missing formal FK constraints
        table_map = {t["table_name"]: t for t in tables_meta}

        for src_name, src_tbl in table_map.items():
            for src_col in src_tbl.get("columns_json", []):
                s_col_name = src_col["name"]
                
                # Check if column name looks like a foreign key reference (e.g., customer_id, product_id)
                if s_col_name.endswith("_id") and len(s_col_name) > 3:
                    target_candidate_stem = s_col_name[:-3]  # e.g., "customer"
                    
                    # Find candidate target table (e.g., "customers", "customer", "products")
                    for tgt_name, tgt_tbl in table_map.items():
                        if src_name == tgt_name:
                            continue
                        
                        # Match candidate table name (e.g. "customer" stem matches "customers" or "customer")
                        if tgt_name in (target_candidate_stem, f"{target_candidate_stem}s", f"{target_candidate_stem}es"):
                            # Find matching primary key or ID column in target table
                            for tgt_col in tgt_tbl.get("columns_json", []):
                                t_col_name = tgt_col["name"]
                                if t_col_name in (s_col_name, "id", f"{target_candidate_stem}_id"):
                                    key = (src_name, s_col_name, tgt_name, t_col_name)
                                    if key not in seen_keys:
                                        seen_keys.add(key)
                                        relationships.append({
                                            "source_table": src_name,
                                            "source_column": s_col_name,
                                            "target_table": tgt_name,
                                            "target_column": t_col_name,
                                            "relationship_type": "many_to_one",
                                            "is_confirmed": False
                                        })

        return relationships
