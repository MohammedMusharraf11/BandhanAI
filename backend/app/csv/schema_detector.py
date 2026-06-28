"""
Step 2 — LLM Schema Detection.

Calls the Groq LLM to classify a CSV file, identify a join key,
decide which columns to keep/drop, and map them to semantic names.
"""

import json
import logging

from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema Detection Prompt (from spec)
# ---------------------------------------------------------------------------

SCHEMA_DETECTION_PROMPT = """You are a data analyst. A business owner has uploaded a CSV file to a CRM system.

File name: {file_name}
Column headers: {headers}
Sample rows (first 5):
{sample_rows}

Your job:
1. Classify what type of data this file contains. Choose ONE: customers | orders | feedback | unknown
2. Identify the best join key — the column that uniquely identifies a customer. Prefer: email > phone > customer_id > id. If none exist, return null.
3. For every column, decide: KEEP or DROP.
   - KEEP if it has customer or business value (name, contact info, purchase data, behaviour, demographics, feedback)
   - DROP if it is: internal IDs with no business meaning, duplicate of another column, completely empty, system-generated timestamps with no analytical value, row numbers
4. For every KEEP column, map it to a semantic name using snake_case. Examples:
   - "Customer Name" → "name"
   - "Email Address" → "email"
   - "Last Purchase Date" → "last_purchase_date"
   - "Total Spend (INR)" → "total_spend"
   - "Churn Risk Score" → "churn_risk"
   - "Product Category" → "product_category"
   Keep names short, lowercase, snake_case, meaningful.

Return ONLY a JSON object. No explanation. No markdown. No preamble.
Format:
{{
  "source_type": "customers",
  "join_key": "email",
  "mapped_columns": {{
    "original_column_name": "semantic_name"
  }},
  "dropped_columns": ["col1", "col2"],
  "reasoning": "one sentence explaining your classification decision"
}}"""


def _parse_llm_json(text: str) -> dict:
    """
    Parse JSON from LLM response, stripping markdown code fences if present.
    """
    text = text.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        # Remove opening fence (possibly with language tag)
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
        elif "```" in text:
            text = text.rsplit("```", 1)[0].strip()

    return json.loads(text)


def _validate_mapping(mapping: dict) -> None:
    """Validate the LLM mapping has all required keys."""
    required_keys = {"source_type", "join_key", "mapped_columns", "dropped_columns"}
    missing = required_keys - set(mapping.keys())
    if missing:
        raise ValueError(f"LLM mapping is missing required keys: {missing}")

    valid_source_types = {"customers", "orders", "feedback", "unknown"}
    if mapping["source_type"] not in valid_source_types:
        mapping["source_type"] = "unknown"

    if not isinstance(mapping["mapped_columns"], dict):
        raise ValueError("mapped_columns must be a dict")

    if not isinstance(mapping["dropped_columns"], list):
        mapping["dropped_columns"] = []


async def detect_schema(
    file_name: str,
    headers: list[str],
    sample_rows: list[dict],
) -> dict:
    """
    Use LLM to classify a CSV and map its columns to semantic names.

    Args:
        file_name: Original filename of the uploaded CSV.
        headers: List of column header strings.
        sample_rows: First 5 rows as list of dicts.

    Returns:
        dict with keys: source_type, join_key, mapped_columns,
                        dropped_columns, reasoning

    Raises:
        ValueError: If LLM returns invalid/unparseable JSON after retry.
    """
    prompt = SCHEMA_DETECTION_PROMPT.format(
        file_name=file_name,
        headers=json.dumps(headers),
        sample_rows=json.dumps(sample_rows, indent=2, default=str),
    )

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

    # Attempt 1
    last_error = None
    for attempt in range(2):
        try:
            response = llm.invoke(prompt)
            response_text = response.content
            logger.info(
                f"Schema detection attempt {attempt + 1} — "
                f"raw response length: {len(response_text)}"
            )

            mapping = _parse_llm_json(response_text)
            _validate_mapping(mapping)

            logger.info(
                f"Schema detected: source_type={mapping['source_type']}, "
                f"join_key={mapping['join_key']}, "
                f"kept={len(mapping['mapped_columns'])}, "
                f"dropped={len(mapping['dropped_columns'])}"
            )
            return mapping

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(
                f"Schema detection attempt {attempt + 1} failed: {e}"
            )
            if attempt == 0:
                logger.info("Retrying schema detection...")
                continue

    raise ValueError(
        f"Schema detection failed after 2 attempts. "
        f"Last error: {str(last_error)}"
    )
