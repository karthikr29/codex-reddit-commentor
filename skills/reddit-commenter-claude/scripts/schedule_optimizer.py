#!/usr/bin/env python3
"""Optimize subreddit selection based on observed activity patterns."""

from __future__ import annotations

import argparse
import json
import re
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


def subreddits_path(runtime_root: Path) -> Path:
    return runtime_root / "subreddits.md"


def canonical_subreddit(name: str) -> str:
    sub = name.strip()
    if not sub:
        return ""
    if not sub.lower().startswith("r/"):
        sub = f"r/{sub}"
    return sub.lower()


def load_configured_subreddits(runtime_root: Path) -> list[str]:
    """Load target subreddit display names from runtime subreddits.md."""
    path = subreddits_path(runtime_root)
    if not path.exists():
        return []

    pattern = re.compile(r"\|\s*(r\/[^|]+?)\s*\|")
    display_by_canonical: dict[str, str] = {}
    ordered: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if not match:
            continue
        display = match.group(1).strip()
        key = canonical_subreddit(display)
        if not key or key in display_by_canonical:
            continue
        display_by_canonical[key] = display
        ordered.append(key)

    return [display_by_canonical[key] for key in ordered]


def build_ranked_list(
    configured: list[str],
    observed_scores: dict[str, float],
    observed_display: dict[str, str],
) -> list[dict[str, Any]]:
    """Return full priority list with observed entries first, then unobserved configured."""
    configured_keys = [canonical_subreddit(sub) for sub in configured if canonical_subreddit(sub)]
    configured_display = {canonical_subreddit(sub): sub for sub in configured if canonical_subreddit(sub)}

    ranked_observed_keys = sorted(observed_scores.keys(), key=lambda key: observed_scores[key], reverse=True)
    result: list[dict[str, Any]] = []
    seen: set[str] = set()

    for key in ranked_observed_keys:
        display = configured_display.get(key) or observed_display.get(key) or key
        result.append({"subreddit": display, "activity_score": round(observed_scores[key], 2)})
        seen.add(key)

    for key in configured_keys:
        if key in seen:
            continue
        display = configured_display[key]
        result.append({"subreddit": display, "activity_score": 0.0})
        seen.add(key)

    return result


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
    configured_subreddits = load_configured_subreddits(runtime_root)

    if not observations:
        base_priority = [{"subreddit": sub, "activity_score": 0.0} for sub in configured_subreddits]
        print(json.dumps({
            "message": "No observations yet.",
            "priorities": {},
            "default_priority": base_priority,
        }, ensure_ascii=True, indent=2))
        return

    # Parse observations into structured data
    # key format: "r/SubName|HH-HH|Day"
    slot_scores: dict[str, dict[str, list[float]]] = {}  # {time_bucket: {canonical_sub: [scores]}}
    observed_display: dict[str, str] = {}  # {canonical_sub: display_name}

    for key, entry in observations.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        subreddit_raw, time_bucket, _ = parts
        subreddit = canonical_subreddit(subreddit_raw)
        if not subreddit:
            continue
        count = entry.get("count", 0)
        if count < 1:
            continue

        avg_posts = entry["total_posts"] / count
        avg_age = entry["total_avg_age"] / count

        # Activity score: more posts + fresher = higher
        freshness_factor = max(0.1, 1.0 - (avg_age / 360))
        activity_score = avg_posts * freshness_factor

        slot_scores.setdefault(time_bucket, {})
        slot_scores[time_bucket].setdefault(subreddit, []).append(activity_score)
        observed_display.setdefault(subreddit, subreddit_raw)

    # Generate priority ordering per slot
    priorities: dict[str, list[dict[str, Any]]] = {}
    for time_bucket, subs in sorted(slot_scores.items()):
        avg_scores = {sub: (sum(scores) / len(scores)) for sub, scores in subs.items()}
        priorities[time_bucket] = build_ranked_list(configured_subreddits, avg_scores, observed_display)

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
    configured_subreddits = load_configured_subreddits(runtime_root)

    if current_hour is None:
        current_hour = datetime.now(timezone.utc).hour

    bucket = hour_bucket(current_hour)

    # Find all observations for this time bucket
    sub_scores: dict[str, list[float]] = {}
    observed_display: dict[str, str] = {}
    for key, entry in observations.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        subreddit_raw, time_bucket, _ = parts
        if time_bucket != bucket:
            continue
        subreddit = canonical_subreddit(subreddit_raw)
        if not subreddit:
            continue

        count = entry.get("count", 0)
        if count < 1:
            continue

        avg_posts = entry["total_posts"] / count
        avg_age = entry["total_avg_age"] / count
        freshness_factor = max(0.1, 1.0 - (avg_age / 360))
        activity_score = avg_posts * freshness_factor

        sub_scores.setdefault(subreddit, []).append(activity_score)
        observed_display.setdefault(subreddit, subreddit_raw)

    # Average scores
    avg_scores = {sub: sum(scores) / len(scores) for sub, scores in sub_scores.items()}
    ranked = build_ranked_list(configured_subreddits, avg_scores, observed_display)

    result = {
        "time_bucket": bucket,
        "suggestion": ranked,
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
