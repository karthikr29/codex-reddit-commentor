# Reddit Commenter Skill: 10 Power Upgrades

## Context

The skill currently posts and forgets. It has no idea which comments perform well, can't detect shadow bans, doesn't read existing threads before commenting, and uses static scoring weights regardless of subreddit culture. These upgrades create feedback loops that make the skill **learn and adapt over time** while adding critical safety checks.

All changes use Python 3.13 stdlib only, Playwright MCP for browser ops, and local JSON/Markdown state files -- fully compatible with Codex.

---

## Phase 1: Foundation (do first -- everything else depends on these)

### 1. Performance Feedback Harvester

**Why:** The skill posts and forgets. Without knowing which comments get upvotes/replies, it can't improve.

**New file:** `scripts/harvest_feedback.py`
- Commands: `harvest --runtime-root X` and `merge --runtime-root X --input FILE`
- Reads `daily_state.json` (current + previous day), outputs list of comment URLs to check
- After Claude visits each URL via Playwright and extracts upvotes/reply count, `merge` persists results to `state/feedback_history.json` (rolling 500-entry cap)

**New file:** `state/feedback_history.json`
```json
[{"url": "...", "subreddit": "r/X", "posted_at": "...", "upvotes": 5, "replies": 2, "visible": true, "harvested_at": "..."}]
```

**Modify:** `SKILL.md` -- Add "Step 0.5: Harvest" before the candidate loop. Harvest comments older than 4h but younger than 48h.
**Modify:** `workflow.md` -- Document harvest step.
**Modify:** `tracking/reddit/template.md` -- Add "24h Performance" section.

---

### 2. Shadow Ban & Account Health Monitor

**Why:** Shadow bans are silent. Without detection, the skill wastes quota posting invisible comments.

**New file:** `scripts/health_check.py`
- Commands: `check --runtime-root X --results FILE` and `status --runtime-root X`
- Takes visibility check results (Claude checks comment URLs from a logged-out browser context via Playwright) and updates `state/health_state.json`
- Thresholds: 1 invisible = yellow, 3 consecutive = red (halt all posting)

**New file:** `state/health_state.json`
```json
{"last_check": "...", "invisible_count": 0, "consecutive_invisible": 0, "health_status": "green"}
```

**Modify:** `SKILL.md` -- Add health gate: if `health_status == "red"`, skip session entirely.
**Modify:** `config.yaml` -- Add `health_check_enabled: true`, `health_invisible_threshold: 3`.
**Modify:** `references/safety.md` -- Document health monitoring protocol.

---

### 3. Smarter Error Recovery

**Why:** Current error handling is one-size-fits-all (pause 30 min, retry 5x). A 404 (deleted post) needs different handling than a 429 (rate limit) or a login expiry.

**New file:** `scripts/error_classifier.py`
- Command: `classify --error-type X --context Y --runtime-root Z`
- Categories: `rate_limit` (progressive backoff: 5/15/30/60 min), `forbidden` (skip subreddit for day), `not_found` (skip silently), `network_timeout` (retry once after 2 min), `login_expired` (end session, flag for manual intervention), `content_policy` (flag comment for style guard improvement)
- Maintains `state/error_log.json` (rolling 100 entries). If 3+ rate limits in last hour, recommends ending session early.

**New file:** `state/error_log.json`

**Modify:** `SKILL.md` -- Wrap each post attempt in error classification logic.
**Modify:** `config.yaml` -- Add `error_handling.progressive_backoff: true`.

---

## Phase 2: Intelligence (immediate quality improvements)

### 4. Thread Context Analysis (Redundancy Avoidance)

**Why:** The skill generates comments without knowing what others already said. This risks repeating existing advice, looking generic or bot-like.

**New file:** `scripts/thread_analyzer.py`
- Command: `analyze --input FILE --output FILE`
- Input: JSON array of existing top-level comments (extracted by Claude via Playwright snapshot)
- Output: thread digest -- `{covered_topics: [...], dominant_tone: "...", gap_areas: [...], comment_count: N}`
- Tokenizes existing comments, identifies key phrases/topics already covered

**Modify:** `score_candidates.py`
- Add `--thread-digest FILE` argument
- New scoring dimension: `novelty_score` -- measures how different a candidate is from existing thread (low token overlap with existing comments = higher novelty)
- Rebalance weights: intent 20% (was 30%), tone 15%, specificity 20%, naturalness 20%, safety 15%, **novelty 10% (new)**

**Modify:** `SKILL.md` -- Between "Find post" and "Generate candidates", add thread analysis step. Include digest in generation prompt so Claude avoids repeating what's been said.
**Modify:** `workflow.md` -- Document thread analysis step.

---

### 5. Style Guard Auto-Retry with Feedback

**Why:** When the best candidate fails style guard on a single fixable issue (e.g., one accidental em dash), the entire post is wasted. A targeted rewrite recovers it.

**New file:** `scripts/rewrite_guide.py`
- Command: `guide --input FILE` (accepts style_guard result JSON)
- Maps each failure to actionable rewrite instructions:
  - `no_em_dash` -> "Replace em dashes with commas or periods"
  - `banned_phrase: "delve"` -> "Replace 'delve' with 'look at' or 'dig into'"
  - `no_semicolon` -> "Split semicolon clauses into two sentences"
- Output: list of rewrite instructions for the candidate generation prompt

**Modify:** `style_guard.py` -- Add `--suggest-fix` flag that appends `fix_hint` field to each issue.
**Modify:** `SKILL.md` -- After scoring, if best candidate has `reject: true` but pre-rejection score > 45, trigger ONE retry: Claude rewrites using the fix hints, then re-validates. Max 1 retry per post.

---

### 6. Post Engagement Prediction

**Why:** Not all posts are worth commenting on. A 2-upvote, 6-hour-old post gets less visibility than a 15-upvote, 30-minute-old post. Prioritize quota on high-visibility posts.

**New file:** `scripts/post_scorer.py`
- Command: `score --input FILE --output FILE`
- Input: JSON array of post metadata (age_minutes, upvotes, comment_count, subreddit, is_question)
- Scoring heuristics (stdlib math only):
  - **Freshness:** <60 min +20, <120 min +10, >360 min -15
  - **Velocity:** upvotes/age ratio
  - **Comment sweet spot:** 0-5 comments +15, 6-15 neutral, 15+ gets -20
  - **Question bonus:** +10 if title has `?`
- Output: ranked list with engagement_potential scores 0-100

**Modify:** `SKILL.md` -- After scanning /new, score all suitable posts and pick the highest engagement_potential one (instead of first suitable).
**Modify:** `workflow.md` -- Document post scoring step.

---

## Phase 3: Learning (needs 2+ weeks of data from Phase 1)

### 7. Comment Structure Diversity Tracking

**Why:** If every comment starts with "I think" and is 40-60 words, the account develops a detectable fingerprint. Active diversity avoidance makes the account harder to flag.

**New file:** `scripts/diversity_tracker.py`
- Commands: `record --runtime-root X --fingerprint FILE` and `guidance --runtime-root X`
- Each posted comment gets a structural fingerprint stored in `state/diversity_state.json` (rolling 30 entries):
  ```json
  {"opener_type": "opinion", "word_count_bucket": "medium", "has_question": false, "paragraph_count": 1, "starts_with_i": true, "uses_list": false}
  ```
- `guidance` analyzes last 30 fingerprints, outputs what to avoid/prefer (e.g., "70% start with 'I' -- avoid opinion openers, prefer question or fact openers")

**New file:** `state/diversity_state.json`

**Modify:** `score_candidates.py` -- Add `--diversity-guidance FILE` argument. Diversity bonus of +8 for preferred patterns, -5 penalty for overrepresented patterns.
**Modify:** `SKILL.md` -- Run diversity guidance before candidate generation, include in prompt context.

---

### 8. Adaptive Per-Subreddit Scoring Weights

**Why:** r/LocalLLaMA rewards technical depth while r/Entrepreneur rewards practical brevity. Static weights can't capture this. Feedback data enables self-tuning.

**New file:** `scripts/weight_optimizer.py`
- Command: `optimize --runtime-root X`
- Reads `feedback_history.json`, groups by subreddit
- For subreddits with 15+ samples: computes rank correlation between each score dimension and upvotes
- Nudges weights toward dimensions that correlate with upvotes (learning rate 0.05, clamped 0.05-0.40 per dimension)
- Output: `state/subreddit_profiles.json`
  ```json
  {"r/LocalLLaMA": {"weights": {"intent": 0.25, "tone": 0.10, "specificity": 0.30, "naturalness": 0.20, "safety": 0.15}, "sample_size": 42, "avg_upvotes": 3.2}}
  ```

**New file:** `state/subreddit_profiles.json`

**Modify:** `score_candidates.py` -- Add `--weights-file FILE` argument. Load per-subreddit weight overrides; fall back to global defaults.
**Modify:** `SKILL.md` -- Run optimizer weekly (or every 15 new data points per subreddit). Pass weights file to scoring.

---

### 9. Adaptive Scheduling (Subreddit Activity Optimization)

**Why:** Fixed sessions at 04:30/08:30/13:30/18:00 IST ignore that US-heavy subreddits peak in IST evening. Posting during peak hours increases visibility.

**New file:** `scripts/schedule_optimizer.py`
- Commands: `observe --runtime-root X --subreddit Y --post-count N --avg-age-minutes M` and `optimize --runtime-root X`
- During each session, record post volume and freshness per subreddit per hour-of-day into `state/activity_observations.json`
- After 2 weeks of observations, `optimize` outputs priority ordering of subreddits for each time slot
- Conservative: never skips subreddits, just reorders preference. Existing caps respected.

**New file:** `state/activity_observations.json`

**Modify:** `SKILL.md` -- Subreddit selection becomes "highest predicted activity for current time slot, breaking ties by oldest activity" (instead of just oldest activity).
**Modify:** `subreddits.md` -- Add "preferred session" column (populated by optimizer over time).

---

### 10. Rich Analytics Dashboard

**Why:** Current daily logs tell you *what* happened but not *what's working*. Analytics enable data-driven decisions.

**New file:** `scripts/analytics_generator.py`
- Commands:
  - `trend-check --runtime-root X` -- 5-line stdout summary for session start context
  - `weekly-report --runtime-root X --week YYYY-WNN` -- Full markdown analytics report
- Weekly report sections:
  - **Volume:** posted/skipped/retry rates, daily distribution (text histogram)
  - **Quality:** avg score by subreddit, score trends, top 5 performers with URLs
  - **Engagement:** avg upvotes by subreddit, best/worst performers, reply rates
  - **Health:** shadow ban checks, rate limit frequency, style guard failure rate
  - **Diversity:** opener distribution, length distribution, pattern alerts
  - **Recommendations:** auto-generated ("Reduce r/artificial at 0.5 avg upvotes, increase r/ClaudeAI at 4.2 avg upvotes")

**New dir:** `tracking/reddit/analytics/`

**Modify:** `SKILL.md` -- Step 1 calls `trend-check` and reads output for session context. Weekly reports generated Sunday evening.

---

## Summary of All New Files

| File | Type | Purpose |
|------|------|---------|
| `scripts/harvest_feedback.py` | Python | Harvest upvotes/replies from posted comments |
| `scripts/health_check.py` | Python | Shadow ban detection & account health |
| `scripts/error_classifier.py` | Python | Smart error categorization & recovery |
| `scripts/thread_analyzer.py` | Python | Analyze existing thread before commenting |
| `scripts/rewrite_guide.py` | Python | Map style failures to rewrite instructions |
| `scripts/post_scorer.py` | Python | Predict post engagement potential |
| `scripts/diversity_tracker.py` | Python | Track & diversify comment structures |
| `scripts/weight_optimizer.py` | Python | Self-tune scoring weights from feedback |
| `scripts/schedule_optimizer.py` | Python | Optimize subreddit timing from activity data |
| `scripts/analytics_generator.py` | Python | Generate trend checks & weekly analytics |
| `state/feedback_history.json` | State | Rolling comment performance data |
| `state/health_state.json` | State | Account health tracking |
| `state/error_log.json` | State | Error history for smart recovery |
| `state/diversity_state.json` | State | Comment structure fingerprints |
| `state/subreddit_profiles.json` | State | Per-subreddit learned weights |
| `state/activity_observations.json` | State | Subreddit activity patterns |

## Files Modified

| File | Changes |
|------|---------|
| `SKILL.md` | Add harvest phase, health gate, thread analysis, retry loop, post scoring, diversity guidance, adaptive weights, smart errors, analytics |
| `score_candidates.py` | Add `--weights-file`, `--thread-digest`, `--diversity-guidance` args; add novelty dimension; rebalance weights |
| `style_guard.py` | Add `--suggest-fix` flag with fix hints |
| `state_manager.py` | Add `update-diversity` command |
| `config.yaml` | Add health check, error handling, and analytics config keys |
| `workflow.md` | Document all new workflow steps |
| `safety.md` | Document health monitoring and error protocols |
| `subreddits.md` | Add preferred session and activity columns |
| `tracking/reddit/template.md` | Add performance and diversity sections |

## Implementation Order

1. **Phase 1** (harvest, health, errors) -- Foundation; everything else depends on feedback data
2. **Phase 2** (thread analysis, style retry, post scoring) -- Immediate quality wins, no data dependency
3. **Phase 3** (diversity, adaptive weights, scheduling, analytics) -- Needs 2+ weeks of accumulated data

## Verification

After each phase:
1. Run each new Python script with `--help` to verify it parses correctly
2. Run with sample JSON input files to verify output format
3. Execute a full skill session and confirm new steps execute in order
4. Check that `daily_state.json`, `feedback_history.json`, and other state files update correctly
5. Verify existing guardrails (style guard, caps, locks) still function identically
6. For health check: manually test with a known-visible comment URL to confirm green status
