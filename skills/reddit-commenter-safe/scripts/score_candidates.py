#!/usr/bin/env python3
"""Score and rank Reddit comment candidates."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
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


def novelty_score(comment_text: str, thread_digest: dict[str, Any] | None) -> float:
    """Score how novel a comment is relative to existing thread comments."""
    if not thread_digest or thread_digest.get("comment_count", 0) == 0:
        return 80.0  # High floor when no existing comments

    covered = set()
    for topic in thread_digest.get("covered_topics", []):
        covered.update(topic.lower().split())

    comment_tokens = set(tokenize(comment_text))
    if not comment_tokens:
        return 50.0

    overlap = comment_tokens & covered
    overlap_ratio = len(overlap) / len(comment_tokens)

    # Lower overlap with existing thread = higher novelty
    score = max(0.0, min(100.0, (1.0 - overlap_ratio) * 100))

    # Bonus if comment addresses a gap area
    gap_areas = thread_digest.get("gap_areas", [])
    lower_text = comment_text.lower()
    for gap in gap_areas:
        if any(word in lower_text for word in gap.split()):
            score = min(100.0, score + 10)

    return score


def diversity_bonus(comment_text: str, guidance: dict[str, Any] | None) -> float:
    """Apply diversity bonus/penalty based on structural guidance."""
    if not guidance or not guidance.get("avoid"):
        return 0.0

    bonus = 0.0
    lower = comment_text.lower().strip()

    avoid_list = guidance.get("avoid", [])
    prefer_list = guidance.get("prefer", [])

    # Check avoid patterns
    for pattern in avoid_list:
        if "starting with 'I'" in pattern and (lower.startswith("i ") or lower.startswith("i'")):
            bonus -= 5.0
        if "opinion opener" in pattern and re.match(r"^(i think|i feel|i believe|imo|personally)", lower):
            bonus -= 5.0
        if "medium length" in pattern:
            words = len(re.findall(r"\b\w+\b", comment_text))
            if 20 <= words <= 60:
                bonus -= 3.0
        if "long length" in pattern:
            words = len(re.findall(r"\b\w+\b", comment_text))
            if words > 60:
                bonus -= 3.0

    # Check prefer patterns
    for pattern in prefer_list:
        if "question opener" in pattern and lower.startswith(("have ", "do ", "what ", "why ", "how ", "is ")):
            bonus += 8.0
        if "non-I openers" in pattern and not (lower.startswith("i ") or lower.startswith("i'")):
            bonus += 5.0
        if "include a question" in pattern and "?" in comment_text:
            bonus += 3.0

    return max(-10.0, min(10.0, bonus))


DEFAULT_WEIGHTS = {
    "intent": 0.20,
    "tone": 0.15,
    "specificity": 0.20,
    "naturalness": 0.20,
    "safety": 0.15,
    "novelty": 0.10,
}


def weighted_total(
    intent: float,
    tone: float,
    specificity: float,
    naturalness: float,
    safety: float,
    novelty: float = 80.0,
    div_bonus: float = 0.0,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    total = (
        w.get("intent", 0.20) * intent
        + w.get("tone", 0.15) * tone
        + w.get("specificity", 0.20) * specificity
        + w.get("naturalness", 0.20) * naturalness
        + w.get("safety", 0.15) * safety
        + w.get("novelty", 0.10) * novelty
    )
    total += div_bonus
    return round(max(0.0, min(100.0, total)), 2)


def evaluate_candidate(
    post_text: str,
    subreddit: str,
    candidate: dict[str, Any],
    promotion_allowed: bool,
    thread_digest: dict[str, Any] | None = None,
    div_guidance: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    text = candidate.get("text", "")
    style = evaluate_text(text, promotion_allowed=promotion_allowed)

    intent = token_overlap_score(post_text, text)
    tone = subreddit_tone_score(subreddit, text)
    specificity = specificity_value_score(text)
    natural = naturalness_score(text)
    safety = safety_score(style)
    novel = novelty_score(text, thread_digest)
    div_bon = diversity_bonus(text, div_guidance)
    total = weighted_total(intent, tone, specificity, natural, safety, novel, div_bon, weights)

    # Pre-rejection score (useful for retry logic)
    pre_rejection_score = total

    if not style["passed"]:
        total = 0.0

    return {
        "id": candidate.get("id"),
        "text": text,
        "total_score": total,
        "pre_rejection_score": pre_rejection_score,
        "reject": not style["passed"],
        "breakdown": {
            "intent_match": round(intent, 2),
            "subreddit_tone_fit": round(tone, 2),
            "specificity_value": round(specificity, 2),
            "naturalness": round(natural, 2),
            "safety_compliance": round(safety, 2),
            "novelty": round(novel, 2),
            "diversity_bonus": round(div_bon, 2),
        },
        "style": style,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score and rank candidate Reddit comments.")
    parser.add_argument("--input", required=True, help="Path to input JSON.")
    parser.add_argument("--output", help="Path to output JSON. If omitted, prints to stdout.")
    parser.add_argument("--promotion-allowed", action="store_true", help="Allow promotion checks.")
    parser.add_argument("--thread-digest", help="Path to thread digest JSON from thread_analyzer.")
    parser.add_argument("--diversity-guidance", help="Path to diversity guidance JSON.")
    parser.add_argument("--weights-file", help="Path to subreddit_profiles.json for adaptive weights.")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    post = payload.get("post", {})
    subreddit = post.get("subreddit", "")
    post_text = f"{post.get('title', '')}\n{post.get('body', '')}".strip()
    candidates = payload.get("candidates", [])

    # Load optional thread digest
    thread_digest = None
    if args.thread_digest:
        thread_digest = json.loads(Path(args.thread_digest).read_text(encoding="utf-8"))

    # Load optional diversity guidance
    div_guidance = None
    if args.diversity_guidance:
        div_guidance = json.loads(Path(args.diversity_guidance).read_text(encoding="utf-8"))

    # Load optional per-subreddit weights
    weights = None
    if args.weights_file:
        profiles = json.loads(Path(args.weights_file).read_text(encoding="utf-8"))
        sub_key = subreddit if subreddit in profiles else subreddit.lower().replace("r/", "")
        if sub_key in profiles:
            weights = profiles[sub_key].get("weights")

    scored = [
        evaluate_candidate(
            post_text=post_text,
            subreddit=subreddit,
            candidate=candidate,
            promotion_allowed=args.promotion_allowed,
            thread_digest=thread_digest,
            div_guidance=div_guidance,
            weights=weights,
        )
        for candidate in candidates
    ]

    scored.sort(key=lambda item: item["total_score"], reverse=True)
    passed = [item for item in scored if not item["reject"]]
    top3 = passed[:3] if len(passed) >= 3 else scored[:3]

    # Check if best rejected candidate has high pre-rejection score (for retry logic)
    best_rejected = None
    rejected = [item for item in scored if item["reject"]]
    if rejected:
        best_rej = max(rejected, key=lambda x: x.get("pre_rejection_score", 0))
        if best_rej.get("pre_rejection_score", 0) > 45:
            best_rejected = best_rej

    result = {
        "selection_policy": "10-12 candidates -> score with novelty & diversity -> top 3 -> final fit check",
        "candidate_count": len(candidates),
        "scored": scored,
        "top3": top3,
        "best": top3[0] if top3 else None,
        "best_rejected_for_retry": best_rejected,
        "weights_used": weights or DEFAULT_WEIGHTS,
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
