# Automated PR Review — example output

Sample reviews produced by running real open Music Assistant PRs through the **Automated PR Review** bot locally. Each review is checked against the project's own coding standards — distilled from this repo's review history, `AGENTS.md`, `copilot-instructions.md`, and the pre-commit config — and every finding links back to where that standard was established.

**7 PRs reviewed · 9 findings raised · 2 passed clean.** Findings map to the existing `[CRITICAL]` / `[PROBLEM]` / `[SUGGESTION]` taxonomy; when posted, line-anchored findings attach as inline review comments on the diff.

The bot deliberately **skips anything pre-commit/CI already catches** and does not invent nitpicks — note the two clean passes at the end.

---
## [#5079 — Adds a new Local Audio Source provider plugin](https://github.com/music-assistant/server/pull/5079)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**3 finding(s)** against the project's coding standards.
<sub>2× PROBLEM, 1× SUGGESTION</sub>

- **[PROBLEM]** `music_assistant/providers/local_audio_source/helpers.py`:21
  get_available_input_devices() catches FileNotFoundError/RuntimeError and collapses them into an empty device list with no logging, silently hiding a missing/broken pactl during setup; the sibling _resolve_audio_format() logs a warning for the identical exceptions.
  _Standard: MUST never silently swallow errors or anomalous data; surface it (log/raise) rather than collapsing a failure into a silent default. — https://github.com/music-assistant/server/pull/1214#discussion_r1557137671_
- **[PROBLEM]** `music_assistant/providers/local_audio_source/provider.py`
  The PR adds a ~700-line provider plus helper modules (capture streaming, auto-trigger sensor loop, format resolution, source-claim lifecycle) but no tests under tests/. New functionality must ship with added/updated tests and keep pytest green.
  _Standard: MUST add or update tests under tests/ for new functionality and keep pytest green. — https://github.com/music-assistant/server/blob/HEAD/.github/PULL_REQUEST_TEMPLATE.md_
- **[SUGGESTION]** `music_assistant/providers/local_audio_source/provider.py`:583
  _auto_stop_playback() reaches into queue.current_item.uri to decide whether to stop; providers are discouraged from reading queue/queue-item state directly rather than coordinating through the queue controller.
  _Standard: MUST not read or mutate queue/player state directly from a provider; let the queue controller own that state. — https://github.com/music-assistant/server/pull/2283#discussion_r2249779942_

---

## [#5151 — Add Overcast podcast provider](https://github.com/music-assistant/server/pull/5151)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**2 finding(s)** against the project's coding standards.
<sub>2× PROBLEM</sub>

- **[PROBLEM]** `music_assistant/providers/overcast/provider.py`:538
  handle_async_init creates its own aiohttp session via create_clientsession() per provider instance instead of reusing self.mass.http_session. The multi-instance cookie-isolation rationale is understandable, but the standard is to reuse the shared global session and never spin up a per-provider one; the authenticated Overcast calls should reuse mass.http_session (e.g. by setting the session cookie per-request).
  _Standard: MUST reuse the shared global aiohttp session (self.mass.http_session); never create a new ClientSession per request or per provider. — https://github.com/music-assistant/server/pull/1817#discussion_r1903244819_
- **[PROBLEM]** `music_assistant/providers/overcast/provider.py`:707
  The Overcast session cookie is a bearer credential (equivalent to the account login) but is persisted via _update_setup_data(CONF_SESSION_COOKIE, morsel.value) without being typed/stored as a SECURE_STRING. Unlike the password, it is therefore not encrypted at rest nor masked in config serialization, so it can leak through config output.
  _Standard: MUST handle secrets carefully: mask secure config values in serialization and never persist credentials in plaintext. — https://github.com/music-assistant/server/pull/4882#discussion_r3634243924_

---

## [#5180 — ytmusic: complete uploaded music resolution](https://github.com/music-assistant/server/pull/5180)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**2 finding(s)** against the project's coding standards.
<sub>1× PROBLEM, 1× SUGGESTION</sub>

- **[PROBLEM]** `music_assistant/providers/ytmusic/helpers.py`:181
  get_library_artists now concatenates get_library_subscriptions() + get_library_artists() + get_library_upload_artists() with no deduplication. A followed artist that also has songs in the library is returned by both get_library_subscriptions and get_library_artists (both key on the same browseId), so it appears twice in the artist listing.
  _Standard: When combining item sources that can overlap, deduplicate in the function body (e.g. via a temporary UniqueList) rather than returning duplicates. — https://github.com/music-assistant/server/pull/2632#issuecomment-3563511797_
- **[SUGGESTION]** `music_assistant/providers/ytmusic/helpers.py`:230
  The new upload calls reuse the hardcoded limit=9999 (notably get_library_upload_songs), a fixed cap a real user can exceed since YouTube Music uploads allow far more than 9999 tracks; anything past the cap is silently dropped. It mirrors the file's existing pattern, but the uploaded-songs path is where a large library will actually be truncated.
  _Standard: MUST not hardcode a limit a real user can exceed (e.g. a fixed library-size cap); paginate or derive the value instead. — https://github.com/music-assistant/server/pull/3640#discussion_r3072722851_

---

## [#5165 — Library item counts now respect the user's provider filter](https://github.com/music-assistant/server/pull/5165)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**1 finding(s)** against the project's coding standards.
<sub>1× PROBLEM</sub>

- **[PROBLEM]** `music_assistant/providers/profiler/provider.py`:295
  The profiler (a plugin-type provider) now reaches into self.mass.music.database.get_count() directly instead of going through the controller API, in order to get unfiltered totals. Providers/plugins must not touch the database directly; expose an unfiltered-total method on the media controller and have both the profiler and the diagnostics controller use it (which also removes the raw-count logic and comment now duplicated across both files).
  _Standard: MUST treat providers as isolated units and never touch the database directly — coordinate through the controller API. — https://github.com/music-assistant/server/pull/2911#discussion_r2853705643_

---

## [#5178 — Establish and keep the duration of podcast episodes if their feed does not supply it](https://github.com/music-assistant/server/pull/5178)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**1 finding(s)** against the project's coding standards.
<sub>1× SUGGESTION</sub>

- **[SUGGESTION]** `music_assistant/controllers/player_queues/controller.py`:971
  The resume-seek duration resolution is added to the player_queues controller (_restore_probed_duration plus the new duration guard in play_index), layered on top of the get_stream_details fallback in streams/audio.py. The direct predecessor of this feature was pushed back for resolving missing durations in the player_queues controller instead of the stream pipeline; consider consolidating the probed-duration restore closer to get_stream_details where it is technically feasible.
  _Standard: Keep shared/player-pipeline logic in its owning controller and resolve missing durations in the stream pipeline rather than special-casing the core player_queues controller. — https://github.com/music-assistant/server/pull/3896#discussion_r3291222180_

---

## [#5179 — Cache podcast episode listings and batch their resume lookups](https://github.com/music-assistant/server/pull/5179)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**No standards violations found.** The change was reviewed against the standards and passed clean.

---

## [#5177 — Fix noisy 'Task exception was never retrieved' errors in the log](https://github.com/music-assistant/server/pull/5177)

> ## 🤖 Automated PR Review
> 
> Reviewed against the project's coding standards. Each note links where the standard is documented.
> 

**No standards violations found.** The change was reviewed against the standards and passed clean.
