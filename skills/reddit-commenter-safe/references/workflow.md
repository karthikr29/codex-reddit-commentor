# Session Workflow

## Step 0: Preconditions

1. Runtime root exists.
2. Config file exists and parses.
3. Playwright browser session is available.
4. Session lock can be acquired.

## Step 1: Session Initialization

1. Confirm local date and time in `Asia/Kolkata`.
2. Ensure run day is allowed.
3. Ensure current time is inside active window.
4. Load or initialize daily state.
5. Calculate remaining daily quota and session target.

## Step 2: Candidate Loop

Repeat until session target reached or stop condition:

1. Select next subreddit under cap and oldest activity.
2. Open `new` feed first. Use `rising` only if no suitable post is found.
3. Find suitable post not already commented today.
4. Skip posts that are video-focused, promo-heavy, or low-context.
5. Skip posts with very high comment saturation when constructive value is likely low.
6. Analyze post intent and community tone.
7. Generate 10-12 candidate comments.
8. Score candidates and shortlist top 3.
9. Re-check top 3 against post intent and choose best 1.
10. Run hard style validation.
11. Determine gate mode (always `auto` since approval ramp is disabled).
12. Post comment when all safety and style checks pass.
14. Log result and update state.
15. Sleep random gap before next post.

## Step 3: Stop Conditions

Stop session when any condition holds:

1. Session target reached.
2. Daily cap reached.
3. Current time leaves active window.
4. Rate-limit retries exhausted.
5. No suitable posts remain.
6. User explicitly stops run.

## Step 4: Cleanup

1. Persist final state and tracking summary.
2. Release session lock.
3. Emit concise completion report.
