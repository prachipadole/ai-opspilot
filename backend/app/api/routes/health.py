"""Health-check endpoint."""
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health", summary="Health check")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
