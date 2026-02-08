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

## Posting Gate Controls

1. Approval mode is disabled (ramp days = 0).
2. Auto mode is always active when all hard checks pass.
3. No manual approval step required.

## Failure Handling

1. Missing login: stop session and request manual login.
2. Lock conflict: stop session and log conflict.
3. No suitable posts: stop gracefully.
4. Rate-limit budget exhausted: stop current session.
