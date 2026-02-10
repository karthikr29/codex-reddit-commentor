# Reddit Commenter Safe -- Codex Skill

A self-learning Reddit commenting automation skill built for **Codex (Claude Code)**. It generates natural, contextually relevant comments across entrepreneurship and AI/tech subreddits with strict safety guardrails, candidate ranking, and feedback-driven improvement.

## How It Works

This is a **Codex skill** -- it runs inside the Codex application (Claude Code CLI) and uses Playwright MCP for browser automation. It does **not** use the Reddit API. All interaction happens through an already logged-in browser session.

Each session follows this flow:

```
Load config -> Acquire lock -> Harvest feedback from past comments
-> Health check (shadow ban detection) -> Candidate loop:
   Pick subreddit -> Score posts for engagement -> Analyze thread
   -> Generate 10-12 candidates -> Score with novelty & diversity
   -> Style validate -> Post -> Update state -> Sleep -> Repeat
-> Release lock -> Report
```

The skill learns over time: it harvests upvote/reply data from past comments, tunes scoring weights per subreddit, tracks comment structure diversity, and generates weekly analytics reports.

## Prerequisites

1. **Codex (Claude Code)** installed and configured
2. **Playwright MCP** server enabled in your Codex settings (`.claude/settings.local.json`)
3. **Python 3.13+** available in your environment
4. **Reddit account** already logged in via the Playwright browser session
5. No pip dependencies required -- all scripts use Python stdlib only

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/karthikr29/codex-reddit-commentor.git
cd codex-reddit-commentor
```

### 2. Configure Codex permissions

Ensure your `.claude/settings.local.json` includes Playwright MCP permissions:

```json
{
  "permissions": {
    "allow": [
      "Bash(python3:*)",
      "mcp__plugin_playwright_playwright__browser_snapshot",
      "mcp__plugin_playwright_playwright__browser_navigate",
      "mcp__plugin_playwright_playwright__browser_evaluate",
      "mcp__plugin_playwright_playwright__browser_click",
      "mcp__plugin_playwright_playwright__browser_type"
    ]
  }
}
```

### 3. Log in to Reddit

Open the Playwright browser and manually log in to your Reddit account. The skill will reuse this session -- it **never** asks for or stores credentials.

### 4. Run from Codex

Invoke the skill from the Codex CLI:

```
Use $reddit-commenter-safe to run a safety-checked Reddit comment session.
```

Or use the full automation prompt:

```
Run one Reddit commenting session with $reddit-commenter-safe.
Load runtime config from runtime/reddit-commenter/config.yaml,
enforce all safety and style guardrails.
```

## Project Structure

```
auto-commentor/
├── skills/
│   └── reddit-commenter-safe/
│       ├── SKILL.md                      # Skill definition & full workflow
│       ├── agents/
│       │   └── openai.yaml               # Agent interface metadata
│       ├── scripts/                      # Python utilities (13 scripts)
│       │   ├── state_manager.py          # State, locks, counters, diversity
│       │   ├── score_candidates.py       # Candidate scoring & ranking
│       │   ├── style_guard.py            # Hard style validation
│       │   ├── harvest_feedback.py       # Upvote/reply collection
│       │   ├── health_check.py           # Shadow ban detection
│       │   ├── error_classifier.py       # Smart error recovery
│       │   ├── thread_analyzer.py        # Existing thread analysis
│       │   ├── rewrite_guide.py          # Style fix instructions
│       │   ├── post_scorer.py            # Post engagement prediction
│       │   ├── diversity_tracker.py      # Comment structure diversity
│       │   ├── weight_optimizer.py       # Adaptive scoring weights
│       │   ├── schedule_optimizer.py     # Subreddit activity timing
│       │   └── analytics_generator.py    # Trend checks & weekly reports
│       └── references/                   # Operational docs
│           ├── workflow.md               # Step-by-step session flow
│           ├── safety.md                 # Safety model & health monitoring
│           ├── style_rules.md            # Banned phrases & hard blocks
│           ├── scheduling.md             # Session schedule policy
│           └── config.md                 # Config key reference
├── runtime/
│   └── reddit-commenter/
│       ├── config.yaml                   # Master runtime configuration
│       ├── personalization_reddit.md     # Voice & tone profile
│       ├── subreddits.md                 # Target subreddits & caps
│       ├── prompts/
│       │   └── automation_prompt.md      # Codex invocation prompt
│       ├── state/                        # Session state (gitignored)
│       │   ├── daily_state.json          # Daily counters & URLs
│       │   ├── feedback_history.json     # Comment performance data
│       │   ├── health_state.json         # Account health tracking
│       │   ├── error_log.json            # Error history
│       │   ├── diversity_state.json      # Comment fingerprints
│       │   ├── subreddit_profiles.json   # Learned scoring weights
│       │   └── activity_observations.json # Subreddit activity data
│       └── tracking/
│           └── reddit/
│               ├── template.md           # Daily report template
│               └── analytics/            # Weekly analytics reports
└── reports/
```

## Scripts Reference

### Core Scripts

| Script | Purpose | Key Commands |
|--------|---------|-------------|
| `state_manager.py` | Manage daily state, session lock, counters | `init-day`, `acquire-lock`, `release-lock`, `update-count`, `remaining`, `should-skip`, `gate-mode`, `update-diversity` |
| `score_candidates.py` | Score and rank 10-12 comment candidates | `--input`, `--thread-digest`, `--diversity-guidance`, `--weights-file` |
| `style_guard.py` | Hard style validation (em dash, semicolon, 47 banned phrases) | `--text`, `--file`, `--suggest-fix`, `--json-only` |

### Feedback & Safety Scripts

| Script | Purpose | Key Commands |
|--------|---------|-------------|
| `harvest_feedback.py` | Collect upvotes/replies from posted comments | `harvest`, `merge`, `stats` |
| `health_check.py` | Shadow ban detection (green/yellow/red) | `check`, `status`, `reset` |
| `error_classifier.py` | Classify errors with progressive backoff | `classify`, `summary` |

### Intelligence Scripts

| Script | Purpose | Key Commands |
|--------|---------|-------------|
| `thread_analyzer.py` | Analyze existing thread for covered topics & gaps | `analyze` |
| `rewrite_guide.py` | Map style failures to fix instructions for retry | `guide` |
| `post_scorer.py` | Rank posts by engagement potential | `score` |

### Learning Scripts

| Script | Purpose | Key Commands |
|--------|---------|-------------|
| `diversity_tracker.py` | Track comment structures, generate diversity guidance | `record`, `fingerprint`, `guidance` |
| `weight_optimizer.py` | Self-tune scoring weights per subreddit | `optimize`, `show` |
| `schedule_optimizer.py` | Learn peak activity times per subreddit | `observe`, `optimize`, `suggest` |
| `analytics_generator.py` | Trend checks and weekly performance reports | `trend-check`, `weekly-report` |

### Local Testing

All scripts run standalone with `--help`:

```bash
# Check style compliance
python3 scripts/style_guard.py --text "Looks good. I'd try adding jitter to your retries." --suggest-fix

# Check remaining quota (session target from config, e.g. 28 for 04:30 session)
python3 scripts/state_manager.py --runtime-root ../../runtime/reddit-commenter remaining --daily-cap 100 --session-target 28

# Score test candidates
python3 scripts/score_candidates.py --input test_input.json --thread-digest digest.json

# Get diversity guidance
python3 scripts/diversity_tracker.py --runtime-root ../../runtime/reddit-commenter guidance

# Quick trend check
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter trend-check
```

## Configuration

All runtime config lives in `runtime/reddit-commenter/config.yaml`:

| Key | Default | Description |
|-----|---------|-------------|
| `timezone` | `Asia/Kolkata` | Timezone for scheduling |
| `mode` | `scheduled_auto_run` | Execution mode |
| `daily_cap` | `100` | Max comments per day |
| `sessions` | See below | Scheduled sessions with per-session targets (IST) |
| `active_window` | `04:00-19:00` | Posting allowed only in this window |
| `gap_minutes_random` | `1-3` | Random delay between posts |
| `promotion_policy` | `none` | Self-promotion disabled |
| `health_check_enabled` | `true` | Shadow ban detection on/off |
| `health_invisible_threshold` | `3` | Consecutive invisible comments before red status |
| `error_handling.progressive_backoff` | `true` | Smart error recovery |

### Per-Session Targets

Each session has a `time` and `target` (max comments). Targets are proportional to session duration and sum to `daily_cap`:

| Session | Window | Duration | Target |
|---------|--------|----------|--------|
| 04:30 | 04:30 - 08:30 | 240 min | 28 |
| 08:30 | 08:30 - 13:30 | 300 min | 34 |
| 13:30 | 13:30 - 18:00 | 270 min | 30 |
| 18:00 | 18:00 - 19:00 | 60 min | 8 |

With a 1-3 minute random gap (avg 2.0 min), the realistic daily maximum is ~500 comments. The daily cap of 100 sits comfortably within this range.

### Codex Automations Setup

Codex automations live in `~/.codex/automations/<id>/automation.toml` and their run state (next/last run time) is stored in `~/.codex/sqlite/codex-dev.db`.

To run the 4 daily sessions automatically, ensure you have **four ACTIVE automations** scheduled for (IST):

| Automation ID | Time |
|--------------|------|
| `reddit-commenter-safe-early-morning` | 04:30 |
| `reddit-commenter-safe-morning` | 08:30 |
| `reddit-commenter-safe-afternoon` | 13:30 |
| `reddit-commenter-safe-evening` | 18:00 |

Keep these schedules in sync with the `sessions` list in `runtime/reddit-commenter/config.yaml`.

## Target Subreddits

44 subreddits across entrepreneurship, AI/tech, and adjacent communities, each with a 10-comment daily cap:

**Entrepreneurship:** r/Entrepreneur, r/Entrepreneurship, r/Entrepreneurial, r/Entrepreneurs, r/EntrepreneurRideAlong

**AI/Tech:** r/ai, r/ChatGPT, r/Claude, r/ClaudeAI, r/Cursor, r/LocalLLaMA, r/AI_Testing, r/AIToolTesting, r/artificial, r/Rag

**Builder:** r/sideprojects, r/SideProject, r/WebDev, r/Obsidian

**Startups/SaaS:** r/startups, r/Startup_Ideas, r/startup, r/smallbusiness, r/SaaS, r/microsaas, r/micro_saas, r/indiehackers

**ML/Learning:** r/MachineLearning, r/learnmachinelearning, r/LangChain, r/learnprogramming

**Sales/Marketing:** r/marketing, r/digital_marketing, r/DigitalMarketing, r/DigitalMarketingHack, r/sales, r/Sales_Professionals, r/salestechniques, r/techsales, r/growthHacking

**Career/Remote:** r/cscareerquestions, r/ProductManagement, r/digitalnomad, r/freelance

## Safety Model

### Non-Negotiable Rules

1. **No credentials** -- Never asks for, stores, or captures Reddit email/password/OTP
2. **Browser-only** -- Operates exclusively through an already logged-in Playwright session
3. **No duplicates** -- Tracks commented URLs to prevent repeat posts
4. **Hard style blocks** -- Em dash, semicolon, and 47 banned AI phrases are instant failures
5. **Promotion disabled** -- No self-promo language while `promotion_policy: none`
6. **Rate limiting** -- Random 1-3 min delays, progressive backoff on errors
7. **Session lock** -- Prevents concurrent sessions from overlapping

### Account Health Monitoring

The skill detects shadow bans by checking comment visibility from a logged-out perspective:

- **Green**: All comments visible. Normal operation.
- **Yellow**: 1 invisible comment. Proceed with caution.
- **Red**: 3+ consecutive invisible. **All posting halted immediately.**

### Error Recovery

Errors are classified and handled differently:

| Error | Action |
|-------|--------|
| Rate limit (429) | Progressive backoff: 5 -> 15 -> 30 -> 60 min |
| Forbidden (403) | Skip subreddit for rest of session |
| Not found (404) | Skip silently (post deleted) |
| Login expired | End session, flag for manual re-login |
| Content policy | Skip post, flag for style guard review |

## Self-Learning System

The skill improves over time through four feedback loops:

### 1. Performance Harvesting
Each session starts by revisiting comments posted 4-48 hours ago to collect upvotes, replies, and visibility status. Data persists in `feedback_history.json` (rolling 500 entries).

### 2. Adaptive Scoring Weights
After accumulating 15+ feedback samples per subreddit, the weight optimizer computes correlations between scoring dimensions and actual upvotes. Weights nudge toward what works in each community (learning rate 0.05, clamped 0.05-0.40).

### 3. Comment Diversity Tracking
Every posted comment gets a structural fingerprint (opener type, length bucket, starts-with-I, uses-list, etc.). When patterns become overrepresented (>40% of recent comments), the diversity tracker generates avoid/prefer guidance that feeds into candidate generation.

### 4. Schedule Optimization
During each session, the skill records subreddit activity levels (post count, freshness) by time-of-day. After 2 weeks of observations, subreddit selection is prioritized by predicted peak activity for the current time slot.

## Scoring Pipeline

Each candidate comment is scored across 6 weighted dimensions:

| Dimension | Default Weight | What It Measures |
|-----------|---------------|-----------------|
| Intent Match | 20% | Token overlap with post content |
| Subreddit Tone | 15% | Word count, technical terms, promo detection |
| Specificity | 20% | Examples, numbers, reasoning phrases |
| Naturalness | 20% | Contractions, sentence variation, formal markers |
| Safety | 15% | Style guard pass/fail + warning count |
| Novelty | 10% | How different from existing thread comments |

Plus a diversity bonus/penalty (+8/-5) based on structural pattern guidance.

Candidates that fail style guard get score 0. If the best rejected candidate had a pre-rejection score > 45, the skill triggers a single rewrite retry using targeted fix instructions.

## Weekly Analytics

Run the analytics dashboard manually or let it auto-generate on Sundays:

```bash
# Quick trend check (5-line summary)
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter trend-check

# Full weekly report
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter weekly-report --week 2026-W06
```

Reports include: volume stats, engagement by subreddit, top-performing comments, health status, error frequency, diversity distribution, and auto-generated recommendations.

## License

Private project. Not open source.
\n
