"""
Step 4 — Data Cleaning & Transformation.

Takes a DataFrame + confirmed column mapping and produces a list of clean
dicts ready for DB insertion, with type coercion and value normalization.
"""

import logging
import re
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def _is_date_column(col_name: str) -> bool:
    """Check if a column name suggests a date field."""
    date_keywords = ["date", "_at", "timestamp", "created", "updated", "purchased"]
    return any(kw in col_name.lower() for kw in date_keywords)


def _is_monetary_column(col_name: str) -> bool:
    """Check if a column name suggests a monetary/financial field."""
    money_keywords = ["spend", "amount", "revenue", "price", "cost", "income", "salary", "total"]
    return any(kw in col_name.lower() for kw in money_keywords)


def _is_score_column(col_name: str) -> bool:
    """Check if a column name suggests a score/rate field."""
    score_keywords = ["risk", "score", "rate", "ratio", "percentage", "pct"]
    return any(kw in col_name.lower() for kw in score_keywords)


def _is_count_column(col_name: str) -> bool:
    """Check if a column name suggests an integer count field."""
    count_keywords = ["count", "quantity", "qty", "age", "num", "number"]
    return any(kw in col_name.lower() for kw in count_keywords)


def _parse_date(val) -> str | None:
    """Try to parse a value as a date and return ISO format string."""
    if val is None:
        return None
    try:
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, pd.Timestamp):
            return val.isoformat()
        # Try common date formats
        val_str = str(val).strip()
        for fmt in [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%d %B %Y",
        ]:
            try:
                return datetime.strptime(val_str, fmt).isoformat()
            except ValueError:
                continue
        # Last resort: pandas
        parsed = pd.to_datetime(val_str, errors="coerce")
        if pd.notna(parsed):
            return parsed.isoformat()
        return val_str  # Return as-is if we can't parse
    except Exception:
        return str(val) if val else None


def _to_float(val) -> float | None:
    """Coerce a value to float, stripping currency symbols."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        # Remove common currency symbols and commas
        val_str = re.sub(r"[₹$€£,]", "", val_str).strip()
        return float(val_str)
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int | None:
    """Coerce a value to int."""
    if val is None:
        return None
    try:
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        val_str = str(val).strip()
        val_str = re.sub(r"[,]", "", val_str).strip()
        return int(float(val_str))
    except (ValueError, TypeError):
        return None


def _clean_value(val, semantic_name: str):
    """
    Clean a single cell value based on the semantic column name.
    Applies type-specific coercion rules.
    """
    # Handle NaN/None
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None

    # Convert numpy types to native Python types
    if hasattr(val, "item"):
        val = val.item()

    # Strip whitespace from strings
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None

    # Apply type coercion based on column name
    if _is_date_column(semantic_name):
        return _parse_date(val)
    elif _is_monetary_column(semantic_name):
        return _to_float(val)
    elif _is_score_column(semantic_name):
        return _to_float(val)
    elif _is_count_column(semantic_name):
        return _to_int(val)

    return val


def transform(
    df: pd.DataFrame,
    mapped_columns: dict[str, str],
    dropped_columns: list[str],
    join_key: str | None,
) -> list[dict]:
    """
    Clean and transform a DataFrame into a list of dicts ready for DB insertion.

    Args:
        df: The raw pandas DataFrame.
        mapped_columns: Dict mapping original column name → semantic name.
        dropped_columns: List of original column names to exclude.
        join_key: The original column name used as join key (e.g., "Email Address"),
                  or None if no join key was identified.

    Returns:
        List of dicts, each with:
            - "email" (str|None): Extracted email if join_key is email-type
            - "data" (dict): All kept columns with semantic keys and cleaned values
    """
    # Determine which columns to keep (intersection of mapped_columns and actual df columns)
    dropped_set = set(dropped_columns or [])
    columns_to_process = {
        orig: semantic
        for orig, semantic in mapped_columns.items()
        if orig in df.columns and orig not in dropped_set
    }

    if not columns_to_process:
        logger.warning("No columns to process after applying mapping and drops.")
        return []

    # Determine the email source column
    email_orig_col = None
    if join_key and join_key in columns_to_process:
        semantic = columns_to_process[join_key]
        if semantic == "email" or "email" in semantic.lower():
            email_orig_col = join_key

    # If no explicit join_key is email, look for any mapped email column
    if not email_orig_col:
        for orig, semantic in columns_to_process.items():
            if semantic == "email":
                email_orig_col = orig
                break

    results = []
    for _, row in df.iterrows():
        data = {}
        for orig_col, semantic_name in columns_to_process.items():
            raw_val = row.get(orig_col)
            cleaned = _clean_value(raw_val, semantic_name)
            data[semantic_name] = cleaned

        # Extract email
        email = None
        if email_orig_col:
            email_val = row.get(email_orig_col)
            if email_val is not None and not (isinstance(email_val, float) and pd.isna(email_val)):
                email_str = str(email_val).strip()
                if email_str and email_str.lower() != "nan":
                    email = email_str

        results.append({"email": email, "data": data})

    logger.info(
        f"Transformed {len(results)} rows with {len(columns_to_process)} columns. "
        f"Email column: {email_orig_col or 'none'}"
    )
    return results
