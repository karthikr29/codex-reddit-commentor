#!/usr/bin/env python3
"""Self-tune scoring weights per subreddit based on feedback data."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

MIN_SAMPLES = 15
LEARNING_RATE = 0.05
WEIGHT_MIN = 0.05
WEIGHT_MAX = 0.40

DEFAULT_WEIGHTS = {
    "intent": 0.20,
    "tone": 0.15,
    "specificity": 0.20,
    "naturalness": 0.20,
    "safety": 0.15,
    "novelty": 0.10,
}

DIMENSION_KEYS = list(DEFAULT_WEIGHTS.keys())


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def spearman_rank_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation between two lists. Stdlib-only."""
    n = len(x)
    if n < 3:
        return 0.0

    def rank(values: list[float]) -> list[float]:
        sorted_indices = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        for rank_val, idx in enumerate(sorted_indices):
            ranks[idx] = float(rank_val + 1)
        return ranks

    rx = rank(x)
    ry = rank(y)

    d_sq_sum = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    rho = 1 - (6 * d_sq_sum) / (n * (n * n - 1))
    return max(-1.0, min(1.0, rho))


def optimize_weights(feedback: list[dict[str, Any]], current_weights: dict[str, float]) -> dict[str, float]:
    """Nudge weights based on correlation between score dimensions and upvotes."""
    if len(feedback) < MIN_SAMPLES:
        return dict(current_weights)

    upvotes = [e.get("upvotes", 0) for e in feedback]

    # For each dimension, compute correlation with upvotes
    correlations: dict[str, float] = {}
    for dim in DIMENSION_KEYS:
        scores = [e.get("breakdown", {}).get(dim, 50.0) for e in feedback]
        if all(s == scores[0] for s in scores):
            correlations[dim] = 0.0
        else:
            correlations[dim] = spearman_rank_correlation(scores, upvotes)

    # Nudge weights toward positively correlated dimensions
    new_weights = dict(current_weights)
    for dim in DIMENSION_KEYS:
        corr = correlations.get(dim, 0.0)
        nudge = corr * LEARNING_RATE
        new_weights[dim] = new_weights.get(dim, DEFAULT_WEIGHTS.get(dim, 0.15)) + nudge

    # Clamp weights
    for dim in DIMENSION_KEYS:
        new_weights[dim] = max(WEIGHT_MIN, min(WEIGHT_MAX, new_weights[dim]))

    # Normalize to sum to 1.0
    total = sum(new_weights[dim] for dim in DIMENSION_KEYS)
    if total > 0:
        for dim in DIMENSION_KEYS:
            new_weights[dim] = round(new_weights[dim] / total, 4)

    return new_weights


def cmd_optimize(runtime_root: Path) -> None:
    """Run weight optimization across all subreddits with enough data."""
    feedback_path = runtime_root / "state" / "feedback_history.json"
    profiles_path = runtime_root / "state" / "subreddit_profiles.json"

    feedback: list[dict[str, Any]] = read_json(feedback_path, [])
    profiles: dict[str, Any] = read_json(profiles_path, {})

    # Group feedback by subreddit
    by_sub: dict[str, list[dict[str, Any]]] = {}
    for entry in feedback:
        sub = entry.get("subreddit", "unknown")
        by_sub.setdefault(sub, []).append(entry)

    updated = 0
    for sub, entries in by_sub.items():
        if len(entries) < MIN_SAMPLES:
            continue

        current = profiles.get(sub, {}).get("weights", dict(DEFAULT_WEIGHTS))
        new_weights = optimize_weights(entries, current)

        upvotes = [e.get("upvotes", 0) for e in entries]
        avg_up = round(sum(upvotes) / len(upvotes), 1) if upvotes else 0

        profiles[sub] = {
            "weights": new_weights,
            "sample_size": len(entries),
            "avg_upvotes": avg_up,
            "last_updated": date.today().isoformat(),
        }
        updated += 1

    write_json(profiles_path, profiles)
    print(json.dumps({
        "subreddits_updated": updated,
        "total_profiles": len(profiles),
        "profiles": profiles,
    }, ensure_ascii=True, indent=2))


def cmd_show(runtime_root: Path) -> None:
    """Show current subreddit profiles."""
    profiles_path = runtime_root / "state" / "subreddit_profiles.json"
    profiles = read_json(profiles_path, {})
    print(json.dumps(profiles, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Self-tune scoring weights per subreddit from feedback.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("optimize", help="Run weight optimization for all subreddits.")
    sub.add_parser("show", help="Show current subreddit weight profiles.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "optimize":
        cmd_optimize(runtime_root)
    elif args.cmd == "show":
        cmd_show(runtime_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
