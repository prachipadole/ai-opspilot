"""
anomaly_detector.py – Unsupervised anomaly detection using Isolation Forest.
Trained on-the-fly from the rolling metric window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from loguru import logger
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from backend.app.config import get_settings

settings = get_settings()


@dataclass
class AnomalyResult:
    metric_name: str
    metric_value: float
    anomaly_score: float          # Higher = more anomalous  (0..1)
    is_anomaly: bool
    threshold: float = 0.5


class AnomalyDetector:
    """
    Maintains a rolling window of metric observations and detects anomalies
    using scikit-learn's IsolationForest with automatic re-training.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        min_samples: int = 20,
        window_size: int = 500,
    ):
        self.contamination = contamination
        self.min_samples = min_samples
        self.window_size = window_size

        self._windows: Dict[str, List[float]] = {}
        self._models:  Dict[str, IsolationForest] = {}
        self._scalers: Dict[str, StandardScaler]  = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def ingest(self, metric_name: str, value: float) -> None:
        """Add a new observation to the rolling window."""
        window = self._windows.setdefault(metric_name, [])
        window.append(value)
        if len(window) > self.window_size:
            window.pop(0)

    def detect(self, metric_name: str, value: float) -> AnomalyResult:
        """Ingest a value and immediately score it for anomaly."""
        self.ingest(metric_name, value)
        window = self._windows[metric_name]

        if len(window) < self.min_samples:
            # Not enough data — use simple z-score
            score = self._zscore_score(window, value)
            return AnomalyResult(
                metric_name=metric_name,
                metric_value=value,
                anomaly_score=score,
                is_anomaly=score > 0.7,
            )

        model, scaler = self._get_or_train(metric_name, window)
        X = scaler.transform([[value]])
        raw_score = model.score_samples(X)[0]          # negative → [-∞, 0]
        # Normalise: convert to [0, 1] where 1 = most anomalous
        normalised = 1.0 - (raw_score + 0.5).clip(0, 1)

        return AnomalyResult(
            metric_name=metric_name,
            metric_value=value,
            anomaly_score=float(normalised),
            is_anomaly=bool(normalised > 0.6),
        )

    def detect_batch(
        self, metrics: Dict[str, List[float]]
    ) -> List[AnomalyResult]:
        """Detect anomalies across multiple metrics."""
        results: List[AnomalyResult] = []
        for metric_name, values in metrics.items():
            for v in values:
                results.append(self.detect(metric_name, v))
        return results

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_or_train(
        self, metric_name: str, window: List[float]
    ) -> tuple[IsolationForest, StandardScaler]:
        scaler = self._scalers.get(metric_name) or StandardScaler()
        X = np.array(window).reshape(-1, 1)
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        model.fit(X_scaled)

        self._models[metric_name]  = model
        self._scalers[metric_name] = scaler
        return model, scaler

    @staticmethod
    def _zscore_score(window: List[float], value: float) -> float:
        if len(window) < 2:
            return 0.0
        arr = np.array(window)
        mean, std = arr.mean(), arr.std()
        if std == 0:
            return 0.0
        z = abs((value - mean) / std)
        return float(min(z / 4.0, 1.0))   # clip to [0, 1]


# ── Module-level singleton ────────────────────────────────────────────────────
_detector: Optional[AnomalyDetector] = None


def get_detector() -> AnomalyDetector:
    global _detector
    if _detector is None:
        _detector = AnomalyDetector(
            contamination=settings.anomaly_contamination
        )
    return _detector
