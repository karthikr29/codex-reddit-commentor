# Reddit Commenter Runtime

This folder stores runtime config, personalization profile, tracking logs, and session state for `reddit-commenter-safe`.

## Key Paths

1. Config: `config.yaml`
2. Personalization: `personalization_reddit.md`
3. Subreddits: `subreddits.md`
4. Tracking template: `tracking/reddit/template.md`
5. State: `state/`
6. Automation prompt: `prompts/automation_prompt.md`

## Safety Defaults

1. Daily cap 100
2. Per-session targets: 28, 34, 30, 8 (proportional to session duration)
3. Promotion disabled
4. Approval disabled (always auto mode)
