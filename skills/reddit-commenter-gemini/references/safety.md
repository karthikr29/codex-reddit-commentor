# Safety Model

## Credential and Identity Safety

1. Never ask for Reddit email, password, OTP, or recovery codes.
2. Never store credentials in config, logs, or state files.
3. Operate only via an already logged-in Playwright browser session.

## Account-Risk Controls

1. Enforce per-session and daily caps.
2. Enforce random delays between comments.
3. Stop on repeated rate-limit errors.
4. Skip subreddits with no suitable posts rather than forcing low-quality comments.

## Anti-Spam Controls

1. No duplicate comments on same post in same day.
2. No copy-paste reuse of prior comments.
3. Respect subreddit tone and post intent.
4. Disable self-promotion while `promotion_policy` is `none`.
5. Skip video-focused threads based on user preference.
6. Actively diversify comment structures to avoid detectable patterns.

## Posting Gate Controls

1. Approval mode is disabled (ramp days = 0).
2. Auto mode is always active when all hard checks pass.
3. No manual approval step required.

## Account Health Monitoring

1. **Shadow ban detection:** During feedback harvest, check comment visibility from a logged-out perspective.
2. **Health states:**
   - `green`: All comments visible. Normal operation.
   - `yellow`: 1 invisible comment detected. Proceed with caution, log warning.
   - `red`: 3+ consecutive invisible comments. **Halt all posting immediately.**
3. **Recovery:** After manual investigation and verification, reset health state with `health_check.py reset`.
4. **Threshold:** Configurable via `health_invisible_threshold` in `config.yaml` (default: 3).

## Error Classification and Recovery

1. **Rate limit (429):** Progressive backoff -- 5, 15, 30, 60 minutes. End session after 3 rate limits in one hour.
2. **Forbidden (403):** Skip subreddit for rest of session. Possible subreddit-level ban.
3. **Not found (404):** Post deleted. Skip silently, no penalty.
4. **Network timeout:** Retry once after 2 minutes.
5. **Login expired:** End session immediately. Flag for manual re-login.
6. **Content policy rejection:** Skip post. Flag comment text for style guard review.
7. **Playwright crash:** Attempt browser recovery. If persistent, end session.
8. **Error logging:** Rolling 100-entry log in `state/error_log.json` for pattern analysis.

## Failure Handling

1. Missing login: stop session and request manual login.
2. Lock conflict: stop session and log conflict.
3. No suitable posts: stop gracefully.
4. Error classifier END_SESSION: stop current session.
5. Health status red: stop immediately, log for manual review.
