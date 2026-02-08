#!/usr/bin/env python3
"""Generate analytics reports and trend checks from feedback and state data."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BLOCK_CHARS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def bar_char(value: float, max_val: float) -> str:
    if max_val <= 0:
        return BLOCK_CHARS[0]
    index = min(len(BLOCK_CHARS) - 1, int(value / max_val * (len(BLOCK_CHARS) - 1)))
    return BLOCK_CHARS[index]


def text_histogram(data: dict[str, float], width: int = 20) -> str:
    if not data:
        return "  (no data)"
    max_val = max(data.values()) if data.values() else 1
    lines = []
    for label, val in data.items():
        bar_len = max(1, int(val / max_val * width)) if max_val > 0 else 1
        bar = "\u2588" * bar_len
        lines.append(f"  {label:>20s} | {bar} {val:.1f}")
    return "\n".join(lines)


def cmd_trend_check(runtime_root: Path) -> None:
    """Quick 5-line trend summary for session start."""
    feedback: list[dict[str, Any]] = read_json(runtime_root / "state" / "feedback_history.json", [])
    health: dict[str, Any] = read_json(runtime_root / "state" / "health_state.json", {})
    daily: dict[str, Any] = read_json(runtime_root / "state" / "daily_state.json", {})
    errors: list[dict[str, Any]] = read_json(runtime_root / "state" / "error_log.json", [])

    # Line 1: Volume
    today_count = daily.get("total_comments", 0)
    total_feedback = len(feedback)

    # Line 2: Engagement (last 7 days)
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = [e for e in feedback if e.get("harvested_at", "") > week_ago]
    avg_upvotes = round(sum(e.get("upvotes", 0) for e in recent) / max(1, len(recent)), 1) if recent else 0

    # Line 3: Health
    health_status = health.get("health_status", "unknown")

    # Line 4: Errors (last 24h)
    day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_errors = sum(1 for e in errors if e.get("timestamp", "") > day_ago)

    # Line 5: Top subreddit
    if recent:
        by_sub: dict[str, list[int]] = {}
        for e in recent:
            sub = e.get("subreddit", "?")
            by_sub.setdefault(sub, []).append(e.get("upvotes", 0))
        best_sub = max(by_sub.items(), key=lambda x: sum(x[1]) / len(x[1]))
        best_line = f"Best: {best_sub[0]} (avg {round(sum(best_sub[1])/len(best_sub[1]), 1)} upvotes)"
    else:
        best_line = "Best: insufficient data"

    lines = [
        f"Today: {today_count} comments | Lifetime feedback: {total_feedback}",
        f"7-day avg upvotes: {avg_upvotes} ({len(recent)} samples)",
        f"Health: {health_status}",
        f"Errors (24h): {recent_errors}",
        best_line,
    ]
    print("\n".join(lines))


def cmd_weekly_report(runtime_root: Path, week_label: str) -> None:
    """Generate a comprehensive weekly analytics markdown report."""
    feedback: list[dict[str, Any]] = read_json(runtime_root / "state" / "feedback_history.json", [])
    health: dict[str, Any] = read_json(runtime_root / "state" / "health_state.json", {})
    errors: list[dict[str, Any]] = read_json(runtime_root / "state" / "error_log.json", [])
    diversity: list[dict[str, Any]] = read_json(runtime_root / "state" / "diversity_state.json", [])
    profiles: dict[str, Any] = read_json(runtime_root / "state" / "subreddit_profiles.json", {})

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_fb = [e for e in feedback if e.get("harvested_at", "") > week_ago]
    recent_errors = [e for e in errors if e.get("timestamp", "") > week_ago]

    sections: list[str] = []
    sections.append(f"# Weekly Analytics Report: {week_label}\n")
    sections.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    # Volume
    sections.append("## Volume\n")
    sections.append(f"- Feedback entries this week: {len(recent_fb)}")
    sections.append(f"- Total feedback history: {len(feedback)}")
    sections.append(f"- Errors this week: {len(recent_errors)}\n")

    # Engagement
    sections.append("## Engagement\n")
    if recent_fb:
        by_sub: dict[str, list[dict[str, Any]]] = {}
        for e in recent_fb:
            sub = e.get("subreddit", "unknown")
            by_sub.setdefault(sub, []).append(e)

        sub_stats: list[tuple[str, float, int]] = []
        for sub, entries in by_sub.items():
            avg_up = sum(e.get("upvotes", 0) for e in entries) / len(entries)
            sub_stats.append((sub, round(avg_up, 1), len(entries)))

        sub_stats.sort(key=lambda x: x[1], reverse=True)

        sections.append("| Subreddit | Avg Upvotes | Sample Size |")
        sections.append("|-----------|-------------|-------------|")
        for sub, avg, n in sub_stats:
            sections.append(f"| {sub} | {avg} | {n} |")

        # Top performers
        top5 = sorted(recent_fb, key=lambda x: x.get("upvotes", 0), reverse=True)[:5]
        if top5:
            sections.append("\n### Top 5 Comments\n")
            for i, e in enumerate(top5, 1):
                sections.append(f"{i}. [{e.get('subreddit', '?')}]({e.get('url', '#')}) - {e.get('upvotes', 0)} upvotes, {e.get('replies', 0)} replies")
    else:
        sections.append("No engagement data this week.\n")

    # Health
    sections.append("\n## Health\n")
    sections.append(f"- Status: **{health.get('health_status', 'unknown')}**")
    sections.append(f"- Total checks: {health.get('total_checks', 0)}")
    sections.append(f"- Invisible count: {health.get('invisible_count', 0)}")
    sections.append(f"- Last check: {health.get('last_check', 'never')}\n")

    # Errors
    sections.append("## Errors\n")
    if recent_errors:
        error_types = Counter(e.get("error_type", "unknown") for e in recent_errors)
        for etype, count in error_types.most_common():
            sections.append(f"- {etype}: {count}")
    else:
        sections.append("No errors this week.\n")

    # Diversity
    sections.append("\n## Diversity\n")
    if diversity:
        openers = Counter(fp.get("opener_type", "?") for fp in diversity)
        buckets = Counter(fp.get("word_count_bucket", "?") for fp in diversity)
        starts_i = sum(1 for fp in diversity if fp.get("starts_with_i")) / len(diversity) * 100

        sections.append(f"- Sample size: {len(diversity)}")
        sections.append(f"- Starts with 'I': {starts_i:.0f}%")
        sections.append(f"- Opener types: {dict(openers)}")
        sections.append(f"- Length buckets: {dict(buckets)}")
    else:
        sections.append("No diversity data yet.\n")

    # Recommendations
    sections.append("\n## Recommendations\n")
    if recent_fb and len(by_sub) > 1:
        best = sub_stats[0]
        worst = sub_stats[-1]
        if best[1] > worst[1] * 2 and worst[2] >= 3:
            sections.append(f"- Consider reducing posting in {worst[0]} (avg {worst[1]} upvotes) and increasing in {best[0]} (avg {best[1]} upvotes)")
        if health.get("health_status") == "yellow":
            sections.append("- Health is yellow. Monitor for shadow ban indicators.")
        if len(recent_errors) > 10:
            sections.append("- High error rate this week. Review error log for patterns.")
    else:
        sections.append("- Not enough data for recommendations yet.")

    report = "\n".join(sections) + "\n"

    # Save to analytics directory
    analytics_dir = runtime_root / "tracking" / "reddit" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    report_path = analytics_dir / f"week-{week_label}.md"
    write_file(report_path, report)
    print(f"Report saved to: {report_path}")
    print(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate analytics reports from feedback and state data.")
    parser.add_argument("--runtime-root", required=True, help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("trend-check", help="Quick 5-line trend summary.")

    weekly = sub.add_parser("weekly-report", help="Generate weekly analytics report.")
    weekly.add_argument("--week", required=True, help="Week label (e.g., 2026-W06).")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve()

    if args.cmd == "trend-check":
        cmd_trend_check(runtime_root)
    elif args.cmd == "weekly-report":
        cmd_weekly_report(runtime_root, args.week)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
