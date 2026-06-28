"""
CSV upload endpoint with LLM-powered schema detection.

Provides:
    POST /data/upload-customers — Upload a CSV file, detect schema via LLM,
                                   store schema_def in tenants table,
                                   insert rows as JSONB into customers table.

The LLM analyzes CSV column headers in a single call and maps each to a
canonical type (name, email, phone, region, total_spend, etc.).
"""

import io
import json
import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from langchain_groq import ChatGroq

from backend.auth import get_current_user, get_org_id_for_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["upload"])

# Reference to the shared pg_pool — set during app startup
_pg_pool = None


def set_pg_pool(pool):
    """Called by frontend.py at startup to inject the shared connection pool."""
    global _pg_pool
    _pg_pool = pool


def _get_pool():
    if _pg_pool is None:
        raise RuntimeError("PostgreSQL pool not initialized. Call set_pg_pool() first.")
    return _pg_pool


# ---------------------------------------------------------------------------
# Schema Detection Prompt
# ---------------------------------------------------------------------------

SCHEMA_DETECTION_PROMPT = """You are a data schema analyst. Given these CSV column headers from a customer dataset, identify what each column represents.

Return a JSON object mapping each original column name to its canonical type and a brief description.

Canonical types (use these exact strings):
- "name": Customer's full name
- "email": Email address
- "phone": Phone number
- "region": Geographic region, city, state, or country
- "age": Customer age
- "income": Income or salary
- "segment": Customer segment or category
- "last_purchase": Date of last purchase
- "total_spend": Total spending amount
- "product_category": Category of products purchased
- "churn_risk": Churn risk score (0-1)
- "feedback_score": Customer feedback or satisfaction score
- "products": List of products purchased
- "custom": Any field that doesn't match the above

Column headers: {headers}

Return ONLY valid JSON — no markdown formatting, no code fences, no explanation. Example:
{{"Customer Name": {{"canonical_type": "name", "description": "Full name of the customer"}}, "Email ID": {{"canonical_type": "email", "description": "Customer email address"}}}}"""


# ---------------------------------------------------------------------------
# Upload Endpoint
# ---------------------------------------------------------------------------

@router.post("/upload-customers")
async def upload_customers(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """
    Upload a CSV of customer data.
    
    Flow:
        1. Read CSV headers
        2. LLM detects schema mapping (single call)
        3. Store schema_def in tenants table
        4. Insert rows as JSONB in customers table
        5. Return import summary
    """
    pool = _get_pool()
    org_id = await get_org_id_for_user(user["sub"], pool)

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Read CSV
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    if len(df.columns) < 2:
        raise HTTPException(status_code=400, detail="CSV must have at least 2 columns")

    # Step 1: LLM schema detection
    headers = list(df.columns)
    logger.info(f"Detecting schema for {len(headers)} columns: {headers}")

    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        schema_response = llm.invoke(
            SCHEMA_DETECTION_PROMPT.format(headers=json.dumps(headers))
        )
        # Parse the LLM's JSON response
        response_text = schema_response.content.strip()
        # Strip markdown code fences if the LLM added them
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0].strip()
        schema_def = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {schema_response.content}")
        raise HTTPException(
            status_code=500,
            detail=f"Schema detection failed — LLM returned invalid JSON: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Schema detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema detection failed: {str(e)}")

    # Step 2: Store schema_def in tenants table
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE tenants SET schema_def = %s WHERE org_id = %s",
            (json.dumps(schema_def), org_id),
        )

    # Step 3: Find the email column (if detected)
    email_column = None
    for col, mapping in schema_def.items():
        if isinstance(mapping, dict) and mapping.get("canonical_type") == "email":
            email_column = col
            break

    # Step 4: Delete existing customers for this org (replace on re-upload)
    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM customers WHERE org_id = %s",
            (org_id,),
        )

    # Step 5: Bulk insert rows as JSONB
    inserted = 0
    errors = 0

    async with pool.connection() as conn:
        for _, row in df.iterrows():
            try:
                data = {}
                for col in df.columns:
                    val = row[col]
                    # Convert NaN/NaT to None for JSON compatibility
                    if pd.isna(val):
                        data[col] = None
                    else:
                        data[col] = val
                        # Convert numpy types to Python native types
                        if hasattr(data[col], "item"):
                            data[col] = data[col].item()

                email = str(data.get(email_column, "")) if email_column else None

                await conn.execute(
                    """
                    INSERT INTO customers (org_id, email, data, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (org_id, email, json.dumps(data), datetime.utcnow()),
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"Failed to insert row: {e}")
                errors += 1

    logger.info(f"CSV upload complete for org_id={org_id}: {inserted} rows inserted, {errors} errors")

    return {
        "status": "success",
        "rows_imported": inserted,
        "rows_failed": errors,
        "total_rows": len(df),
        "columns_detected": len(headers),
        "schema_detected": schema_def,
        "email_column": email_column,
    }
