"""
config.py — ScamShield Configuration & Environment Validation
==============================================================
Centralized, validated settings management for ScamShield backend.
Follows 12-factor application design principles.
"""

import os
from typing import List
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Look for .env in current directory or project root
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


class Settings:
    """Application configuration and validation."""

    def __init__(self):
        self.ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development").lower()
        self.HOST: str = os.environ.get("HOST", "127.0.0.1")
        self.PORT: int = int(os.environ.get("PORT", "8000"))

        # CORS Origins configuration
        raw_origins = os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
        )
        self.CORS_ORIGINS: List[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]
        self.CORS_ALLOW_CREDENTIALS: bool = os.environ.get("CORS_ALLOW_CREDENTIALS", "true").lower() in ("true", "1", "yes")

        # Security check: Browsers reject allow_credentials=True with wildcard origin '*'
        # Furthermore, wildcard credentials represent a critical CSRF risk.
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.CORS_ORIGINS:
            # Filter out '*' to prevent security vulnerabilities and browser rejections
            self.CORS_ORIGINS = [o for o in self.CORS_ORIGINS if o != "*"]

        # Server-secret key for keyed HMAC-SHA256 message fingerprinting
        self.SCAMSHIELD_HMAC_SECRET: str = os.environ.get(
            "SCAMSHIELD_HMAC_SECRET",
            "scamshield-telemetry-isolation-key-v1"
        ).strip()

        # Supabase Cloud settings
        self.SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").strip()
        self.SUPABASE_KEY: str = (
            os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip()
        self.SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

        # Rate limiting and size limits
        self.RATE_LIMIT_PER_MINUTE: int = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "120"))
        self.MAX_REQUEST_SIZE_BYTES: int = int(os.environ.get("MAX_REQUEST_SIZE_BYTES", "65536"))  # 64 KB

        # Outbound HTTP timeout
        self.HTTP_TIMEOUT_SECONDS: float = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "5.0"))


settings = Settings()
