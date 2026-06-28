"""
Authentication module — Supabase JWT validation for FastAPI.

Provides:
    - get_current_user: FastAPI dependency for REST endpoints (reads Bearer token from header)
    - get_ws_user: WebSocket token validation (reads token from query param)
    - get_org_id_for_user: Looks up the org_id for a Supabase auth UID

Signup and login are handled client-side by Supabase Auth JS SDK.
This module only validates the JWT tokens server-side.
"""

import os
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, WebSocket, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

security = HTTPBearer()

# Global cache of JWKS clients to avoid redundant network calls
_jwks_clients = {}

def get_jwks_client(jwks_url: str) -> PyJWKClient:
    """Retrieve or initialize PyJWKClient for a given JWKS endpoint."""
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url)
    return _jwks_clients[jwks_url]


def decode_and_verify_token(token: str) -> dict:
    """
    Decodes and validates a Supabase JWT.
    Supports asymmetric ES256 (via JWKS discovery) and symmetric HS256 fallback.
    """
    try:
        # Decode header and payload without signature verification first to inspect alg & issuer
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        
        alg = unverified_header.get("alg", "HS256")
        iss = unverified_payload.get("iss", "")
        
        # If it uses ES256 or has a Key ID (indicating modern Supabase asymmetric signing)
        if alg == "ES256" or "kid" in unverified_header:
            # Domain sanity check for security: must belong to a supabase project
            if not (iss.startswith("https://") and (".supabase.co" in iss or ".supabase.in" in iss)):
                raise jwt.PyJWTError("Untrusted token issuer")
            
            jwks_url = f"{iss.rstrip('/')}/.well-known/jwks.json"
            jwks_client = get_jwks_client(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated"
            )
            return payload
            
        # Fallback to symmetric HS256 using the SUPABASE_JWT_SECRET
        else:
            if not SUPABASE_JWT_SECRET or SUPABASE_JWT_SECRET == "your-supabase-jwt-signing-secret":
                raise jwt.PyJWTError("Symmetric JWT secret is not configured correctly on the backend")
            
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated"
            )
            return payload
            
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except Exception as e:
        raise jwt.PyJWTError(f"Invalid authentication credentials: {str(e)}")


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate JWT for REST endpoints.
    
    Extracts the Bearer token from the Authorization header,
    decodes and verifies it using dynamic ES256/HS256 validation.
    
    Returns:
        dict: The decoded JWT payload containing user info (sub, email, etc.)
    
    Raises:
        HTTPException 401: If the token is missing, invalid, or expired.
    """
    try:
        return decode_and_verify_token(cred.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


async def get_ws_user(websocket: WebSocket, token: str = Query(None)) -> dict:
    """
    Validate JWT for WebSocket connections.
    
    WebSocket connections cannot use Authorization headers from the browser,
    so the token is passed as a query parameter: /ws/{session_id}?token=<jwt>
    
    Args:
        websocket: The WebSocket connection.
        token: JWT token from query parameters.
    
    Returns:
        dict: The decoded JWT payload.
    
    Raises:
        Closes WebSocket with code 4001 if token is missing or invalid.
    """
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    
    try:
        return decode_and_verify_token(token)
    except jwt.ExpiredSignatureError as e:
        await websocket.close(code=4001, reason="Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except jwt.PyJWTError as e:
        await websocket.close(code=4001, reason="Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


async def get_org_id_for_user(auth_uid: str, pg_pool) -> str:
    """
    Look up the org_id for a given Supabase auth UID from the tenants table.
    
    Args:
        auth_uid: The Supabase auth user ID (JWT 'sub' claim).
        pg_pool: The async PostgreSQL connection pool.
    
    Returns:
        str: The org_id UUID as a string.
    
    Raises:
        HTTPException 404: If no tenant is found for this user.
    """
    async with pg_pool.connection() as conn:
        result = await conn.execute(
            "SELECT org_id FROM tenants WHERE owner_auth_uid = %s",
            (auth_uid,),
        )
        row = await result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenant found for this user. Please complete onboarding first.",
        )
    
    return str(row["org_id"])
