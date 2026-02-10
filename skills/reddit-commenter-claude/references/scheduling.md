# On-Demand Execution Policy

## When to Run

This skill runs whenever the user invokes it. There are no scheduled session slots, no time windows, and no day restrictions.

## Target Count

The user specifies how many comments to post per run (e.g., "post 20 comments"). There is no daily cap or per-subreddit cap.

## Delay Policy

1. Delay between posted comments: random `1-3` minutes. This prevents Reddit rate limiting.
2. On rate-limit: pause `30` minutes, retry up to `5` times, then stop current run.

## No Overlap Prevention

No session lock is used. The user controls when the skill runs and is responsible for not invoking concurrent sessions.
