"""
event_correlator.py – Correlate anomaly signals into actionable incidents.

Rules applied (in order):
1. Critical-level log burst         → create/escalate incident
2. High anomaly score (>0.7)        → create incident
3. Multiple metrics anomalous together → escalate existing incident
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger

from backend.app.services.anomaly_detector import AnomalyResult


@dataclass
class CorrelatedEvent:
    title: str
    severity: str          # low | medium | high | critical
    source: str
    raw_log: str
    anomalies: List[AnomalyResult]


class EventCorrelator:
    """
    Stateless rule engine: maps anomaly results + log entries to incidents.
    """

    SEVERITY_THRESHOLDS = {
        "critical": 0.85,
        "high":     0.70,
        "medium":   0.50,
        "low":      0.30,
    }

    def correlate(
        self,
        anomalies: List[AnomalyResult],
        parsed_logs: List[Dict],
    ) -> List[CorrelatedEvent]:
        events: List[CorrelatedEvent] = []

        # Group anomalies by severity
        flagged = [a for a in anomalies if a.is_anomaly]
        if not flagged:
            return events

        # Rule 1 – critical anomalies
        critical = [a for a in flagged if a.anomaly_score >= self.SEVERITY_THRESHOLDS["critical"]]
        if critical:
            events.append(
                CorrelatedEvent(
                    title=f"Critical anomaly: {', '.join(a.metric_name for a in critical)}",
                    severity="critical",
                    source="anomaly_detector",
                    raw_log=self._build_raw(critical, parsed_logs),
                    anomalies=critical,
                )
            )

        # Rule 2 – high anomalies (not already classified as critical)
        high = [
            a for a in flagged
            if self.SEVERITY_THRESHOLDS["high"] <= a.anomaly_score < self.SEVERITY_THRESHOLDS["critical"]
        ]
        if high:
            events.append(
                CorrelatedEvent(
                    title=f"Elevated anomaly: {', '.join(a.metric_name for a in high)}",
                    severity="high",
                    source="anomaly_detector",
                    raw_log=self._build_raw(high, parsed_logs),
                    anomalies=high,
                )
            )

        # Rule 3 – multi-metric correlation (2+ different metrics flagged → medium)
        if len({a.metric_name for a in flagged}) >= 2 and not (critical or high):
            events.append(
                CorrelatedEvent(
                    title="Multi-metric anomaly correlation",
                    severity="medium",
                    source="event_correlator",
                    raw_log=self._build_raw(flagged, parsed_logs),
                    anomalies=flagged,
                )
            )

        # Rule 4 – log-level burst
        error_logs = [e for e in parsed_logs if e.get("level") in ("ERROR", "CRITICAL", "FATAL")]
        if len(error_logs) >= 5 and not events:
            events.append(
                CorrelatedEvent(
                    title=f"Error burst: {len(error_logs)} errors detected",
                    severity="high",
                    source="log_parser",
                    raw_log="\n".join(e["message"] for e in error_logs[:10]),
                    anomalies=[],
                )
            )

        return events

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_raw(anomalies: List[AnomalyResult], logs: List[Dict]) -> str:
        lines = [f"[{a.metric_name}] value={a.metric_value:.3f} score={a.anomaly_score:.3f}"
                 for a in anomalies]
        recent_errors = [l["message"] for l in logs if l.get("level") in ("ERROR", "CRITICAL")][:5]
        return "\n".join(lines + recent_errors)
