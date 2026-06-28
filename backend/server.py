"""
Custom MCP Marketing Server for BandhanAI.

Exposes two tools over stdio transport:
    - create_campaign: Create a new marketing campaign (scoped by org_id)
    - send_campaign_email: Record a campaign email send (scoped by org_id)

The ORG_ID is passed as an environment variable by the dynamic MCP config builder,
ensuring all database operations are scoped to the calling tenant.
"""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import os
import pandas as pd
from dotenv import load_dotenv
from uuid import UUID

load_dotenv()

# ----------------------------
# DB Session
# ----------------------------

engine = create_engine(url=os.getenv("SUPABASE_URI"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tenant scoping — ORG_ID is injected via MCP server env config
ORG_ID = os.getenv("ORG_ID")

mcp = FastMCP("marketing")


@mcp.tool()
async def create_campaign(
    name: str,
    type: str,
    description: str = None,
    status: str = 'draft'
) -> str:
    """Create a marketing campaign.
    
    Args:
        name: The campaign name.
        type: Campaign type — must be one of: loyalty, referral, re-engagement,
              at risk, new customer, champion, about to sleep, lost, potential loyalist.
        description: Optional campaign description.
        status: Campaign status (default: 'draft').
    
    Returns:
        str: The UUID of the newly created campaign.
    """
    allowed_types = [
        'loyalty', 'referral', 're-engagement', 'at risk', 'new customer',
        'champion', 'about to sleep', 'lost', 'potential loyalist'
    ]
    if type not in allowed_types:
        raise ValueError(f"Invalid campaign type: {type}. Must be one of {allowed_types}")

    if not ORG_ID:
        raise RuntimeError("ORG_ID environment variable not set. Cannot create campaign without tenant context.")

    with SessionLocal() as session:
        result = session.execute(
            text(
                """
                INSERT INTO marketing_campaigns (name, type, description, status, org_id)
                VALUES (:name, :type, :description, :status, :org_id)
                RETURNING id
                """
            ),
            {
                "name": name,
                "type": type,
                "description": description,
                "status": status,
                "org_id": ORG_ID,
            },
        )
        session.commit()
        return str(result.fetchone()[0])


@mcp.tool()
async def send_campaign_email(
    campaign_id: UUID,
    customer_id: int,
    subject: str,
    body: str,
    status: str = 'sent',
    opened: bool = False
) -> str:
    """Record a campaign email send.
    
    This tool records the email in the campaigning_emails table. The actual
    email delivery is handled separately via the Gmail MCP server (GMAIL_SEND_EMAIL).
    
    Args:
        campaign_id: UUID of the campaign this email belongs to.
        customer_id: The customer ID to send the email to.
        subject: Email subject line.
        body: Email body content (HTML).
        status: Email status (default: 'sent').
        opened: Whether the email has been opened (default: False).
    
    Returns:
        str: Success message with subject and customer ID.
    """
    allowed_statuses = [
        'sent', 'failed', 'queued', 'opened', 'bounced', 'delivered', 'clicked', 'unsubscribed'
    ]
    if status not in allowed_statuses:
        raise ValueError(f"Invalid email status: {status}. Must be one of {allowed_statuses}")

    if not ORG_ID:
        raise RuntimeError("ORG_ID environment variable not set. Cannot send email without tenant context.")

    with SessionLocal() as session:
        # Look up the customer's email address, scoped to the tenant
        email_result = session.execute(
            text("SELECT email FROM crm WHERE customer_id = :customer_id AND org_id = :org_id"),
            {"customer_id": customer_id, "org_id": ORG_ID}
        ).fetchone()
        
        # Fallback: check the JSONB customers table if not found in crm
        if not email_result:
            email_result = session.execute(
                text("SELECT email FROM customers WHERE customer_id = :customer_id AND org_id = :org_id"),
                {"customer_id": customer_id, "org_id": ORG_ID}
            ).fetchone()
        
        if not email_result:
            raise ValueError(f"No customer found with ID: {customer_id} for this organization")
        
        email = email_result[0]

        session.execute(
            text(
                """
                INSERT INTO campaigning_emails (campaign_id, customer_id, email, subject, body, status, opened, org_id)
                VALUES (:campaign_id, :customer_id, :email, :subject, :body, :status, :opened, :org_id)
                """
            ),
            {
                "campaign_id": campaign_id,
                "customer_id": customer_id,
                "email": email,
                "subject": subject,
                "body": body,
                "status": status,
                "opened": opened,
                "org_id": ORG_ID,
            },
        )
        session.commit()

    return f"Successfully sent <{subject}> to customer <{customer_id}>!"


if __name__ == "__main__":
    mcp.run(transport="stdio")
