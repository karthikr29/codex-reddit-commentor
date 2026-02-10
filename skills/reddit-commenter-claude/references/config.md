# Runtime Config Contract

Runtime config file:
`/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/config.yaml`

## Keys

| Key | Type | Value |
|---|---|---|
| `timezone` | string | `Asia/Kolkata` |
| `gap_minutes_random` | string | `1-3` |
| `rate_limit_pause_minutes` | int | `30` |
| `rate_limit_retry_max` | int | `5` |
| `promotion_policy` | string | `none` |

## On-Demand Execution

This skill does not use scheduling keys (`daily_cap`, `sessions`, `days`, `active_window`, `approval_ramp_days`). The user specifies how many comments to post at invocation time via a target count parameter.

## Interpretation Rules

1. Target count is provided by the user at runtime (e.g., "post 15 comments").
2. No day eligibility checks. Runs any day, any time.
3. No active window enforcement.
4. Promotion policy `none` means never insert self-promo text.
