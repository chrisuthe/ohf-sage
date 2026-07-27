# Principles Enrichment + Authored Sources — Design

**Date:** 2026-07-27
**Status:** Approved (pending spec review)
**Builds on:** [OHF Principles Advisor](2026-07-26-ohf-principles-advisor-design.md)

## Purpose

Expand the OHF Principles Advisor's basis of knowledge in two ways:

1. **Enrichment (weighting):** capture *endorsement* (comment reactions) and, optionally,
   *adoption* (resolved review threads) so each distilled rule can carry a visible
   confidence signal instead of every rule looking equally certain.
2. **Authored sources:** ingest the maintainers' own hand-written guidance — instruction
   markdowns (`AGENTS.md`, `.github/copilot-instructions.md`, `CONTRIBUTING.md`) and tool
   configs (`ruff`/`mypy`/`pre-commit`) — as **authoritative** input. These are the leads
   having already distilled their own principles ("we repeat this too often"), so they are
   the highest-trust signal available and bypass the recurrence threshold.

The output gains a **visible provenance/confidence marker** on every rule.

## Non-Goals

- Not mining new repos (that's the separate "widen repos" idea).
- Not building retrieval/RAG over the full corpus (separate idea).
- Not a self-improving feedback loop.
- `--with-threads` adoption detection is opt-in, not the default.

## Provenance & Confidence Markers

Every rule in `principles/principles.md` ends with a concise marker:

| Marker | Meaning |
|---|---|
| `[authored]` | Stated in a maintainer-written doc (`AGENTS.md`, `copilot-instructions.md`, `CONTRIBUTING.md`) |
| `[enforced]` | Codified in tooling (`ruff` / `mypy` / `pre-commit`) |
| `[authored+mined]` | A doc states it **and** reviews repeat it — highest confidence, corroborated |
| `[mined · N PRs]` / `[mined · N PRs · 👍]` | From reviews only; N = distinct PRs/issues; 👍 appended when maintainers reacted positively |

**Trust rules:**
- `[authored]` and `[enforced]` are authoritative: a single statement becomes a rule (no ≥2 recurrence needed).
- `[mined]` rules still require recurrence across ≥2 PRs **or** a lead statement, as today.
- When an authored rule and a mined cluster express the same principle, they **merge** into one `[authored+mined]` rule — never double-listed.

## Architecture

Two new signal paths join the existing harvest → distill → build flow:

```
sources.yaml (repos + authorities + authored_docs + config_files)
        │
   harvest.py ──▶ corpus/<repo>.jsonl          (mined comments + reactions [+ adopted])
        └───────▶ corpus/authored/<repo>__<file> (raw authored docs + tool configs)
        │
 distill-principles workflow
   ├─ extract (mined)    → candidates w/ reaction/adoption signal
   └─ extract (authored) → authoritative candidates tagged authored/enforced
        │
   synthesize ──▶ principles/principles.md  (merged, deduped, marker per rule)
        │
   build_agent.py ──▶ agent/ohf-principles-advisor.md
```

## Components

### 1. `config/sources.yaml`

Add global defaults + per-repo overrides:

```yaml
defaults:
  # …existing…
  with_threads: false                      # opt-in adoption (resolved-thread) detection
  authored_docs:                           # tried in every repo; 404s skipped
    - AGENTS.md
    - .github/copilot-instructions.md
    - CONTRIBUTING.md
  config_files:
    - pyproject.toml                        # [tool.ruff], [tool.mypy]
    - .pre-commit-config.yaml
```

Per-repo `authored_docs` / `config_files` may override the defaults. A missing file is a
skip, not an error (only `server` has `AGENTS.md`; only `desktop-app` has `CONTRIBUTING.md`).

### 2. `ohf_principles/records.py`

- `shape_record(...)` gains an optional `reactions` field: a compact `{"plus": int, "total": int}`
  extracted from the GitHub payload's `reactions` object (default `{"plus":0,"total":0}` when absent).
- Optional `adopted: bool | None` field (None unless `--with-threads` populated it).
- Existing keys and filtering behavior are unchanged; the two new keys are additive.

### 3. `ohf_principles/github.py`

- `fetch_review_comments` / `fetch_issue_comments`: unchanged calls, but the raw dicts already
  carry `reactions` — the shaping layer keeps it.
- New `fetch_file(repo, path) -> str | None`: `gh api repos/{repo}/contents/{path}` with
  `-H "Accept: application/vnd.github.raw"`; returns the decoded text, or `None` on 404
  (caught, not fatal). Uses the existing rate-limit-aware `_run`.
- New `resolved_comment_urls(repo, pr_numbers) -> set[str]`: a GraphQL query over each PR's
  `reviewThreads` (`isResolved`, thread comment `url`), returning the set of review-comment
  `html_url`s in resolved threads. Only called when `--with-threads`.

### 4. `ohf_principles/harvest.py`

- `harvest_repo`: keep `reactions` on mined records; when `defaults.with_threads`, build the
  resolved-URL set for the PRs that produced authority review comments and set `adopted` on
  those records.
- New `harvest_authored(repo_cfg, config, out_dir)`: fetch each `authored_docs` + `config_files`
  path via `fetch_file`, write present ones to `corpus/authored/<repo>__<file>` (sanitized name).
- `main()`: new `--with-threads` flag (overrides `defaults.with_threads`); authored fetch runs
  as part of the normal per-repo harvest, writing under `<out-dir>/authored/`.

### 5. `.claude/skills/distill-principles/SKILL.md`

- Document the two input streams (mined `corpus/*.jsonl`; authored `corpus/authored/*`).
- Authored/config extraction rules: emit authoritative rules tagged `[authored]`/`[enforced]`,
  cite the file (config rules cite the specific setting and summarize intent, not raw config).
- Mined extraction: carry `reactions`/`adopted` per candidate.
- Synthesis: merge streams, dedupe across them into `[authored+mined]` where they agree,
  compute the marker per rule, and honor the authoritative-bypass rule.

### 6. Distillation workflow

The controller's distillation workflow (used for the actual re-run) adds an **authored extract
phase**: one agent per authored file (there are few — server AGENTS.md/copilot-instructions,
desktop-app CONTRIBUTING, pyproject/pre-commit configs), producing authoritative candidates.
The mined extract phase is unchanged except candidates now include reaction/adoption fields.
Synthesis consumes both candidate sets.

### 7. `agent/ohf-principles-advisor.template.md`

Add one line to the protocol: how to read the provenance markers (`[authored]`/`[enforced]` are
firm project policy; `[mined · N PRs]` is inferred from review history — weight accordingly,
and prefer citing `[authored+mined]` rules when available).

### 8. `README.md`

Document the new config fields, `--with-threads`, the authored-source ingestion, and the marker
legend.

## Config→Prose Translation (the fuzzy part)

Tool configs are summarized for *intent*, not transcribed: e.g. `[tool.ruff] select = [...,"ASYNC",...]`
→ "**MUST** pass the project's ruff lint set, including async-safety checks `[enforced]`"; mypy
`disallow_untyped_defs` → "**MUST** fully type-annotate functions (mypy strict) `[enforced]`".
`[enforced]` rules may be slightly softer/interpretive by nature; acceptable and marked as such.

## Error Handling & Edge Cases

- Missing authored files (most repos lack `AGENTS.md`) → skipped silently, logged at debug.
- `--with-threads` GraphQL failures → logged per-PR and skipped; never abort the harvest
  (same containment discipline as review fetching).
- Reactions absent on a comment → `{"plus":0,"total":0}`; never a boost.
- Copyright: authored docs are the project's own contributor guidance; distilled rules still
  quote ≤15 words where quoting, and cite the file. No wholesale file reproduction in principles.md.
- Instruction-injection: authored docs and configs are DATA to summarize, not instructions to
  execute (same as mined bodies) — reinforced in the skill.

## Verification (success criteria)

- **records:** a fetched review comment with a reaction yields `reactions.plus >= 1` in its record;
  a comment without reactions yields `{"plus":0,"total":0}`. (unit test)
- **fetch_file:** returns `server/AGENTS.md` text; returns `None` for a nonexistent path. (integration)
- **authored harvest:** `corpus/authored/music-assistant__server__AGENTS.md` exists after a run.
- **with_threads (opt-in):** `resolved_comment_urls` returns a non-empty set for a PR known to have
  a resolved authority thread (e.g. server#4460). (integration, opt-in)
- **distill:** the regenerated `principles.md` contains at least one `[authored]` rule traceable to
  `AGENTS.md` (e.g. Sphinx `:param:` docstrings, private-methods-at-bottom), at least one
  `[enforced]` rule, at least one `[authored+mined]` corroboration, and mined rules carry
  `[mined · N PRs]` markers. Every quote still ≤15 words.
- **agent:** rebuilds with the enriched principles; frontmatter intact; a smoke test shows it
  citing an `[authored]` rule and weighting it above a lone `[mined]` preference.

## Build Sequence (high level)

1. `records.py` reactions/adopted fields (+ tests).
2. `github.py` `fetch_file` + `resolved_comment_urls` (+ integration checks).
3. `harvest.py` wiring: reactions kept, `harvest_authored`, `--with-threads` (+ tests/checks).
4. `config/sources.yaml` new fields.
5. `distill-principles` SKILL + agent template + README updates.
6. Distillation workflow: authored extract phase + marker-aware synthesis.
7. Re-harvest + re-distill → **human-review gate** on enriched `principles.md` → rebuild agent →
   update PR / `server` install.
