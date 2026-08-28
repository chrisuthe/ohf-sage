# Sage Review Benchmark Harness — Design

**Date:** 2026-07-30
**Status:** Draft (pending spec review)
**Builds on:** the OHF Sage pipeline; informs the delivery-path decision in
[Copilot review integration](2026-07-30-copilot-review-integration-design.md).

## Purpose

Turn the "augment Copilot (server-free) vs. native Sage-in-CI" decision into **numbers
instead of arguments**, by measuring how well a Sage-driven review reproduces the project
leads' *actual* review judgments — and, critically, **how much of that quality depends on the
live corpus retrieval** (the one capability you can't have server-free).

The corpus IS the ground truth: it is the leads' real review comments, each with a permalink.
So the benchmark is a **backtest** — run the reviewer on historical diffs the leads commented
on, and score whether it independently raises the same issue, with a real citation, without
inventing noise.

The key experimental lever:

```
Config A: reviewer with the distilled principles only (corpus retrieval OFF)
Config B: reviewer with principles + real lexical retrieval over the corpus (search.py)
```

`recall(B) − recall(A)` is the **measured value of the corpus retrieval** — precisely what a
server (MCP) or the native path buys over the server-free Copilot ceiling. If Config A clears
the bar on its own, ship server-free and never build retrieval infra.

## Why this is measurable server-free

The reviewer-under-test is the **native Sage agent run headless** (single-shot Claude API
call), NOT Copilot. That's deliberate: the native agent is trivially scriptable over N
historical diffs (minutes), whereas Copilot's reviewer only runs on real github.com PRs.
Config A (principles only, no retrieval) is a faithful proxy for the *content ceiling* of a
server-free Copilot skill — so we measure the ceiling without any Copilot plumbing. (Copilot's
own invocation/rendering non-determinism is a separate, smaller effect, measured later only if
Config A's content proves good enough to bother wiring into Copilot.)

## Non-Goals

- Not benchmarking Copilot's live reviewer via github.com (deferred; the native agent is the
  cheap proxy for the content ceiling).
- Not a pass/fail merge gate. It produces numbers; the maintainer sets the bar.
- Not prompt-injection testing (historical MA diffs are trusted input).
- Not a model sweep (single, configurable model in v1).
- No LLM in CI — this is a **local maintainer tool** run with an `ANTHROPIC_API_KEY`.

## Test set

Built from the existing corpus + `gh`, cached to `benchmark/testset.json` (deterministic given
a seed), so scoring runs don't re-hit GitHub.

### Positive cases (recall) — target ~40

A lead flagged a specific issue; a good reviewer should catch it.

- Select corpus records that are: `is_authority` (marcelveldt / MarvinSchenkel),
  `is_substantive`, and **line-anchored review comments** (so a `diff_hunk` exists). Stratify
  across repos (server-heavy is expected — that's the domain). Seeded sample.
- For each, re-fetch via `gh api repos/{repo}/pulls/comments/{id}` (id parsed from `html_url`'s
  `#discussion_r<id>`) → `diff_hunk`, `path`, `commit_id`, `line`, `body` (the ground-truth
  issue).
- The **diff under review** = the PR's patch for that `path`
  (`gh api repos/{repo}/pulls/{n}/files`, take the `patch` for the commented file). Falls back
  to the `diff_hunk` if the file patch can't be fetched.

### Clean cases (precision / noise) — target ~25

Changes that shipped with no lead objection; a good reviewer shouldn't invent hard problems.

- Sample **merged** PRs where no lead left a substantive review comment (exclude any PR in the
  positive set). Take one changed-file patch per PR.
- Caveat (documented): "merged, no lead comment" ≠ "flawless" — a lead may simply not have
  reviewed it. So the clean set measures *does it manufacture hard problems on shipped code*,
  a noise proxy, not ground-truth perfection.

### Leakage guards

- **Config B** excludes the test case's own corpus record (by `html_url`) from the search
  index, so retrieval can't echo the answer.
- Documented in-sample caveat: distilled rules were mined from these PRs, so Config A may
  "know" a topic. That is partly *intended* (a rule generalizing to a new instance is a win),
  but to keep it honest, prefer positive cases **not** among the PRs a directly-matching rule
  cites where determinable.
- **Stretch (optional):** a temporal-holdout set — freshly harvest lead comments from PRs
  newer than the corpus cutoff — as a leak-free set. Not required for v1.

## Components (all under `ohf_principles/benchmark/`)

### 1. `testset.py`

- `build_testset(corpus_paths, n_pos, n_clean, seed) -> dict` — samples + fetches as above,
  returns `{positives: [...], cleans: [...]}` where each case carries `repo`, `pr`, `path`,
  `diff`, and (positives) `ground_truth_comment` + `html_url`.
- `main()` writes `benchmark/testset.json`. Reuses `search._iter_records`, `records.is_authority`
  / `is_substantive`, `github.gh_api_json` / `gh_api_items`.

### 2. `reviewer.py` — the reviewer under test

- `build_review_system_prompt() -> str` — the Sage behavior for benchmarking: the template's
  protocol + authority-weighting + output contract + the spliced `principles.md`, **minus** the
  "Retrieving from review history" grep section (retrieval is handled by config, not an
  in-prompt tool), **plus** a strict JSON output contract. Reuses `build_agent`'s splice with a
  benchmark template variant.
- `review(diff, config, corpus_paths=None, exclude_url=None, model=...) -> list[Finding]` —
  one Claude API call. `Finding = {severity: CRITICAL|PROBLEM|SUGGESTION, issue, principle,
  citation_url}`.
  - **Config A:** user message = the diff.
  - **Config B:** user message = the diff + "Relevant precedents from review history:" + top-5
    `search.search(corpus_paths, query=diff-derived terms, top=5)` with `exclude_url` filtered
    out (author, `html_url`, ≤160-char snippet each).
  - **Config C (optional diagnostic):** inject the `ground_truth_comment` itself — an upper
    bound isolating corpus *coverage* + reviewer skill from retrieval *quality*.
- Malformed (non-JSON) output → one retry, then record as `malformed` (counts against
  grounding).

### 3. `judge.py` — scoring

- `judge_recall(ground_truth_comment, findings, model) -> {verdict: hit|partial|miss, why}` —
  Claude judge: did the reviewer independently raise the same concern the lead raised?
- `check_citation(finding, principles_text, corpus_urls) -> bool` — **deterministic**: is
  `citation_url` a real permalink present in `principles.md` or the corpus?
- `judge_grounding(finding, model) -> {verdict: grounded|weak|ungrounded}` — is the cited
  principle topically relevant to the flagged issue? (Only run when `check_citation` passes; a
  fabricated/absent URL is `ungrounded` outright.)
- Judge model defaults to the strongest available (Opus). v1 = single judge; note variance;
  optional 3-sample majority for borderline recall verdicts.

### 4. `run.py` — orchestrator + scorecard

- Loads `testset.json`, runs A/B (and C if enabled) over all cases concurrently
  (`concurrent.futures`, bounded pool), scores, writes:
  - `benchmark/results/<label>.json` — per-config `{recall, hard_noise_rate, grounding, n}` +
    `delta_recall_B_minus_A` + per-case detail.
  - `benchmark/results/<label>.md` — human-readable table + notable hits/misses/noise for
    spot-checking.
- **Metrics:** `recall = (hits + 0.5·partials)/N_pos`; `hard_noise_rate = (clean cases with ≥1
  CRITICAL/PROBLEM finding)/N_clean`; `grounding = findings with a real, relevant citation /
  all findings`.
- CLI: `python -m ohf_principles.benchmark.run [--label L] [--configs A,B] [--model M]
  [--limit N]`.

### 5. Reporting the decision (documented, not hard-coded)

The report states the three numbers per config and the `B−A` delta. Illustrative reference bar
(NOT mandated): recall ≥ 0.7, hard-noise ≤ 0.1, grounding ≥ 0.9. Interpretation:
- Config A clears the bar → **server-free Copilot skill is sufficient**; no retrieval infra.
- Large `B−A` recall gain → retrieval materially matters → native-CI (no server) or MCP.
- Small `B−A` → retrieval isn't worth the infra; server-free wins.
- (If Config C ≫ B, retrieval *quality* is the bottleneck, not corpus coverage — a signal to
  improve `search.py` / consider semantic retrieval before investing in delivery.)

## Dependencies

- New dev dependency: `anthropic` SDK; `ANTHROPIC_API_KEY` env var. Not added to the shipped
  agent/package runtime — benchmark-only, guarded so `pip install`-for-use is unaffected.
- Reuses: `search.search`, `github._run`/`gh_api_json`/`gh_api_items`/`fetch_file`,
  `records.is_authority`/`is_substantive`, `build_agent`, the corpus, `principles.md`.

## Scale & cost

~65 cases × 2 configs ≈ 130 review calls + ~40 recall-judge + grounding checks. Modest,
parallelizable, run on demand locally. `--limit` for quick smoke runs. Diffs capped in size
(truncate + note) to bound tokens.

## Error Handling & Edge Cases

- Comment 404 / deleted, or unparseable comment id in `html_url` → skip case, log.
- File patch unavailable → fall back to `diff_hunk`; if that's absent too, drop the case.
- Diff exceeds a size cap → truncate to the cap and flag the case as `truncated`.
- Reviewer non-JSON after one retry → `malformed`, excluded from recall denominator but counted
  as a grounding failure and logged.
- Empty corpus for Config B → error clearly (benchmark needs the corpus present).

## Verification (success criteria)

- **testset (unit, mocked gh):** given fixture corpus records + mocked API responses, produces
  the right positive/clean cases with diffs + ground truth; deterministic under a fixed seed.
- **reviewer (unit, mocked API):** builds a valid system prompt; Config B injects top-K and
  **excludes** `exclude_url`; parses well-formed findings; retries then marks malformed.
- **judge (unit):** `check_citation` correct on fixtures (real vs fabricated URL); recall/
  grounding judges parse mocked responses into valid verdicts.
- **run (unit):** metric math correct on a fixture scorecard (`recall`, `hard_noise_rate`,
  `grounding`, `delta`); report renders.
- **smoke (manual, needs key):** `--limit 3` end-to-end produces a scorecard + report.
- Full test suite stays green.

## Build Sequence (high level)

1. `testset.py` (+ tests) → generate and eyeball `benchmark/testset.json`.
2. `reviewer.py` benchmark system-prompt builder + `review()` A/B (+ tests, mocked API).
3. `judge.py` deterministic citation check + recall/grounding judges (+ tests).
4. `run.py` orchestration, metrics, scorecard + report (+ metric-math tests).
5. Smoke run (`--limit`), then a full run; read the numbers; decide delivery path.
