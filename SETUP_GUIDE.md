# Setup Guide: Reddit Commenter Automation

Complete guide to setting up and running the Reddit commenting automation system using **Claude Code (Codex)** or **Gemini CLI**.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone the Repository](#clone-the-repository)
3. [Project Structure Overview](#project-structure-overview)
4. [Option A: Claude Code (Codex) Setup](#option-a-claude-code-codex-setup)
5. [Option B: Gemini CLI Setup](#option-b-gemini-cli-setup)
6. [Reddit Login (Both Platforms)](#reddit-login-both-platforms)
7. [Configuration](#configuration)
8. [Running a Session](#running-a-session)
9. [Scheduling Automated Sessions](#scheduling-automated-sessions)
10. [Scripts Reference](#scripts-reference)
11. [Monitoring and Analytics](#monitoring-and-analytics)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Node.js 18+** (for Playwright MCP)
- **Python 3.13+** (for utility scripts; stdlib-only, no pip installs needed)
- **One of:**
  - [Claude Code (Codex)](https://docs.anthropic.com/en/docs/claude-code) installed and configured
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed and configured
- A **Reddit account** (you will log in manually via the browser; the system never stores credentials)

---

## Clone the Repository

```bash
git clone https://github.com/karthikr29/codex-reddit-commentor.git
cd codex-reddit-commentor
```

---

## Project Structure Overview

```
auto-commentor/
├── skills/
│   ├── reddit-commenter-safe/          # Claude Code (Codex) skill
│   │   ├── SKILL.md                    # Workflow definition (authoritative)
│   │   ├── scripts/                    # 13 Python utility scripts
│   │   └── references/                 # Operational docs
│   └── reddit-commenter-gemini/        # Gemini CLI skill
│       ├── SKILL.md                    # Workflow definition (Gemini edition)
│       ├── scripts/                    # Shared scripts (symlinked/identical)
│       └── references/                 # Operational docs
├── runtime/
│   └── reddit-commenter/               # Shared runtime (both skills use this)
│       ├── config.yaml                 # Master configuration
│       ├── personalization_reddit.md   # Voice and tone rules
│       ├── subreddits.md              # Target subreddits list
│       ├── prompts/                    # Automation invocation prompts
│       │   ├── automation_prompt.md    # For Codex
│       │   └── automation_prompt_gemini.md  # For Gemini
│       ├── state/                      # Session state files (gitignored)
│       └── tracking/                   # Reports and analytics
├── CLAUDE.md                           # Claude Code project instructions
├── GEMINI.md                           # Gemini CLI project instructions
└── .gemini/settings.json              # Gemini project-level MCP config
```

**Key point:** Both skills share the same `runtime/reddit-commenter/` directory for config, state, and personalization. Only the skill layer differs.

---

## Option A: Claude Code (Codex) Setup

### 1. Install Claude Code

Follow the [official Claude Code installation guide](https://docs.anthropic.com/en/docs/claude-code).

### 2. Configure Playwright MCP

Create or update `.claude/settings.local.json` in the project root:

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
  },
  "enableAllProjectMcpServers": true
}
```

This grants the skill permission to:
- Run Python scripts (`python3:*`)
- Use Playwright MCP tools for browser automation (navigate, snapshot, click, type, evaluate)

### 3. Install the Skill

Claude Code discovers skills from the `skills/` directory automatically. The skill `reddit-commenter-safe` will be available as `$reddit-commenter-safe`.

### 4. Verify Setup

Open Claude Code in the project directory and run:

```
What skills are available?
```

You should see `reddit-commenter-safe` listed. Then verify Python scripts work:

```bash
python3 skills/reddit-commenter-safe/scripts/style_guard.py --text "This is a test comment." --suggest-fix
```

---

## Option B: Gemini CLI Setup

### 1. Install Gemini CLI

```bash
npm install -g @anthropic-ai/gemini-cli
```

Or follow the [Gemini CLI setup guide](https://github.com/google-gemini/gemini-cli).

### 2. Configure Playwright MCP

The project already includes Playwright MCP configuration at `.gemini/settings.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

This is project-level, so it activates automatically when you run Gemini CLI from the project directory.

If you need to set it up globally instead, add the same config to `~/.gemini/settings.json`.

### 3. Verify Playwright MCP

Open Gemini CLI in the project directory and check that Playwright tools are available:

```
What MCP tools do you have access to?
```

You should see tools like `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`.

### 4. Verify Python Scripts

```bash
python3 skills/reddit-commenter-gemini/scripts/style_guard.py --text "This is a test comment." --suggest-fix
```

---

## Reddit Login (Both Platforms)

The system **never** stores or asks for Reddit credentials. It operates through an already logged-in browser session.

### Steps:

1. From Claude Code or Gemini CLI, open a browser page:
   ```
   Navigate to https://www.reddit.com
   ```
   This launches the Playwright browser.

2. **Manually log in** to your Reddit account in the browser window that opens.

3. Verify by asking the AI to take a snapshot:
   ```
   Take a browser snapshot and confirm I'm logged in to Reddit.
   ```

4. The browser session persists across the automation session. You only need to log in once per browser launch.

**Important:** If the browser session expires mid-session, the system will detect it (login page redirect) and halt gracefully.

---

## Configuration

### Master Config: `runtime/reddit-commenter/config.yaml`

| Key | Default | Description |
|-----|---------|-------------|
| `timezone` | `Asia/Kolkata` | All times are in this timezone |
| `mode` | `scheduled_auto_run` | Execution mode |
| `daily_cap` | `100` | Maximum comments per day across all sessions |
| `sessions` | 4 slots | Scheduled session times with per-session targets |
| `active_window` | `02:00-22:00` | Posting is only allowed within this window |
| `gap_minutes_random` | `1-3` | Random delay (minutes) between posts |
| `promotion_policy` | `none` | Self-promotion disabled |
| `health_check_enabled` | `true` | Shadow ban detection active |
| `health_invisible_threshold` | `3` | Consecutive invisible comments before red status |

### Session Schedule (IST)

| Session | Time | Window | Target |
|---------|------|--------|--------|
| Early morning | 02:30 | 02:30 - 08:30 | 31 |
| Morning | 08:30 | 08:30 - 13:30 | 26 |
| Afternoon | 13:30 | 13:30 - 18:00 | 23 |
| Evening | 18:00 | 18:00 - 22:00 | 20 |

Targets are proportional to window duration and sum to the daily cap (100).

### Subreddit List: `runtime/reddit-commenter/subreddits.md`

Lists all target subreddits with a 10-comment per-subreddit daily cap. Edit this file to add or remove subreddits.

### Personalization: `runtime/reddit-commenter/personalization_reddit.md`

Defines the commenting voice and hard rules:
- Helpful peer tone, not lecturing
- Casual but credible, direct phrasing
- **Never** use em dash or semicolon
- No fake first-hand claims, no forced closing questions, no sales language

---

## Running a Session

### Claude Code (Codex)

**Quick start:**
```
Use $reddit-commenter-safe to run a safety-checked Reddit comment session.
```

**Full prompt (recommended):**
```
Run one Reddit commenting session with $reddit-commenter-safe.
Load runtime config from runtime/reddit-commenter/config.yaml,
enforce all safety and style guardrails.
```

Or paste the contents of `runtime/reddit-commenter/prompts/automation_prompt.md`.

### Gemini CLI

**Quick start:**
```
Run one Reddit commenting session using the skill at skills/reddit-commenter-gemini/SKILL.md.
Load runtime config from runtime/reddit-commenter/config.yaml,
enforce all safety and style guardrails.
```

Or paste the contents of `runtime/reddit-commenter/prompts/automation_prompt_gemini.md`.

### What Happens During a Session

1. **Initialize** - Load config, acquire session lock, check remaining quota
2. **Analytics** - Run a quick trend check on past performance
3. **Harvest Feedback** - Revisit comments posted 4-48h ago to collect upvotes/replies
4. **Health Gate** - Check for shadow ban (green/yellow/red)
5. **Candidate Loop** (repeats until target met):
   - Pick a subreddit from the list
   - Navigate to subreddit, scan new posts
   - Score posts for engagement potential
   - Open best post, analyze existing thread
   - Generate 10-12 comment candidates with varied structures
   - Score candidates on 6 dimensions (intent, tone, specificity, naturalness, safety, novelty)
   - Apply diversity bonus/penalty
   - Style guard validation on top candidate
   - **Post** the comment via Playwright
   - Wait 1-3 minutes (random delay)
   - Update state and counters
6. **Cleanup** - Release session lock, generate session report

---

## Scheduling Automated Sessions

### Codex Automations

Codex supports scheduled automations. Create four automations for the daily sessions:

| Automation ID | Time (IST) |
|--------------|------------|
| `reddit-commenter-safe-early-morning` | 02:30 |
| `reddit-commenter-safe-morning` | 08:30 |
| `reddit-commenter-safe-afternoon` | 13:30 |
| `reddit-commenter-safe-evening` | 18:00 |

Automations are stored in `~/.codex/automations/<id>/automation.toml`. Each should invoke the automation prompt from `runtime/reddit-commenter/prompts/automation_prompt.md`.

### Gemini CLI

For Gemini, use system-level scheduling (cron, launchd, etc.) to invoke the Gemini CLI at the configured times:

```bash
# Example crontab entry (IST = UTC+5:30, so 02:30 IST = 21:00 UTC previous day)
0 21 * * * cd /path/to/auto-commentor && gemini run "$(cat runtime/reddit-commenter/prompts/automation_prompt_gemini.md)"
```

Adjust the cron times for your timezone.

### Important: Keep Schedules in Sync

The automation schedule must match the `sessions` list in `config.yaml`. If you change session times in config, update your automations/cron jobs accordingly.

---

## Scripts Reference

All scripts are in `skills/reddit-commenter-safe/scripts/` (and mirrored in `skills/reddit-commenter-gemini/scripts/`). They use Python stdlib only - no pip install needed.

### Quick Reference

```bash
# Style validation
python3 scripts/style_guard.py --text "Your comment here" --suggest-fix

# Check remaining quota
python3 scripts/state_manager.py --runtime-root ../../runtime/reddit-commenter remaining --daily-cap 100 --session-target 31

# Score candidates from JSON
python3 scripts/score_candidates.py --input candidates.json --thread-digest digest.json

# Get diversity guidance
python3 scripts/diversity_tracker.py --runtime-root ../../runtime/reddit-commenter guidance

# Health status
python3 scripts/health_check.py --runtime-root ../../runtime/reddit-commenter status

# Analytics trend check
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter trend-check

# Weekly report
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter weekly-report --week 2026-W06
```

Every script supports `--help`. Exit code 0 = success, 3 = lock conflict.

### Full Script List

| Script | Purpose |
|--------|---------|
| `state_manager.py` | Session locks, daily counters, URL tracking, diversity fingerprints |
| `score_candidates.py` | 6-dimension weighted scoring with novelty |
| `style_guard.py` | Hard style validation (em dash, semicolon, 47+ banned AI phrases) |
| `harvest_feedback.py` | Collect upvotes/replies from posted comments |
| `health_check.py` | Shadow ban detection (green/yellow/red) |
| `error_classifier.py` | Error categorization with progressive backoff |
| `thread_analyzer.py` | Analyze existing thread for covered topics and gaps |
| `rewrite_guide.py` | Map style failures to targeted fix instructions |
| `post_scorer.py` | Rank posts by engagement potential |
| `diversity_tracker.py` | Track comment structures, generate diversity guidance |
| `weight_optimizer.py` | Self-tune scoring weights per subreddit |
| `schedule_optimizer.py` | Learn peak activity times per subreddit |
| `analytics_generator.py` | Trend checks and weekly performance reports |

---

## Monitoring and Analytics

### Account Health

The system monitors for shadow bans by checking comment visibility:

| Status | Meaning | Action |
|--------|---------|--------|
| Green | All comments visible | Normal operation |
| Yellow | 1 invisible comment | Proceed with caution |
| Red | 3+ consecutive invisible | **All posting halted immediately** |

Check health status:
```bash
python3 scripts/health_check.py --runtime-root ../../runtime/reddit-commenter status
```

### Self-Learning

The system improves over time through four feedback loops:

1. **Performance Harvesting** - Collects upvote/reply data from past comments (rolling 500 entries)
2. **Adaptive Weights** - After 15+ samples per subreddit, scoring weights auto-tune via Spearman correlation
3. **Diversity Tracking** - Fingerprints comment structures to avoid repetitive patterns
4. **Schedule Optimization** - Learns peak activity times per subreddit over 2+ weeks

### Weekly Reports

Auto-generated on Sundays or run manually:

```bash
python3 scripts/analytics_generator.py --runtime-root ../../runtime/reddit-commenter weekly-report
```

Reports include: volume stats, engagement by subreddit, top comments, health status, error frequency, diversity distribution, and recommendations.

---

## Troubleshooting

### Session Lock Stuck

If a session crashes without releasing the lock:

```bash
# Check lock status
python3 scripts/state_manager.py --runtime-root runtime/reddit-commenter gate-mode

# Manually release (delete the lock file)
rm runtime/reddit-commenter/state/session.lock
```

### Browser Session Expired

If the Playwright browser is no longer logged in:

1. Navigate to Reddit in the browser
2. Log in manually
3. Restart the session

The system detects login page redirects and halts gracefully rather than posting anonymously.

### Style Guard Rejecting Everything

Test your comment style:

```bash
python3 scripts/style_guard.py --text "Your comment here" --suggest-fix
```

Common violations: em dash (`--` or `—`), semicolons, and [47+ banned AI phrases](skills/reddit-commenter-safe/references/style_rules.md) like "game-changer", "leverage", "dive into".

### Health Status Red

If health monitoring triggers red (3+ invisible comments):

1. Check your account manually from a logged-out browser
2. If comments are visible, reset health state:
   ```bash
   python3 scripts/health_check.py --runtime-root runtime/reddit-commenter reset
   ```
3. If comments are genuinely invisible, your account may be shadow-banned. Wait 24-48 hours before resuming.

### Python Version

Scripts require Python 3.13+. Check with:

```bash
python3 --version
```

### Playwright MCP Not Working

For Claude Code:
- Verify `.claude/settings.local.json` has the Playwright permissions listed above
- Ensure `enableAllProjectMcpServers: true` is set

For Gemini CLI:
- Verify `.gemini/settings.json` exists in the project root with the Playwright MCP config
- Run `npx @playwright/mcp@latest` manually to test if it launches

### State Files Missing

State files are created automatically on first run. If the `state/` directory doesn't exist:

```bash
mkdir -p runtime/reddit-commenter/state
```

The scripts will initialize the JSON files as needed.

---

## Safety Model Summary

- **No credentials stored** - relies on existing browser session
- **No duplicates** - tracks all commented URLs
- **Hard style blocks** - em dash, semicolon, 47+ banned phrases
- **No self-promotion** - disabled via `promotion_policy: none`
- **Rate limiting** - 1-3 min random delays, progressive backoff on errors
- **Session lock** - prevents concurrent sessions
- **Shadow ban detection** - auto-halts on red health status
- **Daily and per-subreddit caps** - enforced via state tracking
