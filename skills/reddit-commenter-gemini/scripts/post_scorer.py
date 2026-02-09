#!/usr/bin/env python3
"""Score and rank Reddit posts by engagement potential."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

HIGH_ACTIVITY_SUBS = {
    "chatgpt", "ai", "entrepreneur", "webdev", "programming",
}

LOW_ACTIVITY_SUBS = {
    "rag", "ai_testing", "aitool_testing", "entrepreneurial",
}


def score_post(post: dict[str, Any]) -> dict[str, Any]:
    """Score a single post's engagement potential (0-100)."""
    age_min = post.get("age_minutes", 60)
    upvotes = post.get("upvotes", 1)
    comment_count = post.get("comment_count", 0)
    subreddit = post.get("subreddit", "").lower().replace("r/", "")
    is_question = post.get("is_question", False)
    title = post.get("title", "")

    score = 50.0
    breakdown: dict[str, float] = {}

    # Freshness bonus
    if age_min < 60:
        freshness = 20.0
    elif age_min < 120:
        freshness = 10.0
    elif age_min < 360:
        freshness = 0.0
    else:
        freshness = -15.0

    # Adjust freshness decay for subreddit activity level
    if subreddit in LOW_ACTIVITY_SUBS:
        freshness = max(freshness, -5.0)  # Low-activity subs have longer windows
    elif subreddit in HIGH_ACTIVITY_SUBS and age_min > 180:
        freshness -= 5.0  # High-activity subs decay faster

    score += freshness
    breakdown["freshness"] = round(freshness, 1)

    # Velocity signal (upvotes per hour)
    hours = max(0.1, age_min / 60)
    velocity = upvotes / hours
    velocity_bonus = min(15.0, velocity * 3)
    score += velocity_bonus
    breakdown["velocity"] = round(velocity_bonus, 1)

    # Comment count sweet spot
    if comment_count <= 5:
        comment_bonus = 15.0
    elif comment_count <= 15:
        comment_bonus = 0.0
    else:
        comment_bonus = -20.0
    score += comment_bonus
    breakdown["comment_saturation"] = round(comment_bonus, 1)

    # Question bonus
    if is_question or "?" in title:
        q_bonus = 10.0
    else:
        q_bonus = 0.0
    score += q_bonus
    breakdown["question_bonus"] = round(q_bonus, 1)

    # Upvote floor (very low upvotes = low interest)
    if upvotes <= 0:
        up_penalty = -10.0
    elif upvotes >= 10:
        up_penalty = 5.0
    else:
        up_penalty = 0.0
    score += up_penalty
    breakdown["upvote_signal"] = round(up_penalty, 1)

    total = max(0.0, min(100.0, score))

    return {
        "title": title,
        "subreddit": post.get("subreddit", ""),
        "engagement_potential": round(total, 1),
        "breakdown": breakdown,
        "metadata": {
            "age_minutes": age_min,
            "upvotes": upvotes,
            "comment_count": comment_count,
        },
    }


def cmd_score(input_file: str, output_file: str | None) -> None:
    """Score and rank posts by engagement potential."""
    posts: list[dict[str, Any]] = json.loads(Path(input_file).read_text(encoding="utf-8"))

    scored = [score_post(p) for p in posts]
    scored.sort(key=lambda x: x["engagement_potential"], reverse=True)

    result = {
        "post_count": len(posts),
        "ranked": scored,
        "best": scored[0] if scored else None,
    }

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if output_file:
        Path(output_file).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score Reddit posts by engagement potential.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    score = sub.add_parser("score", help="Score and rank posts.")
    score.add_argument("--input", required=True, help="Path to JSON file with post metadata.")
    score.add_argument("--output", help="Path to output JSON. If omitted, prints to stdout.")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.cmd == "score":
        cmd_score(args.input, getattr(args, "output", None))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
