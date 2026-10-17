"""Evaluate RAG runbook retrieval accuracy and ranking performance."""

import json
import os
import time
from typing import Dict, Any

from backend.app.services.retriever import get_retriever


def evaluate_retrieval(benchmark_file: str = "evaluation/benchmark_data.json", top_k: int = 3) -> Dict[str, Any]:
    """Calculate Hit@1, Hit@K, MRR, and average latency for runbook retrieval."""
    if not os.path.exists(benchmark_file):
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")

    with open(benchmark_file, encoding="utf-8") as f:
        cases = json.load(f)

    retriever = get_retriever()
    hit_at_1 = 0
    hit_at_k = 0
    reciprocal_ranks = []
    latencies = []

    for case in cases:
        query = case["query"]
        expected = case["expected_runbook"]

        start_t = time.perf_counter()
        results = retriever.retrieve(query=query, top_k=top_k)
        latency = (time.perf_counter() - start_t) * 1000
        latencies.append(latency)

        retrieved_files = [
            r.get("metadata", {}).get("filename", "") for r in results
        ]

        # Check Hit@1
        if retrieved_files and retrieved_files[0] == expected:
            hit_at_1 += 1

        # Check Hit@K and MRR
        rank = 0
        for idx, filename in enumerate(retrieved_files):
            if filename == expected:
                rank = idx + 1
                hit_at_k += 1
                break

        if rank > 0:
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

    total = len(cases) if cases else 1
    mrr = sum(reciprocal_ranks) / total
    avg_latency = sum(latencies) / total

    return {
        "total_test_cases": len(cases),
        "hit_at_1_accuracy": round((hit_at_1 / total) * 100, 2),
        "hit_at_k_accuracy": round((hit_at_k / total) * 100, 2),
        "mrr": round(mrr, 4),
        "avg_latency_ms": round(avg_latency, 2),
    }


if __name__ == "__main__":
    report = evaluate_retrieval()
    print("=== RAG Retrieval Evaluation Report ===")
    for k, v in report.items():
        print(f"{k}: {v}")
