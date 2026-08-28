# What does this implement/fix?

An accuracy pass over the Copilot review-instructions standards (added in #5582 / #5620), correcting
distilled rules that no longer match the current project. Every change was verified against **current
`dev`** and the review history; nothing is speculative.

Started as a scope fix for the `API_SCHEMA_VERSION` rule (that history is in this PR's earlier
commits — thanks to the Copilot review for catching a contradiction, a missing case, and a reversed
direction along the way) and grew into a full review that surfaced more stale rules:

**Stale "won't support" positions the project has since reversed**
- *"not a client for Plex/Emby/LMS"* → those providers (`plex`, `plex_connect`, `emby`, `jellyfin`, `opensubsonic`) ship today. Rewritten to the still-true HA-clone point.
- *"Alexa … unsupported"* → `alexa` is a player provider now. Dropped the stale example, kept the "device must accept a stream URL" principle.
- *reverse proxies "in front of the server"* → only the **streams** server is LAN-only; the authenticated webserver/API port may sit behind HTTPS/a reverse proxy (per the same PR the streams rule cites).
- *privileged mode (Linux pipe sizing)* → superseded; SMB/CIFS needs `SYS_ADMIN`/`DAC_READ_SEARCH` capabilities, not blanket privileged mode.

**Rules that contradicted the current code**
- *"bundle provider deps into the image rather than installing at runtime"* → runtime install via `helpers/util.py:install_package` is a supported mechanism.
- *"providers don't cache media items themselves"* → providers cache parsed items through `@use_cache` (e.g. `apple_music/media.py`). Reworded to "never hand-roll a cache layer."
- group-volume *"proportional shift … only to the master"* → the controller preserves members' relative balance via the sync leader.
- *`wait_for_state` helper* → renamed to `wait_for_player_update`; the "debouncer" is `mass.call_later(task_id=…)`.

**Precision / correctness**
- `asyncio.gather` remedy bounded so it doesn't turn an N+1 into a burst against a rate-limited API.
- Walrus false-positive guard corrected: dropped the mypy `possibly-undefined` claim (MA doesn't enable it) and noted the genuine short-circuit case.
- Schema-bump exemption reworded to derive from backwards-compatibility rather than stand as a separate uncited claim.
- **9 citation anchors** were pointing at the wrong comment (the quotes are real, the links weren't) — corrected, each verified.

Both files regenerate from `principles.md` via the same pipeline. **Deferred** (not in this PR): a
`applyTo` widening so the GH-Actions/deployment rules become reachable (needs verifying multi-glob
`applyTo` support first), and the frequently-enforced `strings.json` standard (left to CI's
`check_translatable_labels` hook).

## Files

- `.github/instructions/music-assistant-standards.instructions.md` — read by Copilot code review.
- `.github/pr-review/standards.md` — read by the manual review workflow.

## Types of changes

- [x] Maintenance / chore — `maintenance`

## Checklist

- [x] The code change is tested and works locally.
- [x] `pre-commit run --all-files` passes.
- [x] `pytest` passes, and tests have been added/updated under `tests/` where applicable.
- [x] For changes to shared models, the companion PR in `music-assistant/models` is linked.
- [x] For changes affecting the UI, the companion PR in `music-assistant/frontend` is linked.
- [x] I have read and complied with the project's [AI Policy](https://github.com/music-assistant/.github/blob/main/AI_POLICY.md) for any AI-assisted contributions.
- [x] I have raised a PR against the documentation repository targeting the main or beta branch as appropriate.

<sub>(Instructions-only change: no library code, shared-model, UI, or docs-repo changes.)</sub>
