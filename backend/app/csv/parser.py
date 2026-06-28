"""
Step 1 — CSV Parser & Validator.

Accepts an uploaded file, detects encoding, reads into a pandas DataFrame,
and validates structure (non-empty, ≥2 columns, ≤50,000 rows).
"""

import io
import logging

import chardet
import pandas as pd
from fastapi import UploadFile

logger = logging.getLogger(__name__)


async def parse_csv(file: UploadFile) -> dict:
    """
    Parse and validate an uploaded CSV file.

    Args:
        file: FastAPI UploadFile object.

    Returns:
        dict with keys:
            - headers (list[str]): Column names
            - sample_rows (list[dict]): First 5 rows as dicts
            - total_rows (int): Number of data rows
            - dataframe (pd.DataFrame): The full DataFrame

    Raises:
        ValueError: If file is invalid, empty, too large, or unparseable.
    """
    # Validate file extension
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise ValueError("Invalid file type. Only CSV files are supported.")

    # Read raw bytes
    raw_bytes = await file.read()
    if not raw_bytes:
        raise ValueError("Uploaded file is empty.")

    # Detect encoding
    detected = chardet.detect(raw_bytes)
    encoding = detected.get("encoding") or "utf-8"
    confidence = detected.get("confidence", 0)
    logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2f})")

    # Fallback to utf-8 if confidence is too low
    if confidence < 0.5:
        encoding = "utf-8"

    # Parse CSV into DataFrame
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)
    except UnicodeDecodeError:
        # Retry with utf-8 if detected encoding failed
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding="utf-8")
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")

    # Validate: not empty
    if df.empty or len(df) == 0:
        raise ValueError("CSV file has no data rows.")

    # Validate: minimum columns
    if len(df.columns) < 2:
        raise ValueError("CSV must have at least 2 columns.")

    # Validate: maximum rows
    if len(df) > 50_000:
        raise ValueError(
            f"CSV too large ({len(df):,} rows). Maximum 50,000 rows allowed."
        )

    # Build sample rows (first 5)
    sample_df = df.head(5)
    sample_rows = []
    for _, row in sample_df.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                row_dict[col] = None
            elif hasattr(val, "item"):
                row_dict[col] = val.item()
            else:
                row_dict[col] = val
        sample_rows.append(row_dict)

    headers = list(df.columns)

    logger.info(
        f"CSV parsed: {len(headers)} columns, {len(df)} rows, file={filename}"
    )

    return {
        "headers": headers,
        "sample_rows": sample_rows,
        "total_rows": len(df),
        "dataframe": df,
    }
