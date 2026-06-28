"""
MCP configuration loader and per-tenant config builder.

This module provides:
  1. Static MCP config loading from mcp_config.json (for CLI/dev mode)
  2. Dynamic per-tenant MCP config builder (for multi-tenant production mode)

The static loader resolves env vars and relative paths at import time.
The dynamic builder fetches a tenant's integration credentials from the DB,
decrypts them, and constructs the MCP config dict at runtime.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ===========================================================================
# Static MCP Config (CLI / Dev fallback)
# ===========================================================================

def get_project_root() -> Path:
    """
    Find the project root directory by looking for pyproject.toml.
    This ensures we can resolve relative paths correctly regardless of where the script is run from.
    """
    current_path = Path(__file__).resolve()

    # Walk up the directory tree looking for pyproject.toml
    for parent in current_path.parents:
        if (parent / "pyproject.toml").exists():
            return parent

    # Fallback: assume we're in the backend directory
    return current_path.parent


def resolve_relative_paths(config: dict, project_root: Path) -> dict:
    """
    Resolve relative paths in MCP server configurations to absolute paths.
    This makes the configuration portable across different environments.
    """
    for server_name, server_config in config["mcpServers"].items():
        if "args" in server_config:
            for i, arg in enumerate(server_config["args"]):
                if isinstance(arg, str) and not arg.startswith("${"):
                    # Check if this looks like a relative path to a Python file
                    if arg.endswith(".py") and not os.path.isabs(arg):
                        # Convert relative path to absolute path
                        absolute_path = project_root / arg
                        if absolute_path.exists():
                            config["mcpServers"][server_name]["args"][i] = str(absolute_path)
                        else:
                            # If the file doesn't exist, keep the original path but warn
                            print(f"Warning: Server file not found at {absolute_path}")
                            print(f"Keeping original path: {arg}")

    return config


def resolve_env_vars(config: dict) -> dict:
    """
    Resolve environment variables in the MCP configuration.
    This allows sensitive information to be stored in the .env file rather than in the config.
    """
    skipped_servers = []
    for server_name, server_config in config["mcpServers"].items():
        for property in server_config.keys():
            if property == "env":
                for key, value in server_config[property].items():
                    if isinstance(value, str) and value.startswith("${"):
                        env_var_name = value[2:-1]
                        env_var_value = os.environ.get(env_var_name, None)
                        if env_var_value is None or env_var_value == "":
                            print(f"\nEnvironment variable {env_var_name} is not set\n")
                            print(f"Skipping server {server_name}\n")
                            skipped_servers.append(server_name)
                            continue
                        config["mcpServers"][server_name][property][key] = env_var_value
            if property == "args":
                for i, arg in enumerate(server_config[property]):
                    if isinstance(arg, str) and arg.startswith("${"):
                        env_var_name = arg[2:-1]
                        env_var_value = os.environ.get(env_var_name, None)
                        if env_var_value is None or env_var_value == "":
                            print(f"\nEnvironment variable {env_var_name} is not set\n")
                            print(f"Skipping server {server_name}\n")
                            skipped_servers.append(server_name)
                            continue
                        config["mcpServers"][server_name][property][i] = env_var_value

    # Remove skipped servers
    for server_name in set(skipped_servers):
        del config["mcpServers"][server_name]

    return config


# Load and process the static MCP configuration (for CLI/dev mode)
config_file = Path(__file__).parent / "mcp_config.json"

if config_file.exists():
    with open(config_file, "r") as f:
        config = json.load(f)

    project_root = get_project_root()
    config = resolve_relative_paths(config, project_root)
    mcp_config = resolve_env_vars(config)
else:
    # If no static config file, provide an empty default
    # (multi-tenant mode builds configs dynamically per tenant)
    mcp_config = {"mcpServers": {}}
    logger.info("No mcp_config.json found — using dynamic per-tenant MCP config only")


# ===========================================================================
# Dynamic Per-Tenant MCP Config Builder
# ===========================================================================

async def build_mcp_config_for_tenant(org_id: str, pg_pool) -> dict:
    """
    Build a tenant-specific MCP config by fetching their integration
    credentials from the DB and constructing the config dict at runtime.
    
    Args:
        org_id: The tenant's org_id UUID string.
        pg_pool: The async PostgreSQL connection pool (psycopg AsyncConnectionPool).
    
    Returns:
        dict: An MCP config dict with the structure {"mcpServers": {...}}
              containing only the servers that the tenant has credentials for.
    """
    from backend.encryption import decrypt_token

    # Fetch tenant's integration credentials
    integration = None
    async with pg_pool.connection() as conn:
        result = await conn.execute(
            "SELECT * FROM integrations WHERE org_id = %s",
            (org_id,),
        )
        integration = await result.fetchone()

    # Resolve the path to server.py for the marketing MCP server
    server_py_path = str(Path(__file__).parent / "server.py")

    # Base config — PostgreSQL always points to shared Supabase (RLS isolates data)
    tenant_config = {
        "mcpServers": {
            "postgres": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-postgres",
                    os.getenv("SUPABASE_URI", ""),
                ],
                "transport": "stdio",
            },
            "marketing": {
                "command": "python",
                "args": [server_py_path],
                "transport": "stdio",
                "env": {
                    "ORG_ID": org_id,
                    "SUPABASE_URI": os.getenv("SUPABASE_URI", ""),
                },
            },
        }
    }

    if not integration:
        logger.info(f"No integrations found for org_id={org_id} — using base config only")
        return tenant_config

    # Conditionally add Gmail MCP if tokens exist
    if integration.get("gmail_access_token"):
        try:
            gmail_token = decrypt_token(integration["gmail_access_token"])

            # Check if token needs refresh
            if integration.get("gmail_token_expiry"):
                expiry = integration["gmail_token_expiry"]
                if isinstance(expiry, str):
                    expiry = datetime.fromisoformat(expiry)
                
                if expiry < datetime.utcnow():
                    gmail_token = await _refresh_gmail_token(
                        org_id, integration, pg_pool
                    )

            # Add Pipedream Gmail MCP server
            tenant_config["mcpServers"]["pd"] = {
                "command": "npx",
                "args": ["-y", "supergateway", "--sse"],
                "transport": "sse",
                "url": f"https://mcp.pipedream.net/{gmail_token}/gmail",
            }
        except Exception as e:
            logger.error(f"Failed to configure Gmail MCP for org_id={org_id}: {e}")

    # Conditionally add Slack MCP if bot token exists
    if integration.get("slack_bot_token"):
        try:
            slack_token = decrypt_token(integration["slack_bot_token"])

            tenant_config["mcpServers"]["slack"] = {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": slack_token,
                    "SLACK_TEAM_ID": integration.get("slack_team_id", ""),
                },
                "transport": "stdio",
            }
        except Exception as e:
            logger.error(f"Failed to configure Slack MCP for org_id={org_id}: {e}")

    return tenant_config


async def _refresh_gmail_token(
    org_id: str,
    integration: dict,
    pg_pool,
) -> str:
    """
    Refresh an expired Gmail access token using the stored refresh token.
    Updates the DB with the new access token and expiry.
    
    Returns:
        str: The new (decrypted) access token.
    """
    from backend.encryption import decrypt_token, encrypt_token
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleAuthRequest

    refresh_token = decrypt_token(integration["gmail_refresh_token"])

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    creds.refresh(GoogleAuthRequest())

    new_access_token = creds.token
    new_expiry = creds.expiry.isoformat() if creds.expiry else None

    # Update DB with refreshed tokens
    encrypted_access = encrypt_token(new_access_token)

    async with pg_pool.connection() as conn:
        await conn.execute(
            """
            UPDATE integrations
            SET gmail_access_token = %s, gmail_token_expiry = %s
            WHERE org_id = %s
            """,
            (encrypted_access, new_expiry, org_id),
        )

    logger.info(f"Refreshed Gmail token for org_id={org_id}")
    return new_access_token
