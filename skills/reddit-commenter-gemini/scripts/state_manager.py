#!/usr/bin/env python3
"""State manager for reddit-commenter-safe runtime."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def _read_runtime_timezone_name(runtime_root: Path) -> str | None:
    """Best-effort parse of runtime config.yaml for `timezone: <IANA>`."""
    cfg = runtime_root / "config.yaml"
    if not cfg.exists():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("timezone:"):
            val = s.split(":", 1)[1].strip().strip('"').strip("'")
            return val or None
    return None


def today_iso(runtime_root: Path) -> str:
    """
    Return today's date in the runtime-configured timezone (defaults to local date
    if config is missing or invalid).
    """
    tz_name = _read_runtime_timezone_name(runtime_root)
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name)).date().isoformat()
        except Exception:
            pass
    return date.today().isoformat()


def state_paths(runtime_root: Path) -> dict[str, Path]:
    state_dir = runtime_root / "state"
    return {
        "state_dir": state_dir,
        "daily": state_dir / "daily_state.json",
        "ramp": state_dir / "ramp_state.json",
        "lock": state_dir / "session.lock",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def default_daily_state(day: str | None = None) -> dict[str, Any]:
    return {
        "date": day or today_iso(),
        "total_comments": 0,
        "per_subreddit": {},
        "commented_post_urls": [],
        "session_counts": {},
    }


def default_ramp_state() -> dict[str, Any]:
    return {
        "ramp_start_date": None,
        # Default to auto-posting unless explicitly enabled.
        "approval_ramp_days": 0,
    }


def cmd_init_day(runtime_root: Path, day: str | None, force: bool) -> None:
    paths = state_paths(runtime_root)
    target_day = day or today_iso(runtime_root)

    if not force and paths["daily"].exists():
        existing = read_json(paths["daily"], default_daily_state(day=target_day))
        if existing.get("date") == target_day:
            print(json.dumps(existing, ensure_ascii=True, indent=2))
            return

    state = default_daily_state(day=target_day)
    write_json(paths["daily"], state)
    print(json.dumps(state, ensure_ascii=True, indent=2))


def cmd_acquire_lock(runtime_root: Path, session: str) -> int:
    paths = state_paths(runtime_root)
    lock_path = paths["lock"]
    if lock_path.exists():
        print(lock_path.read_text(encoding="utf-8").strip())
        return 3

    payload = {
        "session": session,
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
    }
    write_json(lock_path, payload)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


def cmd_release_lock(runtime_root: Path) -> None:
    paths = state_paths(runtime_root)
    if paths["lock"].exists():
        paths["lock"].unlink()
    print("released")


def load_daily(runtime_root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    today = today_iso(runtime_root)
    state = read_json(paths["daily"], default_daily_state(day=today))
    if state.get("date") != today:
        state = default_daily_state(day=today)
        write_json(paths["daily"], state)
    return state


def cmd_update_count(runtime_root: Path, subreddit: str, increment: int, post_url: str | None) -> None:
    paths = state_paths(runtime_root)
    state = load_daily(runtime_root, paths)

    per_sub = state.setdefault("per_subreddit", {})
    per_sub[subreddit] = int(per_sub.get(subreddit, 0)) + increment
    state["total_comments"] = int(state.get("total_comments", 0)) + increment

    if post_url:
        urls = state.setdefault("commented_post_urls", [])
        if post_url not in urls:
            urls.append(post_url)

    write_json(paths["daily"], state)
    print(json.dumps(state, ensure_ascii=True, indent=2))


def cmd_remaining(runtime_root: Path, daily_cap: int, session_target: int) -> None:
    paths = state_paths(runtime_root)
    state = load_daily(runtime_root, paths)
    remaining_daily = max(0, daily_cap - int(state.get("total_comments", 0)))
    effective_target = min(session_target, remaining_daily)
    result = {
        "date": state["date"],
        "remaining_daily": remaining_daily,
        "session_target": effective_target,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def cmd_should_skip(runtime_root: Path, post_url: str) -> int:
    paths = state_paths(runtime_root)
    state = load_daily(runtime_root, paths)
    urls = set(state.get("commented_post_urls", []))
    should_skip = post_url in urls
    print(json.dumps({"post_url": post_url, "skip": should_skip}, ensure_ascii=True))
    return 4 if should_skip else 0


def cmd_set_ramp_start(runtime_root: Path, start_date: str) -> None:
    paths = state_paths(runtime_root)
    state = read_json(paths["ramp"], default_ramp_state())
    state["ramp_start_date"] = start_date
    write_json(paths["ramp"], state)
    print(json.dumps(state, ensure_ascii=True, indent=2))


def cmd_gate_mode(runtime_root: Path, check_date: str | None) -> None:
    paths = state_paths(runtime_root)
    ramp = read_json(paths["ramp"], default_ramp_state())
    start = ramp.get("ramp_start_date")
    days = int(ramp.get("approval_ramp_days", 7))
    current = datetime.strptime(check_date or today_iso(runtime_root), "%Y-%m-%d").date()

    # If ramp is disabled, always auto regardless of start date presence.
    if days <= 0:
        mode = "auto"
        day_index = 1
    elif not start:
        mode = "approval"
        day_index = 1
    else:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        delta = (current - start_date).days + 1
        day_index = max(1, delta)
        mode = "approval" if day_index <= days else "auto"

    print(
        json.dumps(
            {
                "date": current.isoformat(),
                "ramp_start_date": start,
                "approval_ramp_days": days,
                "ramp_day": day_index,
                "mode": mode,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


def cmd_update_diversity(runtime_root: Path, text_file: str) -> None:
    """Record a comment fingerprint for diversity tracking."""
    import re as _re

    text = Path(text_file).read_text(encoding="utf-8")

    # Classify opener
    lower = text.strip().lower()
    opener_patterns = {
        "question": r"^(have you|do you|what if|why not|how about|is there|could you|would you|ever)",
        "agreement": r"^(yeah|yes|agreed|same|exactly|right|true|this|100%)",
        "counterpoint": r"^(but|however|actually|not sure|disagree|on the flip|tbh|honestly|nah)",
        "anecdote": r"^(i (used to|was|had|tried|built|ran|worked)|we (had|tried|built)|my|when i)",
        "fact": r"^(the|most|one|there|it|according|studies|data|research|a lot of|many)",
        "opinion": r"^(i think|i feel|i believe|imo|personally|in my|i'd say|i would|i usually)",
    }

    opener_type = "direct"
    for otype, pattern in opener_patterns.items():
        if _re.match(pattern, lower):
            opener_type = otype
            break

    words = len(_re.findall(r"\b\w+\b", text))
    bucket = "short" if words < 20 else ("medium" if words <= 60 else "long")

    fp = {
        "opener_type": opener_type,
        "word_count_bucket": bucket,
        "has_question": "?" in text,
        "paragraph_count": max(1, len([p for p in text.split("\n\n") if p.strip()])),
        "starts_with_i": lower.startswith("i ") or lower.startswith("i'"),
        "uses_list": bool(_re.search(r"^\s*[-*\d]+[.)]?\s", text, _re.MULTILINE)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Persist to diversity_state.json
    diversity_path = runtime_root / "state" / "diversity_state.json"
    state = read_json(diversity_path, [])
    state.append(fp)
    if len(state) > 30:
        state = state[-30:]
    write_json(diversity_path, state)

    print(json.dumps(fp, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage runtime state for reddit-commenter-safe.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_day = sub.add_parser("init-day")
    init_day.add_argument("--date", help="Date in YYYY-MM-DD. Default today.")
    init_day.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing daily_state.json for the target date.",
    )

    acquire = sub.add_parser("acquire-lock")
    acquire.add_argument("--session", required=True, help="Session label.")

    sub.add_parser("release-lock")

    update = sub.add_parser("update-count")
    update.add_argument("--subreddit", required=True)
    update.add_argument("--increment", type=int, default=1)
    update.add_argument("--post-url")

    remaining = sub.add_parser("remaining")
    remaining.add_argument("--daily-cap", type=int, required=True)
    remaining.add_argument("--session-target", type=int, required=True)

    should_skip = sub.add_parser("should-skip")
    should_skip.add_argument("--post-url", required=True)

    set_ramp = sub.add_parser("set-ramp-start")
    set_ramp.add_argument("--start-date", required=True)

    gate = sub.add_parser("gate-mode")
    gate.add_argument("--date", help="Date in YYYY-MM-DD. Default today.")

    diversity = sub.add_parser("update-diversity")
    diversity.add_argument("--text-file", required=True, help="Path to file with posted comment text.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)

    if args.cmd == "init-day":
        cmd_init_day(runtime_root, args.date, args.force)
        return 0
    if args.cmd == "acquire-lock":
        return cmd_acquire_lock(runtime_root, args.session)
    if args.cmd == "release-lock":
        cmd_release_lock(runtime_root)
        return 0
    if args.cmd == "update-count":
        cmd_update_count(runtime_root, args.subreddit, args.increment, args.post_url)
        return 0
    if args.cmd == "remaining":
        cmd_remaining(runtime_root, args.daily_cap, args.session_target)
        return 0
    if args.cmd == "should-skip":
        return cmd_should_skip(runtime_root, args.post_url)
    if args.cmd == "set-ramp-start":
        cmd_set_ramp_start(runtime_root, args.start_date)
        return 0
    if args.cmd == "gate-mode":
        cmd_gate_mode(runtime_root, args.date)
        return 0

    if args.cmd == "update-diversity":
        cmd_update_diversity(runtime_root, args.text_file)
        return 0

    raise ValueError(f"Unsupported command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
