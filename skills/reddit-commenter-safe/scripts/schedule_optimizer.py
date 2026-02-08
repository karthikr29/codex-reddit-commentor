#!/usr/bin/env python3
"""Optimize subreddit selection based on observed activity patterns."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIN_OBSERVATIONS_PER_SLOT = 7  # Need at least a week of data per time slot


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def observations_path(runtime_root: Path) -> Path:
    return runtime_root / "state" / "activity_observations.json"


def hour_bucket(hour: int) -> str:
    """Map hour to a 2-hour bucket for aggregation."""
    bucket_start = (hour // 2) * 2
    return f"{bucket_start:02d}-{bucket_start+2:02d}"


def cmd_observe(runtime_root: Path, subreddit: str, post_count: int, avg_age_minutes: float) -> None:
    """Record an activity observation for a subreddit."""
    obs_path = observations_path(runtime_root)
    observations: dict[str, Any] = read_json(obs_path, {})

    now = datetime.now(timezone.utc)
    bucket = hour_bucket(now.hour)
    day_of_week = now.strftime("%a")  # Mon, Tue, etc.

    key = f"{subreddit}|{bucket}|{day_of_week}"
    entry = observations.get(key, {"count": 0, "total_posts": 0, "total_avg_age": 0.0})

    entry["count"] = entry.get("count", 0) + 1
    entry["total_posts"] = entry.get("total_posts", 0) + post_count
    entry["total_avg_age"] = entry.get("total_avg_age", 0.0) + avg_age_minutes
    entry["last_observed"] = now.isoformat()

    observations[key] = entry
    write_json(obs_path, observations)

    avg_posts = round(entry["total_posts"] / entry["count"], 1)
    print(json.dumps({
        "recorded": True,
        "key": key,
        "observations_for_slot": entry["count"],
        "avg_posts_in_slot": avg_posts,
    }, ensure_ascii=True, indent=2))


def cmd_optimize(runtime_root: Path) -> None:
    """Generate subreddit priority ordering per time slot."""
    obs_path = observations_path(runtime_root)
    observations: dict[str, Any] = read_json(obs_path, {})

    if not observations:
        print(json.dumps({"message": "No observations yet.", "priorities": {}}, ensure_ascii=True, indent=2))
        return

    # Parse observations into structured data
    # key format: "r/SubName|HH-HH|Day"
    slot_data: dict[str, dict[str, float]] = {}  # {time_bucket: {subreddit: avg_activity_score}}

    for key, entry in observations.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        subreddit, time_bucket, _ = parts
        count = entry.get("count", 0)
        if count < 1:
            continue

        avg_posts = entry["total_posts"] / count
        avg_age = entry["total_avg_age"] / count

        # Activity score: more posts + fresher = higher
        freshness_factor = max(0.1, 1.0 - (avg_age / 360))
        activity_score = avg_posts * freshness_factor

        slot_data.setdefault(time_bucket, {})
        existing = slot_data[time_bucket].get(subreddit, 0.0)
        # Average across days of week
        slot_data[time_bucket][subreddit] = (existing + activity_score) / 2 if existing else activity_score

    # Generate priority ordering per slot
    priorities: dict[str, list[dict[str, Any]]] = {}
    for time_bucket, subs in sorted(slot_data.items()):
        ranked = sorted(subs.items(), key=lambda x: x[1], reverse=True)
        priorities[time_bucket] = [
            {"subreddit": sub, "activity_score": round(score, 2)}
            for sub, score in ranked
        ]

    result = {
        "total_observations": len(observations),
        "time_slots": len(priorities),
        "priorities": priorities,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def cmd_suggest(runtime_root: Path, current_hour: int | None) -> None:
    """Suggest subreddit ordering for the current time slot."""
    obs_path = observations_path(runtime_root)
    observations: dict[str, Any] = read_json(obs_path, {})

    if current_hour is None:
        current_hour = datetime.now(timezone.utc).hour

    bucket = hour_bucket(current_hour)

    # Find all observations for this time bucket
    sub_scores: dict[str, list[float]] = {}
    for key, entry in observations.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        subreddit, time_bucket, _ = parts
        if time_bucket != bucket:
            continue

        count = entry.get("count", 0)
        if count < 1:
            continue

        avg_posts = entry["total_posts"] / count
        avg_age = entry["total_avg_age"] / count
        freshness_factor = max(0.1, 1.0 - (avg_age / 360))
        activity_score = avg_posts * freshness_factor

        sub_scores.setdefault(subreddit, []).append(activity_score)

    # Average scores
    avg_scores = {sub: sum(scores) / len(scores) for sub, scores in sub_scores.items()}
    ranked = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)

    result = {
        "time_bucket": bucket,
        "suggestion": [{"subreddit": sub, "activity_score": round(score, 2)} for sub, score in ranked],
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optimize subreddit selection by activity patterns.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    observe = sub.add_parser("observe", help="Record activity observation.")
    observe.add_argument("--subreddit", required=True, help="Subreddit name.")
    observe.add_argument("--post-count", type=int, required=True, help="Number of recent posts observed.")
    observe.add_argument("--avg-age-minutes", type=float, required=True, help="Average age of posts in minutes.")

    sub.add_parser("optimize", help="Generate priority ordering per time slot.")

    suggest = sub.add_parser("suggest", help="Suggest subreddit ordering for current time.")
    suggest.add_argument("--hour", type=int, help="Hour (0-23 UTC). Default: current hour.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "observe":
        cmd_observe(runtime_root, args.subreddit, args.post_count, args.avg_age_minutes)
    elif args.cmd == "optimize":
        cmd_optimize(runtime_root)
    elif args.cmd == "suggest":
        cmd_suggest(runtime_root, getattr(args, "hour", None))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
