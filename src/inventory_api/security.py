import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key_configuration() -> str:
    api_key = os.getenv("API_KEY")
    if api_key is None or len(api_key) < 32 or not api_key.isascii() or not api_key.isprintable():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured with a sufficiently long key.",
        )
    return api_key


def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    expected_api_key = require_api_key_configuration()
    if (
        api_key is None
        or not api_key.isascii()
        or not secrets.compare_digest(api_key, expected_api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid API key is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
