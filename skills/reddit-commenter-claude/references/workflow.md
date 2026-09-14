# Workflow (Pasted Page, Drafts Only)

NEVER post. The user pastes the thread page and posts every draft by hand. `SKILL.md` is the full definition.

1. Load `personalization_reddit.md`, `personal_facts.md`, and `punch_examples.md`.
2. Parse ONLY the post into `state/tmp/post.json` (subreddit, title, body, OP, age, upvotes, comment count). Drop UI noise. Never guess numbers. Title-only post too thin to comment on: say "Skip, not enough in the post" and stop.
3. Top-level comment from the post title and body only. Never read or reference comments. Run `diversity_tracker.py guidance`, write 10-12 candidates, `score_candidates.py` without `--thread-digest`, top 3 including the best one-liner, `style_guard.py`, pick 1.
4. Only now parse comments into `state/tmp/comments.json` (author, text, upvotes, age, replies, depth, is OP).
5. Replies: pick 0-3 comments (OP first, then active high-upvote comments, then questions or claims worth adding to or correcting). 5-6 candidates each from the post plus that one comment only. Drop any that repeat your top-level pick. Score, style guard, pick 1.
6. Output: thread line, top-level ranked table with top 3 and pick, comments list, then each reply's ranked table with top 3 and pick. Pick reasons never cite other commenters.
7. Delete temp files. Run `state_manager.py update-diversity` only for drafts the user says they posted.
