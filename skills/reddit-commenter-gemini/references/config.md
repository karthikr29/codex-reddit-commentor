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
| `active_window` | string | `04:00-19:00` |
| `gap_minutes_random` | string | `5-10` |
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
    target: 28
  - time: "08:30"
    target: 34
  - time: "13:30"
    target: 30
  - time: "18:00"
    target: 8
```

| Session | Window | Duration | Target |
|---------|--------|----------|--------|
| 04:30 | 04:30 - 08:30 | 240 min | 28 |
| 08:30 | 08:30 - 13:30 | 300 min | 34 |
| 13:30 | 13:30 - 18:00 | 270 min | 30 |
| 18:00 | 18:00 - 19:00 | 60 min | 8 |

## Interpretation Rules

1. Session target is `min(session.target, daily_cap - total_comments)`.
2. Day eligibility is based on local timezone and `days` list.
3. Session must stop when current local time is outside `active_window`.
4. Promotion policy `none` means never insert self-promo text.
