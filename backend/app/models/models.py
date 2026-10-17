"""SQLAlchemy ORM models for AI-OpsPilot."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Float, ForeignKey,
    String, Text, DateTime, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title      = Column(Text, nullable=False)
    severity   = Column(String(10), nullable=False)
    status     = Column(String(20), nullable=False, default="open")
    source     = Column(Text)
    raw_log    = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    anomalies    = relationship("Anomaly",     back_populates="incident", cascade="all, delete")
    analyses     = relationship("Analysis",    back_populates="incident", cascade="all, delete")
    remediations = relationship("Remediation", back_populates="incident", cascade="all, delete")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id     = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"))
    metric_name     = Column(Text, nullable=False)
    metric_value    = Column(Float, nullable=False)
    anomaly_score   = Column(Float, nullable=False)
    detected_at     = Column(DateTime(timezone=True), server_default=func.now())
    is_acknowledged = Column(Boolean, default=False)

    incident = relationship("Incident", back_populates="anomalies")


class Analysis(Base):
    __tablename__ = "analyses"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id   = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    root_cause    = Column(Text)
    summary       = Column(Text)
    runbooks_used = Column(JSONB, default=list)
    llm_model     = Column(Text)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", back_populates="analyses")


class Remediation(Base):
    __tablename__ = "remediations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    action_name = Column(Text, nullable=False)
    parameters  = Column(JSONB, default=dict)
    status      = Column(String(20), default="pending")
    approved_by = Column(Text)
    executed_at = Column(DateTime(timezone=True))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", back_populates="remediations")


class LogEntry(Base):
    __tablename__ = "log_entries"

    id        = Column(BigInteger, primary_key=True, autoincrement=True)
    service   = Column(Text)
    level     = Column(String(10))
    message   = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    raw       = Column(JSONB, default=dict)
