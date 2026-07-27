# OHF Principles Advisor

A reproducible pipeline that mines Open Home Foundation / Music Assistant PR
reviews and rejected feature requests, distills them into a cited, layered
principles document, and packages the result as a portable Claude Code
subagent.

The shipped agent (`agent/ohf-principles-advisor.md`) has two modes:

- **Consult** — ask it *before* choosing an implementation approach ("should
  I do it this way or that way?", "is this in scope, or something the
  project won't support?").
- **Review** — hand it a diff, PR, or set of files, and it checks the change
  against the same principles, citing the PR/issue each rule came from.

Every rule in `principles/principles.md` is traceable to the real PR review
comment or rejected-issue thread it was mined from — the agent doesn't
invent standards, it applies ones on record.

**Scope:** Music Assistant repositories today (`server`, `support`,
`frontend`, `mobile-app`, `desktop-app`). Other OHF projects (ESPHome,
OHF-Voice, Sendspin) can be added via `config/sources.yaml` once harvested.
**Home Assistant is explicitly out of scope** and will not be added.

## Prerequisites

- [`gh`](https://cli.github.com/) (GitHub CLI), authenticated with at least
  `repo` scope (`gh auth login` / `gh auth status`) — used for every GitHub
  fetch, no direct API tokens needed.
- Python 3.9+ with [`pyyaml`](https://pypi.org/project/PyYAML/) installed.
- `pytest`, if you want to run the test suite (`tests/`).

## Usage

### 1. Configure sources

Edit `config/sources.yaml` to set which repos to harvest and who the
authoritative reviewers are for each (see "Authority model" below).

Configuration fields include:
- `defaults.harvest_reviews` — fetch review summaries (slower, more signal).
- `defaults.review_pr_limit` — number of PRs per authority to scan for reviews.
- `with_threads` — opt-in per-PR GraphQL queries to fetch full discussion threads (slow; off by default).
- `authored_docs` — list of maintainer doc paths (AGENTS.md, CONTRIBUTING.md, copilot-instructions.md, etc.) to fetch as authoritative guidance.
- `config_files` — tool config files (pyproject.toml, .pre-commit-config.yaml, etc.) to extract and treat as project policy.

### 2. Discover authorities for a new repo

Before adding a new repo to `sources.yaml`, find out who actually reviews
there:

```
python -m ohf_principles.harvest --suggest-authorities <owner/repo>
```

This prints logins ranked by review-comment count on that repo, so you can
pick the real core maintainers rather than guessing.

### 3. Harvest

```
python -m ohf_principles.harvest
```

Fetches review comments, issue/PR-thread comments, and (if
`defaults.harvest_reviews` is set) review summaries for every repo in
`config/sources.yaml`, filtered to the configured authorities, and writes
one JSONL file per repo to `corpus/`.

Also fetches **authored sources** (maintainer docs and tool configs from
`config/sources.yaml` entries `authored_docs` and `config_files`) to
`corpus/authored/`, treating them as authoritative project policy.

Useful flags:

- `--with-threads` — fetch full PR discussion threads via GraphQL (opt-in, per-PR query, slower). Off by default.
- `--repo <owner/repo>` — limit the run to one repo (repeatable).
- `--review-limit N` — override `defaults.review_pr_limit`, the number of
  PRs per authority scanned for review summaries (smaller = faster, less
  signal).
- `--config <path>` / `--out-dir <dir>` — override the config file or
  output directory.

A full run hits several GitHub search and REST endpoints per authority per
repo. Pace it (e.g. start with `--review-limit` set low, or harvest one
`--repo` at a time) to avoid tripping GitHub's secondary rate limits; the
harvester retries with backoff on rate-limit errors but a very large,
unpaced run can still get throttled hard.

### 4. Distill

Run the `distill-principles` skill (`.claude/skills/distill-principles/`)
in Claude Code. It reads every `corpus/*.jsonl` file, classifies and
clusters recurring themes, and writes a cited, layered
`principles/principles.md`.

### 5. Review the principles

`principles/principles.md` is the human checkpoint: read it, edit it,
correct anything that got mis-clustered. Nothing downstream should be
trusted until this file has been reviewed.

### 6. Build the agent

```
python scripts/build_agent.py
```

Embeds `principles/principles.md` into
`agent/ohf-principles-advisor.template.md` between the
`<!-- PRINCIPLES:START -->` / `<!-- PRINCIPLES:END -->` markers, producing
`agent/ohf-principles-advisor.md` — the file you actually install.

### 7. Install into a repo

```
python scripts/install.py <repo_dir> [--local-exclude]
```

Copies `agent/ohf-principles-advisor.md` into
`<repo_dir>/.claude/agents/ohf-principles-advisor.md` so Claude Code can
load it as a subagent in that repo.

## Installing into a repo you don't own

If you're installing the advisor into a repo you don't control (a fork, or
someone else's checkout) and don't want the agent file to ever end up
tracked, staged, committed, or accidentally included in a PR, pass
`--local-exclude`:

```
python scripts/install.py <repo_dir> --local-exclude
```

When the target directory has a `.git/info/` directory (i.e. it's a git
repo), this appends the installed agent's repo-relative path (e.g.
`.claude/agents/ohf-principles-advisor.md`) to that repo's
`.git/info/exclude` — the same mechanism as `.gitignore`, but local-only:
it lives inside `.git/`, is never committed, and never shows up in a diff
or PR. The line is only added once (repeat installs are idempotent). If the
target isn't a git repo, `--local-exclude` prints a note and skips the
exclude step without erroring — the copy still happens.

## Authority model

Principle strength depends on who said it:

- **marcelveldt** — authoritative across every OHF project (`global_authorities`
  in `config/sources.yaml`).
- **MarvinSchenkel** — authoritative for Music Assistant specifically.
- Other core maintainers are authoritative per-project (e.g. `OzGav`,
  `florianhorner` for `music-assistant/server`).

Only comments/reviews from these logins are harvested and considered
principle signal; everyone else's feedback is noise for this purpose. The
authority list per repo is set in `config/sources.yaml`, and can be
extended as new projects are onboarded (see `--suggest-authorities` above).

## Provenance markers

Every rule in `principles/principles.md` is marked with exactly one confidence/provenance marker:

- `[authored]` — from a maintainer doc (AGENTS.md, CONTRIBUTING.md, etc.). No recurrence needed; a single statement is a rule.
- `[enforced]` — from a tool config (pyproject.toml, .pre-commit-config.yaml, etc.). Summarizes the *intent*, not raw config. Cites the config file/setting.
- `[authored+mined]` — a doc states it AND reviews repeat it. Merged into ONE rule; not double-listed.
- `[mined · N PRs]` — inferred from review history only; N = distinct PRs/issues in the cluster. Appends ` · 👍` when any contributing comment had positive reactions. Mined rules still require N≥2 or a lead statement.

Strongest to weakest: `[authored]` / `[enforced]` (firm project policy) → `[authored+mined]` → `[mined · N PRs]` (inferred, higher N = firmer).

## Tests

```
python -m pytest -q
```

Covers `scripts/build_agent.py` (marker injection, header stripping) and
the `ohf_principles` package: `config.py` (loading/merging authorities),
`records.py` (authority/substantive filtering, record shaping), and
`harvest.py` (rate-limit retry/backoff, partial-failure handling). See
`tests/` for the current set.
