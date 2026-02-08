# Runtime State Files

All state files are generated during sessions and gitignored. They are safe to edit only when no session is running.

## Core State

1. `daily_state.json`: Rolling counters and commented post URLs for the current day.
2. `daily_state.template.json`: Template for daily reset.
3. `ramp_state.json`: Approval ramp start date and duration.
4. `session.lock`: Overlap prevention lock file (deleted on session end).

## Feedback & Health State

5. `feedback_history.json`: Rolling log of comment performance data (upvotes, replies, visibility). Capped at 500 entries.
6. `health_state.json`: Account health tracking (green/yellow/red status, invisible comment count).
7. `error_log.json`: Rolling error history for smart recovery. Capped at 100 entries.

## Learning State

8. `diversity_state.json`: Structural fingerprints of the last 30 posted comments (opener type, length, patterns).
9. `subreddit_profiles.json`: Per-subreddit scoring weight overrides, learned from feedback data.
10. `activity_observations.json`: Subreddit activity levels by time-of-day, used for schedule optimization.
