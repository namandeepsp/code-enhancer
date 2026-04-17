import os
from fastapi import Request, HTTPException, status


async def verify_api_key(request: Request) -> str:
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
