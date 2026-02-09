---
name: reddit-commenter-gemini
description: Run a safety-checked Reddit commenting session. Use to automate posting comments on Reddit with strict safety guardrails, candidate ranking, and feedback tracking.
---

# Reddit Commenter (Gemini Edition)

## Overview
Run high-quality Reddit commenting sessions with strong controls for account safety and writing quality. Enforce hard style checks, generate candidates, rank them, and post automatically.

**Runtime Root:** `runtime/reddit-commenter` (Shared with Codex skill)

## Required Workflow

### Step 0: Session Initialization
1.  **Load Config:** Read `references/config.md` and `runtime/reddit-commenter/config.yaml`.
2.  **Determine Session:** Check the current time against `references/scheduling.md`.
3.  **Acquire Lock:**
    ```bash
    python3 skills/reddit-commenter-gemini/scripts/state_manager.py --runtime-root runtime/reddit-commenter acquire-lock --session "<current_slot>"
    ```
    *If this fails (exit code 3), STOP immediately (session already active).*
4.  **Check Login:**
    *   Use `navigate_page` to go to `https://www.reddit.com/notifications`.
    *   Use `take_snapshot` to verify the user is logged in.
    *   *If not logged in, ask user to log in manually and STOP.*
5.  **Calculate Target:**
    ```bash
    python3 skills/reddit-commenter-gemini/scripts/state_manager.py --runtime-root runtime/reddit-commenter remaining --daily-cap 100 --session-target <target_from_config>
    ```

### Step 1: Harvest Feedback
1.  **Get Eligible URLs:**
    ```bash
    python3 skills/reddit-commenter-gemini/scripts/harvest_feedback.py --runtime-root runtime/reddit-commenter harvest
    ```
2.  **Collect Data:** For each URL in the output:
    *   `navigate_page(url=...)`
    *   `take_snapshot()`
    *   Extract `upvotes`, `reply_count`, and check if the comment text is visible.
3.  **Merge Data:**
    *   Create a JSON file `harvest_results.json` with the data.
    *   `python3 skills/reddit-commenter-gemini/scripts/harvest_feedback.py --runtime-root runtime/reddit-commenter merge --input harvest_results.json`

### Step 2: Candidate Loop
Repeat until session target is reached:

1.  **Select Subreddit:**
    *   Run `python3 skills/reddit-commenter-gemini/scripts/schedule_optimizer.py --runtime-root runtime/reddit-commenter suggest` to get the best subreddit.
2.  **Find Post:**
    *   `navigate_page(url="https://www.reddit.com/r/<subreddit>/new/")`
    *   `take_snapshot()`
    *   Identify a suitable text post (avoid video/image heavy, avoid promotional).
3.  **Analyze Post:**
    *   `navigate_page(url="<post_url>")`
    *   `take_snapshot(verbose=true)`
    *   Create `thread_context.json` with post title, body, and existing top comments.
    *   Run `python3 skills/reddit-commenter-gemini/scripts/thread_analyzer.py --input thread_context.json analyze`
4.  **Generate Candidates:**
    *   Run `python3 skills/reddit-commenter-gemini/scripts/diversity_tracker.py --runtime-root runtime/reddit-commenter guidance`
    *   **Prompt:** "Generate 10-12 comments for this post. Use the thread digest and diversity guidance. Output as JSON."
5.  **Score & Select:**
    *   Save candidates to `candidates.json`.
    *   Run `python3 skills/reddit-commenter-gemini/scripts/score_candidates.py --input candidates.json --thread-digest thread_digest.json --diversity-guidance guidance.json`
    *   Pick the candidate with the highest score.
6.  **Style Guard:**
    *   Run `python3 skills/reddit-commenter-gemini/scripts/style_guard.py --text "<candidate_text>" --suggest-fix`
    *   *If fail:* Use `scripts/rewrite_guide.py` to fix or skip.
7.  **Post Comment:**
    *   In the browser (already on post page):
    *   `click` the comment input area.
    *   `fill` the comment text.
    *   `click` the 'Comment' button.
    *   Wait for the comment to appear.
    *   *On Error:* Run `scripts/error_classifier.py` to decide action.
8.  **Update State:**
    *   `python3 skills/reddit-commenter-gemini/scripts/state_manager.py --runtime-root runtime/reddit-commenter update-count --subreddit <sub> --post-url <url>`
    *   `python3 skills/reddit-commenter-gemini/scripts/state_manager.py --runtime-root runtime/reddit-commenter update-diversity --text-file <comment_text_file>`
9.  **Sleep:** Wait 5-10 minutes (simulate delay or ask user).

### Step 3: Stop Conditions
*   Target met.
*   Daily cap met.
*   Health status RED (check via `scripts/health_check.py status`).

### Step 4: Cleanup
*   `python3 skills/reddit-commenter-gemini/scripts/state_manager.py --runtime-root runtime/reddit-commenter release-lock`

## References
*   [Configuration](references/config.md)
*   [Safety Model](references/safety.md)
*   [Scheduling](references/scheduling.md)
*   [Style Rules](references/style_rules.md)