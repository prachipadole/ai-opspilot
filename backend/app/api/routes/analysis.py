"""LLM analysis routes – trigger and retrieve analyses."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.models import Analysis, Incident
from backend.app.repositories.repositories import AnalysisRepository, IncidentRepository
from backend.app.schemas.schemas import AnalysisOut, AnalysisRequest
from backend.app.services.llm_analyzer import get_analyzer

router = APIRouter()


@router.post("/analysis", response_model=AnalysisOut, status_code=201)
async def run_analysis(
    payload: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Trigger LLM analysis for an incident (synchronous – waits for Ollama)."""
    inc_repo  = IncidentRepository(db)
    anal_repo = AnalysisRepository(db)

    incident: Incident = await inc_repo.get(payload.incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")

    analyzer = get_analyzer()
    result   = analyzer.analyse(
        incident_title=incident.title,
        raw_log=incident.raw_log or "",
    )

    analysis = Analysis(
        incident_id   = incident.id,
        root_cause    = result.get("root_cause"),
        summary       = result.get("summary"),
        runbooks_used = result.get("runbooks_used", []),
        llm_model     = result.get("llm_model"),
    )
    return await anal_repo.create(analysis)


@router.get("/analysis/incident/{incident_id}", response_model=List[AnalysisOut])
async def get_analyses_for_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = AnalysisRepository(db)
    return await repo.for_incident(incident_id)
