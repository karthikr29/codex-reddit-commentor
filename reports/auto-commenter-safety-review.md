# Auto-Commenter Safety Review

Date: 2026-02-08
Source reviewed: `/tmp/auto-commenter`

## Scope

One-time safety review of workflow, credential handling assumptions, posting behavior, style risks, and moderation exposure before Codex-skill conversion.

## Findings

### High Risk

1. High-volume automation can trigger platform anti-spam systems when comments are frequent or repetitive.
2. Batch workflows can run long and create pattern-like behavior if delays are too short.
3. Auto-posting without strong quality checks can produce tone mismatch and moderator reports.

### Medium Risk

1. Candidate generation without hard style gating can produce AI-like phrasing.
2. Missing duplicate-post checks can lead to same-day repeat comments on same post.
3. Lack of session overlap lock can produce accidental concurrent posting.

### Low Risk

1. Workflow documentation was clear on login requirement but did not define credential storage contract.
2. Tracking templates existed but did not include all quality and gate metadata needed for audits.

## Controls Implemented in Converted Skill

1. No credential capture. No prompts for email/password/OTP.
2. Login-session-only operation in Playwright browser.
3. Daily/session limits with hard caps.
4. Randomized delays between comments.
5. Rate-limit pause and retry budget with stop condition.
6. Duplicate-post prevention via commented URL state.
7. Session lock to prevent overlap.
8. Strict style hard blocks: no em dash, no semicolon, banned phrase filters.
9. Candidate ranking contract: 10-12 -> top 3 -> best 1 after fit checks.
10. Approval ramp disabled; always auto mode when checks pass.
11. Promotion disabled by policy.

## Residual Risks

1. Platform policy enforcement can still change without notice.
2. High daily cap remains riskier than low-volume manual activity.
3. Human-like output cannot be guaranteed in every context, so continuous monitoring is required.

## Recommendation

Keep monitoring account health signals and tighten caps immediately if rate-limit or moderation flags increase.
