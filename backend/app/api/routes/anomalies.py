"""Anomaly listing and acknowledgement routes."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.repositories.repositories import AnomalyRepository
from backend.app.schemas.schemas import AnomalyOut

router = APIRouter()


@router.get("/anomalies", response_model=List[AnomalyOut])
async def list_anomalies(limit: int = 100, db: AsyncSession = Depends(get_db)):
    repo = AnomalyRepository(db)
    return await repo.list(limit=limit)


@router.get("/anomalies/unacknowledged", response_model=List[AnomalyOut])
async def unacknowledged_anomalies(db: AsyncSession = Depends(get_db)):
    repo = AnomalyRepository(db)
    return await repo.unacknowledged()


@router.post("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(anomaly_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = AnomalyRepository(db)
    obj  = await repo.get(anomaly_id)
    if not obj:
        raise HTTPException(404, "Anomaly not found")
    obj.is_acknowledged = True
    await db.flush()
    return {"acknowledged": True, "id": str(anomaly_id)}
