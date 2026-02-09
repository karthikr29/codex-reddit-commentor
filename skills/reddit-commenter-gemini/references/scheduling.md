# Scheduling and Session Policy

## Daily Schedule (IST)

| Session | Time | Window | Target |
|---------|------|--------|--------|
| Early morning | 04:30 | 04:30 - 08:30 (240 min) | 28 |
| Morning | 08:30 | 08:30 - 13:30 (300 min) | 34 |
| Afternoon | 13:30 | 13:30 - 18:00 (270 min) | 30 |
| Evening | 18:00 | 18:00 - 19:00 (60 min) | 8 |

Active window: `04:00-19:00`
Days: every day (`MO,TU,WE,TH,FR,SA,SU`)

## Session Limits

1. Daily cap: `100`
2. Per-session targets sum to daily cap (28 + 34 + 30 + 8 = 100).
3. Targets are proportional to each session's available time window.
4. Effective session target: `min(session.target, daily_cap - total_comments)`. If earlier sessions underperform, later sessions can absorb remaining quota up to their target.

## How Targets Were Calculated

With a 5-10 minute random gap (avg 7.5 min) and 870 minutes of total posting time (04:30-19:00), the realistic maximum is ~116 comments/day. The daily cap of 100 sits comfortably within this range. Each session target is proportional to its duration:

- 240 min / 870 min * 100 = 28
- 300 min / 870 min * 100 = 34
- 270 min / 870 min * 100 = 30
- 60 min / 870 min * 100 = 8

## Delay and Retry Policy

1. Delay between posted comments: random `5-10` minutes.
2. On rate-limit: pause `30` minutes, retry up to `5` times, then stop current session.

## Ramp Policy

1. Approval ramp days: `0` (disabled).
2. All sessions run in `auto` mode when safety checks pass.
3. No manual approval step required.

## Overlap Prevention

1. Use session lock file before starting work.
2. If lock exists, exit session immediately.
