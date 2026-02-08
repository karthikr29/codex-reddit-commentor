#!/usr/bin/env python3
"""Analyze existing thread comments to identify covered topics and gaps."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

STOP_WORDS = {
    "a", "an", "the", "and", "or", "to", "for", "of", "in", "on", "at", "with", "is", "are", "was", "were",
    "it", "that", "this", "as", "be", "by", "from", "if", "you", "your", "i", "we", "they", "he", "she",
    "my", "me", "do", "does", "did", "have", "has", "had", "not", "but", "so", "just", "can", "will",
    "about", "up", "out", "what", "which", "who", "how", "when", "where", "there", "been", "would", "could",
    "should", "its", "them", "their", "than", "then", "also", "more", "some", "any", "all", "no", "very",
    "too", "here", "like", "think", "know", "get", "got", "one", "make", "way", "use", "go", "going",
}

MIN_PHRASE_LENGTH = 2
MAX_TOPICS = 15


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t and t not in STOP_WORDS and len(t) > 2]


def extract_bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]


def detect_tone(texts: list[str]) -> str:
    combined = " ".join(texts).lower()
    technical_terms = len(re.findall(r"\b(api|code|debug|function|deploy|config|server|database|model|training)\b", combined))
    casual_markers = len(re.findall(r"\b(lol|haha|tbh|imo|ngl|bruh|dude|yeah)\b", combined))
    question_marks = combined.count("?")
    total_words = len(combined.split())

    if total_words == 0:
        return "neutral"

    tech_ratio = technical_terms / max(1, total_words)
    if tech_ratio > 0.03:
        return "technical"
    if casual_markers > 2 or casual_markers / max(1, total_words) > 0.01:
        return "casual"
    if question_marks > len(texts) * 0.5:
        return "inquisitive"
    return "conversational"


def cmd_analyze(input_file: str, output_file: str | None) -> None:
    """Analyze thread comments and produce a digest."""
    comments: list[dict[str, str]] = json.loads(Path(input_file).read_text(encoding="utf-8"))

    texts = [c.get("text", c.get("body", "")) for c in comments if c.get("text") or c.get("body")]

    # Tokenize all comments
    all_tokens: list[str] = []
    all_bigrams: list[str] = []
    for text in texts:
        tokens = tokenize(text)
        all_tokens.extend(tokens)
        all_bigrams.extend(extract_bigrams(tokens))

    # Find most common topics (unigrams and bigrams)
    token_counts = Counter(all_tokens)
    bigram_counts = Counter(all_bigrams)

    # Merge top unigrams and bigrams as "covered topics"
    top_unigrams = [word for word, _ in token_counts.most_common(10)]
    top_bigrams = [phrase for phrase, count in bigram_counts.most_common(8) if count >= 2]
    covered_topics = list(dict.fromkeys(top_bigrams + top_unigrams))[:MAX_TOPICS]

    # Detect tone
    dominant_tone = detect_tone(texts)

    # Identify potential gaps (topics in post title/body not covered by comments)
    # This is a heuristic -- gap areas are inferred as uncommon angles
    gap_hints = []
    if not any("example" in t or "instance" in t for t in all_tokens):
        gap_hints.append("concrete examples")
    if not any("why" in t or "reason" in t or "because" in t for t in all_tokens):
        gap_hints.append("reasoning or explanation")
    if not any("alternative" in t or "instead" in t or "option" in t for t in all_tokens):
        gap_hints.append("alternative approaches")
    if not any("experience" in t or "tried" in t or "worked" in t for t in all_tokens):
        gap_hints.append("practical experience")
    if not any(char.isdigit() for text in texts for char in text):
        gap_hints.append("specific numbers or data")

    digest = {
        "comment_count": len(texts),
        "covered_topics": covered_topics,
        "dominant_tone": dominant_tone,
        "gap_areas": gap_hints,
        "unique_token_count": len(token_counts),
    }

    output = json.dumps(digest, ensure_ascii=True, indent=2)
    if output_file:
        Path(output_file).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze existing thread to identify covered topics and gaps.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyze = sub.add_parser("analyze", help="Analyze thread comments.")
    analyze.add_argument("--input", required=True, help="Path to JSON file with existing comments.")
    analyze.add_argument("--output", help="Path to output JSON. If omitted, prints to stdout.")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.cmd == "analyze":
        cmd_analyze(args.input, getattr(args, "output", None))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
