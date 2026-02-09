# Plan: Fix Session Cap Logic

## Context

The current `session_cap: 235` in config.yaml is nonsensical. It's higher than the `daily_cap: 70`, so it never constrains anything. The formula `min(session_cap, daily_cap - total_comments)` always resolves to the daily cap side.

A meaningful session cap should reflect the physical reality: how many comments can actually be posted in a session's time window given the 5-10 minute random gap.

## The Math

Active window: 04:00-19:00 IST. First session at 04:30, last window ends at 19:00 = 870 minutes of posting time.

Gap between comments: 5-10 minutes (random), average 7.5 minutes.

| Scenario | Gap | Max comments in 870 min |
|----------|-----|------------------------|
| Fastest | 5 min | 174 |
| Slowest | 10 min | 87 |
| Average | 7.5 min | 116 |

**Agreed daily cap: 100** (comfortable within the 87-116 realistic range).

Per-session targets distributed proportionally to session duration:

| Session | Window | Duration | Target | % of day |
|---------|--------|----------|--------|----------|
| 04:30 | 04:30 - 08:30 | 240 min | 28 | 28% |
| 08:30 | 08:30 - 13:30 | 300 min | 34 | 34% |
| 13:30 | 13:30 - 18:00 | 270 min | 30 | 30% |
| 18:00 | 18:00 - 19:00 | 60 min | 8 | 8% |
| **Total** | | **870 min** | **100** | 100% |

## Changes

### 1. Update daily cap and replace flat session_cap with per-session targets

**File:** `runtime/reddit-commenter/config.yaml`
- Change `daily_cap: 70` to `daily_cap: 100`
- Remove `session_cap: 235`
- Restructure `sessions` from a flat list of times to objects with time and target:

```yaml
daily_cap: 100
sessions:
  - time: "04:30"
    target: 28
  - time: "08:30"
    target: 34
  - time: "13:30"
    target: 30
  - time: "18:00"
    target: 8
```

### 2. Update session target calculation in state_manager.py

**File:** `skills/reddit-commenter-safe/scripts/state_manager.py`
- Update `cmd_remaining` to accept `--session-target` (the per-session target from config) instead of `--session-cap`
- Formula becomes: `remaining = min(session_target, daily_cap - total_comments)`

### 3. Update SKILL.md workflow

**File:** `skills/reddit-commenter-safe/SKILL.md`
- Step 0 item 6: Change from `min(session_cap, daily_cap - total_comments)` to `min(session_target, daily_cap - total_comments)`
- Document that session_target comes from the matching session entry in config

### 4. Update reference docs

**File:** `skills/reddit-commenter-safe/references/config.md`
- Remove `session_cap` key documentation
- Add documentation for per-session `target` field
- Update `daily_cap` from 70 to 100

**File:** `skills/reddit-commenter-safe/references/scheduling.md`
- Update to reflect per-session targets instead of a global session cap

**File:** `skills/reddit-commenter-safe/references/workflow.md`
- Update Step 1 to reference per-session target

### 5. Update README.md

**File:** `README.md`
- Update Configuration table: remove `session_cap`, change `daily_cap` to 100
- Add per-session target explanation
- Update the "Target Subreddits" section cap reference if needed

### 6. No change needed

**File:** `skills/reddit-commenter-safe/scripts/analytics_generator.py`
- Reads daily state, not session cap -- no changes required

## Files to Modify

1. `runtime/reddit-commenter/config.yaml` -- daily_cap 100, restructure sessions with per-session targets
2. `skills/reddit-commenter-safe/scripts/state_manager.py` -- update `remaining` command args
3. `skills/reddit-commenter-safe/SKILL.md` -- update session target formula
4. `skills/reddit-commenter-safe/references/config.md` -- update config key docs
5. `skills/reddit-commenter-safe/references/scheduling.md` -- update schedule docs
6. `skills/reddit-commenter-safe/references/workflow.md` -- update workflow step 1
7. `README.md` -- update configuration table and daily cap

## Verification

1. Run `state_manager.py remaining --runtime-root ... --daily-cap 100 --session-target 28` and confirm correct output
2. Confirm config.yaml parses correctly (valid YAML)
3. Read through SKILL.md to verify the session target formula is consistent
