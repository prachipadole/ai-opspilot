"""
api_client.py – Typed HTTP client wrapping the FastAPI backend.
"""

import os
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = os.getenv("STREAMLIT_BACKEND_URL", "http://localhost:8000")
TIMEOUT  = 30.0
PREFIX   = "/api/v1"


def _url(path: str) -> str:
    return f"{BASE_URL}{PREFIX}{path}"


def _get(path: str, params: dict | None = None) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(_url(path), params=params)
        r.raise_for_status()
        return r.json()


def _post(path: str, json: Any = None) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.post(_url(path), json=json)
        r.raise_for_status()
        return r.json()


def _patch(path: str, json: Any = None) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.patch(_url(path), json=json)
        r.raise_for_status()
        return r.json()


# ── Health ─────────────────────────────────────────────────────────────────────
def health_check() -> Dict:
    return _get("/health")


# ── Incidents ──────────────────────────────────────────────────────────────────
def list_incidents(status: str | None = None, limit: int = 50) -> List[Dict]:
    params = {"limit": limit}
    if status:
        params["status"] = status
    return _get("/incidents", params=params)


def create_incident(title: str, severity: str, source: str = "", raw_log: str = "") -> Dict:
    return _post("/incidents", json={
        "title": title, "severity": severity,
        "source": source, "raw_log": raw_log,
    })


def update_incident_status(incident_id: str, status: str) -> Dict:
    return _patch(f"/incidents/{incident_id}", json={"status": status})


def investigate_incident(incident_id: str) -> Dict:
    return _post(f"/incidents/{incident_id}/investigate")


# ── Anomalies ──────────────────────────────────────────────────────────────────
def list_anomalies(limit: int = 100) -> List[Dict]:
    return _get("/anomalies", params={"limit": limit})


def unacknowledged_anomalies() -> List[Dict]:
    return _get("/anomalies/unacknowledged")


def acknowledge_anomaly(anomaly_id: str) -> Dict:
    return _post(f"/anomalies/{anomaly_id}/acknowledge")


# ── Logs ───────────────────────────────────────────────────────────────────────
def ingest_logs(log_lines: List[str]) -> Dict:
    return _post("/logs/ingest", json={
        "logs": [{"message": line} for line in log_lines]
    })


def recent_logs(limit: int = 100) -> List[Dict]:
    return _get("/logs/recent", params={"limit": limit})


# ── Analysis ───────────────────────────────────────────────────────────────────
def run_analysis(incident_id: str) -> Dict:
    return _post("/analysis", json={"incident_id": incident_id})


def get_analyses(incident_id: str) -> List[Dict]:
    return _get(f"/analysis/incident/{incident_id}")


# ── Remediation ────────────────────────────────────────────────────────────────
def list_actions() -> List[Dict]:
    return _get("/remediation/actions")


def suggest_actions(incident_id: str) -> Dict:
    return _post(f"/remediation/suggest/{incident_id}")


def create_remediation(incident_id: str, action_name: str, parameters: Dict = {}) -> Dict:
    return _post("/remediation", json={
        "incident_id": incident_id,
        "action_name": action_name,
        "parameters": parameters,
    })


def pending_remediations() -> List[Dict]:
    return _get("/remediation/pending")


def approve_remediation(remediation_id: str, approved_by: str, approved: bool = True) -> Dict:
    return _post(f"/remediation/{remediation_id}/approve",
                 json={"approved_by": approved_by, "approved": approved})


def execute_remediation(remediation_id: str, dry_run: bool = True) -> Dict:
    return _post(f"/remediation/{remediation_id}/execute?dry_run={str(dry_run).lower()}")
