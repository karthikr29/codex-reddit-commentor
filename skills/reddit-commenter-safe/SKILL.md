---
name: reddit-commenter-safe
description: Safety-first Reddit comment generation and posting workflow with strict human-style guardrails, candidate ranking, and scheduled session controls. Use when running Reddit comment sessions with Playwright MCP under daily/session limits, anti-spam controls, no credential capture, and full activity tracking.
---

# Reddit Commenter Safe

## Overview

Run high-quality Reddit commenting sessions with strong controls for account safety and writing quality. Enforce hard style checks, generate 10-12 candidates per post, rank to top 3, select 1 best comment, then post automatically when all safety checks pass.

## Inputs

1. Runtime root: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter`
2. Skill references in `references/`
3. Playwright MCP browser session already logged in to Reddit

## Session Triggering

Use this skill for:

1. Scheduled session runs (morning or afternoon)
2. Manual runs that must obey the same limits and safety checks
3. Draft-only review runs before posting

## Required Workflow

1. Load config from `references/config.md` and runtime `config.yaml`.
2. Acquire session lock with `scripts/state_manager.py acquire-lock`.
3. Confirm active window and run-day eligibility from `references/scheduling.md`.
4. Confirm login state. Never ask for Reddit email or password.
5. Initialize or load daily state.
6. Compute session target: `min(session_cap, daily_cap - total_comments)`.
7. For each attempt:
   - Select subreddit under per-subreddit cap and oldest last-activity.
   - Find suitable post not already commented today.
   - Analyze post intent and subreddit tone.
   - Generate 10-12 candidates.
   - Score candidates with `scripts/score_candidates.py`.
   - Keep top 3, perform final fit check, choose best 1.
   - Enforce hard style checks using `scripts/style_guard.py`.
   - Determine gate mode (always `auto` since approval ramp is disabled).
   - Post only when all checks pass.
   - Update tracking and state files.
   - Sleep random delay within configured range.
8. On rate-limit, pause and retry as configured. Stop the session when retry budget is exhausted.
9. Release session lock in all exit paths.

## Non-Negotiable Guardrails

1. Never collect, request, or persist Reddit credentials.
2. Use only active logged-in browser session.
3. Do not post duplicate comments on the same post in the same day.
4. Enforce no em dash and no semicolon in final comments.
5. Enforce banned AI-phrasing rules in `references/style_rules.md`.
6. Keep promotion disabled unless policy changes.
7. Respect time window, per-session cap, and daily cap.

## Scripts

1. `scripts/style_guard.py`
Purpose: hard-style compliance checks for a candidate comment.

2. `scripts/score_candidates.py`
Purpose: score and rank 10-12 candidate comments, return top 3 and best-fit metadata.

3. `scripts/state_manager.py`
Purpose: manage daily state, ramp mode, counters, and session lock.

## References

1. `references/workflow.md`: full execution sequence and stop conditions.
2. `references/safety.md`: platform safety model and account-risk controls.
3. `references/style_rules.md`: strict human-writing constraints and banned patterns.
4. `references/scheduling.md`: two-session daily schedule and ramp rules.
5. `references/config.md`: runtime config contract.

## Runtime Files

1. Config: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/config.yaml`
2. Personalization: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/personalization_reddit.md`
3. Tracking template: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/tracking/reddit/template.md`
4. State folder: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/state`

## Recovery Rules

1. If lock exists, exit the session to prevent overlap.
2. If login is missing, stop and ask for manual login in automation browser.
3. If rate-limit retry budget is exhausted, stop the current session.
4. If no suitable posts are found across all configured subreddits, stop gracefully and log status.
