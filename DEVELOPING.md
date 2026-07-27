# Developing / regenerating the principles

This repo is also the **pipeline** that produces the advisor agent: it mines
Open Home Foundation / Music Assistant PR reviews and rejected feature requests
(plus maintainer-authored docs and tool configs), distills them into a cited,
layered `principles/principles.md`, and builds that into the shipped
`agent/ohf-principles-advisor.md`.

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
    → agent/ohf-principles-advisor.md → install.py
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

### 4. Distill

Run the `distill-principles` skill (`.claude/skills/distill-principles/`) in
Claude Code. It reads `corpus/*.jsonl` (mined) and `corpus/authored/*`
(authoritative), classifies and clusters recurring themes, and writes a cited,
layered `principles/principles.md` where every rule carries a provenance marker
(see the marker legend in [README.md](README.md#understanding-its-answers)).

For a large corpus, chunk the mined records and fan the extraction out across
agents, then synthesize — a single agent can't hold ~10k comments in context.

### 5. Review the principles (required)

`principles/principles.md` is the human checkpoint: read it, correct anything
mis-clustered or mis-marked, drop anything that doesn't match how the leads
actually think. Nothing downstream should ship until this file is reviewed —
it's what goes out to your team and the public.

### 6. Build the agent

```
python scripts/build_agent.py
```

Injects `principles/principles.md` into `agent/ohf-principles-advisor.template.md`
between the `<!-- PRINCIPLES:START -->` / `<!-- PRINCIPLES:END -->` markers,
producing `agent/ohf-principles-advisor.md` — the file people install.

Then install it (see [README.md](README.md#install)).

## Tests

```
python -m pytest -q
```

Covers `scripts/build_agent.py` (marker injection, header stripping) and the
`ohf_principles` package: `config.py` (loading/merging authorities), `records.py`
(authority/substantive filtering, record shaping, reactions), `github.py`
(resolved-thread parsing), and `harvest.py` (rate-limit backoff, partial-failure
containment, authored-file fetch).
