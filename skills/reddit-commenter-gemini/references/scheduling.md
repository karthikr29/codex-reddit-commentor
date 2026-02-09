# Scheduling and Session Policy

## Daily Schedule (IST)

| Session | Time | Window | Target |
|---------|------|--------|--------|
| Early morning | 04:30 | 04:30 - 08:30 (240 min) | 23 |
| Morning | 08:30 | 08:30 - 13:30 (300 min) | 29 |
| Afternoon | 13:30 | 13:30 - 18:00 (270 min) | 26 |
| Evening | 18:00 | 18:00 - 22:00 (240 min) | 22 |

Active window: `04:00-22:00`
Days: every day (`MO,TU,WE,TH,FR,SA,SU`)

## Session Limits

1. Daily cap: `100`
2. Per-session targets sum to daily cap (23 + 29 + 26 + 22 = 100).
3. Targets are proportional to each session's available time window.
4. Effective session target: `min(session.target, daily_cap - total_comments)`. If earlier sessions underperform, later sessions can absorb remaining quota up to their target.

## How Targets Were Calculated

With a 1-3 minute random gap (avg 2.0 min) and 1050 minutes of total posting time (04:30-22:00), the realistic maximum is ~500 comments/day. The daily cap of 100 sits comfortably within this range. Each session target is proportional to its duration:

- 240 min / 1050 min * 100 = 23
- 300 min / 1050 min * 100 = 29
- 270 min / 1050 min * 100 = 26
- 240 min / 1050 min * 100 = 22

## Delay and Retry Policy

1. Delay between posted comments: random `1-3` minutes.
2. On rate-limit: pause `30` minutes, retry up to `5` times, then stop current session.

## Ramp Policy

1. Approval ramp days: `0` (disabled).
2. All sessions run in `auto` mode when safety checks pass.
3. No manual approval step required.

## Overlap Prevention

1. Use session lock file before starting work.
2. If lock exists, exit session immediately.
