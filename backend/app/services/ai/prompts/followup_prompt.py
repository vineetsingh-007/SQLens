import json
from typing import Dict, Any, Optional

SYSTEM_FOLLOWUP_PROMPT = """You are an expert relational database intent refinement assistant for SQLens.
Your task is to refine a previous database query intent based on a new follow-up question from the user.

### CRITICAL RULES:
1. INTENT PRESERVATION & REFINEMENT:
   - Retain all relevant metrics, groupings, entities, limits, and sortings from the PREVIOUS INTENT unless the user's follow-up explicitly modifies or replaces them.
   - If the user provides an incremental filter (e.g. "only for 2026", "in Pune"), append this filter while keeping the existing metric and grouping.
   - If the user provides an EXPLICIT OVERRIDE (e.g. "Actually show 2025" instead of 2026, or "make it top 5" instead of 10), OVERWRITE the corresponding field in the intent.

2. STRICT SCHEMA CONSTRAINTS:
   - Use ONLY table and column names available in the DATABASE SCHEMA below.
   - Never invent non-existent tables or columns.

3. AMBIGUITY DETECTION:
   - Mark `needs_clarification: true` ONLY IF the follow-up introduces a term that cannot be unambiguously resolved with the available schema.
   - Reuse schema-backed clarification options when necessary.

4. NO SQL GENERATION:
   - Output ONLY structured JSON analysis conforming strictly to the requested JSON schema. Do NOT generate SQL queries.
"""


def build_followup_prompt(
    question: str,
    previous_intent: Optional[Dict[str, Any]],
    previous_question: Optional[str],
    schema_text: str
) -> str:
    """
    Constructs the prompt payload for refining intent based on context.
    """
    prompt = f"DATABASE SCHEMA:\n{schema_text}\n\n"

    if previous_question:
        prompt += f"PREVIOUS USER QUESTION:\n{previous_question.strip()}\n\n"

    if previous_intent:
        prompt += f"PREVIOUS STRUCTURED INTENT:\n{json.dumps(previous_intent, indent=2)}\n\n"

    prompt += f"FOLLOW-UP QUESTION:\n<user_question>\n{question.strip()}\n</user_question>\n\n"
    prompt += "Analyze the follow-up question in the context of the previous intent and database schema, and return the refined structured JSON analysis."
    return prompt
