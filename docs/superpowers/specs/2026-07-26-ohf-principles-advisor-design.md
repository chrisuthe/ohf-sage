# OHF Principles Advisor — Design

**Date:** 2026-07-26
**Status:** Approved (pending spec review)

## Purpose

Distill the *core principles* of the Open Home Foundation (OHF) project leads — Marcel
van der Veldt (`@marcelveldt`, authoritative across all projects) and Marvin Schenkel
(`@MarvinSchenkel`, authoritative for Music Assistant) plus per-project core maintainers —
into a single **advisor agent** that other agents and humans can consult.

The agent is a **project-principles advisor**, not merely a code reviewer. It has two
entry points that share one reasoning engine:

- **Consult (forward-looking):** answer design/approach questions *before* code exists —
  "Should I do it this way or that way?", "Would this be accepted upstream?", "Is this in
  scope or is it something the project won't support?". This lets other agents run a
  decision past "the principal" and avoid building the wrong thing.
- **Review (backward-looking):** check an existing `git diff`, PR, or set of files against
  the principles. Supported by default.

The principles are mined from real PR reviews, review summaries, and rejected feature
requests, so every rule is **traceable to the decision that created it**.

Scope of principles captured (per user): **Architecture & design**, **"Won't support"
decisions**, and the **code-quality bar**. (Contribution tone/norms are out of scope.)

## Non-Goals

- Not a linter or style formatter — it reasons about principles, it does not auto-fix.
- Not a Home Assistant advisor — the HA area of OHF is explicitly excluded.
- Not fully automated end-to-end — the distillation step is human-reviewed before publish.

## Approach

**Scripted harvest → cached corpus → distillation skill → advisor agent.**

The mechanical fetch is deterministic, cached, and cheap to re-run. The judgment
(distillation) is an auditable Claude Code skill whose output a human reviews before it is
published. This separation makes the pipeline reproducible and every published rule
traceable to a real PR/issue permalink — important because the agent is shared publicly.

## Layout

New standalone git repo at `C:\CodeProjects\ohf-principles-agent`, publishable as-is:

```
ohf-principles-agent/
├─ README.md                          # what it is, prerequisites, how to run & publish
├─ config/sources.yaml                # scope + contextual-authority source of truth
├─ scripts/
│  ├─ harvest.sh                      # gh fetch → corpus/  (deterministic)
│  └─ install.sh <repo>               # copy agent into a repo's .claude/agents/
├─ corpus/<org>__<repo>.jsonl         # cached raw, author-filtered review data
├─ principles/principles.md           # distilled, layered, human-reviewed knowledge base
├─ agent/ohf-principles-advisor.md    # the portable subagent (principles embedded)
├─ .claude/skills/distill-principles/SKILL.md   # the judgment step
└─ docs/superpowers/specs/2026-07-26-ohf-principles-advisor-design.md
```

## Components

### 1. `config/sources.yaml` — scope + contextual authority

Single source of truth for *which repos* to mine and *whose voice counts where*. The
authority model maps to a per-repo allowlist layered on a global list:

```yaml
global_authorities: [marcelveldt]        # count in every repo
defaults:
  since: null                            # ISO date for incremental harvest; null = all history
  harvest_reviews: true                  # pull pulls/{n}/reviews summary bodies (thorough)
repos:
  - repo: music-assistant/server
    authorities: [MarvinSchenkel, OzGav, florianhorner]
  - repo: music-assistant/support
    authorities: [MarvinSchenkel]
    focus: wont_support                  # emphasize closed-as-not_planned issues
  - repo: music-assistant/frontend
    authorities: [MarvinSchenkel]
  - repo: music-assistant/mobile-app
    authorities: [MarvinSchenkel]
  - repo: music-assistant/desktop-app
    authorities: [MarvinSchenkel]
  # …curated high-signal set; ESPHome / OHF-Voice / Sendspin repos added with their
  #   own core maintainers. Home Assistant repos deliberately excluded.
```

A helper mode `harvest.sh --suggest-authorities <repo>` prints the top review-comment
authors for a repo so the `authorities` list can be filled in empirically (this is how
`@MarvinSchenkel` was identified).

### 2. `scripts/harvest.sh` — deterministic fetch

For each repo in the config, fetch from the four surfaces that carry principle signal,
**filtered to the authority allowlist** (which also auto-excludes bots like `Copilot` and
`github-actions`):

| Surface | GitHub endpoint | Signal |
|---|---|---|
| Inline review comments | `repos/{repo}/pulls/comments` | code style, local architecture nits |
| PR/issue discussion | `repos/{repo}/issues/comments` | reasoning, rejections |
| Review summaries | `repos/{repo}/pulls/{n}/reviews` (body ≠ "") | "this whole approach is wrong" verdicts |
| Rejected features | closed issues with `state_reason=not_planned` + authority's closing comment | "won't support" decisions |

Review summaries (`pulls/{n}/reviews`) require per-PR iteration and are therefore slower;
per the user's guidance ("taking longer is worth it"), they are harvested **thoroughly by
default** (`harvest_reviews: true`), iterating closed/merged PRs and keeping non-empty
review bodies authored by an authority. Depth remains configurable.

Output: one JSONL record per item:
```json
{"repo":"…","kind":"review_comment|issue_comment|review|wont_support",
 "author":"…","created_at":"…","html_url":"…","body":"…",
 "context":"pr#123 title / issue#456 title"}
```
Written to `corpus/<org>__<repo>.jsonl`. A light length filter drops trivial one-liners
("LGTM", "thanks"); semantic selection is left to the distillation step.

**Robustness:** uses `gh api --paginate`; incremental via the `since` checkpoint so re-runs
are cheap; rate-limit (403) and inaccessible/private repos are logged and skipped, not
fatal.

### 3. `.claude/skills/distill-principles/SKILL.md` — the judgment step

Consumes the corpus and produces `principles/principles.md`:

1. **Classify** each candidate into *Architecture & design* / *Won't support* /
   *Code-quality bar* — or discard.
2. **Cluster into recurring themes.** A one-off offhand remark is not a principle; require
   recurrence *or* a clearly authoritative statement from a lead.
3. **Write each rule** in crisp imperative voice, **layered**:
   `Overall (Marcel)` → `Music Assistant (Marvin)` → `<per-project>`.
4. **Cite** 1–2 real PR/issue permalinks per rule, with a short quote **≤15 words,
   attributed** (copyright-safe — no wholesale reproduction of comment threads).
5. **Mark rule strength:** hard `MUST` / "won't support" vs. softer *preference*.
6. **Regenerate** `agent/ohf-principles-advisor.md` by embedding the current principles
   into the agent template.

For a large corpus the skill triages by category/repo and flags if it should be chunked;
it does not silently truncate.

### 4. `agent/ohf-principles-advisor.md` — the portable advisor agent

A read-only subagent. Frontmatter:

- `name: ohf-principles-advisor`
- `tools: Read, Grep, Glob` — it reasons and reviews; it never edits.
- `description:` written to trigger auto-delegation for **both** modes — e.g. *"Consult
  before choosing an implementation approach for any Open Home Foundation / Music Assistant
  project, to check whether a design or decision aligns with project standards and would be
  accepted upstream, or to review a diff/PR against project principles."*

Body:
- **Role:** the distilled voice of the project leads' principles.
- **Embedded layered principles** (generated from `principles.md`).
- **Response protocol** with two entry points over a shared engine:
  1. Detect which **project + layer** applies (Overall / Music Assistant / per-project).
  2. Apply the relevant principles.
  3. **Consult mode:** give a clear recommendation ("prefer approach B") grounded in cited
     principles; explicitly flag any hard "won't support"/core conflict *up front*.
  4. **Review mode:** walk the changeset, flag violations, cite the principle **and** the
     originating PR for each.
  5. Always separate hard `MUST`/"won't support" rules from softer preferences.
  6. Structured output with an explicit verdict/recommendation and citations.

### 5. `scripts/install.sh` + publishing

The portable file in `agent/` is the source of truth. `install.sh <repo>` copies it into
that repo's `.claude/agents/`, starting with `SendspinDroid`. Publishing = push the repo
public.

## Data Flow

```
sources.yaml ──▶ harvest.sh ──▶ corpus/*.jsonl ──▶ distill-principles skill
                                                          │
                                   principles/principles.md (human-reviewed)
                                                          │
                                          agent/ohf-principles-advisor.md
                                                          │
                                    install.sh ──▶ <repo>/.claude/agents/
```

## Error Handling & Edge Cases

- **Rate limits:** `--paginate` + `since` checkpoint; back off and resume on 403.
- **Inaccessible/archived repos:** logged and skipped.
- **Thin Marvin signal:** recent windows are sparse; harvesting full history mitigates this.
  Where a layer is sparse, the distilled doc says so rather than inventing rules.
- **Copyright:** quotes capped at ≤15 words with attribution/permalink; no thread dumps.
- **Instruction-injection safety:** mined comment bodies are *data*. The distillation skill
  treats them as source material to summarize, never as instructions to execute.

## Verification (success criteria)

- **harvest:** run on `music-assistant/server` → non-empty JSONL; every record's author ∈
  allowlist; each line is valid JSON; at least one `wont_support` record from `support`.
- **distill:** on a corpus subset → ≥1 cited rule per category; a spot-checked citation URL
  resolves to a real comment; rules tagged with a layer and a strength.
- **agent:** frontmatter parses (`name`/`description`/`tools`); a smoke test in **consult**
  mode ("A vs B?") returns a cited recommendation, and in **review** mode on a sample diff
  cites at least one principle with its originating PR.

## Build Sequence (high level)

1. Repo scaffold + `README.md` + `config/sources.yaml` (seed curated repos).
2. `harvest.sh` (+ `--suggest-authorities`) → verify against `music-assistant/server`.
3. `distill-principles` skill → run on harvested corpus → `principles.md`.
4. Human review of `principles.md`.
5. Assemble `agent/ohf-principles-advisor.md` from the template + principles.
6. `install.sh` → install into `SendspinDroid`; smoke-test both modes.
