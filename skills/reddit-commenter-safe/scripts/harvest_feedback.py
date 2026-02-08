#!/usr/bin/env python3
"""Harvest and persist performance feedback for posted Reddit comments."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_HISTORY = 500


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def state_paths(runtime_root: Path) -> dict[str, Path]:
    state_dir = runtime_root / "state"
    return {
        "daily": state_dir / "daily_state.json",
        "feedback": state_dir / "feedback_history.json",
    }


def cmd_harvest(runtime_root: Path, prev_state_file: str | None) -> None:
    """Output comment URLs eligible for harvesting (older than 4h, younger than 48h)."""
    paths = state_paths(runtime_root)
    now = datetime.now(timezone.utc)

    urls: list[dict[str, str]] = []

    # Current day state
    daily = read_json(paths["daily"], {})
    if daily.get("commented_post_urls"):
        for url in daily["commented_post_urls"]:
            urls.append({"url": url, "date": daily.get("date", ""), "subreddit": ""})

    # Previous day state if provided
    if prev_state_file:
        prev_path = Path(prev_state_file)
        prev = read_json(prev_path, {})
        if prev.get("commented_post_urls"):
            for url in prev["commented_post_urls"]:
                urls.append({"url": url, "date": prev.get("date", ""), "subreddit": ""})

    # Deduplicate against already-harvested URLs
    feedback = read_json(paths["feedback"], [])
    harvested_urls = {entry["url"] for entry in feedback}
    eligible = [u for u in urls if u["url"] not in harvested_urls]

    print(json.dumps({"eligible_count": len(eligible), "urls": eligible}, ensure_ascii=True, indent=2))


def cmd_merge(runtime_root: Path, input_file: str) -> None:
    """Merge harvested feedback results into feedback_history.json."""
    paths = state_paths(runtime_root)
    input_path = Path(input_file)

    new_entries: list[dict[str, Any]] = json.loads(input_path.read_text(encoding="utf-8"))
    feedback: list[dict[str, Any]] = read_json(paths["feedback"], [])

    existing_urls = {entry["url"] for entry in feedback}
    now_iso = datetime.now(timezone.utc).isoformat()

    added = 0
    for entry in new_entries:
        if entry.get("url") and entry["url"] not in existing_urls:
            entry["harvested_at"] = now_iso
            feedback.append(entry)
            existing_urls.add(entry["url"])
            added += 1

    # Trim to MAX_HISTORY (keep newest)
    if len(feedback) > MAX_HISTORY:
        feedback = feedback[-MAX_HISTORY:]

    write_json(paths["feedback"], feedback)
    print(json.dumps({"merged": added, "total": len(feedback)}, ensure_ascii=True, indent=2))


def cmd_stats(runtime_root: Path) -> None:
    """Print summary stats from feedback history."""
    paths = state_paths(runtime_root)
    feedback: list[dict[str, Any]] = read_json(paths["feedback"], [])

    if not feedback:
        print(json.dumps({"total": 0, "message": "No feedback data yet."}, ensure_ascii=True, indent=2))
        return

    total = len(feedback)
    upvotes = [e.get("upvotes", 0) for e in feedback]
    replies = [e.get("replies", 0) for e in feedback]
    visible = sum(1 for e in feedback if e.get("visible", True))

    by_sub: dict[str, list[int]] = {}
    for e in feedback:
        sub = e.get("subreddit", "unknown")
        by_sub.setdefault(sub, []).append(e.get("upvotes", 0))

    sub_avgs = {sub: round(sum(v) / len(v), 1) for sub, v in by_sub.items()}

    result = {
        "total_entries": total,
        "avg_upvotes": round(sum(upvotes) / total, 1),
        "avg_replies": round(sum(replies) / total, 1),
        "visible_pct": round(visible / total * 100, 1),
        "by_subreddit_avg_upvotes": sub_avgs,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest and persist comment performance feedback.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    harvest = sub.add_parser("harvest", help="List comment URLs eligible for harvesting.")
    harvest.add_argument("--prev-state", help="Path to previous day's daily_state.json.")

    merge = sub.add_parser("merge", help="Merge harvested feedback into history.")
    merge.add_argument("--input", required=True, help="Path to JSON file with harvest results.")

    sub.add_parser("stats", help="Print feedback summary statistics.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "harvest":
        cmd_harvest(runtime_root, getattr(args, "prev_state", None))
    elif args.cmd == "merge":
        cmd_merge(runtime_root, args.input)
    elif args.cmd == "stats":
        cmd_stats(runtime_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
