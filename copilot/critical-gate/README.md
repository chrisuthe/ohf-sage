# Critical review gate

Two small workflows that turn a `[CRITICAL]` finding from Copilot's automated review into a real
merge block on `music-assistant/server`: the PR is **converted to a draft** (a draft PR cannot be
merged) with one comment saying why. The intent is to stop still-being-worked-on PRs from sitting
in the "ready to merge" state.

Deterministic glue, **not** a reviewer: it reacts to Copilot's own verdict, it does not judge the
code. No model, no secrets, and it checks out no PR code.

## Why two workflows (the fork-token constraint)

Drafting a PR is a **write**. On a public repo, a `pull_request_review` workflow triggered by a
**fork** PR gets a **read-only** `GITHUB_TOKEN` — GitHub downgrades it exactly as for
`pull_request`, and the same fork also runs its own copy of the workflow. So a single
`pull_request_review` workflow could neither write nor be trusted. It is split:

| File | Trigger | Token | Role |
|---|---|---|---|
| `critical-gate-detect.yml` | `pull_request_review` | read-only, untrusted | Scan the review for `[CRITICAL]`; if found, upload a bare **hint** artifact. |
| `critical-gate-enforce.yml` | `workflow_run` (after detect) | **read/write**, trusted | Resolve the PR from the trusted `head_sha`, re-verify the finding, draft + comment. |

`workflow_run` is GitHub's documented pattern for trusted writes in response to untrusted fork
activity: it runs in the base-repo context with a write token even when the upstream run was
fork-originated.

## Security: nothing from detect is trusted

Because a fork PR runs its own copy of `critical-gate-detect.yml`, its output is attacker-controlled.
So enforce treats the artifact as a mere **existence hint** ("worth checking") and **re-derives every
fact**:

- The PR is resolved from **`workflow_run.head_sha`** — which GitHub stamps on the event and a fork
  cannot forge — via `listPullRequestsAssociatedWithCommit`, filtered to open PRs whose current head
  still equals that SHA. This mirrors the repo's own `dependency-security-report.yml`.
- The `[CRITICAL]` finding is **re-checked** against that PR's latest Copilot review (paginated). A
  forged or absent artifact can therefore only make enforce do nothing — never draft a victim PR.

## Install

Copy both files to `.github/workflows/` **on the branch PRs target** (`dev` for
`music-assistant/server`). `pull_request_review` / `workflow_run` workflows only take effect from
the base branch, so both must be merged there. No secrets, no PAT: the default `GITHUB_TOKEN`
suffices.

**Prerequisite:** Copilot automatic code review must be enabled, so a review is submitted (that
submission fires detect) carrying the `[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy.

## Behaviour

- **Only `[CRITICAL]` gates.** `[PROBLEM]`/`[SUGGESTION]` are left as ordinary review comments.
- **Draft is the gate.** No review-state is set (see "Not yet"), so there is nothing to get stuck;
  the author clears the draft themselves via **Ready for review**.
- **Head-checked:** enforce only acts if the PR's current head still equals the reviewed `head_sha`,
  so it won't draft a commit the author has already fixed and re-pushed.
- **Idempotent:** the draft happens only if the PR isn't already one, and the explanation carries a
  hidden marker so it's posted at most once — even across reruns.
- **False-positive escape hatch:** add the **`override-critical`** label and the gate skips the PR.
  Create that label in the repo (any colour) to make it available.
- **Paginated detection:** review comments are read across all pages, so a `[CRITICAL]` beyond the
  first 30 comments is not missed.

## Not yet (deferred by design)

- **A durable gate.** A draft PR can be re-readied by its author, so draft alone is a soft signal,
  not an unbypassable block. The durable version is a **required commit status** that stays failing
  until the finding is resolved or `override-critical` is applied — the same mechanism the repo's
  `Dependency Security Review` uses — which additionally requires adding that status to the branch
  ruleset's required checks.
- **A request-changes review + its dismissal lifecycle.** `dev`'s ruleset has
  `dismiss_stale_reviews_on_push: false`, so a bot request-changes review would persist and keep the
  PR blocked after the author re-readies; adding it safely means also auto-dismissing the stale
  review on a later clean review.
