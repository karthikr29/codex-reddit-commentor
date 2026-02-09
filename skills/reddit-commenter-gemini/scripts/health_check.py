#!/usr/bin/env python3
"""Shadow ban detection and account health monitoring."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD = 3


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def default_health() -> dict[str, Any]:
    return {
        "last_check": None,
        "total_checks": 0,
        "invisible_count": 0,
        "consecutive_invisible": 0,
        "health_status": "green",
        "last_visible_url": None,
    }


def health_path(runtime_root: Path) -> Path:
    return runtime_root / "state" / "health_state.json"


def cmd_check(runtime_root: Path, results_file: str, threshold: int) -> int:
    """Process visibility check results and update health state."""
    hp = health_path(runtime_root)
    state = read_json(hp, default_health())
    results: list[dict[str, Any]] = json.loads(Path(results_file).read_text(encoding="utf-8"))

    now_iso = datetime.now(timezone.utc).isoformat()
    state["last_check"] = now_iso

    for r in results:
        state["total_checks"] = state.get("total_checks", 0) + 1
        visible = r.get("visible", True)

        if visible:
            state["consecutive_invisible"] = 0
            state["last_visible_url"] = r.get("url")
        else:
            state["invisible_count"] = state.get("invisible_count", 0) + 1
            state["consecutive_invisible"] = state.get("consecutive_invisible", 0) + 1

    # Determine health status
    consec = state.get("consecutive_invisible", 0)
    if consec >= threshold:
        state["health_status"] = "red"
    elif consec >= 1:
        state["health_status"] = "yellow"
    else:
        state["health_status"] = "green"

    write_json(hp, state)
    print(json.dumps(state, ensure_ascii=True, indent=2))

    return 1 if state["health_status"] == "red" else 0


def cmd_status(runtime_root: Path) -> int:
    """Print current health status."""
    hp = health_path(runtime_root)
    state = read_json(hp, default_health())
    print(json.dumps(state, ensure_ascii=True, indent=2))
    return 1 if state["health_status"] == "red" else 0


def cmd_reset(runtime_root: Path) -> None:
    """Reset health state to green (after manual verification)."""
    hp = health_path(runtime_root)
    state = default_health()
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    write_json(hp, state)
    print(json.dumps(state, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shadow ban detection and account health monitor.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="Process visibility check results.")
    check.add_argument("--results", required=True, help="Path to JSON file with visibility results.")
    check.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Consecutive invisible threshold for red status.")

    sub.add_parser("status", help="Print current health status.")
    sub.add_parser("reset", help="Reset health state to green.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "check":
        return cmd_check(runtime_root, args.results, args.threshold)
    elif args.cmd == "status":
        return cmd_status(runtime_root)
    elif args.cmd == "reset":
        cmd_reset(runtime_root)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
