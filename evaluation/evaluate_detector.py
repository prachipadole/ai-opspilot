"""Evaluate Anomaly Detection accuracy, Precision, Recall, and F1."""

import random
import time
from typing import Dict, Any

from backend.app.services.anomaly_detector import AnomalyDetector


def evaluate_detector(n_normal: int = 200, n_anomalies: int = 20) -> Dict[str, Any]:
    """Generate synthetic time series with known injected anomalies and evaluate detection."""
    random.seed(42)
    detector = AnomalyDetector(min_samples=10, contamination=0.10)

    # 1. Warm-up detector with normal Gaussian distribution
    baseline_mean = 50.0
    baseline_std = 5.0
    for _ in range(50):
        detector.ingest("cpu_usage", random.gauss(baseline_mean, baseline_std))

    # 2. Prepare test dataset with ground truth
    test_samples = []
    # Normal samples
    for _ in range(n_normal):
        val = random.gauss(baseline_mean, baseline_std)
        test_samples.append((val, False))

    # Injected anomalies (massive spikes / drops)
    for _ in range(n_anomalies):
        if random.random() > 0.5:
            val = baseline_mean + random.uniform(30.0, 60.0)  # Extreme spike (80-110%)
        else:
            val = max(0.0, baseline_mean - random.uniform(35.0, 48.0))  # Sudden drop
        test_samples.append((val, True))

    random.shuffle(test_samples)

    tp, fp, fn, tn = 0, 0, 0, 0
    latencies = []

    for val, is_ground_truth_anomaly in test_samples:
        t0 = time.perf_counter()
        result = detector.detect("cpu_usage", val)
        latencies.append((time.perf_counter() - t0) * 1000)

        predicted_anomaly = result.is_anomaly

        if predicted_anomaly and is_ground_truth_anomaly:
            tp += 1
        elif predicted_anomaly and not is_ground_truth_anomaly:
            fp += 1
        elif not predicted_anomaly and is_ground_truth_anomaly:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(test_samples)

    return {
        "total_evaluated": len(test_samples),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "accuracy": round(accuracy * 100, 2),
        "precision": round(precision * 100, 2),
        "recall": round(recall * 100, 2),
        "f1_score": round(f1, 4),
        "avg_detection_latency_ms": round(sum(latencies) / len(latencies), 3),
    }


if __name__ == "__main__":
    report = evaluate_detector()
    print("=== Anomaly Detector Evaluation Report ===")
    for k, v in report.items():
        print(f"{k}: {v}")
