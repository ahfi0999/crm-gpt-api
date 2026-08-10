import hmac
import os

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    expected = os.getenv("CRM_API_KEY", "")
    supplied = credentials.credentials if credentials else ""
    valid_scheme = credentials is not None and credentials.scheme.lower() == "bearer"
    if expected in ("", "CHANGE_ME") or not valid_scheme or not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
