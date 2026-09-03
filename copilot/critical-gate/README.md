# Critical review gate

Two small workflows that turn a `[CRITICAL]` finding from Copilot's automated review into a real
merge block on `music-assistant/server`: the PR is **converted to a draft** (a draft PR cannot be
merged) with one comment saying why. The intent is to stop still-being-worked-on PRs from sitting
in the "ready to merge" state.

Deterministic glue, **not** a reviewer: it reacts to Copilot's own verdict, it does not judge the
code. No model, no secrets, and it checks out no PR code — it only substring-matches `[CRITICAL]`.

## Why two workflows (the fork-token constraint)

Drafting a PR is a **write**. On a public repo, a `pull_request_review` workflow triggered by a
**fork** PR gets a **read-only** `GITHUB_TOKEN` — GitHub downgrades it exactly as it does for
`pull_request`. (Only `pull_request_target` and `workflow_run` get a write token for fork PRs, and
the "send write tokens to fork PRs" setting is private-repo-only.) A single `pull_request_review`
workflow would therefore silently fail on every external contribution — the very PRs the gate most
needs to cover. So it is split:

| File | Trigger | Token | Role |
|---|---|---|---|
| `critical-gate-detect.yml` | `pull_request_review` | read-only | Scan the review for `[CRITICAL]`; if found, upload the PR number as an artifact. |
| `critical-gate-enforce.yml` | `workflow_run` (after detect) | **read/write** | Download the artifact; convert that PR to a draft + comment. |

`workflow_run` is GitHub's documented pattern for doing trusted writes in response to untrusted
fork activity: it runs in the base-repo context with a write token even when the upstream run was
fork-originated. The PR number is passed via artifact because `workflow_run.pull_requests` is empty
for fork PRs.

## Install

Copy both files to `.github/workflows/` **on the branch PRs target** (`dev` for
`music-assistant/server`). A `pull_request_review` / `workflow_run` workflow only takes effect from
the base branch, so both must be merged there — they will not run from a PR's own head. No secrets,
no PAT: the default `GITHUB_TOKEN` suffices.

**Prerequisite:** Copilot automatic code review must be enabled, so a review is submitted (that
submission fires the detect stage) carrying the `[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy.

## Behaviour

- **Only `[CRITICAL]` gates.** `[PROBLEM]`/`[SUGGESTION]` are left as ordinary review comments.
- **Draft is the whole gate.** No review-state is set (see "Not yet" below), so there is nothing to
  get stuck; the author clears the block themselves by clicking **Ready for review**.
- **False-positive escape hatch:** add the **`override-critical`** label and the gate skips the PR.
  Create that label in the repo (any colour) to make it available.
- **Idempotent:** if the PR is already a draft (already gated, or author-drafted), enforce does
  nothing — it won't re-post.
- **Paginated detection:** the review's inline comments are read across all pages, so a `[CRITICAL]`
  beyond the first 30 comments is not missed.

## Not yet (deferred by design)

- **A "changes requested" review + its lifecycle.** `dev`'s ruleset requires an approving review and
  has `dismiss_stale_reviews_on_push: false`, so a bot request-changes review would persist and keep
  the PR blocked after the author re-readies — nothing the author does (resolving threads, pushing a
  fix, a fresh clean Copilot review by a *different* bot identity) dismisses it. Adding the review
  state safely means also building an auto-dismiss step (dismiss the bot's stale review on a later
  clean review). Draft-only avoids that entirely for now.
