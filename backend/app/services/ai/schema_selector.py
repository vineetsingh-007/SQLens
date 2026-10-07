import re
from typing import List, Dict, Any, Set


class SchemaSelector:
    """
    Deterministic schema selection and formatting utility.
    Filters database schema to relevant tables/columns based on token matching and foreign keys,
    and formats them into clean text representation for LLM prompt context.
    """

    @staticmethod
    def extract_tokens(text: str) -> Set[str]:
        """Extract lowercase alphanumeric tokens from text."""
        if not text:
            return set()
        words = re.findall(r'[a-zA-Z0-9_]+', text.lower())
        # Add basic stemming/plural removal (e.g., 'customers' -> 'customer')
        tokens = set(words)
        for w in words:
            if w.endswith('s') and len(w) > 3:
                tokens.add(w[:-1])
            if w.endswith('es') and len(w) > 4:
                tokens.add(w[:-2])
        return tokens

    @classmethod
    def select_relevant_schema(
        cls,
        tables_metadata: List[Dict[str, Any]],
        relationships_metadata: List[Dict[str, Any]],
        question: str
    ) -> Dict[str, Any]:
        """
        Determines relevant tables based on token matching and relationship expansion.
        Returns dictionary containing relevant tables and formatted schema string.
        """
        question_tokens = cls.extract_tokens(question)

        matched_table_names: Set[str] = set()
        all_table_names: Set[str] = {t["table_name"] for t in tables_metadata}

        # 1. Match tokens against table names and column names
        for t in tables_metadata:
            t_name = t["table_name"]
            t_display = t.get("display_name", "")
            t_tokens = cls.extract_tokens(t_name) | cls.extract_tokens(t_display)

            # Check if any question token matches table name
            if question_tokens & t_tokens:
                matched_table_names.add(t_name)
                continue

            # Check column names
            columns = t.get("columns", [])
            for col in columns:
                col_name = col.get("name", "")
                col_display = col.get("display_name", "")
                col_tokens = cls.extract_tokens(col_name) | cls.extract_tokens(col_display)
                if question_tokens & col_tokens:
                    matched_table_names.add(t_name)
                    break

        # 2. Relationship Expansion: Include FK related tables for matched tables
        expanded_table_names = set(matched_table_names)
        for rel in relationships_metadata:
            from_t = rel.get("from_table")
            to_t = rel.get("to_table")

            if from_t in matched_table_names and to_t in all_table_names:
                expanded_table_names.add(to_t)
            if to_t in matched_table_names and from_t in all_table_names:
                expanded_table_names.add(from_t)

        # 3. Fallback: If no tables matched, include all tables to avoid under-contextualization
        if not expanded_table_names:
            expanded_table_names = set(all_table_names)

        # 4. Build selected schema metadata
        selected_tables = [t for t in tables_metadata if t["table_name"] in expanded_table_names]

        # 5. Format schema text
        schema_text_lines = []
        for t in selected_tables:
            schema_text_lines.append(f"TABLE: {t['table_name']}")

            # PKs and FKs lookup maps
            pks = set(t.get("primary_keys", []))
            fks = {fk["column_name"]: fk for fk in t.get("foreign_keys", [])}

            for col in t.get("columns", []):
                col_name = col.get("name")
                col_type = col.get("type", "text")

                annotations = []
                if col_name in pks or col.get("is_primary_key"):
                    annotations.append("PRIMARY KEY")
                if col_name in fks:
                    fk_info = fks[col_name]
                    annotations.append(f"FOREIGN KEY -> {fk_info['referenced_table']}.{fk_info['referenced_column']}")
                elif col.get("is_foreign_key") and col.get("referenced_table"):
                    annotations.append(f"FOREIGN KEY -> {col.get('referenced_table')}.{col.get('referenced_column')}")

                anno_str = f" [{', '.join(annotations)}]" if annotations else ""
                schema_text_lines.append(f"  - {col_name}: {col_type.lower()}{anno_str}")

            schema_text_lines.append("")

        # Add relationships section
        if relationships_metadata:
            schema_text_lines.append("RELATIONSHIPS:")
            for rel in relationships_metadata:
                from_t = rel.get("from_table")
                to_t = rel.get("to_table")
                if from_t in expanded_table_names and to_t in expanded_table_names:
                    conf = "Confirmed" if rel.get("is_confirmed") else "Inferred"
                    schema_text_lines.append(
                        f"  - {from_t}.{rel.get('from_column')} -> {to_t}.{rel.get('to_column')} ({conf})"
                    )

        schema_text = "\n".join(schema_text_lines)

        return {
            "relevant_table_names": list(expanded_table_names),
            "selected_tables": selected_tables,
            "schema_text": schema_text
        }
