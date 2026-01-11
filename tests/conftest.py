"""Root pytest configuration for gepa-adk tests.

This module provides shared fixtures and configuration for all tests.
It automatically loads environment variables from .env file.

Note:
    Environment variables are loaded at pytest startup to ensure
    integration tests have access to API keys and configuration.
"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
_env_file = _project_root / ".env"

if _env_file.exists():
    load_dotenv(_env_file)
