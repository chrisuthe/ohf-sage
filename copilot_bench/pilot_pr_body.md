# What does this implement/fix?

Adds a manual, opt-in pilot of an **Automated PR Review** bot. It checks a pull request against the
project's established coding standards — distilled from this repo's own review history and its
`AGENTS.md` / `copilot-instructions.md` / pre-commit config — and posts findings as a review, each
linking where the standard is documented.

The intent is to evaluate **replacing / augmenting the current Copilot code review** with a
reviewer grounded in the project's own on-record standards.

**This is a draft pilot — not for merge.** The goal is to run it manually against a few existing
PRs and see the output first.

**Related issue (if applicable):**

- n/a (pilot / evaluation)

## Types of changes

- [ ] Bugfix (non-breaking change which fixes an issue) — `bugfix`
- [ ] New feature (non-breaking change which adds functionality) — `new-feature`
- [ ] Enhancement to an existing feature — `enhancement`
- [ ] New music/player/metadata/plugin provider — `new-provider`
- [ ] Breaking change — `breaking-change`
- [ ] Refactor (no behaviour change) — `refactor`
- [ ] Documentation only — `documentation`
- [ ] Maintenance / chore — `maintenance`
- [x] CI / workflow change — `ci`
- [ ] Dependencies bump — `dependencies`

## How it works

- **Manual only** (`workflow_dispatch`): *Actions → Automated PR Review (manual) → Run workflow →*
  a PR number. No automatic triggers in this pilot.
- Runs the **GitHub Copilot CLI** inside Actions as a full-attention agent that greps the project's
  review history for precedents. Inference is billed to the **org's Copilot plan** via
  `permissions: copilot-requests: write` (the built-in Actions token) — **no personal Copilot
  seat / PAT**.
- Posts a structured review as **`musicassistant-bot[bot]`**, **advisory only** (never a merge
  gate). Findings map to the existing `[CRITICAL]/[PROBLEM]/[SUGGESTION]` taxonomy and deliberately
  skip anything pre-commit/CI already catches.

## Files

- `.github/workflows/automated-pr-review.yml` — the manual workflow
- `.github/scripts/post_pr_review.py` — renders findings into a posted review

## Prerequisites to actually run it

- The org needs a **Copilot plan with AI-credit budget** and the **coding-agent / CLI policy
  enabled** (for `copilot-requests` billing).
- Reuses the existing `MUSIC_ASSISTANT_BOT_CLIENT_ID` / `MUSIC_ASSISTANT_BOT_PRIVATE_KEY` for the
  bot identity — **no new secrets**.

## Checklist

- [x] The code change is tested and works locally.
- [x] `pre-commit run --all-files` passes.
- [x] `pytest` passes, and tests have been added/updated under `tests/` where applicable.
- [x] For changes to shared models, the companion PR in `music-assistant/models` is linked.
- [x] For changes affecting the UI, the companion PR in `music-assistant/frontend` is linked.
- [x] I have read and complied with the project's [AI Policy](https://github.com/music-assistant/.github/blob/main/AI_POLICY.md) for any AI-assisted contributions.
- [x] I have raised a PR against the documentation repository targeting the main or beta branch as appropriate.

<sub>(CI-only change: no library code, shared-model, UI, or docs changes — the conditional items above are vacuously satisfied.)</sub>
