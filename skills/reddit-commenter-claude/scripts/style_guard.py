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

# Patterns that indicate fabricated personal claims (job titles, teams, companies, etc.)
# These are compiled as case-insensitive regexes and checked against comment text.
FABRICATION_PATTERNS = [
    r"\bwe had\b",
    r"\bteams i know\b",
    r"\bwhat worked for us\b",
    r"\bwhen i ran\b",
    r"\bin my experience at\b",
    r"\bi used to work\b",
    r"\bat my company\b",
    r"\bmy team\b",
    r"\bour company\b",
    r"\bback when i was\b",
    r"\bin my previous role\b",
    r"\bclients i'?ve worked with\b",
    r"\bmy (?:startup|agency|firm|business|shop)\b",
    r"\bour (?:team|org|department|startup)\b",
    r"\bi ran (?:a|an|the|my)\b",
    r"\bi managed (?:a|an|the|my|our|several|multiple)\b",
    r"\bi led (?:a|an|the|my|our)\b",
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

    for fab_pattern in FABRICATION_PATTERNS:
        if re.search(fab_pattern, text, re.IGNORECASE):
            issues.append(
                {
                    "rule": "fabrication_blocked",
                    "message": f"Contains fabricated personal claim matching: '{fab_pattern}'.",
                    "phrase": fab_pattern,
                }
            )
            break

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


FIX_HINTS = {
    "no_em_dash": "Replace all em dashes with commas, periods, or short dashes (-).",
    "no_semicolon": "Split semicolon-joined clauses into two separate sentences.",
    "promo_blocked": "Remove promotional language entirely. Rewrite as genuine advice.",
    "fabrication_blocked": "Remove the fabricated personal claim. Use a factual observation or practical suggestion instead. Only reference personal experience from the personal_facts.md fact bank.",
}

PHRASE_ALTERNATIVES = {
    "delve": "look at, dig into",
    "dive into": "look at, get into",
    "unpack": "break down, walk through",
    "navigate": "work through, handle",
    "landscape": "space, area",
    "realm": "area, space",
    "leverage": "use, take advantage of",
    "utilize": "use, apply",
    "robust": "solid, strong",
    "comprehensive": "full, thorough",
    "streamline": "simplify, speed up",
    "furthermore": "also, plus",
    "moreover": "also, and",
    "additionally": "also, and",
    "crucial": "important, key",
    "vital": "important, key",
    "essential": "important, needed",
    "fascinating": "interesting, cool",
    "intriguing": "interesting, curious",
    "absolutely": "for sure, yes",
    "definitely": "for sure, yes",
    "great question": "good question, fair question",
    "as someone who": "from my experience, having done",
    "fabrication_blocked": "Use a factual observation or practical suggestion instead",
}


def add_fix_hints(result: dict[str, Any]) -> dict[str, Any]:
    """Add fix_hint field to each issue for rewrite guidance."""
    for issue in result.get("issues", []):
        rule = issue.get("rule", "")
        phrase = issue.get("phrase", "").lower()

        if rule == "banned_phrase" and phrase in PHRASE_ALTERNATIVES:
            issue["fix_hint"] = f"Replace '{phrase}' with: {PHRASE_ALTERNATIVES[phrase]}"
        elif rule in FIX_HINTS:
            issue["fix_hint"] = FIX_HINTS[rule]
        else:
            issue["fix_hint"] = f"Remove or rewrite to fix: {issue.get('message', rule)}"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Reddit comment text against strict style guardrails.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Raw comment text.")
    source.add_argument("--file", help="Path to file containing comment text.")
    parser.add_argument("--promotion-allowed", action="store_true", help="Allow promotional wording checks to pass.")
    parser.add_argument("--json-only", action="store_true", help="Print only JSON output.")
    parser.add_argument("--suggest-fix", action="store_true", help="Add fix_hint to each issue for rewrite guidance.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = args.text or ""

    result = evaluate_text(text=text, promotion_allowed=args.promotion_allowed)

    if args.suggest_fix:
        result = add_fix_hints(result)

    if args.json_only:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] style guard")
        print(json.dumps(result, ensure_ascii=True, indent=2))

    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
