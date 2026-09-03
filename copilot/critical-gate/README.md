# Critical review gate

A tiny, **deterministic** GitHub Actions workflow that turns a `[CRITICAL]` finding from
Copilot's automated review into a real merge block. When Copilot posts a review containing a
`[CRITICAL]` item, it:

1. **converts the PR to a draft** — a draft PR *cannot* be merged (the hard gate), and
2. **submits a request-changes review** whose body explains that it did so and why.

The intent: stop still-being-worked-on PRs from sitting in the "ready to merge" state.

## How this differs from `../cli-reviewer/`

| | `cli-reviewer/` | `critical-gate/` (this) |
|---|---|---|
| What it is | A full LLM reviewer (greps the mined corpus, cites leads) | Glue that reacts to Copilot's *own* review |
| Determinism | Non-deterministic (a model) — **advisory only** | Deterministic (a substring match) — safe to **enforce** |
| Reviews the code? | Yes | No — it only reads Copilot's verdict |
| Cost | Copilot AI credits + Actions minutes | A few seconds of Actions minutes |

They compose: the `[CRITICAL]` taxonomy this gate keys on is produced by Copilot's *native*
review under our instruction shards (`music-assistant-standards.instructions.md` et al.). This
gate is only the enforcement layer on top of that verdict.

## Install

Copy `critical-gate.yml` to `.github/workflows/critical-gate.yml` **on the branch PRs target**
(for `music-assistant/server` that is `dev`). A `pull_request_review` workflow only takes effect
from the base branch, so it must be merged there — it will not run from a PR's own head.

No secrets, no PAT: it uses the default `GITHUB_TOKEN` with `pull-requests: write`.

**Prerequisite:** Copilot automatic code review must be enabled on the repo, so a review is
actually *submitted* (that submission is what fires the workflow) and carries the
`[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy.

## Behaviour & tuning

- **Only `[CRITICAL]` gates.** `[PROBLEM]`/`[SUGGESTION]` are left as ordinary review comments.
- **Draft = hard block; request-changes = soft signal.** A draft PR can't be merged at all. The
  request-changes review is the visible "why" and, if branch protection requires review approval /
  resolved conversations, an additional gate — otherwise it's advisory. You control that via branch
  protection.
- **False-positive escape hatch:** add the **`override-critical`** label to a PR and the gate
  skips it. Create that label in the repo (any colour) if you want it available.
- **Idempotent:** if the PR is already a draft (already gated, or author-drafted), the gate does
  nothing — it won't re-post.

## Why `pull_request_review`

`pull_request` workflows get a **read-only** token for PRs from forks, so they can't draft a PR or
post a review — which is exactly why `cli-reviewer` warns about forks. `pull_request_review` is a
*trusted* event that runs in the base repo with a **writable** token even for fork PRs, so this
gate covers outside contributions too. It is safe to trust here because it **checks out no PR code**
and only substring-matches `[CRITICAL]` — none of the code-execution surface that makes trusted
events risky.

## Not in v1 (deliberately)

- **Auto-recovery.** When the author fixes the issue and Copilot's next review is clean, the gate
  does nothing — un-drafting stays a human "Ready for review" action, so a re-fired critical can't
  fight the author. To auto-clear the stale request-changes review, enable **"Dismiss stale pull
  request approvals when new commits are pushed"** in branch protection, or add a follow-up step
  that dismisses the bot's prior review on a clean re-review.
