# ruff: noqa: INP001, T201, E501  # local showcase helper
"""Render a focused demo of Automated PR Review WITH change-suggestion blocks (#5079, #5180).

The per-finding body is built the same way post_pr_review.py now builds an inline comment:
prose + Standard citation + (for a mechanical one-line fix) an applyable ```suggestion block.
"""

from pathlib import Path

REPO = "music-assistant/server"
HERE = Path(__file__).resolve().parent
SEV = {"CRITICAL": 0, "PROBLEM": 1, "SUGGESTION": 2}

DATA = {
    "5079": {
        "title": "Adds a new Local Audio Source provider plugin",
        "findings": [
            {"severity": "CRITICAL", "path": "music_assistant/providers/local_audio_source/helpers.py", "line": 21,
             "issue": "`except FileNotFoundError, RuntimeError:` is Python-2 exception syntax and is a SyntaxError under Python 3, so this module fails to even import and the whole provider is dead on load. The correct tuple form is used elsewhere in this same PR (provider.py `_resolve_audio_format`).",
             "principle": "Code must be valid Python for the required 3.14 runtime and parse under Ruff; catch specific exception types using the tuple form `except (A, B):`.",
             "citation_url": "https://github.com/music-assistant/server/blob/HEAD/pyproject.toml",
             "suggestion": "    except (FileNotFoundError, RuntimeError):"},
            {"severity": "CRITICAL", "path": "music_assistant/providers/local_audio_source/pa_simple.py", "line": 133,
             "issue": "`except IndexError, ValueError:` is Python-2 exception syntax → SyntaxError under Python 3, so `enumerate_pa_sources` (and therefore source discovery and the setup flow) fails to import. The corrected tuple form appears at the same spot in the pre-existing local_audio provider.",
             "principle": "Code must be valid Python for the required 3.14 runtime and parse under Ruff; catch specific exception types using the tuple form `except (A, B):`.",
             "citation_url": "https://github.com/music-assistant/server/blob/HEAD/pyproject.toml",
             "suggestion": "        except (IndexError, ValueError):"},
            {"severity": "PROBLEM", "path": "music_assistant/providers/local_audio_source/provider.py", "line": None,
             "issue": "This ~700-line new provider (capture streaming, auto-trigger sensor loop, format resolution, session handling) adds no tests under `tests/`. New functionality must add/update tests and keep pytest green.",
             "principle": "New functionality requires tests added/updated under `tests/` and a passing pytest run.",
             "citation_url": "https://github.com/music-assistant/server/blob/HEAD/.github/PULL_REQUEST_TEMPLATE.md",
             "suggestion": None},
            {"severity": "PROBLEM", "path": "music_assistant/providers/local_audio_source/icon.svg", "line": None,
             "issue": "The provider ships `icon.svg` (hardcoded `fill=\"#000000\"`) plus preset images, but no `icon_monochrome.svg`. New providers are consistently required to include both `icon.svg` and a single-tone `icon_monochrome.svg` (currentColor, under the 5KB budget).",
             "principle": "A new provider must supply both `icon.svg` and `icon_monochrome.svg`.",
             "citation_url": "https://github.com/music-assistant/server/pull/3127#issuecomment-3878007386",
             "suggestion": None},
        ],
    },
    "5180": {
        "title": "ytmusic: complete uploaded music resolution",
        "findings": [
            {"severity": "PROBLEM", "path": "music_assistant/providers/ytmusic/helpers.py", "line": 230,
             "issue": "The newly added upload listing calls hardcode `limit=9999`. Uploaded YouTube Music libraries can hold up to 100,000 items, so a real user's uploaded songs/albums/artists can exceed 9999 and be silently truncated. Same issue on the added calls at lines 181 and 200.",
             "principle": "MUST not hardcode a limit a real user can exceed; paginate or derive the value instead.",
             "citation_url": "https://github.com/music-assistant/server/pull/3640#discussion_r3072722851",
             "suggestion": None},
            {"severity": "SUGGESTION", "path": "music_assistant/providers/ytmusic/helpers.py", "line": 181,
             "issue": "Concatenating `get_library_subscriptions() + get_library_artists() + get_library_upload_artists()` runs three independent blocking API calls sequentially in one thread (likewise the two-call concatenations at lines 200 and 230). These could be wrapped in separate `asyncio.to_thread` calls and combined with `asyncio.gather` to avoid serializing the round-trips.",
             "principle": "Batch or `asyncio.gather` independent API calls rather than running them sequentially.",
             "citation_url": "https://github.com/music-assistant/server/pull/2501#discussion_r2429740886",
             "suggestion": None},
            {"severity": "SUGGESTION", "path": "music_assistant/providers/ytmusic/helpers.py", "line": 60,
             "issue": "This comment is a first-person rationale/change-history note ('so I'm reproducing that here given we don't need to...') rather than a description of what the code does. Project standard is to comment only complex blocks and describe current behavior.",
             "principle": "Comments explain complex blocks and describe current behavior, never change history or rationale.",
             "citation_url": "https://github.com/music-assistant/server/pull/3387#discussion_r3011557784",
             "suggestion": None},
        ],
    },
}
ORDER = ["5079", "5180"]


def finding_block(f):
    """Render one finding exactly as post_pr_review.py builds an inline comment body."""
    sev = f["severity"]
    line = f.get("line")
    loc = f"`{f['path']}`" + (f":{line}" if isinstance(line, int) else "")
    out = [f"- **[{sev}]** {loc}", f"  {f['issue']}"]
    if f.get("citation_url"):
        out.append(f"  _Standard: {f['principle']} — {f['citation_url']}_")
    suggestion = f.get("suggestion")
    if isinstance(line, int) and isinstance(suggestion, str) and suggestion.strip():
        out.append("")
        out.append("  ```suggestion")
        out.append(f"  {suggestion}")
        out.append("  ```")
        out.append("  <sub>↑ applyable — one click commits this change on the PR</sub>")
    return "\n".join(out)


def render_pr(number, entry):
    """Render one PR section."""
    findings = sorted(entry["findings"], key=lambda f: SEV.get(f["severity"], 3))
    url = f"https://github.com/{REPO}/pull/{number}"
    n_sug = sum(1 for f in findings if isinstance(f.get("suggestion"), str) and f["suggestion"].strip())
    out = [f"## [#{number} — {entry['title']}]({url})", ""]
    out.append(f"**{len(findings)} finding(s)** · **{n_sug}** with an applyable change-suggestion.")
    out.append("")
    out += [finding_block(f) for f in findings]
    out.append("")
    return "\n".join(out)


def main():
    """Write the focused change-suggestion demo document."""
    total_sug = sum(
        1 for n in ORDER for f in DATA[n]["findings"]
        if isinstance(f.get("suggestion"), str) and f["suggestion"].strip()
    )
    header = [
        "# Automated PR Review — change-suggestion demo",
        "",
        "The reviewer now emits GitHub **change-suggestion blocks** for concrete one-line fixes: a "
        "```suggestion``` fence the maintainer applies with one click. It sets these **only** for "
        "mechanical fixes and leaves judgment/architectural findings as prose — so the suggestions "
        "stay trustworthy.",
        "",
        f"Below: #5079 and #5180 re-run through the reviewer. **{total_sug} applyable suggestions** "
        "surfaced — both on #5079's real Python-3 syntax bugs. #5180 shows the reviewer correctly "
        "**declining** to suggest (a hardcoded cap needs pagination, not a one-liner; `asyncio.gather` "
        "is multi-line; a comment rewrite is prose).",
        "",
        "---",
        "",
    ]
    body = "\n---\n\n".join(render_pr(n, DATA[n]) for n in ORDER)
    (HERE / "automated-pr-review-suggestions-demo.md").write_text(
        "\n".join(header) + body, encoding="utf-8",
    )
    print(f"wrote automated-pr-review-suggestions-demo.md — {total_sug} applyable suggestions")


if __name__ == "__main__":
    main()
