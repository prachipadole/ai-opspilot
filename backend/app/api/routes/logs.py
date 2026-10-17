"""Log ingestion routes – parse, store, and trigger anomaly detection."""

import asyncio
from typing import List

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, AsyncSessionLocal
from backend.app.models.models import LogEntry, Incident, Anomaly
from backend.app.repositories.repositories import LogRepository, IncidentRepository, AnomalyRepository
from backend.app.schemas.schemas import BulkLogIngest, LogEntryCreate, LogEntryOut
from backend.app.services.log_parser import parse_logs, extract_metrics
from backend.app.services.anomaly_detector import get_detector
from backend.app.services.event_correlator import EventCorrelator, CorrelatedEvent
from backend.app.services.anomaly_detector import AnomalyResult
from loguru import logger

router = APIRouter()


async def _process_logs_background(raw_texts: List[str]):
    """Parse logs, detect anomalies, and auto-create incidents."""
    async with AsyncSessionLocal() as db:
        try:
            parsed   = parse_logs(raw_texts)
            metrics  = extract_metrics(parsed)
            detector = get_detector()
            anomaly_results: List[AnomalyResult] = detector.detect_batch(metrics)

            # Persist anomalies
            anom_repo = AnomalyRepository(db)
            for ar in anomaly_results:
                if ar.is_anomaly:
                    await anom_repo.create(
                        Anomaly(
                            metric_name=ar.metric_name,
                            metric_value=ar.metric_value,
                            anomaly_score=ar.anomaly_score,
                        )
                    )

            # Correlate events → incidents
            correlator = EventCorrelator()
            events: List[CorrelatedEvent] = correlator.correlate(anomaly_results, parsed)
            inc_repo = IncidentRepository(db)
            for ev in events:
                await inc_repo.create(
                    Incident(
                        title=ev.title,
                        severity=ev.severity,
                        source=ev.source,
                        raw_log=ev.raw_log,
                    )
                )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Background log processing failed: {exc}")


@router.post("/logs/ingest", summary="Ingest a batch of log lines")
async def ingest_logs(
    payload: BulkLogIngest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept raw log lines, parse them, and persist to the database.
    Anomaly detection + incident creation run as a background task.
    """
    log_repo = LogRepository(db)
    entries  = []
    for item in payload.logs:
        entry = LogEntry(
            service=item.service,
            level=item.level,
            message=item.message,
            raw=item.raw,
        )
        entries.append(await log_repo.create(entry))

    # Trigger anomaly detection asynchronously
    raw_texts = [item.message for item in payload.logs]
    background_tasks.add_task(_process_logs_background, raw_texts)

    return {"ingested": len(entries), "status": "processing"}


@router.get("/logs/recent", response_model=List[LogEntryOut], summary="Fetch recent logs")
async def recent_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    repo = LogRepository(db)
    return await repo.recent(limit=limit)
