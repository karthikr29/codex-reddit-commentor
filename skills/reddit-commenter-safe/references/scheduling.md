# Scheduling and Session Policy

## Daily Schedule (IST)

1. Early morning session: `04:30`
2. Morning session: `08:30`
3. Afternoon session: `13:30`
4. Evening session: `18:00`
3. Active window: `04:00-19:00`
4. Days: every day (`MO,TU,WE,TH,FR,SA,SU`)

## Session Limits

1. Daily cap: `70`
2. Per-session cap: up to `235`
3. Adaptive quota: afternoon session may consume remaining quota from morning skips.

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
