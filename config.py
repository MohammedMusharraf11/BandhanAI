"""
This file loads required secrets from the .env file into the mcp_config.
It also resolves relative paths to absolute paths for local server files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import json


load_dotenv()


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

    # Fallback: assume we're in src/ralph/mymcp/ and go up 3 levels
    return current_path.parent.parent.parent


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


# Load and process the MCP configuration
config_file = Path(__file__).parent / "mcp_config.json"
if not config_file.exists():
    raise FileNotFoundError(f"mcp_config.json file {config_file} does not exist")

with open(config_file, "r") as f:
    config = json.load(f)

# Get the project root for resolving relative paths
project_root = get_project_root()

# Resolve relative paths to absolute paths
config = resolve_relative_paths(config, project_root)

# Resolve environment variables
mcp_config = resolve_env_vars(config)
