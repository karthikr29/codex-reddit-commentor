# Runtime Config Contract

Runtime config file:
`/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/config.yaml`

## Keys

| Key | Type | Value |
|---|---|---|
| `timezone` | string | `Asia/Kolkata` |
| `mode` | string | `scheduled_auto_run` |
| `daily_cap` | int | `100` |
| `sessions` | list[object] | See below |
| `days` | list[string] | `["MO","TU","WE","TH","FR","SA","SU"]` |
| `active_window` | string | `04:00-22:00` |
| `gap_minutes_random` | string | `1-3` |
| `rate_limit_pause_minutes` | int | `30` |
| `rate_limit_retry_max` | int | `5` |
| `batch_enabled` | bool | `false` |
| `promotion_policy` | string | `none` |
| `approval_ramp_days` | int | `0` |
| `approval_timeout_minutes` | int | `2` |
| `approval_timeout_action` | string | `skip_and_continue` |

## Sessions Format

Each session is an object with `time` (IST) and `target` (max comments for that session). Targets are proportional to session duration and sum to `daily_cap`.

```yaml
sessions:
  - time: "04:30"
    target: 23
  - time: "08:30"
    target: 29
  - time: "13:30"
    target: 26
  - time: "18:00"
    target: 22
```

| Session | Window | Duration | Target |
|---------|--------|----------|--------|
| 04:30 | 04:30 - 08:30 | 240 min | 23 |
| 08:30 | 08:30 - 13:30 | 300 min | 29 |
| 13:30 | 13:30 - 18:00 | 270 min | 26 |
| 18:00 | 18:00 - 22:00 | 240 min | 22 |

## Interpretation Rules

1. Session target is `min(session.target, daily_cap - total_comments)`.
2. Day eligibility is based on local timezone and `days` list.
3. Session must stop when current local time is outside `active_window`.
4. Promotion policy `none` means never insert self-promo text.
