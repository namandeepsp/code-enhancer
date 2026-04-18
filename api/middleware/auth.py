import os
from fastapi import Request, HTTPException, status


async def verify_api_key(request: Request) -> str:
    # Phase 1: skip auth entirely in development
    # Phase 2: replace this body with SSO JWT validation — signature stays identical
    if os.getenv("ENVIRONMENT", "development") == "development":
        return "dev-key"

    api_key = request.headers.get("X-API-Key")
    valid_key = os.getenv("API_KEY")

    if not api_key or api_key != valid_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    return api_key
