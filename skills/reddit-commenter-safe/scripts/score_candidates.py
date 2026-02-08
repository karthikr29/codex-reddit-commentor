#!/usr/bin/env python3
"""Score and rank Reddit comment candidates."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from typing import Any

from style_guard import evaluate_text

STOP_WORDS = {
    "a", "an", "the", "and", "or", "to", "for", "of", "in", "on", "at", "with", "is", "are", "was", "were",
    "it", "that", "this", "as", "be", "by", "from", "if", "you", "your", "i", "we", "they", "he", "she",
}

TECH_SUBREDDITS = {
    "webdev",
    "claudeai",
    "claude",
    "cursor",
    "localllama",
    "chatgpt",
    "sideproject",
    "sideprojects",
    "obsidian",
    "rag",
    "programming",
    "ai",
    "entrepreneur",
    "entrepreneurship",
    "entrepreneurial",
}


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t and t not in STOP_WORDS]


def token_overlap_score(post_text: str, comment_text: str) -> float:
    post_tokens = tokenize(post_text)
    comment_tokens = tokenize(comment_text)
    if not post_tokens or not comment_tokens:
        return 0.0

    post_counts = Counter(post_tokens)
    comment_counts = Counter(comment_tokens)

    overlap = 0
    for token, count in post_counts.items():
        overlap += min(count, comment_counts.get(token, 0))

    score = (overlap / max(1, len(post_tokens))) * 100
    return min(100.0, score)


def subreddit_tone_score(subreddit: str, comment_text: str) -> float:
    sub = subreddit.lower().replace("r/", "")
    words = len(re.findall(r"\b\w+\b", comment_text))
    score = 65.0

    if sub in TECH_SUBREDDITS:
        if 12 <= words <= 90:
            score += 15
        if re.search(r"\b(debug|tradeoff|latency|workflow|context|quota|rate|cache|session)\b", comment_text.lower()):
            score += 10
    else:
        if 8 <= words <= 70:
            score += 10

    if re.search(r"\b(buy now|dm me|sign up|free trial|book a demo)\b", comment_text.lower()):
        score -= 35

    if comment_text.count("!") > 2:
        score -= 10

    return max(0.0, min(100.0, score))


def specificity_value_score(comment_text: str) -> float:
    score = 40.0
    lower = comment_text.lower()

    if re.search(r"\b(for example|for instance|one way|in practice|step|try|check)\b", lower):
        score += 15

    if re.search(r"\b\d+\b", comment_text):
        score += 10

    if re.search(r"\b(why|because|so that|which means)\b", lower):
        score += 15

    if re.search(r"\b(idk|lol same)$", lower.strip()):
        score -= 15

    return max(0.0, min(100.0, score))


def naturalness_score(comment_text: str) -> float:
    score = 70.0
    lower = comment_text.lower()

    contractions = len(re.findall(r"\b\w+'\w+\b", comment_text))
    if contractions >= 1:
        score += 8

    comma_count = comment_text.count(",")
    if comma_count > 5:
        score -= 8

    sentences = [s.strip() for s in re.split(r"[.!?]+", comment_text) if s.strip()]
    if len(sentences) >= 2:
        lengths = [len(s.split()) for s in sentences]
        if max(lengths) - min(lengths) >= 5:
            score += 7

    if re.search(r"\b(furthermore|moreover|additionally|therefore)\b", lower):
        score -= 20

    return max(0.0, min(100.0, score))


def safety_score(style_result: dict[str, Any]) -> float:
    if not style_result["passed"]:
        return 0.0

    warning_penalty = min(15, len(style_result.get("warnings", [])) * 5)
    return max(0.0, 100.0 - warning_penalty)


def weighted_total(intent: float, tone: float, specificity: float, naturalness: float, safety: float) -> float:
    total = (
        0.30 * intent
        + 0.15 * tone
        + 0.20 * specificity
        + 0.20 * naturalness
        + 0.15 * safety
    )
    return round(total, 2)


def evaluate_candidate(post_text: str, subreddit: str, candidate: dict[str, Any], promotion_allowed: bool) -> dict[str, Any]:
    text = candidate.get("text", "")
    style = evaluate_text(text, promotion_allowed=promotion_allowed)

    intent = token_overlap_score(post_text, text)
    tone = subreddit_tone_score(subreddit, text)
    specificity = specificity_value_score(text)
    naturalness = naturalness_score(text)
    safety = safety_score(style)
    total = weighted_total(intent, tone, specificity, naturalness, safety)

    if not style["passed"]:
        total = 0.0

    return {
        "id": candidate.get("id"),
        "text": text,
        "total_score": total,
        "reject": not style["passed"],
        "breakdown": {
            "intent_match": round(intent, 2),
            "subreddit_tone_fit": round(tone, 2),
            "specificity_value": round(specificity, 2),
            "naturalness": round(naturalness, 2),
            "safety_compliance": round(safety, 2),
        },
        "style": style,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and rank candidate Reddit comments.")
    parser.add_argument("--input", required=True, help="Path to input JSON.")
    parser.add_argument("--output", help="Path to output JSON. If omitted, prints to stdout.")
    parser.add_argument("--promotion-allowed", action="store_true", help="Allow promotion checks.")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    post = payload.get("post", {})
    subreddit = post.get("subreddit", "")
    post_text = f"{post.get('title', '')}\n{post.get('body', '')}".strip()
    candidates = payload.get("candidates", [])

    scored = [
        evaluate_candidate(
            post_text=post_text,
            subreddit=subreddit,
            candidate=candidate,
            promotion_allowed=args.promotion_allowed,
        )
        for candidate in candidates
    ]

    scored.sort(key=lambda item: item["total_score"], reverse=True)
    passed = [item for item in scored if not item["reject"]]
    top3 = passed[:3] if len(passed) >= 3 else scored[:3]

    result = {
        "selection_policy": "10-12 candidates -> top 3 -> final manual fit check",
        "candidate_count": len(candidates),
        "scored": scored,
        "top3": top3,
        "best": top3[0] if top3 else None,
    }

    output = json.dumps(result, ensure_ascii=True, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
