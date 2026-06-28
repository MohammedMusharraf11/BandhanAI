"""
Step 3 — CSV Upload & Confirm Routes.

Two-step HTTP flow:
  POST /csv/upload   → Parse CSV + LLM schema detection → return mapping for review
  POST /csv/confirm  → Apply mapping, clean data, upsert → return counts
"""

import json
import logging
import uuid
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.auth import get_current_user, get_org_id_for_user
from backend.app.csv.parser import parse_csv
from backend.app.csv.schema_detector import detect_schema
from backend.app.csv.transformer import transform
from backend.app.csv.ingestion import upsert_customers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/csv", tags=["CSV Ingestion"])

# ---------------------------------------------------------------------------
# In-memory cache for upload sessions (DataFrame + mapping)
# Key: upload_session_id (str) → value: dict with df, mapping, timestamp
# TTL: 10 minutes
# ---------------------------------------------------------------------------

_upload_sessions: dict[str, dict] = {}
_SESSION_TTL_SECONDS = 600  # 10 minutes


def _cleanup_expired_sessions():
    """Remove sessions older than TTL."""
    now = time.time()
    expired = [
        sid for sid, session in _upload_sessions.items()
        if now - session["created_at"] > _SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _upload_sessions[sid]
        logger.info(f"Expired upload session: {sid}")


# Reference to the shared pg_pool — set during app startup
_pg_pool = None


def set_pg_pool(pool):
    """Called by frontend.py at startup to inject the shared connection pool."""
    global _pg_pool
    _pg_pool = pool


def _get_pool():
    if _pg_pool is None:
        raise RuntimeError("PostgreSQL pool not initialized.")
    return _pg_pool


# ---------------------------------------------------------------------------
# POST /csv/upload — Steps 1 + 2
# ---------------------------------------------------------------------------

@router.post("/upload")
async def csv_upload(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a CSV file, parse it, and run LLM schema detection.

    Returns the detected mapping for user review/confirmation.
    The DataFrame is cached in memory for 10 minutes.
    """
    pool = _get_pool()
    org_id = await get_org_id_for_user(user["sub"], pool)

    # Cleanup expired sessions
    _cleanup_expired_sessions()

    # Step 1: Parse & validate CSV
    try:
        parsed = await parse_csv(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    df = parsed["dataframe"]
    headers = parsed["headers"]
    sample_rows = parsed["sample_rows"]
    total_rows = parsed["total_rows"]
    file_name = file.filename or "unknown.csv"

    # Step 2: LLM schema detection
    try:
        mapping = await detect_schema(file_name, headers, sample_rows)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Generate upload session ID
    upload_session_id = str(uuid.uuid4())

    # Create data_sources row
    source_id = None
    try:
        async with pool.connection() as conn:
            result = await conn.execute(
                """
                INSERT INTO data_sources (org_id, file_name, source_type, row_count, status)
                VALUES (%s, %s, %s, %s, 'processing')
                RETURNING source_id
                """,
                (org_id, file_name, mapping.get("source_type", "unknown"), total_rows),
            )
            row = await result.fetchone()
            source_id = str(row["source_id"])
    except Exception as e:
        logger.error(f"Failed to create data_sources row: {e}")
        raise HTTPException(status_code=500, detail="Failed to register upload.")

    # Create schema_mappings row
    try:
        async with pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO schema_mappings
                    (source_id, org_id, original_columns, mapped_columns, join_key, dropped_columns)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    source_id,
                    org_id,
                    json.dumps(headers),
                    json.dumps(mapping["mapped_columns"]),
                    mapping.get("join_key"),
                    json.dumps(mapping.get("dropped_columns", [])),
                ),
            )
    except Exception as e:
        logger.error(f"Failed to create schema_mappings row: {e}")
        # Non-fatal — continue

    # Cache the DataFrame and mapping
    _upload_sessions[upload_session_id] = {
        "dataframe": df,
        "mapping": mapping,
        "source_id": source_id,
        "org_id": org_id,
        "file_name": file_name,
        "created_at": time.time(),
    }

    logger.info(
        f"CSV upload session created: {upload_session_id} "
        f"(file={file_name}, rows={total_rows}, source_id={source_id})"
    )

    return {
        "upload_session_id": upload_session_id,
        "source_id": source_id,
        "source_type": mapping.get("source_type", "unknown"),
        "join_key": mapping.get("join_key"),
        "total_rows": total_rows,
        "mapped_columns": mapping["mapped_columns"],
        "dropped_columns": mapping.get("dropped_columns", []),
        "reasoning": mapping.get("reasoning", ""),
    }


# ---------------------------------------------------------------------------
# POST /csv/confirm — Steps 4 + 5
# ---------------------------------------------------------------------------

class ConfirmRequest(BaseModel):
    upload_session_id: str
    overrides: Optional[dict] = None  # Optional user corrections to the mapping


@router.post("/confirm")
async def csv_confirm(
    req: ConfirmRequest,
    user: dict = Depends(get_current_user),
):
    """
    Confirm the schema mapping, clean data, and upsert into the customers table.

    Optionally accepts 'overrides' to correct the LLM mapping:
      - overrides.mapped_columns: dict of {original: new_semantic_name} to override
      - overrides.dropped_columns: list of columns to add to the drop list
      - overrides.restored_columns: list of columns to remove from the drop list
    """
    pool = _get_pool()
    org_id = await get_org_id_for_user(user["sub"], pool)

    # Cleanup expired sessions
    _cleanup_expired_sessions()

    # Retrieve session
    session = _upload_sessions.get(req.upload_session_id)
    if not session:
        raise HTTPException(
            status_code=410,
            detail="Upload session expired or not found. Please re-upload the CSV.",
        )

    # Verify org_id matches
    if session["org_id"] != org_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this tenant.")

    df = session["dataframe"]
    mapping = session["mapping"]
    source_id = session["source_id"]

    # Apply user overrides
    mapped_columns = dict(mapping["mapped_columns"])
    dropped_columns = list(mapping.get("dropped_columns", []))
    join_key = mapping.get("join_key")

    if req.overrides:
        # Override specific column mappings
        if req.overrides.get("mapped_columns"):
            for orig, new_name in req.overrides["mapped_columns"].items():
                mapped_columns[orig] = new_name

        # Add columns to drop list
        if req.overrides.get("dropped_columns"):
            for col in req.overrides["dropped_columns"]:
                if col not in dropped_columns:
                    dropped_columns.append(col)
                # Also remove from mapped if it was there
                mapped_columns.pop(col, None)

        # Restore columns from drop list
        if req.overrides.get("restored_columns"):
            for col in req.overrides["restored_columns"]:
                if col in dropped_columns:
                    dropped_columns.remove(col)
                # Auto-map restored column if not already mapped
                if col not in mapped_columns:
                    mapped_columns[col] = col.lower().replace(" ", "_")

    # Step 4: Transform
    try:
        cleaned_rows = transform(df, mapped_columns, dropped_columns, join_key)
    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        # Update data_sources status
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "UPDATE data_sources SET status = 'failed', error_message = %s WHERE source_id = %s",
                    (str(e), source_id),
                )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Data transformation failed: {str(e)}")

    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No data rows after transformation.")

    # Step 5: Upsert
    try:
        result = await upsert_customers(
            pg_pool=pool,
            org_id=org_id,
            cleaned_rows=cleaned_rows,
            mapped_columns=mapped_columns,
            join_key=join_key,
        )
    except Exception as e:
        logger.error(f"Upsert failed: {e}")
        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "UPDATE data_sources SET status = 'failed', error_message = %s WHERE source_id = %s",
                    (str(e), source_id),
                )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Data ingestion failed: {str(e)}")

    # Update data_sources status to 'done'
    try:
        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE data_sources SET status = 'done' WHERE source_id = %s",
                (source_id,),
            )
    except Exception as e:
        logger.warning(f"Failed to update data_sources status: {e}")

    # Remove session from cache
    _upload_sessions.pop(req.upload_session_id, None)

    logger.info(
        f"CSV confirm complete: session={req.upload_session_id}, "
        f"inserted={result['inserted']}, updated={result['updated']}, "
        f"skipped={result['skipped']}"
    )

    return {
        "status": "success",
        "source_id": source_id,
        "customers_inserted": result["inserted"],
        "customers_updated": result["updated"],
        "customers_skipped": result["skipped"],
        "total_customers": result["total_customers"],
    }
