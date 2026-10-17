"""Evaluation Suite Orchestrator for AI-OpsPilot.

Runs anomaly detection benchmarks and RAG runbook retrieval benchmarks.
Usage:
    python evaluation/run_eval.py
"""

import json
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluate_detector import evaluate_detector


def main():
    print("==================================================")
    print("      🛡️  AI-OpsPilot — Evaluation Suite          ")
    print("==================================================")

    # 1. Anomaly Detector Benchmark
    print("\n[1/2] Running Anomaly Detection Benchmark...")
    detector_results = evaluate_detector(n_normal=200, n_anomalies=25)
    print(f"  • Accuracy: {detector_results['accuracy']}%")
    print(f"  • Precision: {detector_results['precision']}%")
    print(f"  • Recall: {detector_results['recall']}%")
    print(f"  • F1 Score: {detector_results['f1_score']}")
    print(f"  • Detection Latency: {detector_results['avg_detection_latency_ms']} ms/sample")

    # 2. RAG Retrieval Benchmark
    print("\n[2/2] Running RAG Runbook Retrieval Benchmark...")
    retriever_results = {}
    try:
        from evaluation.evaluate_retriever import evaluate_retrieval
        retriever_results = evaluate_retrieval()
        print(f"  • Hit@1 Accuracy: {retriever_results['hit_at_1_accuracy']}%")
        print(f"  • Hit@K Accuracy: {retriever_results['hit_at_k_accuracy']}%")
        print(f"  • MRR: {retriever_results['mrr']}")
        print(f"  • Avg Latency: {retriever_results['avg_latency_ms']} ms")
    except Exception as exc:
        print(f"  ⚠️ RAG Retrieval evaluation skipped or offline: {exc}")
        retriever_results = {"status": "skipped", "error": str(exc)}

    # Save summary report
    summary = {
        "anomaly_detector": detector_results,
        "rag_retriever": retriever_results,
    }
    report_path = os.path.join(os.path.dirname(__file__), "eval_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n==================================================")
    print(f"✅ Evaluation complete! Summary saved to {report_path}")
    print("==================================================")


if __name__ == "__main__":
    main()
