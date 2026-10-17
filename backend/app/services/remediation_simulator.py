"""
remediation_simulator.py – Simulate and execute remediation actions.

In production, actions would call real APIs (k8s, cloud provider, etc.).
Here we provide a safe simulation layer with a human-approval gate.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


# ── Action catalogue ──────────────────────────────────────────────────────────
ACTION_CATALOGUE: Dict[str, Dict[str, Any]] = {
    "restart_service": {
        "description": "Restart a named system service.",
        "params":      ["service_name"],
        "risk":        "low",
        "simulated_duration_s": 3,
    },
    "scale_up": {
        "description": "Increase replica count for a deployment.",
        "params":      ["deployment", "replicas"],
        "risk":        "low",
        "simulated_duration_s": 5,
    },
    "rollback_deployment": {
        "description": "Roll back to the previous deployment revision.",
        "params":      ["deployment", "namespace"],
        "risk":        "medium",
        "simulated_duration_s": 10,
    },
    "clear_cache": {
        "description": "Flush application / Redis cache.",
        "params":      ["cache_host"],
        "risk":        "low",
        "simulated_duration_s": 2,
    },
    "isolate_node": {
        "description": "Cordon and drain a Kubernetes node.",
        "params":      ["node_name"],
        "risk":        "high",
        "simulated_duration_s": 15,
    },
    "rotate_credentials": {
        "description": "Rotate compromised API keys or DB credentials.",
        "params":      ["resource_name"],
        "risk":        "medium",
        "simulated_duration_s": 7,
    },
}


@dataclass_ish := lambda: None  # noqa – use plain class for simplicity


class RemediationSimulator:
    """
    Simulate execution of remediation actions with a human-approval gate.
    """

    def list_actions(self) -> List[Dict[str, Any]]:
        """Return the full catalogue of available actions."""
        return [
            {"name": name, **details}
            for name, details in ACTION_CATALOGUE.items()
        ]

    def suggest_actions(self, severity: str, root_cause: str) -> List[str]:
        """
        Heuristically suggest action names given severity and root-cause text.
        """
        suggestions: List[str] = []
        root_lower = (root_cause or "").lower()

        if "memory" in root_lower or "oom" in root_lower:
            suggestions += ["restart_service", "scale_up"]
        if "deploy" in root_lower or "release" in root_lower:
            suggestions += ["rollback_deployment"]
        if "cache" in root_lower or "redis" in root_lower:
            suggestions += ["clear_cache"]
        if "node" in root_lower or "hardware" in root_lower:
            suggestions += ["isolate_node"]
        if "credential" in root_lower or "auth" in root_lower or "key" in root_lower:
            suggestions += ["rotate_credentials"]

        # Fallback
        if not suggestions:
            if severity in ("critical", "high"):
                suggestions = ["restart_service", "scale_up"]
            else:
                suggestions = ["clear_cache", "restart_service"]

        # De-duplicate
        seen: set = set()
        return [x for x in suggestions if not (x in seen or seen.add(x))]

    async def execute(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute (or simulate) an action.
        Always runs in dry-run mode unless dry_run=False.
        """
        if action_name not in ACTION_CATALOGUE:
            return {"success": False, "error": f"Unknown action: {action_name}"}

        spec = ACTION_CATALOGUE[action_name]
        duration = spec["simulated_duration_s"]

        if dry_run:
            logger.info(f"[DRY-RUN] Would execute: {action_name} with {parameters}")
            await asyncio.sleep(0.5)   # simulate network latency
            return {
                "success": True,
                "mode": "dry_run",
                "action": action_name,
                "parameters": parameters,
                "message": f"Dry-run: {spec['description']}",
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Simulate actual execution
        logger.warning(f"[EXECUTE] Running: {action_name} with {parameters}")
        await asyncio.sleep(duration)

        # Inject ~5 % failure rate for realism
        if random.random() < 0.05:
            return {
                "success": False,
                "mode": "live",
                "action": action_name,
                "error": "Simulated execution failure (transient).",
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "success": True,
            "mode": "live",
            "action": action_name,
            "parameters": parameters,
            "message": f"Successfully executed: {spec['description']}",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }


# ── Module-level singleton ────────────────────────────────────────────────────
_simulator: Optional[RemediationSimulator] = None


def get_simulator() -> RemediationSimulator:
    global _simulator
    if _simulator is None:
        _simulator = RemediationSimulator()
    return _simulator
