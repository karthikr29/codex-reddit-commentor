---
name: reddit-commenter-safe
description: Safety-first Reddit comment generation and posting workflow with strict human-style guardrails, candidate ranking, feedback learning, and scheduled session controls. Use when running Reddit comment sessions with Playwright MCP under daily/session limits, anti-spam controls, no credential capture, and full activity tracking.
---

# Reddit Commenter Safe

## Overview

Run high-quality Reddit commenting sessions with strong controls for account safety and writing quality. Enforce hard style checks, generate 10-12 candidates per post, rank to top 3 with novelty and diversity scoring, select 1 best comment, then post automatically when all safety checks pass. Harvest feedback to self-tune over time.

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

### Step 0: Session Initialization

1. Load config from `references/config.md` and runtime `config.yaml`.
2. Acquire session lock with `scripts/state_manager.py acquire-lock`.
3. Confirm active window and run-day eligibility from `references/scheduling.md`.
4. Confirm login state. Never ask for Reddit email or password.
5. Initialize or load daily state.
6. Compute session target: `min(session_cap, daily_cap - total_comments)`.

### Step 0.5: Analytics Trend Check

If `analytics.trend_check_on_start` is true in config:
1. Run `scripts/analytics_generator.py trend-check --runtime-root <root>`.
2. Read the 5-line summary for session context (recent performance, health, errors).

### Step 1: Harvest Feedback

Before the candidate loop, harvest performance data for previously posted comments:
1. Run `scripts/harvest_feedback.py harvest --runtime-root <root>` to get eligible URLs (posted 4-48h ago, not yet harvested).
2. For each eligible URL, use Playwright to visit the comment and extract: upvotes, reply count, and whether the comment is visible.
3. Write results to a temp JSON file, then run `scripts/harvest_feedback.py merge --runtime-root <root> --input <temp_file>`.

### Step 1.5: Health Gate

If `health_check_enabled` is true in config:
1. During harvest (Step 1), also check comment visibility from a logged-out perspective. For up to 3 recent comments, navigate to the post URL in a non-logged-in context and check if the comment text appears.
2. Write visibility results to a temp JSON, then run `scripts/health_check.py check --runtime-root <root> --results <temp_file>`.
3. Run `scripts/health_check.py status --runtime-root <root>`.
4. If `health_status == "red"`: **STOP the session**. Log the reason. Do not post any comments.
5. If `health_status == "yellow"`: proceed with caution, log a warning.

### Step 2: Candidate Loop

Repeat until session target reached or stop condition:

1. **Select subreddit.** If `state/activity_observations.json` exists and has data, prefer subreddits with highest predicted activity for the current time slot (from `scripts/schedule_optimizer.py suggest`). Otherwise, use the subreddit under cap with oldest last-activity. Always respect per-subreddit caps.

2. **Scan posts.** Open `new` feed first. Use `rising` only if no suitable post is found.

3. **Score posts for engagement.** Extract metadata (age, upvotes, comment count, is_question) for up to 10 suitable posts. Run `scripts/post_scorer.py score --input <temp_file>` and pick the highest engagement_potential post.

4. **Find suitable post** not already commented today. Skip video-focused, promo-heavy, or low-context posts. Skip high-saturation posts.

5. **Analyze thread context.** Read existing top-level comments (up to 20) via Playwright snapshot. Write them to a temp JSON file, then run `scripts/thread_analyzer.py analyze --input <temp_file>` to get a thread digest with covered topics, gaps, and tone.

6. **Get diversity guidance.** Run `scripts/diversity_tracker.py --runtime-root <root> guidance` to get avoid/prefer instructions based on recent comment patterns.

7. **Generate 10-12 candidate comments.** Include in the generation prompt:
   - Post intent and subreddit tone
   - Thread digest (covered topics and gap areas) so candidates say something new
   - Diversity guidance (what structural patterns to avoid/prefer)
   - Personalization profile from `personalization_reddit.md`

8. **Score candidates.** Run `scripts/score_candidates.py --input <temp_file>` with optional flags:
   - `--thread-digest <digest_file>` for novelty scoring
   - `--diversity-guidance <guidance_file>` for diversity bonus
   - `--weights-file <state/subreddit_profiles.json>` for adaptive per-subreddit weights (if file exists)

9. **Shortlist top 3.** Re-check against post intent and choose best 1.

10. **Run hard style validation** using `scripts/style_guard.py --suggest-fix`.

11. **Style guard retry (if applicable).** If best candidate has `reject: true` but `pre_rejection_score > 45`:
    - Run `scripts/rewrite_guide.py guide --input <style_result_file>` to get rewrite instructions.
    - Generate 3 rewritten variants using the fix hints.
    - Re-validate through `scripts/style_guard.py`.
    - If any pass, use the best passing variant. Max 1 retry per post.

12. **Determine gate mode** (always `auto` since approval ramp is disabled).

13. **Post comment** when all safety and style checks pass. On error, classify it:
    - Run `scripts/error_classifier.py classify --runtime-root <root> --error-type <type> --context <msg> --subreddit <sub>`.
    - Follow the recommended action (RETRY, SKIP_POST, SKIP_SUBREDDIT, or END_SESSION).

14. **Update state:**
    - Run `scripts/state_manager.py update-count --runtime-root <root> --subreddit <sub> --post-url <url>`.
    - Run `scripts/state_manager.py update-diversity --runtime-root <root> --text-file <comment_file>`.
    - Record activity observation: `scripts/schedule_optimizer.py observe --runtime-root <root> --subreddit <sub> --post-count <N> --avg-age-minutes <M>`.
    - Log result in tracking file.

15. **Sleep** random gap before next post.

### Step 3: Stop Conditions

Stop session when any condition holds:

1. Session target reached.
2. Daily cap reached.
3. Current time leaves active window.
4. Error classifier recommends END_SESSION.
5. No suitable posts remain.
6. User explicitly stops run.
7. Health status turns red during session.

### Step 4: Cleanup

1. Persist final state and tracking summary.
2. Release session lock.
3. Emit concise completion report.

### Step 5: Periodic Tasks (outside normal sessions)

1. **Weight optimization** (weekly or every 15 new feedback entries per subreddit): Run `scripts/weight_optimizer.py optimize --runtime-root <root>`.
2. **Schedule optimization** (weekly): Run `scripts/schedule_optimizer.py optimize --runtime-root <root>`.
3. **Weekly analytics report** (Sunday evening): Run `scripts/analytics_generator.py weekly-report --runtime-root <root> --week <YYYY-WNN>`.

## Non-Negotiable Guardrails

1. Never collect, request, or persist Reddit credentials.
2. Use only active logged-in browser session.
3. Do not post duplicate comments on the same post in the same day.
4. Enforce no em dash and no semicolon in final comments.
5. Enforce banned AI-phrasing rules in `references/style_rules.md`.
6. Keep promotion disabled unless policy changes.
7. Respect time window, per-session cap, and daily cap.
8. Stop all posting if account health status is red.

## Scripts

### Core (existing)

1. `scripts/style_guard.py`
Purpose: hard-style compliance checks. Supports `--suggest-fix` for rewrite hints.

2. `scripts/score_candidates.py`
Purpose: score and rank candidates with intent, tone, specificity, naturalness, safety, novelty, and diversity dimensions. Supports `--thread-digest`, `--diversity-guidance`, and `--weights-file`.

3. `scripts/state_manager.py`
Purpose: manage daily state, ramp mode, counters, session lock, and diversity fingerprints.

### Phase 1: Foundation

4. `scripts/harvest_feedback.py`
Purpose: harvest upvotes/replies for posted comments and persist to feedback history.

5. `scripts/health_check.py`
Purpose: shadow ban detection and account health monitoring.

6. `scripts/error_classifier.py`
Purpose: classify errors and prescribe recovery actions with progressive backoff.

### Phase 2: Intelligence

7. `scripts/thread_analyzer.py`
Purpose: analyze existing thread comments to identify covered topics and gaps.

8. `scripts/rewrite_guide.py`
Purpose: map style guard failures to actionable rewrite instructions.

9. `scripts/post_scorer.py`
Purpose: score posts by engagement potential (freshness, velocity, saturation).

### Phase 3: Learning

10. `scripts/diversity_tracker.py`
Purpose: track comment structural patterns and generate diversity guidance.

11. `scripts/weight_optimizer.py`
Purpose: self-tune scoring weights per subreddit from feedback data.

12. `scripts/schedule_optimizer.py`
Purpose: optimize subreddit selection by observed activity patterns.

13. `scripts/analytics_generator.py`
Purpose: generate trend checks and weekly analytics reports.

## References

1. `references/workflow.md`: full execution sequence and stop conditions.
2. `references/safety.md`: platform safety model, account-risk controls, and health monitoring.
3. `references/style_rules.md`: strict human-writing constraints and banned patterns.
4. `references/scheduling.md`: daily schedule and ramp rules.
5. `references/config.md`: runtime config contract.

## Runtime Files

1. Config: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/config.yaml`
2. Personalization: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/personalization_reddit.md`
3. Tracking template: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/tracking/reddit/template.md`
4. State folder: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/state`

## Recovery Rules

1. If lock exists, exit the session to prevent overlap.
2. If login is missing, stop and ask for manual login in automation browser.
3. If error classifier recommends END_SESSION, stop the current session.
4. If no suitable posts are found across all configured subreddits, stop gracefully and log status.
5. If health status is red, stop immediately and log for manual review.
