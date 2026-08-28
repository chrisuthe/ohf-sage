# Automated PR Review — change-suggestion demo

The reviewer now emits GitHub **change-suggestion blocks** for concrete one-line fixes: a ```suggestion``` fence the maintainer applies with one click. It sets these **only** for mechanical fixes and leaves judgment/architectural findings as prose — so the suggestions stay trustworthy.

Below: #5079 and #5180 re-run through the reviewer. **2 applyable suggestions** surfaced — both on #5079's real Python-3 syntax bugs. #5180 shows the reviewer correctly **declining** to suggest (a hardcoded cap needs pagination, not a one-liner; `asyncio.gather` is multi-line; a comment rewrite is prose).

---
## [#5079 — Adds a new Local Audio Source provider plugin](https://github.com/music-assistant/server/pull/5079)

**4 finding(s)** · **2** with an applyable change-suggestion.

- **[CRITICAL]** `music_assistant/providers/local_audio_source/helpers.py`:21
  `except FileNotFoundError, RuntimeError:` is Python-2 exception syntax and is a SyntaxError under Python 3, so this module fails to even import and the whole provider is dead on load. The correct tuple form is used elsewhere in this same PR (provider.py `_resolve_audio_format`).
  _Standard: Code must be valid Python for the required 3.14 runtime and parse under Ruff; catch specific exception types using the tuple form `except (A, B):`. — https://github.com/music-assistant/server/blob/HEAD/pyproject.toml_

  ```suggestion
      except (FileNotFoundError, RuntimeError):
  ```
  <sub>↑ applyable — one click commits this change on the PR</sub>
- **[CRITICAL]** `music_assistant/providers/local_audio_source/pa_simple.py`:133
  `except IndexError, ValueError:` is Python-2 exception syntax → SyntaxError under Python 3, so `enumerate_pa_sources` (and therefore source discovery and the setup flow) fails to import. The corrected tuple form appears at the same spot in the pre-existing local_audio provider.
  _Standard: Code must be valid Python for the required 3.14 runtime and parse under Ruff; catch specific exception types using the tuple form `except (A, B):`. — https://github.com/music-assistant/server/blob/HEAD/pyproject.toml_

  ```suggestion
          except (IndexError, ValueError):
  ```
  <sub>↑ applyable — one click commits this change on the PR</sub>
- **[PROBLEM]** `music_assistant/providers/local_audio_source/provider.py`
  This ~700-line new provider (capture streaming, auto-trigger sensor loop, format resolution, session handling) adds no tests under `tests/`. New functionality must add/update tests and keep pytest green.
  _Standard: New functionality requires tests added/updated under `tests/` and a passing pytest run. — https://github.com/music-assistant/server/blob/HEAD/.github/PULL_REQUEST_TEMPLATE.md_
- **[PROBLEM]** `music_assistant/providers/local_audio_source/icon.svg`
  The provider ships `icon.svg` (hardcoded `fill="#000000"`) plus preset images, but no `icon_monochrome.svg`. New providers are consistently required to include both `icon.svg` and a single-tone `icon_monochrome.svg` (currentColor, under the 5KB budget).
  _Standard: A new provider must supply both `icon.svg` and `icon_monochrome.svg`. — https://github.com/music-assistant/server/pull/3127#issuecomment-3878007386_

---

## [#5180 — ytmusic: complete uploaded music resolution](https://github.com/music-assistant/server/pull/5180)

**3 finding(s)** · **0** with an applyable change-suggestion.

- **[PROBLEM]** `music_assistant/providers/ytmusic/helpers.py`:230
  The newly added upload listing calls hardcode `limit=9999`. Uploaded YouTube Music libraries can hold up to 100,000 items, so a real user's uploaded songs/albums/artists can exceed 9999 and be silently truncated. Same issue on the added calls at lines 181 and 200.
  _Standard: MUST not hardcode a limit a real user can exceed; paginate or derive the value instead. — https://github.com/music-assistant/server/pull/3640#discussion_r3072722851_
- **[SUGGESTION]** `music_assistant/providers/ytmusic/helpers.py`:181
  Concatenating `get_library_subscriptions() + get_library_artists() + get_library_upload_artists()` runs three independent blocking API calls sequentially in one thread (likewise the two-call concatenations at lines 200 and 230). These could be wrapped in separate `asyncio.to_thread` calls and combined with `asyncio.gather` to avoid serializing the round-trips.
  _Standard: Batch or `asyncio.gather` independent API calls rather than running them sequentially. — https://github.com/music-assistant/server/pull/2501#discussion_r2429740886_
- **[SUGGESTION]** `music_assistant/providers/ytmusic/helpers.py`:60
  This comment is a first-person rationale/change-history note ('so I'm reproducing that here given we don't need to...') rather than a description of what the code does. Project standard is to comment only complex blocks and describe current behavior.
  _Standard: Comments explain complex blocks and describe current behavior, never change history or rationale. — https://github.com/music-assistant/server/pull/3387#discussion_r3011557784_
