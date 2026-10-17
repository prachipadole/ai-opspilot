"""
Generic async repository base + domain-specific repositories.
"""

from __future__ import annotations

import uuid
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import Base
from backend.app.models.models import Incident, Anomaly, Analysis, Remediation, LogEntry

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Async CRUD base repository."""

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID | int) -> Optional[T]:
        result = await self.session.get(self.model, id)
        return result

    async def list(self, limit: int = 50, offset: int = 0) -> List[T]:
        q = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID | int) -> bool:
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            return True
        return False


class IncidentRepository(BaseRepository[Incident]):
    def __init__(self, session: AsyncSession):
        super().__init__(Incident, session)

    async def list_by_status(self, status: str, limit: int = 50) -> List[Incident]:
        q = select(Incident).where(Incident.status == status).limit(limit)
        r = await self.session.execute(q)
        return list(r.scalars().all())

    async def update_status(self, id: uuid.UUID, status: str) -> Optional[Incident]:
        await self.session.execute(
            update(Incident).where(Incident.id == id).values(status=status)
        )
        return await self.get(id)


class AnomalyRepository(BaseRepository[Anomaly]):
    def __init__(self, session: AsyncSession):
        super().__init__(Anomaly, session)

    async def unacknowledged(self, limit: int = 100) -> List[Anomaly]:
        q = (
            select(Anomaly)
            .where(Anomaly.is_acknowledged == False)
            .order_by(Anomaly.detected_at.desc())
            .limit(limit)
        )
        r = await self.session.execute(q)
        return list(r.scalars().all())


class AnalysisRepository(BaseRepository[Analysis]):
    def __init__(self, session: AsyncSession):
        super().__init__(Analysis, session)

    async def for_incident(self, incident_id: uuid.UUID) -> List[Analysis]:
        q = select(Analysis).where(Analysis.incident_id == incident_id)
        r = await self.session.execute(q)
        return list(r.scalars().all())


class RemediationRepository(BaseRepository[Remediation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Remediation, session)

    async def pending(self) -> List[Remediation]:
        q = select(Remediation).where(Remediation.status == "pending")
        r = await self.session.execute(q)
        return list(r.scalars().all())


class LogRepository(BaseRepository[LogEntry]):
    def __init__(self, session: AsyncSession):
        super().__init__(LogEntry, session)

    async def recent(self, limit: int = 200) -> List[LogEntry]:
        q = select(LogEntry).order_by(LogEntry.timestamp.desc()).limit(limit)
        r = await self.session.execute(q)
        return list(r.scalars().all())
