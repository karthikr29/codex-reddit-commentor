---
name: reddit-commenter-claude
description: Reddit comment drafting from a pasted page. The user pastes the full Reddit thread text, the skill extracts the post, author, votes and comments, then recommends one top-level comment plus 1-3 replies to existing comments. NEVER posts. The user posts everything by hand.
---

# Reddit Commenter (Claude Code Edition)

## Overview

The user copies an entire Reddit thread page and pastes it into chat. Parse it, run the candidate pipeline (10-12 candidates, scoring, style guard), and hand back exactly what to paste and where. No browser, no Playwright, no posting.

## NEVER AUTO-POST (hard rule)

1. Never post, reply, vote, or type into Reddit. Never open Reddit in a browser or Playwright.
2. The only input is the page text the user pastes. The only output is drafts the user posts by hand.
3. Never ask whether to post, and never ask for a URL. If the paste is missing something (like comments), work with what is there and say what was missing in one line.

## Temporary File Management

- **Storage:** ALL temporary files (thread_context.json, candidates, digests) MUST be stored in `runtime/reddit-commenter/state/tmp/`.
- **Cleanup:** Delete the temp files created for this thread once the output is delivered.

## Comment Structure Variety

Every batch of candidates MUST use varied structures. Use these 8 opener types:

| Opener | Example Start | When to Use |
|--------|--------------|-------------|
| one-liner | "sellotape", "the refund button" | Punchy or witty answer, especially "what's your best/worst X" threads |
| question | "Have you tried...", "What if..." | When post invites discussion |
| agreement | "Yeah", "Agreed", "Same" | When OP makes a valid point |
| counterpoint | "Actually", "Honestly", "Not sure about that" | When offering alternative view |
| anecdote | "I tried this...", "I built..." | ONLY when sharing a fact from `personal_facts.md` |
| fact | "Most X tend to...", "One thing about..." | When adding objective context |
| opinion | "I think", "IMO", "Personally" | When sharing a take |
| direct | Jump straight to the point | Default for concise replies |

### One-liner rules

1. Every top-level batch MUST include 2-3 one-liners (12 words or fewer). Skip them only in serious threads (grief, crisis, layoffs, health) where a joke would land badly.
2. A one-liner can be a joke, a dry observation, or a one-phrase answer. It must read obviously as a joke or a take, never as a made-up factual claim about the user's life.
3. A real detail from `personal_facts.md` squeezed into one line is the best kind of one-liner.
4. The scorer undervalues very short comments, so the best one-liner that passes style guard ALWAYS goes into the top 3 for the final pick.

### Punch (the most important writing rule)

Punch comes from short sentences, not low word count. Copy this rhythm:
"Yeah, life is messy for them right now. That explains the 180. It does not explain covering up work they didn't do."

1. **Sentences of 12 words or fewer.** Most should be 3-8 words. Never string clauses together with commas.
2. **One idea per comment.** No "here's the advice, here's how, here's why" chains.
3. **Cut pass:** after writing each candidate, delete the weakest sentence or clause. If it still works, it stays deleted. Repeat once.
4. **No explanation tails:** because, which means, so that, in order to, that way. State it and stop.
5. **Say it with confidence.** Take a side. "That's a trust problem" beats "that could be seen as a trust issue".
6. **Pictures beat abstractions.** Use a concrete image from the OP's world (casino vs a stall in the lobby, shop window vs slot machine) instead of an abstract reframe.

### Sound like a person, not a copywriter

Before writing, read the real comments in the paste. Copy how those people type: their slang, their punctuation, how messy they are. Every thread is different, so don't use a fixed word list. Pick up whatever's current and make stuff up if it fits.

Write each comment as one loose thought, the way you'd say it out loud. Stuff like "i mean", "tho", "kinda", "cuz", "lol" is fine when it fits naturally. Lowercase is fine. Skipping the last period is fine.

Don't write slogans. No matched pairs like "X first, Y second" or "your X isn't their Y". No trying to end on a mic drop every time.

Short still matters. One or two sentences. Just don't polish them.

Serious threads: plain and kind, no slang.

Check before picking: would a guy type this on his phone without thinking twice? If it sounds written, it's wrong.

### Length and shape

1. One-liners: 12 words or fewer.
2. Everything else: 2-4 short sentences, 45 words max.
3. At least half of every batch is 20 words or fewer.
4. One paragraph. No bullet lists, no headers, no colon-led openers ("One thing that helps:").
5. Avoid starting more than 2-3 candidates with "I".

### Register (context-aware, all cards on the table)

Match the thread and subreddit, then commit:
- **Blunt:** hard calls, managers/sales/business threads ("Cut your losses.")
- **Sarcastic / dry:** when OP or the thread is being ridiculous
- **Mild swearing:** casual subs and threads that already swear ("that's a dealbreaker tbh", "yeah that's fucked")
- **Funny:** light threads, "best/worst X" questions
- **Warm and plain:** grief, layoffs, health, crisis. No jokes, no sarcasm, no swearing.

The goal is upvotes, replies that start conversations, reach, and karma. Write the comment people upvote and argue with, not the safe one.

See `references/punch_examples.md` before generating.

## Inputs

1. Pasted page text from the user (the whole Reddit thread copied from the browser).
2. Runtime root: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter`
3. Scripts: `skills/reddit-commenter-claude/scripts/`

## Required Workflow

### Step 0: Load Context

1. Read `runtime/reddit-commenter/personalization_reddit.md`.
2. Read `runtime/reddit-commenter/personal_facts.md`.
3. Read `skills/reddit-commenter-claude/references/punch_examples.md`.

### Step 1: Extract the Thread

Parse the pasted text and write `state/tmp/thread_context.json`:

- **Post:** subreddit, title, body, author (OP username), age, upvotes, comment count, flair
- **Comments:** for each comment: author, text, upvotes, age, reply count, depth (top-level or reply to whom), and whether the author is OP

Pasted Reddit pages include UI noise (Reply, Share, Award, "Sort by", sidebar, ads, "more replies"). Drop it. If upvotes or ages are not in the paste, leave them null. Never guess numbers.

### Step 2: Analyze

1. Write the comments array to `state/tmp/thread_comments.json` and run `python3 skills/reddit-commenter-claude/scripts/thread_analyzer.py analyze --input runtime/reddit-commenter/state/tmp/thread_comments.json --output runtime/reddit-commenter/state/tmp/thread_digest.json`.
2. Run `python3 skills/reddit-commenter-claude/scripts/diversity_tracker.py --runtime-root runtime/reddit-commenter guidance` and save to `state/tmp/guidance.json`.

### Step 3: Top-Level Comment

1. **Generate 10-12 candidates** using:
   - Post intent and subreddit tone
   - Thread digest, so candidates say something the thread has not said
   - Diversity guidance
   - Personalization profile and personal fact bank
   - Opener, one-liner, punch, length, and register rules above. Run the cut pass on every candidate before scoring.
   - **CRITICAL STYLE RULE: NEVER use em dashes (—) or en dashes (–). Never use semicolons (;). These are hard blocks.**
   - **CRITICAL ANTI-FABRICATION RULE: NEVER invent personal stories, team experiences, company names, job titles, or events. All personal references MUST come from `personal_facts.md`. Never reference anything (a comment, a detail, a plan) that is not in the pasted page.**
   - **Reply approach (prefer higher tiers):**
     1. Practical suggestion the reader can act on
     2. Sharp perspective or take the thread has not heard
     3. One-liner (joke or punchy answer)
     4. Genuine question that adds to the discussion
     5. Personal fact from the fact bank (ONLY when directly relevant)
2. **Score:** save `{"post": {...}, "candidates": [...]}` to `state/tmp/candidates_top.json` and run `python3 skills/reddit-commenter-claude/scripts/score_candidates.py --input runtime/reddit-commenter/state/tmp/candidates_top.json --thread-digest runtime/reddit-commenter/state/tmp/thread_digest.json --diversity-guidance runtime/reddit-commenter/state/tmp/guidance.json`. Add `--weights-file runtime/reddit-commenter/state/subreddit_profiles.json` if it exists.
3. **Shortlist top 3** (always including the best passing one-liner). Pick the best 1 on judgment: which one gets upvoted and replied to in THIS thread. Punch and fit beat raw score. Scores within ~3 points are a tie.
   **Pre-pick check (reject the candidate if any of these fail):**
   - Template leftovers or placeholders ("Handmade X near me")
   - Invented specifics not in the paste (a mug when OP never named their craft)
   - If a candidate is funnier and another tells OP what to do, try merging them into 2-3 short sentences and score the merge.

   **Aggression check (the pick must pass this too):**
   - Be aggressive and confident. Write like a sharp guy who clearly writes well and is pushing OP forward, not a polite advisor.
   - Calling OP out is fine ("Honestly you're projecting. Your addiction is not their addiction."). Don't soften it.
   - Blunt, punchy endings are good ("Show the work. Then get off."). Don't reject a line for sounding harsh.
   - If the pick reads careful, neutral, or old-fashioned, swap it for the boldest candidate that still fits the thread.
   - Serious threads (grief, layoffs, health, crisis) stay warm and plain. No aggression there.
4. **Style guard:** `python3 skills/reddit-commenter-claude/scripts/style_guard.py --text "<text>" --suggest-fix`. If rejected but `pre_rejection_score > 45`, run `rewrite_guide.py guide`, write 3 variants, re-validate, keep the best passing one. Max 1 retry.

### Step 4: Replies to Existing Comments

1. **Pick 0-3 comments to reply to.** Only reply when the reply earns it:
   - It adds one point on top of what they said
   - It corrects something wrong or off in the comment
   - It answers a question OP or a commenter asked
   Prefer OP's comments, then high-upvote or active comments. Skip hostile, deleted, or heavily replied comments, and anything that would repeat the top-level comment. **If no comment is worth replying to, skip replies entirely and say "No replies worth it" in one line.**
   Before skipping an agreeable comment, try one angle that ties it back to OP's real concern ("They're not policing others. They're scared of feeding the thing they're quitting."). Skip only if that angle doesn't work either.
2. For each chosen comment, generate 5-6 candidates with the same punch, length, and register rules. Replies are never longer than top-level comments. Score them with `score_candidates.py`, using `{"post": {"subreddit": ..., "title": <post title>, "body": <parent comment text>}, "candidates": [...]}`.
3. Style-guard the winner the same way as Step 3.

### Step 5: Output

Always show the full work. The user compares candidate sets across models, so never show only the winner.

**Thread:** r/sub · u/OP · "title" · upvotes · N comments · age (skip any value not in the paste)

**Comments found:** one line each: u/author · upvotes · gist in 8 words or fewer. Max 10 lines. Say how many more there are if you cut the list.

**COMMENT ON THE POST: all candidates, best to worst**

| Rank | Candidate | Type | Words | Score |
|------|-----------|------|-------|-------|

List EVERY candidate, sorted by score, highest first. Mark the top 3 with ⭐. If the final pick is not rank 1, say why in the Why line.

**Top 3:** the three shortlisted candidates, best first, each in its own code block (one unbroken line).

**Pick:** rank number + one-line why.

**REPLY TO u/author** (their comment starts: "first few words..."):
Same ranked table with every reply candidate, top 3 marked, top 3 in code blocks, then Pick + one-line why.

Repeat the reply section for each chosen comment (max 3). No blockquotes.

### Step 6: Cleanup and Tracking

1. Delete the temp files for this thread from `runtime/reddit-commenter/state/tmp/`.
2. When the user confirms they posted a draft, run `python3 skills/reddit-commenter-claude/scripts/state_manager.py --runtime-root runtime/reddit-commenter update-diversity --text-file <file with that text>` so future batches stay varied.

## Non-Negotiable Guardrails

1. NEVER post, reply, vote, or open Reddit. Drafts only.
2. Never collect, request, or persist Reddit credentials.
3. Enforce no em dash and no semicolon in final comments.
4. Enforce banned AI-phrasing rules in `references/style_rules.md`.
5. Never fabricate personal stories, team experiences, company names, job titles, or thread details. Personal references come only from `personal_facts.md`.
6. One-liners are jokes or takes, never false claims presented as the user's real experience.
7. No promotion while `promotion_policy` is `none`.

## Scripts

### Used in this workflow

1. `scripts/style_guard.py`: hard-style compliance checks. Supports `--suggest-fix`.
2. `scripts/score_candidates.py`: scores candidates on intent, tone, specificity, naturalness, safety, novelty, diversity.
3. `scripts/thread_analyzer.py`: covered topics and gaps in existing comments.
4. `scripts/diversity_tracker.py`: structural pattern guidance.
5. `scripts/rewrite_guide.py`: rewrite instructions for style guard failures.
6. `scripts/state_manager.py`: diversity fingerprints (`update-diversity`).

### Not used (need a browser or auto-posting)

`harvest_feedback.py`, `health_check.py`, `error_classifier.py`, `post_scorer.py`, `schedule_optimizer.py`, `weight_optimizer.py`, `analytics_generator.py`.

## References

1. `references/workflow.md`: short version of this workflow.
2. `references/style_rules.md`: strict human-writing constraints and banned patterns.
3. `references/safety.md`: no-posting rule and account safety.

## Runtime Files

1. Personalization: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/personalization_reddit.md`
2. Personal fact bank: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/personal_facts.md`
3. State folder: `/Users/karthikr/Documents/AI/Projects/auto-commentor/runtime/reddit-commenter/state`
