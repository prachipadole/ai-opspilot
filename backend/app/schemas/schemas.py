"""Pydantic v2 schemas for request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ── Shared ────────────────────────────────────────────────────────────────────
class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Incidents ─────────────────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    title: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    source: Optional[str] = None
    raw_log: Optional[str] = None


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


class IncidentOut(OrmBase):
    id: uuid.UUID
    title: str
    severity: str
    status: str
    source: Optional[str]
    created_at: datetime
    updated_at: datetime


# ── Anomalies ─────────────────────────────────────────────────────────────────
class AnomalyCreate(BaseModel):
    metric_name: str
    metric_value: float
    anomaly_score: float
    incident_id: Optional[uuid.UUID] = None


class AnomalyOut(OrmBase):
    id: uuid.UUID
    incident_id: Optional[uuid.UUID]
    metric_name: str
    metric_value: float
    anomaly_score: float
    detected_at: datetime
    is_acknowledged: bool


# ── Log Entries ────────────────────────────────────────────────────────────────
class LogEntryCreate(BaseModel):
    service: Optional[str] = None
    level: Optional[str] = None
    message: str
    raw: Dict[str, Any] = Field(default_factory=dict)


class LogEntryOut(OrmBase):
    id: int
    service: Optional[str]
    level: Optional[str]
    message: str
    timestamp: datetime


# ── Analysis ──────────────────────────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    incident_id: uuid.UUID


class AnalysisOut(OrmBase):
    id: uuid.UUID
    incident_id: uuid.UUID
    root_cause: Optional[str]
    summary: Optional[str]
    runbooks_used: List[Any]
    llm_model: Optional[str]
    created_at: datetime


# ── Remediation ───────────────────────────────────────────────────────────────
class RemediationCreate(BaseModel):
    incident_id: uuid.UUID
    action_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class RemediationApproval(BaseModel):
    approved_by: str
    approved: bool = True


class RemediationOut(OrmBase):
    id: uuid.UUID
    incident_id: uuid.UUID
    action_name: str
    parameters: Dict[str, Any]
    status: str
    approved_by: Optional[str]
    executed_at: Optional[datetime]
    created_at: datetime


# ── Bulk log ingest ───────────────────────────────────────────────────────────
class BulkLogIngest(BaseModel):
    logs: List[LogEntryCreate]
