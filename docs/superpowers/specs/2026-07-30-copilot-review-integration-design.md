# Copilot Code-Review Integration (Phase 1: static instruction render) — Design

**Date:** 2026-07-30
**Status:** Approved shape (pending spec review)
**Builds on:** [CI auto-refresh + release distribution](2026-07-30-ci-auto-refresh-design.md) and the
OHF Sage agent pipeline it sits in.

## Purpose

Bring OHF Sage's distilled, PR-cited principles into the **GitHub Copilot code-review**
process, so the maintainers' standards are applied to pull requests automatically — starting
in the `chrisuthe/server` fork, with the explicit goal of proposing it upstream to
`music-assistant/server` (so **every** contributor's PR is reviewed against the cited
principles) once it proves out.

This is **Phase 1** of a larger integration mapped during brainstorming: a **static
instruction render** — zero infrastructure, no API key, no LLM in CI. Phases 2 (a Sage MCP
retrieval server for the live corpus) and 3 (an agent skill) are deliberately deferred and
out of scope here (see **Future phases**).

## Context that shaped this design

- **Target surface:** the automatic Copilot code-review bot on github.com PRs (the user's
  chosen surface). As of the **2026-07-29** GA, that bot also supports MCP + agent skills,
  which is what makes Phases 2–3 viable later; Phase 1 needs none of it.
- **The fork already has a developed Copilot review config.** `chrisuthe/server` (mirroring
  upstream) ships:
  - `.github/copilot-instructions.md` (~89 lines) — a full **"PR Review Standards"** file:
    severity taxonomy `[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]`, an output-comment format, a
    review philosophy, a "skip these" list, CI-context awareness, new-provider review via
    `_demo_*_provider` ground truth, and helper-reuse checks.
  - `AGENTS.md` (~84 lines) — the project dev/style guide (async Python, provider structure,
    Sphinx docstrings, private-methods-at-bottom, PRs target `dev`).
  - `CLAUDE.md` — a one-line pointer to `AGENTS.md`.
  - Copilot code review **merges** all of these; **conflicting** instructions across files
    produce undefined behavior (GitHub explicitly advises against them).
- **Consequence:** the Sage artifact must be a **separate, additive file** that **slots into**
  the existing severity/output framework rather than restating or competing with it.

## Chosen shape

A new build target in the OHF Sage pipeline renders `principles/principles.md` into a
**dedicated, path-scoped Copilot instruction file** that is committed into the target repo:

- **File:** `.github/instructions/ohf-sage.instructions.md` (NOT the existing
  `copilot-instructions.md` — that stays untouched).
- **Frontmatter:** `applyTo: "**"` so it applies to every reviewed file. Path-scoped
  `*.instructions.md` files are read by the code-review bot (GA 2025-09-03) and the coding
  agent — exactly the target surface. (They are *not* read by github.com Chat, which is
  irrelevant here.)
- **Body:** a short **reconciled preamble** (below) + the full `principles.md` spliced in
  verbatim between `PRINCIPLES:START/END` markers.

### The reconciled preamble

The preamble defers output formatting to the repo's existing review-standards file and only
adds what Sage uniquely brings — authority, scope, provenance weighting, and **citations**:

```markdown
---
applyTo: "**"
---
# Music Assistant — leads' principles (OHF Sage)

Cited engineering principles of the project leads, mined from real PR reviews. They speak for
Marcel van der Veldt (`marcelveldt`) across all projects and Marvin Schenkel
(`MarvinSchenkel`) for Music Assistant. Home Assistant is out of scope.

Apply these when reviewing a change, alongside the repo's existing review standards:
- When a change violates a principle below, flag it and **cite the linked PR/issue permalink**
  the principle came from — every rule carries its source.
- Map severity to the existing taxonomy: a `MUST` / "won't support" violation is
  `[CRITICAL]` or `[PROBLEM]`; a `Prefer` mismatch is `[SUGGESTION]`.
- Weigh by provenance marker: `[authored]`/`[enforced]` are firm policy, `[authored+mined]`
  is strongest, `[mined · N PRs]` is inferred from review history (higher N = firmer).
- If no principle below covers the case, don't invent one — defer to the existing standards.

<!-- PRINCIPLES:START --> … principles.md body spliced here … <!-- PRINCIPLES:END -->
```

It deliberately does **not** restate a verdict/output format, a "when to comment" philosophy,
or the corpus-grep and manual-overlay behaviors from the Claude agent template — those either
belong to the existing `copilot-instructions.md` (output/philosophy) or to later phases
(corpus/overlay = the MCP phase).

## Non-Goals

- No MCP server / live corpus retrieval (Phase 2).
- No `.github/skills/` agent skill (Phase 3).
- No Anthropic API key or any LLM in CI — this stays a pure text render.
- **Do not modify** the existing `.github/copilot-instructions.md` or `AGENTS.md`.
- **Do not fork or trim `principles.md`** per target — it stays the single source of truth;
  the whole doc is rendered, citations included, even where a topic overlaps an existing
  bare bullet.

## Components

### 1. `agent/copilot-instructions.template.md` (new)

The Copilot-shaped template: the `applyTo: "**"` frontmatter, the reconciled preamble above,
and the `<!-- PRINCIPLES:START -->` / `<!-- PRINCIPLES:END -->` markers. Mirrors the role of
`agent/ohf-sage.template.md` but for the Copilot target.

### 2. `scripts/build_copilot.py` (new)

- Reuses `scripts/build_agent.py`'s `build_agent(template_path, principles_path, out_path)`
  splice **as-is** (it already strips the leading `# ` title and splices between the markers —
  identical mechanics). No new splice logic.
- Adds one Copilot-specific guard: after rendering, count lines and **warn to stderr** if the
  output approaches the documented ~1,000-line best-practice ceiling (GitHub warns longer
  files get "overlooked"). `principles.md` (~151 lines) + preamble is far under, so this is a
  future-proofing guard, not an active limit.
- CLI signature mirrors `build_agent.py`:
  `python scripts/build_copilot.py [template] [principles] [out]`, defaulting
  `template = agent/copilot-instructions.template.md`, `principles = principles/principles.md`,
  `out = agent/ohf-sage.instructions.md`. The `out` path may point straight at the target
  repo, e.g. `…/server/.github/instructions/ohf-sage.instructions.md`.

### 3. `tests/test_build_copilot.py` (new)

Mirrors the existing `build_agent` test. Asserts: markers present in output; `applyTo`
frontmatter preserved at the top; the preamble text and a known principle line (e.g. the
blocking-IO `MUST`) both appear; the line-count guard warns above the threshold and is silent
below it (drive it with a tiny synthetic principles file for the over-threshold case).

### 4. Docs

- `DEVELOPING.md`: a note under the local principles-refresh flow that after `principles.md`
  changes, re-render **both** `build_agent.py` (the Claude agent) **and** `build_copilot.py`
  (the Copilot file) — they share one source. No CI change (principles refresh stays local and
  human-gated, per the CI design's integrity split).
- `README.md`: a short "GitHub Copilot code review" subsection pointing at the new build
  target and how to install the rendered file into a repo.

### 5. The rendered artifact in `chrisuthe/server` (committed)

- `.github/instructions/ohf-sage.instructions.md`, generated by `build_copilot.py`, **committed
  to the fork's `dev` branch** (upstream's and the fork's primary dev branch; PRs target `dev`
  and branch off it, so the file is present on PR head branches — which is where the review bot
  reads instructions from).
- **This file is git-visible by necessity** — Copilot reads committed files on the PR head
  branch, so the `.git/info/exclude` "git-invisible" approach used for the Claude agent cannot
  apply. That is intended: visibility is the point given the upstream goal.

## Placement & git visibility

The Claude agent (`.claude/agents/ohf-sage.md` + corpus) is installed git-invisibly because it
is a *local tool*. The Copilot instruction file is the **opposite**: it only works if
committed, and the end goal is for it to live in the shared repo. So Phase 1 commits it openly
to the fork's `dev`. If the user ever opens a fork→upstream PR before the upstream proposal
lands, the file rides along in that diff; that is acceptable (and, given the goal, desirable).

## Path to upstream (`music-assistant/server`)

Once the file proves out on the fork's PRs:

1. Open a PR to `music-assistant/server` adding `.github/instructions/ohf-sage.instructions.md`.
   Framing: it **extends** their existing Copilot review config with the leads' own cited,
   mined principles; **provenance links are verifiable receipts** a maintainer can click.
2. At that point, reconcile **topical overlaps** with their existing `copilot-instructions.md`
   / `AGENTS.md` (e.g. blocking-IO, helper reuse, docstrings): the maintainers may choose to
   drop their bare bullets in favor of Sage's cited versions, or keep both. This is a
   maintainer decision made at PR time — **not** something Phase 1 pre-empts by trimming.
3. Phase 2 (MCP live-corpus retrieval) would then require an upstream-reachable host + the
   `COPILOT_MCP_`-prefixed secret + maintainer repo-admin — a separate future step, gated on
   Phase 1 acceptance.

## Error Handling & Edge Cases

- **Template missing markers:** `build_agent`'s existing `ValueError("template missing
  PRINCIPLES markers")` already covers this; `build_copilot.py` inherits it.
- **Output nears the line ceiling:** warn to stderr, still write the file (soft guard).
- **Existing-file coexistence:** the new file is separate and additive; the preamble is written
  to defer to (not duplicate) the existing severity/output framework, avoiding the
  merged-conflict failure mode GitHub warns about.
- **Wrong target branch:** if committed to a branch PRs don't branch from, the bot won't see
  it. Phase 1 commits to `dev` for this reason; documented.
- **Corpus/manual-overlay absent:** intentionally not referenced by the Phase-1 file, so there
  is nothing to be missing.

## Verification (success criteria)

- **build_copilot (unit):** given the real template + `principles.md`, the rendered file has
  intact `applyTo` frontmatter, both markers, the preamble, and every principle line;
  round-trips deterministically. The line-count guard warns above the threshold and is silent
  below it. `tests/test_build_copilot.py` passes; the full suite stays green.
- **Render into the fork:** `build_copilot.py` writes a valid
  `.github/instructions/ohf-sage.instructions.md`; it coexists with the existing
  `copilot-instructions.md`/`AGENTS.md` without contradiction on inspection.
- **Live acceptance (real PR):** on a test PR in `chrisuthe/server` (targeting `dev`, with the
  file present on the head branch), Copilot code review produces comments that (a) apply a
  Sage principle, (b) cite its PR/issue permalink, and (c) use the existing
  `[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy — demonstrating the file is read and merged
  coherently. This first real run is the true acceptance test (as with the CI phase, the
  GitHub-side behavior can only be fully verified live).
- **Docs:** `DEVELOPING.md` re-render note and `README.md` Copilot subsection present.

## Build Sequence (high level)

1. `agent/copilot-instructions.template.md` (the reconciled preamble + markers).
2. `scripts/build_copilot.py` (reuse `build_agent`'s splice; add the line-count guard) +
   `tests/test_build_copilot.py`.
3. `DEVELOPING.md` + `README.md` updates.
4. Render into `chrisuthe/server` at `.github/instructions/ohf-sage.instructions.md` on `dev`;
   eyeball it against the existing review-standards file for coherence; commit.
5. Open a test PR against the fork's `dev` to exercise the live review (acceptance test).
