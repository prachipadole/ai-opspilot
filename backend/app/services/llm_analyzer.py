"""
llm_analyzer.py – LLM-powered incident analysis using Ollama.

Workflow:
1. Retrieve relevant runbooks (RAG)
2. Build a structured prompt with incident context + runbook excerpts
3. Call Ollama and parse the structured response
4. Return root-cause, summary, and recommended actions
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import ollama
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.app.config import get_settings
from backend.app.services.retriever import get_retriever

settings = get_settings()

_SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) and IT operations analyst.
Your task is to diagnose incidents and provide actionable remediation steps.

Always respond with valid JSON in this exact schema:
{
  "root_cause": "<concise one-sentence root cause>",
  "summary": "<2-3 sentence explanation of what happened and its impact>",
  "severity_assessment": "<low|medium|high|critical with brief justification>",
  "recommended_actions": [
    {"step": 1, "action": "<action description>", "command": "<optional shell command>"}
  ],
  "runbooks_referenced": ["<runbook filename>"]
}

Be precise, technical, and concise."""


def _build_prompt(incident_title: str, raw_log: str, runbooks: List[Dict[str, Any]]) -> str:
    runbook_section = ""
    if runbooks:
        runbook_section = "\n\n## Relevant Runbooks\n"
        for rb in runbooks:
            name = rb.get("metadata", {}).get("filename", rb.get("id", "unknown"))
            # Limit each runbook excerpt to 800 chars to stay within context
            excerpt = rb.get("document", "")[:800]
            runbook_section += f"\n### {name}\n{excerpt}\n"

    return f"""## Incident Report

**Title:** {incident_title}

**Raw Log / Symptoms:**
```
{raw_log or "No raw log provided."}
```
{runbook_section}

## Task
Analyse the incident above. Use the runbook excerpts if relevant.
Return ONLY the JSON response, no markdown fences."""


class LLMAnalyzer:
    """Wraps the Ollama client for incident analysis with RAG augmentation."""

    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.model  = settings.ollama_model
        self.retriever = get_retriever()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def analyse(
        self,
        incident_title: str,
        raw_log: str,
        top_k_runbooks: int = 3,
    ) -> Dict[str, Any]:
        """
        Analyse an incident and return structured JSON with root cause,
        summary, severity, recommended actions, and referenced runbooks.
        """
        # Step 1 – RAG retrieval
        runbooks: List[Dict] = []
        try:
            runbooks = self.retriever.retrieve(
                query=f"{incident_title}\n{raw_log[:500]}",
                top_k=top_k_runbooks,
            )
        except Exception as exc:
            logger.warning(f"Runbook retrieval failed (will continue without): {exc}")

        # Step 2 – Build prompt
        user_prompt = _build_prompt(incident_title, raw_log, runbooks)

        # Step 3 – Call Ollama
        logger.info(f"Calling Ollama ({self.model}) for incident: {incident_title!r}")
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            options={"temperature": 0.2, "num_predict": 1024},
        )
        raw_content = response["message"]["content"].strip()

        # Step 4 – Parse JSON
        try:
            # Strip any accidental markdown fences
            if raw_content.startswith("```"):
                raw_content = raw_content.split("```")[1]
                if raw_content.startswith("json"):
                    raw_content = raw_content[4:]
            result = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON; wrapping as summary.")
            result = {
                "root_cause": "Unable to parse structured response.",
                "summary": raw_content[:500],
                "severity_assessment": "unknown",
                "recommended_actions": [],
                "runbooks_referenced": [],
            }

        result["runbooks_used"] = [r.get("id") for r in runbooks]
        result["llm_model"]     = self.model
        return result


# ── Module-level singleton ────────────────────────────────────────────────────
_analyzer: Optional[LLMAnalyzer] = None


def get_analyzer() -> LLMAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = LLMAnalyzer()
    return _analyzer
