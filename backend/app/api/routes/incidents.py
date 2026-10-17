"""Incident CRUD + workflow trigger routes."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.models import Incident
from backend.app.repositories.repositories import IncidentRepository
from backend.app.schemas.schemas import IncidentCreate, IncidentOut, IncidentUpdate
from backend.app.workflows.investigation_workflow import run_investigation

router = APIRouter()


@router.post("/incidents", response_model=IncidentOut, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
):
    repo = IncidentRepository(db)
    incident = Incident(**payload.model_dump())
    return await repo.create(incident)


@router.get("/incidents", response_model=List[IncidentOut])
async def list_incidents(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    repo = IncidentRepository(db)
    if status:
        return await repo.list_by_status(status, limit=limit)
    return await repo.list(limit=limit)


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = IncidentRepository(db)
    obj  = await repo.get(incident_id)
    if not obj:
        raise HTTPException(404, "Incident not found")
    return obj


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
):
    repo = IncidentRepository(db)
    obj  = await repo.get(incident_id)
    if not obj:
        raise HTTPException(404, "Incident not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.post("/incidents/{incident_id}/investigate", summary="Run full LangGraph investigation")
async def investigate_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the multi-stage LangGraph investigation workflow."""
    repo = IncidentRepository(db)
    inc  = await repo.get(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")

    raw_logs = [inc.raw_log] if inc.raw_log else []
    result   = run_investigation(raw_logs)

    # Update incident status
    await repo.update_status(incident_id, "investigating")

    return {
        "incident_id": str(incident_id),
        "analysis":    result.get("analysis"),
        "remediations": result.get("remediations"),
        "anomalies_detected": len(result.get("anomalies", [])),
    }
