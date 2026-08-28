# What does this implement/fix?

Follow-up to #5582. Adds a short **"Avoid these false positives"** section to
`.github/instructions/music-assistant-standards.instructions.md` — three guards for patterns the
Copilot reviewer has misfired on recently, each already dismissed by a maintainer with the
reasoning captured here so it stops re-raising them:

- **A walrus-bound name is not unbound** — a name assigned with `:=` inside a condition is bound as
  soon as the expression evaluates, even when the condition is False (it just holds `None`), so it
  is not an `UnboundLocalError`.
- **A quoted type in `cast()` is not an unused import** — `cast("SomeType", x)` is ruff's `TC006`
  form; ruff and mypy resolve names inside quoted casts, so the import is used.
- **No `await`, no race** — don't report a TOCTOU / check-then-act race when there's no suspension
  point between the check and the mutation; single-threaded asyncio can't interleave there.

These are precision-only (they tell the reviewer what *not* to raise); they don't change any of the
mined precedents from #5582.

## Files

- `.github/instructions/music-assistant-standards.instructions.md` — +10 lines (the guards section).

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

<sub>(Instructions-only change: no library code, shared-model, UI, or docs-repo changes — the conditional items above are vacuously satisfied.)</sub>
