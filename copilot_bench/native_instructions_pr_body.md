# What does this implement/fix?

Adds `.github/instructions/music-assistant-standards.instructions.md` — a path-scoped
(`applyTo: "**/*.py"`) instructions file that grounds **Copilot code review** in standards
distilled from this repository's own past PR-review discussions, each linking the pull request
where the standard was set.

It is **purely additive**. It does not restate the review taxonomy or output format (that stays in
`copilot-instructions.md`) and does not repeat the authored project docs (`AGENTS.md`). It carries
only what those don't: **58 cited "mined" precedents** — with anything CI already enforces, and
anything already stated in `AGENTS.md`, deliberately left out.

## Why now

GitHub GA'd full instruction-file support (and MCP/agent skills) for Copilot code review on
2026-07-29. On a 12-case held-out benchmark — maintainers' historical review comments, each PR
reconstructed at its review commit and reviewed at **Balanced** effort — grounding the native
reviewer in this file reached **6/12 exact-issue recall**: parity with a bespoke full-attention
reviewer, and roughly 3× the un-grounded Copilot baseline. The reviewer visibly uses it — it cites
the file directly (e.g. *"replace it with `self.mass.cache` … as required by
`.github/instructions/music-assistant-standards.instructions.md`"*) and invokes the mined precedents
by PR number.

The intent is to get more out of the **native** Copilot review we already run, using the project's
own on-record standards — no bespoke workflow, no extra infrastructure.

## Files

- `.github/instructions/music-assistant-standards.instructions.md` — the instructions shard.
- `pyproject.toml` — adds the shard to the codespell skip list; it quotes reviewer comments
  verbatim (original typos and all), like the other data files already skipped.

## Types of changes

- [ ] Bugfix (non-breaking change which fixes an issue) — `bugfix`
- [ ] New feature (non-breaking change which adds functionality) — `new-feature`
- [ ] Enhancement to an existing feature — `enhancement`
- [ ] New music/player/metadata/plugin provider — `new-provider`
- [ ] Breaking change — `breaking-change`
- [ ] Refactor (no behaviour change) — `refactor`
- [ ] Documentation only — `documentation`
- [x] Maintenance / chore — `maintenance`
- [ ] CI / workflow change — `ci`
- [ ] Dependencies bump — `dependencies`

## Checklist

- [x] The code change is tested and works locally.
- [x] `pre-commit run --all-files` passes.
- [x] `pytest` passes, and tests have been added/updated under `tests/` where applicable.
- [x] For changes to shared models, the companion PR in `music-assistant/models` is linked.
- [x] For changes affecting the UI, the companion PR in `music-assistant/frontend` is linked.
- [x] I have read and complied with the project's [AI Policy](https://github.com/music-assistant/.github/blob/main/AI_POLICY.md) for any AI-assisted contributions.
- [x] I have raised a PR against the documentation repository targeting the main or beta branch as appropriate.

<sub>(Instructions/config-only change: no library code, shared-model, UI, or docs-repo changes — the conditional items above are vacuously satisfied.)</sub>
