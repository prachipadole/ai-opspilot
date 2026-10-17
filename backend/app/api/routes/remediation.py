"""Remediation proposal, approval, and execution routes."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.models import Remediation
from backend.app.repositories.repositories import RemediationRepository, IncidentRepository
from backend.app.schemas.schemas import RemediationCreate, RemediationApproval, RemediationOut
from backend.app.services.remediation_simulator import get_simulator

router = APIRouter()


@router.get("/remediation/actions", summary="List available remediation actions")
async def list_actions():
    simulator = get_simulator()
    return simulator.list_actions()


@router.post("/remediation/suggest/{incident_id}", summary="AI-suggested actions for an incident")
async def suggest_actions(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    from backend.app.repositories.repositories import AnalysisRepository
    inc_repo   = IncidentRepository(db)
    anal_repo  = AnalysisRepository(db)

    incident = await inc_repo.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")

    analyses = await anal_repo.for_incident(incident_id)
    root_cause = analyses[0].root_cause if analyses else ""

    simulator  = get_simulator()
    suggestions = simulator.suggest_actions(incident.severity, root_cause or "")
    return {"incident_id": str(incident_id), "suggested_actions": suggestions}


@router.post("/remediation", response_model=RemediationOut, status_code=201)
async def create_remediation(
    payload: RemediationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a remediation proposal (status=pending, awaiting approval)."""
    repo = RemediationRepository(db)
    obj  = Remediation(
        incident_id = payload.incident_id,
        action_name = payload.action_name,
        parameters  = payload.parameters,
    )
    return await repo.create(obj)


@router.get("/remediation/pending", response_model=List[RemediationOut])
async def pending_remediations(db: AsyncSession = Depends(get_db)):
    repo = RemediationRepository(db)
    return await repo.pending()


@router.post("/remediation/{remediation_id}/approve", response_model=RemediationOut)
async def approve_remediation(
    remediation_id: uuid.UUID,
    payload: RemediationApproval,
    db: AsyncSession = Depends(get_db),
):
    repo = RemediationRepository(db)
    obj  = await repo.get(remediation_id)
    if not obj:
        raise HTTPException(404, "Remediation not found")

    obj.status      = "approved" if payload.approved else "rejected"
    obj.approved_by = payload.approved_by
    await db.flush()
    await db.refresh(obj)
    return obj


@router.post("/remediation/{remediation_id}/execute", response_model=RemediationOut)
async def execute_remediation(
    remediation_id: uuid.UUID,
    dry_run: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Execute an approved remediation (dry_run=True by default for safety)."""
    repo = RemediationRepository(db)
    obj  = await repo.get(remediation_id)
    if not obj:
        raise HTTPException(404, "Remediation not found")
    if obj.status not in ("approved", "pending"):
        raise HTTPException(400, f"Cannot execute remediation with status '{obj.status}'")

    simulator = get_simulator()
    result    = await simulator.execute(obj.action_name, obj.parameters or {}, dry_run=dry_run)

    obj.status      = "executed" if result["success"] else "failed"
    obj.executed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(obj)
    return obj
