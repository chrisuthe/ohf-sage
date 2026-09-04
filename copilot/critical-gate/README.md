# Critical review gate

A single scheduled workflow that turns a `[CRITICAL]` finding from Copilot's automated review into a
real merge block on `music-assistant/server`: every ~10 minutes it scans open non-draft PRs and
**converts to a draft** (a draft PR cannot be merged) any whose latest Copilot review still carries
an unresolved `[CRITICAL]`, leaving one explanatory comment. The intent is to keep
still-being-worked-on PRs out of the "ready to merge" state.

Deterministic glue, **not** a reviewer: it reacts to Copilot's own verdict, it does not judge the
code.

## Why a poller (and not an event trigger)

The obvious design — trigger on `pull_request_review` when Copilot posts a review — does not work:
**GitHub holds workflow runs triggered by a bot/app actor (which is what Copilot submitting a review
is) for manual approval.** They sit at `action_required` and never execute, so the gate never fires
— even for same-repo PRs, with no owner bypass. A poller avoids this because a `schedule` run
executes as a trusted actor. That single choice also sidesteps two other walls the event design hit:

- **Fork tokens** — a `pull_request_review` run on a fork PR gets a read-only token, so it cannot
  draft anything. A scheduled run is base-context and keeps its write token.
- **Artifact trust** — the two-stage `workflow_run` workaround had to pass the PR across a trust
  boundary. The poller reads everything first-hand, so there is nothing to forge.

## Install

Copy `critical-gate-poll.yml` to `.github/workflows/critical-gate-poll.yml` on the default branch
(`dev` for `music-assistant/server`) — scheduled workflows run from the default branch. No secrets,
no PAT: the default `GITHUB_TOKEN` with `pull-requests: write` suffices.

**Prerequisite:** Copilot automatic code review must be enabled, so reviews carrying the
`[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy exist to scan.

## Behaviour

- **Only `[CRITICAL]` gates.** `[PROBLEM]`/`[SUGGESTION]` are ignored.
- **Scoped to mergeable bases** (`dev`, `stable`).
- **Unresolved findings only:** it gates on **unresolved, non-outdated** Copilot `[CRITICAL]` review
  *threads* (queried via GraphQL), so a resolved critical — or one whose code the author has since
  changed — no longer gates. The review summary body is ignored (it has no resolved state to clear).
- **Draft first, fail closed:** the draft (the gate) happens before the comment, and a failure fails
  the run rather than leaving a PR silently ungated.
- **Idempotent & self-repairing:** the draft happens only if the PR isn't already one; the
  explanation carries a hidden marker so it is posted at most once, and a later poll re-posts it if
  an earlier run drafted the PR but failed to comment.
- **More persistent than a one-shot:** because it re-scans every ~10 min, a PR re-readied by its
  author while a `[CRITICAL]` is still unresolved is drafted again on the next pass.
- **False-positive escape hatch:** add the **`override-critical`** label and the gate skips the PR.
  Create that label in the repo (any colour) to make it available.
- **Test it:** the workflow also has a `workflow_dispatch` trigger — run it manually (a human actor,
  no approval) to exercise it immediately.

## Not yet (deferred by design)

- **A durable required-status gate.** A draft can be re-readied, so it is a soft (if self-healing)
  signal, not an unbypassable block. The durable version is a required commit status that stays
  failing until the finding is resolved or `override-critical` is applied — the mechanism the repo's
  `Dependency Security Review` uses — which additionally needs that status added to the branch
  ruleset's required checks.
