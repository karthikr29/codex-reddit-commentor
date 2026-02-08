#!/usr/bin/env python3
"""Style guard for strict human-like Reddit comments."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

BANNED_PHRASES = [
    "delve",
    "dive into",
    "unpack",
    "navigate",
    "landscape",
    "realm",
    "leverage",
    "utilize",
    "robust",
    "comprehensive",
    "streamline",
    "furthermore",
    "moreover",
    "additionally",
    "it is worth noting",
    "it is important to note",
    "at the end of the day",
    "game changer",
    "paradigm shift",
    "crucial",
    "vital",
    "essential",
    "fascinating",
    "intriguing",
    "i would be happy to",
    "absolutely",
    "definitely",
    "that being said",
    "on one hand",
    "great question",
    "i totally agree",
    "this is underrated",
    "as someone who",
    "in my humble opinion",
]

PROMO_PHRASES = [
    "buy now",
    "dm me",
    "check my product",
    "sign up",
    "free trial",
    "book a demo",
]


def evaluate_text(text: str, promotion_allowed: bool = False) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    warnings: list[str] = []

    lowered = text.lower()

    if "—" in text:
        issues.append({"rule": "no_em_dash", "message": "Contains em dash character."})

    if ";" in text:
        issues.append({"rule": "no_semicolon", "message": "Contains semicolon."})

    for phrase in BANNED_PHRASES:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        if pattern.search(text):
            issues.append(
                {
                    "rule": "banned_phrase",
                    "message": f"Contains banned phrase: '{phrase}'.",
                    "phrase": phrase,
                }
            )

    if not promotion_allowed:
        for phrase in PROMO_PHRASES:
            pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
            if pattern.search(text):
                issues.append(
                    {
                        "rule": "promo_blocked",
                        "message": f"Contains promotional phrase while promotion is disabled: '{phrase}'.",
                        "phrase": phrase,
                    }
                )

    sentence_count = max(1, len([s for s in re.split(r"[.!?]+", text) if s.strip()]))
    word_count = len(re.findall(r"\b\w+\b", text))

    if word_count > 140:
        warnings.append("Comment is long. Consider reducing length for natural Reddit style.")

    if text.count("?") > 1:
        warnings.append("Multiple trailing questions can look forced.")

    if sentence_count >= 4 and all(s.strip().lower().startswith(("first", "second", "third", "finally")) for s in re.split(r"[.!?]", text) if s.strip()):
        warnings.append("Rigid list cadence may look editorial.")

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "metrics": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "question_count": text.count("?"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Reddit comment text against strict style guardrails.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Raw comment text.")
    source.add_argument("--file", help="Path to file containing comment text.")
    parser.add_argument("--promotion-allowed", action="store_true", help="Allow promotional wording checks to pass.")
    parser.add_argument("--json-only", action="store_true", help="Print only JSON output.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = args.text or ""

    result = evaluate_text(text=text, promotion_allowed=args.promotion_allowed)

    if args.json_only:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] style guard")
        print(json.dumps(result, ensure_ascii=True, indent=2))

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
