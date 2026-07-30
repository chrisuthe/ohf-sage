# Developing / regenerating the principles

This repo is also the **pipeline** that produces the advisor agent: it mines
Open Home Foundation / Music Assistant PR reviews and rejected feature requests
(plus maintainer-authored docs and tool configs), distills them into a cited,
layered `principles/principles.md`, and builds that into the shipped
`agent/ohf-sage.md`.

Most people only need to **install and use** the agent — see [README.md](README.md).
This document is for refreshing the principles or mining additional repos.

## Prerequisites

- [`gh`](https://cli.github.com/) (GitHub CLI), authenticated with at least
  `repo` scope (`gh auth login` / `gh auth status`) — used for every GitHub
  fetch, no direct API tokens needed.
- Python 3.9+ with [`pyyaml`](https://pypi.org/project/PyYAML/).
- `pytest`, to run the test suite (`tests/`).

## The flow

```
config/sources.yaml → harvest → corpus/ → distill-principles skill
    → principles/principles.md (human review) → build_agent.py
    → agent/ohf-sage.md → install.py
                       ↓ build_corpus.py
                   agent/ohf-sage-corpus.jsonl
```

### 1. Configure sources

Edit `config/sources.yaml` — which repos to harvest and who the authoritative
reviewers are for each. Fields:

- `global_authorities` — logins authoritative in every repo (e.g. `marcelveldt`).
- per-repo `authorities` — core maintainers for that repo.
- `defaults.harvest_reviews` — fetch review summaries (slower, more signal).
- `defaults.review_pr_limit` — PRs per authority to scan for review summaries.
- `defaults.with_threads` — detect adopted (resolved-thread) review comments via
  GraphQL (opt-in; off by default).
- `authored_docs` — maintainer doc paths (`AGENTS.md`, `.github/copilot-instructions.md`,
  `CONTRIBUTING.md`, …) fetched as authoritative guidance.
- `config_files` — tool configs (`pyproject.toml`, `.pre-commit-config.yaml`, …)
  whose enforced intent becomes project policy.

### 2. Discover authorities for a new repo

```
python -m ohf_principles.harvest --suggest-authorities <owner/repo>
```

Prints logins ranked by review-comment count, so you pick real core maintainers
rather than guessing.

### 3. Harvest

```
python -m ohf_principles.harvest
```

Fetches review comments, issue/PR-thread comments, and (if
`defaults.harvest_reviews`) review summaries for every repo in `sources.yaml`,
filtered to the configured authorities, into one JSONL file per repo under
`corpus/`. Reaction counts ride along on each comment. Also fetches the
**authored sources** (`authored_docs` + `config_files`) to `corpus/authored/`.

Useful flags:

- `--with-threads` — detect adopted (resolved-thread) review comments (opt-in,
  per-PR GraphQL query; off by default).
- `--repo <owner/repo>` — limit to one repo (repeatable).
- `--review-limit N` — override `defaults.review_pr_limit` (smaller = faster).
- `--config <path>` / `--out-dir <dir>` — override config file / output dir.

A full run hits several GitHub search and REST endpoints per authority per repo.
**Pace it** (start with `--review-limit` low, or harvest one `--repo` at a time)
to avoid GitHub's *secondary* rate limits — those are a burst ceiling separate
from the 5000/hr core quota, and the endpoint that reports remaining quota won't
warn you about them. The harvester retries with backoff on rate-limit errors,
but a large unpaced run can still get throttled hard.

### 4. Build the corpus

```
python scripts/build_corpus.py
```

Merges `corpus/*.jsonl` (the harvested review comments) into
`agent/ohf-sage-corpus.jsonl`, which is built locally and shipped via GitHub Releases. This file is used as a
fallback when embedded rules don't cover a question — ohf-sage greps it to find
real review comments.

You can also query the corpus directly with the `search` CLI for ad-hoc queries:

```
python -m ohf_principles.search "<terms>" [--repo <owner/repo>] [--author <login>] [--top N]
```

### 5. Distill

Run the `distill-principles` skill (`.claude/skills/distill-principles/`) in
Claude Code. It reads `corpus/*.jsonl` (mined) and `corpus/authored/*`
(authoritative), classifies and clusters recurring themes, and writes a cited,
layered `principles/principles.md` where every rule carries a provenance marker
(see the marker legend in [README.md](README.md#understanding-its-answers)).

For a large corpus, chunk the mined records and fan the extraction out across
agents, then synthesize — a single agent can't hold ~10k comments in context.

### 5a. Manual overlay (local, per-user)

In addition to the harvested and distilled `principles/principles.md`, ohf-sage
supports a per-user **local overlay** `.claude/agents/ohf-sage-manual.md` (git-excluded)
captured via the `add-manual-principle` skill. This overlay is not harvested, not
part of the shipped corpus, and stays private to your setup. To contribute an
entry to the shared `principles.md` upstream, use `propose-principle-upstream`,
which opens a GitHub issue for maintainer review and publishes the claim publicly
(with explicit confirmation).

### 6. Review the principles (required)

`principles/principles.md` is the human checkpoint: read it, correct anything
mis-clustered or mis-marked, drop anything that doesn't match how the leads
actually think. Nothing downstream should ship until this file is reviewed —
it's what goes out to your team and the public.

### 7. Build the agent

```
python scripts/build_agent.py
```

Injects `principles/principles.md` into `agent/ohf-sage.template.md`
between the `<!-- PRINCIPLES:START -->` / `<!-- PRINCIPLES:END -->` markers,
producing `agent/ohf-sage.md` — the file people install.

Then install it (see [README.md](README.md#install)).

## Staying current

The corpus and principles are refreshed regularly without requiring a new checkout:

**Corpus refresh (automated, weekly via CI):**

- `.github/workflows/refresh.yml` runs weekly on a schedule: it re-harvests from the
  configured repos, rebuilds the corpus, and opens a pull request that touches only
  `corpus-manifest.json` (a timestamp plus per-repo record counts, and the total).
- On merge, `.github/workflows/publish.yml` promotes the prerelease to the `latest`
  Release, making the new corpus available via `--from-release` / `releases/latest/download` URLs.
- Users installing via `--from-release` or the `curl` routes always get the newest corpus
  without needing to re-clone or rebuild locally.

**Principles refresh (local, human-driven):**

- Refreshing the principles is a local step — CI never runs Claude. To update them:
  1. Re-harvest: run `python -m ohf_principles.harvest` to fetch new review comments.
  2. Distill: run the full distillation — chunk the corpus and fan extraction out across
     agents, then synthesize and run a critic pass (a single agent can't hold ~10k comments) —
     then human-review `principles/principles.md`, verify provenance markers, and correct
     any mis-clusters.
  3. Build: run `python scripts/build_agent.py` to inject the updated principles into
     the agent template.
  4. Test & commit: run the test suite, open a PR with the new `principles/principles.md`
     and rebuilt `agent/ohf-sage.md`.
- On merge to `master`, the next automated corpus refresh bundles the new agent into the
  release.

## Tests

```
python -m pytest -q
```

Covers `scripts/build_agent.py` (marker injection, header stripping) and the
`ohf_principles` package: `config.py` (loading/merging authorities), `records.py`
(authority/substantive filtering, record shaping, reactions), `github.py`
(resolved-thread parsing), and `harvest.py` (rate-limit backoff, partial-failure
containment, authored-file fetch).
