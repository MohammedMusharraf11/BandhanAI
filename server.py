from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
import os
import pandas as pd
from dotenv import load_dotenv
from uuid import UUID

load_dotenv()

# ----------------------------
# DB Session
# ----------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(url=os.getenv("SUPABASE_URI"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

mcp = FastMCP("marketing")

@mcp.tool()
async def create_campaign(
    name: str,
    type: str,
    description: str = None,
    status: str = 'draft'
) -> str:
    """Create a marketing campaign."""
    allowed_types = [
        'loyalty', 'referral', 're-engagement', 'at risk', 'new customer',
        'champion', 'about to sleep', 'lost', 'potential loyalist'
    ]
    if type not in allowed_types:
        raise ValueError(f"Invalid campaign type: {type}. Must be one of {allowed_types}")

    with SessionLocal() as session:
        result = session.execute(
            text(
                """
                INSERT INTO marketing_campaigns (name, type, description, status)
                VALUES (:name, :type, :description, :status)
                RETURNING id
                """
            ),
            {"name": name, "type": type, "description": description, "status": status},
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
    """Send a campaign email."""
    allowed_statuses = [
        'sent', 'failed', 'queued', 'opened', 'bounced', 'delivered', 'clicked', 'unsubscribed'
    ]
    if status not in allowed_statuses:
        raise ValueError(f"Invalid email status: {status}. Must be one of {allowed_statuses}")

    with SessionLocal() as session:
        # FIXED: Changed CRM to crm (lowercase)
        email_result = session.execute(
            text("SELECT email FROM crm WHERE customer_id = :customer_id"),  # CORRECTED
            {"customer_id": customer_id}
        ).fetchone()
        
        if not email_result:
            raise ValueError(f"No customer found with ID: {customer_id}")
        
        email = email_result[0]

        session.execute(
            text(
                """
                INSERT INTO campaigning_emails (campaign_id, customer_id, email, subject, body, status, opened)
                VALUES (:campaign_id, :customer_id, :email, :subject, :body, :status, :opened)
                """
            ),
            {
                "campaign_id": campaign_id,
                "customer_id": customer_id,
                "email": email,
                "subject": subject,
                "body": body,
                "status": status,
                "opened": opened
            },
        )
        session.commit()

    return f"Successfully sent <{subject}> to customer <{customer_id}>!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
