# RAG Retrieval Mode — Design

**Date:** 2026-07-27
**Status:** Approved (pending spec review)
**Builds on:** [OHF Sage](2026-07-26-ohf-principles-advisor-design.md) + [enrichment](2026-07-27-principles-enrichment-authored-sources-design.md)

## Purpose

Give OHF Sage reach beyond its 91 distilled rules by letting it — and the user —
retrieve the **actual review comments** behind the principles. Distillation is
lossy by design; the long tail (a real, relevant maintainer comment with no
corresponding distilled rule) is currently invisible. RAG mode surfaces it.

**Chosen shape: hybrid lexical retrieval, two consumers.**
- **Hybrid** — the 91 curated rules stay primary; corpus retrieval is a *fallback*
  for novel/long-tail questions, never a replacement.
- **Lexical** — retrieval is grep-based, not embeddings-based, so OHF Sage stays a
  drop-in file. The paraphrase-robustness that embeddings would provide instead
  comes from the LLM expanding the query into domain vocabulary before grepping.
- **Two consumers** — the **agent** uses retrieval to answer with evidence, and a
  standalone **`search` CLI** lets the user query the corpus directly.

## Non-Goals

- Not semantic/vector retrieval (no embeddings, no vector store, no MCP). That
  would make OHF Sage a setup-required tool; explicitly rejected in favor of the
  portable drop-in model. May be revisited as an optional power-user add-on later.
- Not live GitHub search at query time (the agent has no network/Bash).
- Retrieval does not override or re-rank the curated rules; it only adds long-tail
  coverage when no rule applies.

## The load-bearing constraint

OHF Sage's tools are `Read, Grep, Glob` — read-only, no Bash, no embedding model.
So at query time it can only grep local files. Two consequences the design is
built around:

1. **The corpus must be a local file** the agent can grep — shipped alongside the
   agent, not fetched.
2. **Grep it by explicit path.** The corpus lives in a gitignored `.claude/` dir
   (the `--local-exclude` feature), and ripgrep skips gitignored files during
   *directory traversal* — but searches a path given *explicitly*. Verified:
   `rg -i "event loop" corpus/…jsonl` returns matches even though the file is
   gitignored. The agent protocol must target the corpus path explicitly, never a
   project-wide search.

## Architecture

```
corpus/*.jsonl (local harvest cache, gitignored)
      │  scripts/build_corpus.py  (merge)
      ▼
agent/ohf-sage-corpus.jsonl  (committed, ~6 MB, all ~10.5k records)
      │  install.py copies alongside the agent
      ▼
<repo>/.claude/agents/ohf-sage-corpus.jsonl   ← agent greps this by explicit path
      ▲
      │  python -m ohf_principles.search "<query>"   (human side, over local corpus)
```

## Components

### 1. `scripts/build_corpus.py` — the shipped artifact

Merges every `corpus/*.jsonl` into a single committed
`agent/ohf-sage-corpus.jsonl` (one record per line, unmodified — **all records,
full bodies, max recall** per the chosen compaction level). Deterministic;
regenerated after each harvest. Prints the record count written.

### 2. `.gitignore`

Keep `corpus/` ignored (local harvest cache), but the merged
`agent/ohf-sage-corpus.jsonl` is **committed** so clone / `curl` / install all
receive it. (Add an explicit un-ignore only if a broader ignore rule would catch
it; today `corpus/` is the only relevant rule and `agent/` is not ignored.)

### 3. `scripts/install.py` — ship the corpus with the agent

- Copies **both** `agent/ohf-sage.md` and `agent/ohf-sage-corpus.jsonl` into
  `<repo>/.claude/agents/`.
- `--local-exclude` excludes **both** installed files from the target repo's git.
- New `--no-corpus` flag: install the agent only (rules-only, no retrieval
  fallback). Default is to ship the corpus.
- Existing `install(agent_path, repo_dir)` behavior for the agent file is
  preserved; corpus copy is additive.

### 4. Agent retrieval protocol (`agent/ohf-sage.template.md`)

Add a **retrieval fallback** step to the response protocol and a short section
documenting the corpus (path + record schema). Behavior:

1. Answer from the embedded rules first (unchanged). If a rule covers the
   question, cite it — done.
2. **Only if no rule applies** (a novel/long-tail question): expand the question
   into ~5–15 domain keywords / a regex alternation, then **grep
   `.claude/agents/ohf-sage-corpus.jsonl` by that explicit path** (case-insensitive).
3. Rank the matching records by: query-term overlap, then author authority
   (`marcelveldt` / `MarvinSchenkel` highest), then `reactions.plus`.
4. Present the top few **real comments** with their `html_url`, clearly labeled
   *"from review history (not a distilled rule)"* — quote ≤15 words each. If
   nothing relevant matches, say so; never fabricate a rule.

The corpus record schema (documented for the agent): `{repo, kind, author,
created_at, html_url, context, body, reactions:{plus,total}, adopted}`.

### 5. `ohf_principles/search.py` — standalone human search

- `score(record: dict, terms: list[str]) -> float` — pure, testable ranking:
  term-overlap count in `body` (case-insensitive) + an authority bonus
  (`marcelveldt`/`MarvinSchenkel` > other authors) + a small `reactions.plus`
  bonus. Records with zero term hits score 0 (excluded).
- `search(corpus_paths, query, repo=None, author=None, top=10) -> list[dict]` —
  tokenizes the query, scores every record, filters by optional `repo`/`author`,
  returns the top-N.
- `main()` — CLI `python -m ohf_principles.search "<query>" [--repo R]
  [--author A] [--top N] [--corpus <glob>]`, printing rank, author, `html_url`,
  and a body snippet per hit. Defaults corpus to `corpus/*.jsonl`.

### 6. Docs

- **README.md** (`Using it`): note the agent's retrieval fallback (it will cite
  real comments when no rule applies) and add a short **"Searching the review
  history"** subsection for the `search` CLI. Mention the ~6 MB corpus footprint
  and `--no-corpus`.
- **DEVELOPING.md**: add the `build_corpus.py` step to the flow (after harvest,
  before/with build_agent) and document the shipped artifact.

## Two retrieval implementations (by necessity)

The **CLI ranks in code** (`score`, deterministic). The **agent ranks via its own
reasoning** over grep output (it has no Bash to call the CLI — only Grep/Read).
They share the same *intent* and heuristic but not code; this is inherent to the
portable-agent model, documented so it isn't mistaken for a shortcut.

## Footprint

~6 MB committed to the repo and copied into each install's `.claude/agents/`. It
is **data grepped on demand, never auto-loaded into context**, so it adds disk,
not tokens. `--no-corpus` opts out.

## Error Handling & Edge Cases

- Missing corpus file at query time (e.g. `--no-corpus` install): the agent's
  grep finds nothing → it says the review history isn't available and answers from
  rules only. The CLI errors clearly if no corpus files match.
- Gitignored corpus: agent must grep by explicit path (see constraint above);
  documented in the protocol.
- Copyright: retrieved snippets follow the same ≤15-word attributed-quote rule as
  distilled rules; the agent links to the permalink for full context.
- Injection: corpus bodies are DATA to summarize, never instructions (same as the
  distill skill) — reinforced in the agent protocol.

## Verification (success criteria)

- **build_corpus:** produces `agent/ohf-sage-corpus.jsonl` with a line count equal
  to the sum of `corpus/*.jsonl`; every line is valid JSON.
- **search CLI / `score`:** unit tests — a query term present in a body scores > 0;
  a leads' comment outranks a non-lead comment with equal term hits; zero-hit
  records are excluded; `--repo`/`--author` filters apply. A real run
  (`search "event loop"`) returns relevant server comments with permalinks.
- **install:** ships both files; `--local-exclude` excludes both; `--no-corpus`
  installs only the agent. (unit/integration test)
- **agent (smoke):** given a novel question not covered by the 91 rules, OHF Sage
  greps the corpus by explicit path, cites ≥1 real comment with its permalink
  labeled as retrieved (not a rule); given a rule-covered question, it still leads
  with the rule.

## Build Sequence (high level)

1. `build_corpus.py` + `.gitignore` handling (+ verify merged artifact).
2. `search.py` `score`/`search`/CLI (+ unit tests + real run).
3. `install.py` corpus shipping + `--no-corpus` (+ tests).
4. Agent template retrieval protocol + corpus schema docs.
5. README + DEVELOPING updates.
6. Generate the shipped corpus, rebuild the agent, install into `server`, smoke-test
   both modes, final review.
