#!/usr/bin/env python3
"""Track comment structural patterns and generate diversity guidance."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MAX_FINGERPRINTS = 30

OPENER_PATTERNS = {
    "question": re.compile(r"^(have you|do you|what if|why not|how about|is there|could you|would you|ever)", re.IGNORECASE),
    "agreement": re.compile(r"^(yeah|yes|agreed|same|exactly|right|true|this|100%)", re.IGNORECASE),
    "counterpoint": re.compile(r"^(but|however|actually|not sure|disagree|on the flip|tbh|honestly|nah)", re.IGNORECASE),
    "anecdote": re.compile(r"^(i (used to|was|had|tried|built|ran|worked)|we (had|tried|built)|my|when i)", re.IGNORECASE),
    "fact": re.compile(r"^(the|most|one|there|it|according|studies|data|research|a lot of|many)", re.IGNORECASE),
    "opinion": re.compile(r"^(i think|i feel|i believe|imo|personally|in my|i'd say|i would|i usually)", re.IGNORECASE),
}


def classify_opener(text: str) -> str:
    first_line = text.strip().split("\n")[0].strip()
    for opener_type, pattern in OPENER_PATTERNS.items():
        if pattern.match(first_line):
            return opener_type
    return "direct"


def word_count_bucket(text: str) -> str:
    words = len(re.findall(r"\b\w+\b", text))
    if words < 20:
        return "short"
    elif words <= 60:
        return "medium"
    else:
        return "long"


def fingerprint_comment(text: str) -> dict[str, Any]:
    """Generate a structural fingerprint for a comment."""
    return {
        "opener_type": classify_opener(text),
        "word_count_bucket": word_count_bucket(text),
        "has_question": "?" in text,
        "paragraph_count": max(1, len([p for p in text.split("\n\n") if p.strip()])),
        "starts_with_i": text.strip().lower().startswith("i ") or text.strip().lower().startswith("i'"),
        "uses_list": bool(re.search(r"^\s*[-*\d]+[.)]?\s", text, re.MULTILINE)),
    }


def diversity_path(runtime_root: Path) -> Path:
    return runtime_root / "state" / "diversity_state.json"


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def cmd_record(runtime_root: Path, fingerprint_file: str) -> None:
    """Record a comment fingerprint into diversity state."""
    dp = diversity_path(runtime_root)
    state: list[dict[str, Any]] = read_json(dp, [])

    fp = json.loads(Path(fingerprint_file).read_text(encoding="utf-8"))
    state.append(fp)

    # Trim to MAX_FINGERPRINTS
    if len(state) > MAX_FINGERPRINTS:
        state = state[-MAX_FINGERPRINTS:]

    write_json(dp, state)
    print(json.dumps({"recorded": True, "total": len(state)}, ensure_ascii=True, indent=2))


def cmd_fingerprint(text_file: str) -> None:
    """Generate a fingerprint for a comment text."""
    text = Path(text_file).read_text(encoding="utf-8")
    fp = fingerprint_comment(text)
    print(json.dumps(fp, ensure_ascii=True, indent=2))


def cmd_guidance(runtime_root: Path) -> None:
    """Analyze recent fingerprints and output diversity guidance."""
    dp = diversity_path(runtime_root)
    state: list[dict[str, Any]] = read_json(dp, [])

    if len(state) < 5:
        print(json.dumps({
            "sample_size": len(state),
            "avoid": [],
            "prefer": [],
            "message": "Not enough data yet. Continue posting normally.",
        }, ensure_ascii=True, indent=2))
        return

    # Analyze distributions
    openers = Counter(fp.get("opener_type", "direct") for fp in state)
    buckets = Counter(fp.get("word_count_bucket", "medium") for fp in state)
    starts_i_pct = sum(1 for fp in state if fp.get("starts_with_i")) / len(state)
    has_question_pct = sum(1 for fp in state if fp.get("has_question")) / len(state)
    uses_list_pct = sum(1 for fp in state if fp.get("uses_list")) / len(state)

    total = len(state)
    avoid: list[str] = []
    prefer: list[str] = []

    # Flag overrepresented opener types (>40%)
    for opener, count in openers.items():
        pct = count / total
        if pct > 0.40:
            avoid.append(f"{opener} opener ({round(pct*100)}%)")

    # Flag underrepresented opener types (<10% and not 'direct')
    all_opener_types = ["question", "agreement", "counterpoint", "anecdote", "fact", "opinion"]
    for opener in all_opener_types:
        pct = openers.get(opener, 0) / total
        if pct < 0.10:
            prefer.append(f"{opener} opener")

    # Flag overrepresented length buckets
    for bucket, count in buckets.items():
        pct = count / total
        if pct > 0.60:
            avoid.append(f"{bucket} length ({round(pct*100)}%)")

    # Flag "starts with I" pattern
    if starts_i_pct > 0.50:
        avoid.append(f"starting with 'I' ({round(starts_i_pct*100)}%)")
        prefer.append("starting with non-I openers")

    # Flag low question usage
    if has_question_pct < 0.15:
        prefer.append("include a question")

    # Flag low list usage
    if uses_list_pct < 0.10:
        prefer.append("use a short list or bullet")

    result = {
        "sample_size": total,
        "avoid": avoid,
        "prefer": prefer,
        "distributions": {
            "openers": dict(openers),
            "length_buckets": dict(buckets),
            "starts_with_i_pct": round(starts_i_pct * 100, 1),
            "has_question_pct": round(has_question_pct * 100, 1),
            "uses_list_pct": round(uses_list_pct * 100, 1),
        },
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track comment structure and generate diversity guidance.")
    parser.add_argument("--runtime-root", help="Runtime root path.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="Record a comment fingerprint.")
    record.add_argument("--fingerprint", required=True, help="Path to fingerprint JSON file.")

    fp = sub.add_parser("fingerprint", help="Generate fingerprint from comment text.")
    fp.add_argument("--text-file", required=True, help="Path to text file with comment.")

    sub.add_parser("guidance", help="Generate diversity guidance from recent patterns.")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_root = Path(args.runtime_root).resolve() if args.runtime_root else None

    if args.cmd == "record":
        if not runtime_root:
            print("Error: --runtime-root required for record command.", file=__import__("sys").stderr)
            return 1
        cmd_record(runtime_root, args.fingerprint)
    elif args.cmd == "fingerprint":
        cmd_fingerprint(args.text_file)
    elif args.cmd == "guidance":
        if not runtime_root:
            print("Error: --runtime-root required for guidance command.", file=__import__("sys").stderr)
            return 1
        cmd_guidance(runtime_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
