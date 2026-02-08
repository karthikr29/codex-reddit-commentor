# Runtime State Files

1. `daily_state.json`: rolling counters and commented post URLs for current day.
2. `daily_state.template.json`: template for reset.
3. `ramp_state.json`: approval ramp start and duration.
4. `session.lock`: overlap prevention lock file.

These files are operational state. They are safe to edit only when no session is running.
