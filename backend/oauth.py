"""
OAuth flow handlers for Gmail and Slack integrations.

Provides FastAPI router with endpoints:
    GET  /auth/gmail/connect   — Initiate Gmail OAuth, returns auth URL
    GET  /auth/gmail/callback  — Handle Gmail OAuth callback, store encrypted tokens
    GET  /auth/slack/connect   — Initiate Slack OAuth, returns auth URL
    GET  /auth/slack/callback  — Handle Slack OAuth callback, store encrypted bot token

Both flows encrypt tokens via Fernet before storing in the integrations table.
"""

import os
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from slack_sdk import WebClient

from backend.auth import get_current_user, get_org_id_for_user
from backend.encryption import encrypt_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["oauth"])

# ---------------------------------------------------------------------------
# Gmail OAuth Configuration
# ---------------------------------------------------------------------------

GMAIL_CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [
            os.getenv("GMAIL_REDIRECT_URI", "http://localhost:8000/auth/gmail/callback")
        ],
    }
}

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Reference to the shared pg_pool — set during app startup via set_pg_pool()
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
# Gmail OAuth Endpoints
# ---------------------------------------------------------------------------

@router.get("/gmail/connect")
async def gmail_connect(user: dict = Depends(get_current_user)):
    """
    Initiate Gmail OAuth flow.
    
    Returns the Google authorization URL that the frontend should redirect to.
    The user's auth_uid is embedded in the OAuth state parameter so we can
    associate the tokens with the correct tenant on callback.
    """
    if not GMAIL_CLIENT_CONFIG["web"]["client_id"]:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID not configured on server",
        )

    flow = Flow.from_client_config(
        GMAIL_CLIENT_CONFIG,
        scopes=GMAIL_SCOPES,
        redirect_uri=GMAIL_CLIENT_CONFIG["web"]["redirect_uris"][0],
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Force consent to always get refresh_token
        state=user["sub"],  # Embed auth_uid in state for callback
    )

    return {"auth_url": auth_url, "state": state}


@router.get("/gmail/callback")
async def gmail_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle Gmail OAuth callback.
    
    Exchanges the authorization code for access + refresh tokens,
    encrypts them, and stores them in the integrations table.
    
    Redirects to the frontend settings page on success.
    """
    pool = _get_pool()

    try:
        flow = Flow.from_client_config(
            GMAIL_CLIENT_CONFIG,
            scopes=GMAIL_SCOPES,
            redirect_uri=GMAIL_CLIENT_CONFIG["web"]["redirect_uris"][0],
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
    except Exception as e:
        logger.error(f"Gmail OAuth token exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    # state = auth_uid passed during /gmail/connect
    auth_uid = state

    try:
        org_id = await get_org_id_for_user(auth_uid, pool)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Tenant not found for this user")

    # Encrypt tokens
    encrypted_access = encrypt_token(creds.token)
    encrypted_refresh = encrypt_token(creds.refresh_token) if creds.refresh_token else None
    expiry = creds.expiry.isoformat() if creds.expiry else None

    # Upsert into integrations table
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO integrations (org_id, gmail_access_token, gmail_refresh_token, gmail_token_expiry, connected_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (org_id) DO UPDATE SET
                gmail_access_token = EXCLUDED.gmail_access_token,
                gmail_refresh_token = EXCLUDED.gmail_refresh_token,
                gmail_token_expiry = EXCLUDED.gmail_token_expiry,
                connected_at = EXCLUDED.connected_at
            """,
            (org_id, encrypted_access, encrypted_refresh, expiry, datetime.utcnow()),
        )

    logger.info(f"Gmail connected for org_id={org_id}")

    # Redirect to frontend settings page
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/settings?gmail=connected")


# ---------------------------------------------------------------------------
# Slack OAuth Endpoints
# ---------------------------------------------------------------------------

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "http://localhost:8000/auth/slack/callback")
SLACK_SCOPES = "channels:read,chat:write,users:read"


@router.get("/slack/connect")
async def slack_connect(user: dict = Depends(get_current_user)):
    """
    Initiate Slack OAuth flow.
    
    Returns the Slack authorization URL. The user's auth_uid is embedded
    in the state parameter for CSRF protection and tenant association.
    """
    if not SLACK_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="SLACK_CLIENT_ID not configured on server",
        )

    slack_auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SLACK_CLIENT_ID}"
        f"&scope={SLACK_SCOPES}"
        f"&redirect_uri={SLACK_REDIRECT_URI}"
        f"&state={user['sub']}"
    )

    return {"auth_url": slack_auth_url}


@router.get("/slack/callback")
async def slack_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle Slack OAuth callback.
    
    Exchanges the code for a bot token, encrypts it, and stores in integrations.
    Redirects to the frontend settings page on success.
    """
    pool = _get_pool()

    try:
        client = WebClient()
        response = client.oauth_v2_access(
            client_id=SLACK_CLIENT_ID,
            client_secret=SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=SLACK_REDIRECT_URI,
        )
    except Exception as e:
        logger.error(f"Slack OAuth token exchange failed: {e}")
        raise HTTPException(status_code=400, detail=f"Slack token exchange failed: {str(e)}")

    bot_token = response.get("access_token", "")
    team_id = response.get("team", {}).get("id", "")

    if not bot_token:
        raise HTTPException(status_code=400, detail="No bot token received from Slack")

    # state = auth_uid
    auth_uid = state

    try:
        org_id = await get_org_id_for_user(auth_uid, pool)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Tenant not found for this user")

    # Encrypt and store
    encrypted_bot_token = encrypt_token(bot_token)

    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO integrations (org_id, slack_bot_token, slack_team_id, connected_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (org_id) DO UPDATE SET
                slack_bot_token = EXCLUDED.slack_bot_token,
                slack_team_id = EXCLUDED.slack_team_id,
                connected_at = EXCLUDED.connected_at
            """,
            (org_id, encrypted_bot_token, team_id, datetime.utcnow()),
        )

    logger.info(f"Slack connected for org_id={org_id}")

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/settings?slack=connected")
