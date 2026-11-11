"""Bearer authentication for the single-owner Atlas workspace."""
import secrets
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)

def require_owner(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
    expected = request.app.state.settings.api_token.encode("utf-8")
    supplied = credentials.credentials.encode("utf-8") if credentials else b""
    if not credentials or not secrets.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid or missing Atlas access token", headers={"WWW-Authenticate": "Bearer"})
    # Every holder of this server's token controls the same workspace. Not multi-user auth.
    return "owner"

Owner = Annotated[str, Depends(require_owner)]
