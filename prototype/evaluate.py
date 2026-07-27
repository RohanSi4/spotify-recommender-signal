"""Credential-free quality and latency evaluation for the ranking core."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from typing import Any

from demo_data import build_demo_catalog
from recommender import RecommendationEngine, reciprocal_rank_hit_rate


def evaluate(iterations: int = 250, k: int = 5) -> dict[str, Any]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    catalog = build_demo_catalog()
    hit_rate, mean_reciprocal_rank = reciprocal_rank_hit_rate(catalog, k=k)
    engine = RecommendationEngine()
    latencies_ms: list[float] = []
    for index in range(iterations):
        seed = catalog[index % len(catalog)]
        started = time.perf_counter_ns()
        engine.recommend([seed], catalog, k)
        latencies_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(latencies_ms)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "dataset": "synthetic-mood-fixture-v1",
        "tracks": len(catalog),
        "queries": len(catalog),
        "k": k,
        "hit_rate_at_k": round(hit_rate, 4),
        "mean_reciprocal_rank": round(mean_reciprocal_rank, 4),
        "benchmark_iterations": iterations,
        "latency_ms_median": round(statistics.median(latencies_ms), 3),
        "latency_ms_p95": round(ordered[p95_index], 3),
        "disclosure": "Synthetic regression fixture; not evidence of real-user recommendation quality.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=250)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args()
    result = evaluate(args.iterations, args.k)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    print("Offline recommendation evaluation")
    print(f"  dataset: {result['dataset']} ({result['tracks']} tracks)")
    print(f"  hit-rate@{result['k']}: {result['hit_rate_at_k']:.1%}")
    print(f"  mean reciprocal rank: {result['mean_reciprocal_rank']:.3f}")
    print(
        f"  ranking latency: {result['latency_ms_median']:.3f} ms median / {result['latency_ms_p95']:.3f} ms p95"
    )
    print(f"  disclosure: {result['disclosure']}")


if __name__ == "__main__":
    main()
