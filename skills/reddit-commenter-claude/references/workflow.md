# Workflow (Pasted Page, Drafts Only)

NEVER post. The user pastes the thread page and posts every draft by hand. `SKILL.md` is the full definition.

1. Load `personalization_reddit.md` and `personal_facts.md`.
2. Parse the paste into `state/tmp/thread_context.json`: post (subreddit, title, body, OP, age, upvotes, comment count) and comments (author, text, upvotes, age, replies, depth, is OP). Drop UI noise. Never guess numbers.
3. Run `thread_analyzer.py analyze` and `diversity_tracker.py guidance`.
4. Top-level comment: 10-12 candidates (2-3 one-liners of 12 words or fewer, the rest 12-35 words), `score_candidates.py`, top 3 including the best one-liner, `style_guard.py`, pick 1.
5. Replies: pick 1-3 comments (OP first, then active high-upvote comments, then questions or claims worth building on). 5-6 candidates each, score, style guard, pick 1.
6. Output: thread line, short comments list, then for the post and each reply: a table of EVERY candidate ranked best to worst with scores, top 3 marked and shown in code blocks, and the pick with a one-line why.
7. Delete temp files. Run `state_manager.py update-diversity` only for drafts the user says they posted.
