"""
Test suite for AI-OpsPilot.
Run: pytest tests/ -v
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Log Parser Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestLogParser:
    def test_json_log(self):
        from backend.app.services.log_parser import parse_log_line
        line = '{"service":"api","level":"ERROR","message":"DB timeout","response_time":3000}'
        result = parse_log_line(line)
        assert result["level"]   == "ERROR"
        assert result["service"] == "api"
        assert "timeout" in result["message"]

    def test_syslog(self):
        from backend.app.services.log_parser import parse_log_line
        line = "Oct 17 09:23:11 host01 nginx[1234]: [ERROR] upstream failed"
        result = parse_log_line(line)
        assert result["service"] == "nginx"
        assert result["level"]   == "ERROR"

    def test_plaintext_level_extraction(self):
        from backend.app.services.log_parser import parse_log_line
        result = parse_log_line("CRITICAL: disk full on /dev/sda1")
        assert result["level"] == "CRITICAL"

    def test_metric_extraction(self):
        from backend.app.services.log_parser import parse_logs, extract_metrics
        lines = [
            '{"service":"api","level":"ERROR","message":"fail"}',
            '{"service":"api","level":"INFO","message":"ok"}',
        ]
        parsed  = parse_logs(lines)
        metrics = extract_metrics(parsed)
        assert "error_rate" in metrics
        assert sum(metrics["error_rate"]) == 1.0   # exactly one error


# ─────────────────────────────────────────────────────────────────────────────
# Anomaly Detector Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestAnomalyDetector:
    def test_cold_start_returns_result(self):
        from backend.app.services.anomaly_detector import AnomalyDetector
        det = AnomalyDetector()
        result = det.detect("cpu_usage", 0.5)
        assert 0.0 <= result.anomaly_score <= 1.0

    def test_anomalous_value(self):
        from backend.app.services.anomaly_detector import AnomalyDetector
        det = AnomalyDetector(min_samples=5)
        # Feed normal values
        for _ in range(30):
            det.ingest("latency", 50.0)
        # Now inject outlier
        result = det.detect("latency", 9999.0)
        assert result.anomaly_score > 0.5

    def test_batch_detection(self):
        from backend.app.services.anomaly_detector import AnomalyDetector
        det = AnomalyDetector()
        metrics = {"error_rate": [0.0, 1.0, 0.0, 1.0, 1.0]}
        results = det.detect_batch(metrics)
        assert len(results) == 5


# ─────────────────────────────────────────────────────────────────────────────
# Event Correlator Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestEventCorrelator:
    def _make_anomaly(self, score: float, name: str = "cpu"):
        from backend.app.services.anomaly_detector import AnomalyResult
        return AnomalyResult(
            metric_name=name,
            metric_value=0.9,
            anomaly_score=score,
            is_anomaly=score > 0.5,
        )

    def test_critical_event(self):
        from backend.app.services.event_correlator import EventCorrelator
        corr   = EventCorrelator()
        events = corr.correlate([self._make_anomaly(0.9)], [])
        assert any(e.severity == "critical" for e in events)

    def test_no_anomaly_no_events(self):
        from backend.app.services.event_correlator import EventCorrelator
        corr   = EventCorrelator()
        events = corr.correlate([self._make_anomaly(0.1)], [])
        assert events == []

    def test_error_burst(self):
        from backend.app.services.event_correlator import EventCorrelator
        corr = EventCorrelator()
        logs = [{"level": "ERROR", "message": f"error {i}"} for i in range(6)]
        events = corr.correlate([], logs)
        assert any("burst" in e.title.lower() for e in events)


# ─────────────────────────────────────────────────────────────────────────────
# Remediation Simulator Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRemediationSimulator:
    def test_list_actions(self):
        from backend.app.services.remediation_simulator import RemediationSimulator
        sim = RemediationSimulator()
        actions = sim.list_actions()
        assert len(actions) > 0
        assert all("name" in a for a in actions)

    def test_suggest_memory(self):
        from backend.app.services.remediation_simulator import RemediationSimulator
        sim = RemediationSimulator()
        sug = sim.suggest_actions("critical", "OOM kill detected – memory leak in payment-api")
        assert "restart_service" in sug or "scale_up" in sug

    @pytest.mark.asyncio
    async def test_dry_run(self):
        from backend.app.services.remediation_simulator import RemediationSimulator
        sim = RemediationSimulator()
        result = await sim.execute("restart_service", {"service_name": "api"}, dry_run=True)
        assert result["success"] is True
        assert result["mode"] == "dry_run"

    def test_unknown_action(self):
        import asyncio
        from backend.app.services.remediation_simulator import RemediationSimulator
        sim = RemediationSimulator()
        result = asyncio.get_event_loop().run_until_complete(
            sim.execute("nonexistent_action", {})
        )
        assert result["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# LLM Analyzer Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestLLMAnalyzer:
    @patch("backend.app.services.llm_analyzer.ollama.Client")
    @patch("backend.app.services.llm_analyzer.get_retriever")
    def test_llm_analyzer_success(self, mock_get_retriever, mock_ollama_client):
        from backend.app.services.llm_analyzer import LLMAnalyzer

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"id": "db_conn.md", "document": "Runbook content", "metadata": {"filename": "db_conn.md"}}
        ]
        mock_get_retriever.return_value = mock_retriever

        mock_client_inst = MagicMock()
        mock_client_inst.chat.return_value = {
            "message": {
                "content": '{"root_cause":"Exhausted DB connection pool","summary":"Service could not acquire connection","severity_assessment":"critical","recommended_actions":[{"step":1,"action":"restart"}]}'
            }
        }
        mock_ollama_client.return_value = mock_client_inst

        analyzer = LLMAnalyzer()
        res = analyzer.analyse("DB Pool Outage", "FATAL: too many connections")

        assert res["root_cause"] == "Exhausted DB connection pool"
        assert res["severity_assessment"] == "critical"
        assert "db_conn.md" in res["runbooks_used"]

    @patch("backend.app.services.llm_analyzer.ollama.Client")
    @patch("backend.app.services.llm_analyzer.get_retriever")
    def test_llm_analyzer_fallback_on_invalid_json(self, mock_get_retriever, mock_ollama_client):
        from backend.app.services.llm_analyzer import LLMAnalyzer

        mock_get_retriever.return_value.retrieve.return_value = []
        mock_client_inst = MagicMock()
        mock_client_inst.chat.return_value = {
            "message": {"content": "This is raw unstructured text not valid JSON."}
        }
        mock_ollama_client.return_value = mock_client_inst

        analyzer = LLMAnalyzer()
        res = analyzer.analyse("Unstructured Issue", "some log")
        assert "Unable to parse" in res["root_cause"]
        assert "This is raw" in res["summary"]


# ─────────────────────────────────────────────────────────────────────────────
# Runbook Retriever Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRunbookRetriever:
    @patch("backend.app.services.retriever.SentenceTransformer")
    @patch("backend.app.services.retriever.chromadb.HttpClient")
    def test_retrieve_format(self, mock_chroma, mock_st):
        from backend.app.services.retriever import RunbookRetriever

        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.query.return_value = {
            "ids": [["runbook1.md"]],
            "documents": [["Restart service"]],
            "metadatas": [[{"filename": "runbook1.md"}]],
            "distances": [[0.12]],
        }
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
        mock_st.return_value.encode.return_value.tolist.return_value = [[0.1] * 384]

        retriever = RunbookRetriever()
        results = retriever.retrieve("OOM killed", top_k=1)
        assert len(results) == 1
        assert results[0]["id"] == "runbook1.md"
        assert results[0]["metadata"]["filename"] == "runbook1.md"


# ─────────────────────────────────────────────────────────────────────────────
# Investigation Workflow Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestInvestigationWorkflow:
    def test_graph_compilation(self):
        from backend.app.workflows.investigation_workflow import build_graph
        graph = build_graph()
        compiled = graph.compile()
        assert compiled is not None

    @patch("backend.app.workflows.investigation_workflow.get_analyzer")
    def test_workflow_execution(self, mock_get_analyzer):
        from backend.app.workflows.investigation_workflow import run_investigation

        mock_analyzer = MagicMock()
        mock_analyzer.analyse.return_value = {
            "root_cause": "Memory leak detected",
            "summary": "Service memory spiked",
            "recommended_actions": [],
            "runbooks_used": [],
        }
        mock_get_analyzer.return_value = mock_analyzer

        raw_logs = [
            '{"service":"api","level":"ERROR","message":"OOM memory critical"}',
            '{"service":"api","level":"ERROR","message":"Out of memory error"}',
        ]
        result = run_investigation(raw_logs)

        assert "parsed_logs" in result
        assert len(result["parsed_logs"]) == 2
        assert "anomalies" in result
        assert result["human_approved"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Suite Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestEvaluationSuite:
    def test_anomaly_detector_eval(self):
        from evaluation.evaluate_detector import evaluate_detector
        res = evaluate_detector(n_normal=50, n_anomalies=10)
        assert "accuracy" in res
        assert "precision" in res
        assert "recall" in res
        assert "f1_score" in res
        assert 0.0 <= res["accuracy"] <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Frontend API Client Unit Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestFrontendAPIClient:
    @patch("frontend.api_client.httpx.Client")
    def test_pending_remediations_call(self, mock_httpx):
        import frontend.api_client as client

        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "rem-1", "action_name": "restart_service"}]
        mock_response.raise_for_status = MagicMock()

        mock_client_inst = MagicMock()
        mock_client_inst.__enter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_client_inst

        pending = client.pending_remediations()
        assert len(pending) == 1
        assert pending[0]["action_name"] == "restart_service"


# ─────────────────────────────────────────────────────────────────────────────
# API Integration Tests (requires running backend)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
class TestAPI:
    """Integration tests – skipped if backend is not running."""

    @pytest.fixture
    def client(self):
        import httpx
        return httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0)

    async def test_health(self, client):
        async with client as c:
            r = await c.get("/api/v1/health")
        assert r.status_code == 200

    async def test_create_and_list_incident(self, client):
        async with client as c:
            r = await c.post("/api/v1/incidents", json={
                "title": "Test incident from pytest",
                "severity": "low",
            })
            assert r.status_code == 201
            inc_id = r.json()["id"]

            r2 = await c.get("/api/v1/incidents")
            assert r2.status_code == 200
            ids = [i["id"] for i in r2.json()]
            assert inc_id in ids

    async def test_ingest_logs(self, client):
        async with client as c:
            r = await c.post("/api/v1/logs/ingest", json={
                "logs": [{"message": "ERROR: payment timeout", "level": "ERROR"}]
            })
            assert r.status_code == 200
            assert r.json()["ingested"] == 1
