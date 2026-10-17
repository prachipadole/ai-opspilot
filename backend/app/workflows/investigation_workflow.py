"""
investigation_workflow.py – LangGraph multi-stage incident investigation.

Stages:
  ingest → detect → correlate → analyse → remediate → human_review → done
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph
from loguru import logger

from backend.app.services.anomaly_detector import get_detector
from backend.app.services.event_correlator import EventCorrelator
from backend.app.services.llm_analyzer import get_analyzer
from backend.app.services.log_parser import extract_metrics, parse_logs
from backend.app.services.remediation_simulator import get_simulator


# ── State definition ──────────────────────────────────────────────────────────

class InvestigationState(TypedDict):
    raw_logs:      List[str]
    parsed_logs:   List[Dict[str, Any]]
    metrics:       Dict[str, List[float]]
    anomalies:     List[Any]
    correlated:    List[Any]
    analysis:      Optional[Dict[str, Any]]
    remediations:  List[str]
    human_approved: bool
    error:         Optional[str]


# ── Node functions ─────────────────────────────────────────────────────────────

def node_ingest(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Stage: ingest")
    parsed = parse_logs(state["raw_logs"])
    state["parsed_logs"] = parsed
    return state


def node_detect(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Stage: detect")
    metrics = extract_metrics(state["parsed_logs"])
    state["metrics"] = metrics

    detector = get_detector()
    results = detector.detect_batch(metrics)
    state["anomalies"] = [vars(r) for r in results]
    return state


def node_correlate(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Stage: correlate")
    from backend.app.services.anomaly_detector import AnomalyResult
    correlator = EventCorrelator()
    anomaly_objs = [AnomalyResult(**a) for a in state["anomalies"]]
    events = correlator.correlate(anomaly_objs, state["parsed_logs"])
    state["correlated"] = [vars(e) for e in events]
    return state


def node_analyse(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Stage: analyse")
    correlated = state["correlated"]
    if not correlated:
        state["analysis"] = {"summary": "No anomalies detected.", "root_cause": "N/A",
                             "recommended_actions": [], "runbooks_used": []}
        return state

    top = correlated[0]
    analyzer = get_analyzer()
    try:
        result = analyzer.analyse(
            incident_title=top["title"],
            raw_log=top["raw_log"],
        )
        state["analysis"] = result
    except Exception as exc:
        logger.error(f"LLM analysis failed: {exc}")
        state["analysis"] = {
            "summary": "Analysis unavailable (LLM error).",
            "root_cause": str(exc),
            "recommended_actions": [],
            "runbooks_used": [],
            "error": str(exc),
        }
    return state


def node_remediate(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Stage: remediate")
    simulator = get_simulator()
    analysis  = state.get("analysis") or {}
    correlated = state.get("correlated") or [{}]
    severity   = correlated[0].get("severity", "medium") if correlated else "medium"

    suggestions = simulator.suggest_actions(
        severity=severity,
        root_cause=analysis.get("root_cause", ""),
    )
    state["remediations"] = suggestions
    return state


def node_human_review(state: InvestigationState) -> InvestigationState:
    """
    Pause point for human approval.
    In API usage the caller inspects `human_approved` and resumes the graph.
    In automated mode we auto-approve for demo purposes.
    """
    logger.info("[Workflow] Stage: human_review – awaiting approval")
    # This would block until a human sets state["human_approved"] = True
    # via a webhook / UI action.  For demo, auto-approve.
    state["human_approved"] = True
    return state


def node_done(state: InvestigationState) -> InvestigationState:
    logger.info("[Workflow] Investigation complete.")
    return state


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(InvestigationState)

    graph.add_node("ingest",       node_ingest)
    graph.add_node("detect",       node_detect)
    graph.add_node("correlate",    node_correlate)
    graph.add_node("analyse",      node_analyse)
    graph.add_node("remediate",    node_remediate)
    graph.add_node("human_review", node_human_review)
    graph.add_node("done",         node_done)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest",       "detect")
    graph.add_edge("detect",       "correlate")
    graph.add_edge("correlate",    "analyse")
    graph.add_edge("analyse",      "remediate")
    graph.add_edge("remediate",    "human_review")
    graph.add_edge("human_review", "done")
    graph.add_edge("done",         END)

    return graph


def run_investigation(raw_logs: List[str]) -> InvestigationState:
    """Entry-point: run the full investigation workflow synchronously."""
    graph = build_graph()
    compiled = graph.compile()

    initial: InvestigationState = {
        "raw_logs":       raw_logs,
        "parsed_logs":    [],
        "metrics":        {},
        "anomalies":      [],
        "correlated":     [],
        "analysis":       None,
        "remediations":   [],
        "human_approved": False,
        "error":          None,
    }
    return compiled.invoke(initial)
