---
description: Ship stickman-render — run the battery, then commit and push only if everything is green.
agent: absolute
---

Ship stickman-render. In order:

1. Read this project's `RULES.md` (binding). If there is no RULES.md, say so and offer `/contract` before shipping.
2. Run the battery if one exists (`/battery`). Anything red -> STOP, report, do not commit.
3. `git status -sb` — review every changed file. No secrets, no build output, no junk.
4. Stage only what belongs in this change. Commit with a real message (what + why, imperative).
5. Push (never force). If rejected: `git pull --rebase`, re-run the battery if it changed, push again once.
6. Refresh `HANDOFF.md` — what landed, what is next.

Report in max 4 lines: verdict, commit hash + subject, push result, next step.
