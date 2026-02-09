#!/usr/bin/env python3
"""Map style guard failures to actionable rewrite instructions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Rewrite rules keyed by style_guard issue rule names
REWRITE_MAP: dict[str, str] = {
    "no_em_dash": "Replace all em dashes (\u2014) with commas, periods, or short dashes (-).",
    "no_semicolon": "Split semicolon-joined clauses into two separate sentences.",
    "promo_blocked": "Remove all promotional language. Rewrite as genuinely helpful advice with no sales intent.",
}

# Alternative phrasing for common banned phrases
BANNED_PHRASE_ALTERNATIVES: dict[str, list[str]] = {
    "delve": ["look at", "dig into", "explore"],
    "dive into": ["look at", "get into", "break down"],
    "unpack": ["break down", "walk through", "explain"],
    "navigate": ["work through", "handle", "deal with"],
    "landscape": ["space", "area", "field"],
    "realm": ["area", "space", "world"],
    "leverage": ["use", "take advantage of", "rely on"],
    "utilize": ["use", "apply", "work with"],
    "robust": ["solid", "strong", "reliable"],
    "comprehensive": ["full", "thorough", "complete"],
    "streamline": ["simplify", "speed up", "clean up"],
    "furthermore": ["also", "plus", "on top of that"],
    "moreover": ["also", "and", "plus"],
    "additionally": ["also", "and", "on top of that"],
    "it is worth noting": ["worth mentioning", "one thing to note"],
    "it is important to note": ["keep in mind", "one thing"],
    "at the end of the day": ["ultimately", "in the end"],
    "game changer": ["really helpful", "big improvement", "solid upgrade"],
    "paradigm shift": ["big change", "major shift"],
    "crucial": ["important", "key", "big"],
    "vital": ["important", "key", "necessary"],
    "essential": ["important", "key", "needed"],
    "fascinating": ["interesting", "cool", "neat"],
    "intriguing": ["interesting", "curious", "worth looking at"],
    "i would be happy to": ["happy to", "glad to", "can"],
    "absolutely": ["for sure", "yes", "100%"],
    "definitely": ["for sure", "yes", "probably"],
    "that being said": ["still", "but", "that said"],
    "on one hand": ["one angle", "one way to look at it"],
    "great question": ["good question", "fair question"],
    "i totally agree": ["agreed", "same here", "yeah"],
    "this is underrated": ["doesn't get enough attention", "overlooked"],
    "as someone who": ["from my experience", "having done"],
    "in my humble opinion": ["imo", "personally"],
}


def generate_instructions(style_result: dict[str, Any]) -> list[dict[str, str]]:
    """Generate rewrite instructions from a style_guard result."""
    instructions: list[dict[str, str]] = []

    for issue in style_result.get("issues", []):
        rule = issue.get("rule", "")
        phrase = issue.get("phrase", "")

        if rule == "banned_phrase" and phrase:
            alts = BANNED_PHRASE_ALTERNATIVES.get(phrase.lower(), ["a simpler alternative"])
            alt_text = " or ".join(f"'{a}'" for a in alts[:3])
            instructions.append({
                "rule": rule,
                "phrase": phrase,
                "instruction": f"Replace '{phrase}' with {alt_text}.",
                "alternatives": alts[:3],
            })
        elif rule in REWRITE_MAP:
            instructions.append({
                "rule": rule,
                "phrase": phrase,
                "instruction": REWRITE_MAP[rule],
            })
        else:
            instructions.append({
                "rule": rule,
                "phrase": phrase,
                "instruction": f"Fix issue: {issue.get('message', rule)}",
            })

    return instructions


def cmd_guide(input_file: str) -> None:
    """Generate rewrite guide from style_guard output."""
    style_result = json.loads(Path(input_file).read_text(encoding="utf-8"))
    instructions = generate_instructions(style_result)

    output = {
        "original_passed": style_result.get("passed", False),
        "issue_count": len(style_result.get("issues", [])),
        "rewrite_instructions": instructions,
        "summary": "; ".join(i["instruction"] for i in instructions) if instructions else "No issues to fix.",
    }
    print(json.dumps(output, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Map style guard failures to rewrite instructions.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    guide = sub.add_parser("guide", help="Generate rewrite instructions from style_guard output.")
    guide.add_argument("--input", required=True, help="Path to style_guard result JSON.")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.cmd == "guide":
        cmd_guide(args.input)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
