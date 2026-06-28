"""
Step 5 — Upsert into customers + Update tenants.schema_def.

Handles batch upsert with email-based deduplication, JSONB merging,
and builds the structured schema_def for the AI agent.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Batch size for DB operations
BATCH_SIZE = 500


def _infer_field_type(values: list) -> str:
    """
    Infer the data type of a field from a sample of its values.
    Returns one of: string, float, int, date, boolean, unknown.
    """
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "string"

    # Check types of actual values
    type_counts = {}
    for v in non_null[:50]:  # Sample first 50
        t = type(v).__name__
        if t == "str":
            # Check if it looks like a date
            if any(c in str(v) for c in ["-", "/", "T"]) and len(str(v)) >= 8:
                try:
                    from dateutil.parser import parse as dateparse
                    dateparse(str(v))
                    t = "date"
                except Exception:
                    pass
        type_counts[t] = type_counts.get(t, 0) + 1

    if not type_counts:
        return "string"

    dominant = max(type_counts, key=type_counts.get)

    type_map = {
        "int": "int",
        "float": "float",
        "bool": "boolean",
        "date": "date",
        "str": "string",
    }
    return type_map.get(dominant, "string")


def _build_schema_def(
    cleaned_rows: list[dict],
    mapped_columns: dict[str, str],
    join_key: str | None,
    total_customers: int,
) -> dict:
    """
    Build the structured schema_def for tenants.schema_def.

    Args:
        cleaned_rows: The transformed rows (list of {"email": ..., "data": {...}}).
        mapped_columns: The confirmed column mapping (original → semantic).
        join_key: The original join key column name.
        total_customers: Total customer count after upsert.

    Returns:
        dict with available_fields, join_key, field_types, last_updated, total_customers.
    """
    # Get all semantic field names
    semantic_names = list(set(mapped_columns.values()))
    semantic_names.sort()

    # Infer types from actual data
    field_types = {}
    for field in semantic_names:
        values = [row["data"].get(field) for row in cleaned_rows[:100]]
        field_types[field] = _infer_field_type(values)

    # Resolve join_key to semantic name
    semantic_join_key = None
    if join_key and join_key in mapped_columns:
        semantic_join_key = mapped_columns[join_key]

    return {
        "available_fields": semantic_names,
        "join_key": semantic_join_key,
        "field_types": field_types,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_customers": total_customers,
    }


async def upsert_customers(
    pg_pool,
    org_id: str,
    cleaned_rows: list[dict],
    mapped_columns: dict[str, str],
    join_key: str | None,
) -> dict:
    """
    Upsert cleaned rows into the customers table and update tenants.schema_def.

    Args:
        pg_pool: Async PostgreSQL connection pool.
        org_id: The tenant's org_id.
        cleaned_rows: List of {"email": str|None, "data": dict}.
        mapped_columns: Original → semantic column mapping.
        join_key: Original join key column name.

    Returns:
        dict with inserted, updated, skipped counts.
    """
    inserted = 0
    updated = 0
    skipped = 0

    # Process in batches
    total = len(cleaned_rows)
    logger.info(f"Upserting {total} rows for org_id={org_id} in batches of {BATCH_SIZE}")

    for batch_start in range(0, total, BATCH_SIZE):
        batch = cleaned_rows[batch_start : batch_start + BATCH_SIZE]
        batch_num = (batch_start // BATCH_SIZE) + 1

        async with pg_pool.connection() as conn:
            for row in batch:
                email = row["email"]
                data_json = json.dumps(row["data"], default=str)

                try:
                    if email:
                        # Check if customer exists for this org + email
                        result = await conn.execute(
                            "SELECT customer_id, data FROM customers WHERE org_id = %s AND email = %s",
                            (org_id, email),
                        )
                        existing = await result.fetchone()

                        if existing:
                            # Merge: existing data + new data (new wins)
                            existing_data = existing["data"] if isinstance(existing["data"], dict) else json.loads(existing["data"]) if existing["data"] else {}
                            merged = {**existing_data, **row["data"]}

                            await conn.execute(
                                "UPDATE customers SET data = %s WHERE customer_id = %s",
                                (json.dumps(merged, default=str), existing["customer_id"]),
                            )
                            updated += 1
                        else:
                            # Insert new
                            await conn.execute(
                                """
                                INSERT INTO customers (org_id, email, data, created_at)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (org_id, email, data_json, datetime.now(timezone.utc)),
                            )
                            inserted += 1
                    else:
                        # No email — always insert (cannot deduplicate)
                        await conn.execute(
                            """
                            INSERT INTO customers (org_id, email, data, created_at)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (org_id, None, data_json, datetime.now(timezone.utc)),
                        )
                        inserted += 1

                except Exception as e:
                    logger.warning(f"Failed to upsert row (email={email}): {e}")
                    skipped += 1

        logger.info(
            f"Batch {batch_num}: inserted={inserted}, updated={updated}, skipped={skipped}"
        )

    # Count total customers for this org
    async with pg_pool.connection() as conn:
        result = await conn.execute(
            "SELECT COUNT(*) as cnt FROM customers WHERE org_id = %s",
            (org_id,),
        )
        count_row = await result.fetchone()
        total_customers = count_row["cnt"] if count_row else len(cleaned_rows)

    # Build and store schema_def
    schema_def = _build_schema_def(
        cleaned_rows, mapped_columns, join_key, total_customers
    )

    async with pg_pool.connection() as conn:
        await conn.execute(
            "UPDATE tenants SET schema_def = %s WHERE org_id = %s",
            (json.dumps(schema_def), org_id),
        )

    logger.info(
        f"Upsert complete for org_id={org_id}: "
        f"inserted={inserted}, updated={updated}, skipped={skipped}, "
        f"total_customers={total_customers}, "
        f"schema_fields={len(schema_def['available_fields'])}"
    )

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "total_customers": total_customers,
        "schema_def": schema_def,
    }
