# What does this implement/fix?

Adds a manual, opt-in pilot of an **Automated PR Review** bot. It checks a pull request against the
project's established coding standards — distilled from this repo's own review history and its
`AGENTS.md` / `copilot-instructions.md` / pre-commit config — and posts findings as a review, each
linking where the standard is documented.

The intent is to evaluate **replacing / augmenting the current Copilot code review** with a
reviewer grounded in the project's own on-record standards.

## How it works

- **Manual only** (`workflow_dispatch`): *Actions → Automated PR Review (manual) → Run workflow →* a
  PR number. No automatic triggers in this pilot.
- **Everything it needs is bundled in-repo** under `.github/pr-review/` — no external downloads:
  - `standards.md` — the coding standards + review protocol it checks against.
  - `review-corpus.jsonl.gz` (~1.2 MB) — a compressed, greppable index of past **public** PR/issue
    review discussions, used only as a fallback to cite a prior decision when the standards don't
    cover something. Decompressed at run time.
- Runs the **GitHub Copilot CLI** in Actions as a full-attention agent (read + grep only — no write,
  no network). Inference bills to the **org Copilot plan** via `permissions: copilot-requests: write`
  — no personal Copilot seat / PAT.
- Posts a structured review as **`musicassistant-bot[bot]`**, **advisory only** (never a merge gate).
  Findings use the existing `[CRITICAL]/[PROBLEM]/[SUGGESTION]` taxonomy and deliberately skip
  anything pre-commit/CI already catches.

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


## Checklist

- [x] The code change is tested and works locally.
- [x] `pre-commit run --all-files` passes.
- [x] `pytest` passes, and tests have been added/updated under `tests/` where applicable.
- [x] For changes to shared models, the companion PR in `music-assistant/models` is linked.
- [x] For changes affecting the UI, the companion PR in `music-assistant/frontend` is linked.
- [x] I have read and complied with the project's [AI Policy](https://github.com/music-assistant/.github/blob/main/AI_POLICY.md) for any AI-assisted contributions.
- [x] I have raised a PR against the documentation repository targeting the main or beta branch as appropriate.

<sub>(CI-only change: no library code, shared-model, UI, or docs changes — the conditional items above are vacuously satisfied.)</sub>
