# CI Auto-Refresh + Release Distribution — Design

**Date:** 2026-07-30
**Status:** Approved (pending spec review)
**Builds on:** [OHF Sage](2026-07-26-ohf-principles-advisor-design.md) through [global install](../plans/2026-07-27-attested-manual-additions.md)

## Purpose

Keep the published OHF Sage current so downloaders always get the latest corpus/agent,
**without** compromising the pipeline's two integrity properties: the deterministic corpus
can refresh automatically, but the LLM-distilled principles keep their human-review gate.

**Chosen shape (from brainstorming):**
- **Corpus auto-refreshes on a schedule** (deterministic, no LLM); **principles re-distill
  is a local, human-driven step** (full extract→synthesize→critic orchestration + review).
- **All CI-produced changes land via a reviewable PR** (the corpus refresh's PR carries a
  small stats manifest, not a 6 MB blob).
- **Distribution moves to GitHub Release assets** so frequent corpus refreshes don't bloat
  git history.

## Non-Goals

- No Claude / LLM in CI (no `ANTHROPIC_API_KEY` secret). The distillation stays local.
- CI does not auto-merge or push principles to `master`.
- Not re-mining authored docs/tool configs on the schedule (they change rarely; refreshed
  with the local principles pass).

## The integrity split

| Half | Nature | Where it runs |
|---|---|---|
| harvest → `corpus` → manifest | deterministic, cheap | **CI** (scheduled) |
| distill → `principles.md` | LLM, non-deterministic, needs review | **local** (maintainer) |
| `build_agent` (embed principles) | deterministic | both |

## Distribution → GitHub Release assets

- **Un-track the shipped corpus:** `git rm --cached agent/ohf-sage-corpus.jsonl` and add it
  to `.gitignore`. Future refreshes never touch git history. (History keeps the already-
  committed copies; that bloat is already paid once.)
- The **`latest` Release** carries two assets: `ohf-sage.md` and `ohf-sage-corpus.jsonl`.
- `agent/ohf-sage.md` stays committed too — it's small, human-readable, and it's what a
  principles-refresh PR diff shows.
- **`scripts/install.py --from-release`:** downloads both assets from the latest Release
  over plain HTTPS (stdlib `urllib.request` on
  `https://github.com/chrisuthe/ohf-sage/releases/latest/download/<asset>`) into the target's
  `.claude/agents/`, honoring `--local-exclude`. Public release assets need **no `gh` and no
  auth**, so any user can use it. The existing local-clone install path is unchanged;
  without `--from-release` and without a local corpus file, it installs the agent only (as
  today).
- README/INSTALL: the `curl` / no-clone install points at
  `https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage.md` (and the
  corpus); `install.py --from-release` documented as the easy "get the latest" path.

## Components

### 1. `scripts/build_manifest.py` — the reviewable stats file

- `build_manifest(corpus_glob, now) -> dict` — reads `corpus/*.jsonl`, returns
  `{"generated": <ISO date>, "total": N, "repos": {repo: count, …}}` (sorted repos).
  `now` is injected (an ISO string) so it's testable/deterministic.
- `main()` writes `corpus-manifest.json` (pretty-printed, stable key order) and prints the
  total.
- `corpus-manifest.json` is **committed** — it's the small diff the refresh PR carries
  ("server 6268 → 6300"). It is the human-visible signal of what a refresh changed.

### 2. `scripts/install.py` — `--from-release`

- New flag `--from-release` (optionally `--release-repo`, default `chrisuthe/ohf-sage`).
  When set, before copying, download `ohf-sage.md` + `ohf-sage-corpus.jsonl` from the latest
  release into a temp dir and install those (instead of the local `agent/` files). Reuse the
  existing copy + `add_local_exclude` logic. Reports what it fetched.
- Uses `gh release download` (the repo already depends on `gh`). Errors (no release / no gh)
  are reported plainly, not fatal-with-traceback.

### 3. `.github/workflows/refresh.yml` — scheduled corpus refresh

Trigger: `schedule` (weekly cron, e.g. Monday 06:00 UTC) + `workflow_dispatch` (manual, with
an optional `review_limit` input). Permissions: `contents: write`, `pull-requests: write`.

Steps:
1. `actions/checkout`.
2. `actions/setup-python` (3.11) + `pip install -e .`.
3. **Paced harvest** — run the sequential/spaced harvest (one repo at a time, brief sleeps)
   with `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` and a modest `--review-limit`, to stay under
   GitHub's secondary rate limits. Reuse the shipped harvest CLI.
4. `python scripts/build_corpus.py` → `agent/ohf-sage-corpus.jsonl`.
5. `python scripts/build_manifest.py` → `corpus-manifest.json`.
6. `python scripts/build_agent.py` → `agent/ohf-sage.md` (unchanged unless principles
   changed; rebuilt for a consistent release bundle).
7. **Publish a prerelease** (tag `corpus-<run-date>`, `--prerelease`) with the corpus + agent
   assets and the stat deltas in the notes (`gh release create`).
8. **Open a PR** via `peter-evans/create-pull-request` whose only committed change is
   `corpus-manifest.json`, body summarizing per-repo deltas and linking the prerelease for a
   spot-check. Branch e.g. `corpus-refresh/<date>`.

If the manifest is unchanged (no new authority comments), skip the PR/prerelease (nothing to
ship) and log it.

### 4. `.github/workflows/publish.yml` — promote on merge

Trigger: `push` to `master` whose changed files include `corpus-manifest.json` (i.e., a
refresh PR merged). Permissions: `contents: write`.

Steps: find the newest `corpus-*` prerelease and **promote it to the published `latest`
release** (`gh release edit <tag> --prerelease=false --latest`). The exact reviewed assets
become `latest`; nothing is rebuilt or re-harvested.

### 5. Principles refresh — local, documented (`DEVELOPING.md`)

A **"Refreshing the principles"** section: (a) re-harvest, (b) run the full distillation
(chunk the corpus, extract→synthesize→critic — the orchestrated flow, not a bare skill
call), (c) human-review `principles/principles.md`, (d) `build_agent.py`, (e) open a PR.
On merge, the next scheduled `refresh.yml` (or a manual dispatch) rebuilds the agent into the
release bundle. No Claude in CI.

## Error Handling & Edge Cases

- **Harvest rate-limited in CI:** the paced/sequential approach + `_run`'s backoff absorb
  transient limits; a repo that still fails is skipped (its prior corpus lines are retained
  only if we re-harvest incrementally — for v1 the refresh is a full re-harvest, so a failed
  repo means its section is missing that run; the manifest delta makes this visible and the
  next run recovers).
- **No changes since last run:** manifest identical → no PR, no prerelease.
- **`--from-release` with no published release yet:** report it; fall back to local/agent-only.
- **Secrets:** only the built-in `GITHUB_TOKEN` (read public repos, write PRs/releases in
  this repo). No third-party secret.
- **Prerelease cleanup:** promoting `latest` leaves old `corpus-*` prereleases; a retention
  note (keep last N) is a nice-to-have, not required for v1.

## Verification (success criteria)

- **build_manifest (unit):** given sample corpus files, returns correct per-repo counts +
  total; `now` is reflected; output JSON has stable key order. `corpus-manifest.json` written
  by `main()` round-trips.
- **install --from-release (integration):** `python scripts/install.py <tmp> --from-release`
  against the real repo's latest release downloads both assets into `<tmp>/.claude/agents/`
  over HTTPS (run once a release exists). The URL-building + graceful "download failed /
  no release" handling is unit-tested (with the network call stubbed) so it doesn't require a
  live release to verify the logic.
- **refresh.yml (dry validation):** the workflow is syntactically valid and, on a manual
  dispatch with a tiny `--review-limit`, produces a `corpus-manifest.json` diff + a
  prerelease with both assets + a manifest PR. (First real run is the acceptance test.)
- **publish.yml:** merging a manifest change promotes the matching prerelease to `latest`
  (verified on the first real cycle).
- **docs:** README/INSTALL show the release-URL install + `--from-release`; DEVELOPING has
  the local principles-refresh section.

## Build Sequence (high level)

1. `scripts/build_manifest.py` (+ unit tests) and generate the initial `corpus-manifest.json`.
2. `.gitignore` + `git rm --cached agent/ohf-sage-corpus.jsonl` (un-track the shipped corpus).
3. `scripts/install.py --from-release` (+ tests for arg wiring / graceful no-release).
4. `.github/workflows/refresh.yml` + `.github/workflows/publish.yml`.
5. README/INSTALL/DEVELOPING updates (release-URL install, `--from-release`, local principles
   refresh).
6. Controller: `yamllint`/`actionlint` the workflows; cut an initial `latest` Release with the
   current corpus + agent so `--from-release` works immediately; a manual `workflow_dispatch`
   dry run; final review; PR.
