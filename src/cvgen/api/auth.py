"""Simple API key authentication for CVGen API."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException

# API key from environment variable (optional — disabled if not set)
API_KEY = os.environ.get("CVGEN_API_KEY")


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Verify API key if authentication is enabled.

    Authentication is disabled by default. Set CVGEN_API_KEY environment
    variable to enable it.
    """
    if API_KEY is None:
        return  # Auth disabled

    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
