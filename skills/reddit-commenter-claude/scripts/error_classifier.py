#!/usr/bin/env python3
"""Classify errors and prescribe recovery actions with progressive backoff."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

MAX_LOG_ENTRIES = 100

ERROR_CATEGORIES = {
    "rate_limit": {
        "backoff_minutes": [5, 15, 30, 60],
        "max_retries": 4,
        "should_continue_session": True,
        "description": "Reddit rate limit (429). Progressive backoff applied.",
    },
    "forbidden": {
        "backoff_minutes": [0],
        "max_retries": 0,
        "should_continue_session": True,
        "description": "Forbidden (403). Possible subreddit ban. Skip subreddit for rest of day.",
    },
    "not_found": {
        "backoff_minutes": [0],
        "max_retries": 0,
        "should_continue_session": True,
        "description": "Not found (404). Post was deleted. Skip silently.",
    },
    "network_timeout": {
        "backoff_minutes": [2],
        "max_retries": 1,
        "should_continue_session": True,
        "description": "Network timeout. Retry once after 2 minutes.",
    },
    "login_expired": {
        "backoff_minutes": [0],
        "max_retries": 0,
        "should_continue_session": False,
        "description": "Login session expired. End session. Manual re-login required.",
    },
    "content_policy": {
        "backoff_minutes": [0],
        "max_retries": 0,
        "should_continue_session": True,
        "description": "Reddit rejected comment content. Flag for style guard review. Skip post.",
    },
    "playwright_crash": {
        "backoff_minutes": [1],
        "max_retries": 1,
        "should_continue_session": True,
        "description": "Playwright browser error. Attempt recovery. If persistent, end session.",
    },
    "unknown": {
        "backoff_minutes": [5],
        "max_retries": 1,
        "should_continue_session": True,
        "description": "Unknown error. Retry once with short backoff.",
    },
}


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def error_log_path(runtime_root: Path) -> Path:
    return runtime_root / "state" / "error_log.json"


def cmd_classify(runtime_root: Path, error_type: str, context: str, subreddit: str) -> None:
    """Classify an error and return a recovery recommendation."""
    log_path = error_log_path(runtime_root)
    log: list[dict[str, Any]] = read_json(log_path, [])
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    category = ERROR_CATEGORIES.get(error_type, ERROR_CATEGORIES["unknown"])

    # Count recent errors of same type in last hour
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    recent_same_type = sum(
        1 for e in log
        if e.get("error_type") == error_type and e.get("timestamp", "") > one_hour_ago
    )

    # Determine backoff based on retry count
    backoff_schedule = category["backoff_minutes"]
    backoff_index = min(recent_same_type, len(backoff_schedule) - 1)
    cooldown = backoff_schedule[backoff_index]

    # Check if we should recommend ending session
    should_continue = category["should_continue_session"]
    if error_type == "rate_limit" and recent_same_type >= 3:
        should_continue = False

    # Check if retries exceeded
    retries_exhausted = recent_same_type >= category["max_retries"]
    if retries_exhausted and error_type not in ("not_found", "content_policy"):
        should_continue = error_type not in ("login_expired", "playwright_crash")

    # Log the error
    entry = {
        "timestamp": now_iso,
        "error_type": error_type,
        "context": context,
        "subreddit": subreddit,
        "recent_count": recent_same_type + 1,
    }
    log.append(entry)

    # Trim log
    if len(log) > MAX_LOG_ENTRIES:
        log = log[-MAX_LOG_ENTRIES:]
    write_json(log_path, log)

    recommendation = {
        "error_type": error_type,
        "category": category["description"],
        "cooldown_minutes": cooldown,
        "should_continue_session": should_continue,
        "retries_exhausted": retries_exhausted,
        "recent_same_type_count": recent_same_type + 1,
        "action": _recommend_action(error_type, retries_exhausted, should_continue, subreddit),
    }

    print(json.dumps(recommendation, ensure_ascii=True, indent=2))


def _recommend_action(error_type: str, retries_exhausted: bool, should_continue: bool, subreddit: str) -> str:
    if not should_continue:
        if error_type == "login_expired":
            return "END_SESSION: Login expired. Manual re-login required."
        if error_type == "rate_limit":
            return "END_SESSION: Too many rate limits in the last hour. Resume in next session."
        return "END_SESSION: Repeated errors. Stop gracefully."

    if error_type == "forbidden":
        return f"SKIP_SUBREDDIT: Skip {subreddit} for the rest of this session."
    if error_type == "not_found":
        return "SKIP_POST: Post deleted. Move to next post."
    if error_type == "content_policy":
        return "SKIP_POST: Content rejected by Reddit. Flag comment text for review. Move to next post."
    if retries_exhausted:
        return "SKIP_POST: Retries exhausted for this error. Move to next post."

    return "RETRY: Wait for cooldown then retry."


def cmd_summary(runtime_root: Path) -> None:
    """Print error summary for recent session."""
    log_path = error_log_path(runtime_root)
    log: list[dict[str, Any]] = read_json(log_path, [])

    if not log:
        print(json.dumps({"total": 0, "message": "No errors logged."}, ensure_ascii=True, indent=2))
        return

    now = datetime.now(timezone.utc)
    last_24h = (now - timedelta(hours=24)).isoformat()
    recent = [e for e in log if e.get("timestamp", "") > last_24h]

    by_type: dict[str, int] = {}
    for e in recent:
        t = e.get("error_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    result = {
        "total_last_24h": len(recent),
        "by_type": by_type,
        "total_all_time": len(log),
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify errors and prescribe recovery actions.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    classify = sub.add_parser("classify", help="Classify an error and get recovery action.")
    classify.add_argument("--error-type", required=True, choices=list(ERROR_CATEGORIES.keys()), help="Error category.")
    classify.add_argument("--context", default="", help="Error context/message.")
    classify.add_argument("--subreddit", default="", help="Subreddit where error occurred.")

    sub.add_parser("summary", help="Print error summary.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "classify":
        cmd_classify(runtime_root, args.error_type, args.context, args.subreddit)
    elif args.cmd == "summary":
        cmd_summary(runtime_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
