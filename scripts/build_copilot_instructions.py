"""Build an additive Copilot code-review instructions shard from the mined standards.

Emits `.github/instructions/music-assistant-standards.instructions.md`: the corpus-derived
rules (`[mined]` / `[authored+mined]`) with their PR citations, scoped to Python files via
`applyTo`. Deliberately ADDITIVE to the repo's existing config:

  - drops `[enforced]` rules  -> copilot-instructions.md already says "Don't duplicate CI"
  - drops pure `[authored]` rules -> already stated in the repo's AGENTS.md
  - drops the frontend/desktop/mobile per-project sections -> other repos

so the shard carries only what the mined review history adds beyond the repo's own docs.
"""

import sys
from pathlib import Path

FRONTMATTER = '---\napplyTo: "**/*.py"\n---\n\n'

PREAMBLE = (
    "<!-- Generated from mined PR-review precedents; additive to copilot-instructions.md + "
    "AGENTS.md. -->\n"
    "# Music Assistant — mined review precedents\n\n"
    "Project standards distilled from this repository's own past pull-request review "
    "discussions; each links the PR where the standard was set. They augment the standards in "
    "`AGENTS.md`. Grade against the existing `[CRITICAL]`/`[PROBLEM]`/`[SUGGESTION]` taxonomy in "
    "`copilot-instructions.md` — do not restate the output format here. Treat a **MUST** or "
    '"won\'t support" deviation as at least `[PROBLEM]` (a `[CRITICAL]` when it breaks '
    "functionality or security); treat a *Prefer* deviation as `[SUGGESTION]`. When you raise "
    "one of these, cite its linked PR so the author can see the precedent.\n\n"
)

# Precision guards: recurring false positives maintainers have dismissed. Each is grounded in a
# real misfire, so the reviewer stops re-raising it.
GUARDS = (
    "---\n\n"
    "## Avoid these false positives\n\n"
    "Patterns that look like bugs but are correct here — do not raise them:\n\n"
    "- **A walrus-bound name is bound once its expression runs.** A name assigned with `:=` is "
    "bound as soon as that walrus expression evaluates — even if the surrounding condition is then "
    "False — so do not report `UnboundLocalError` / \"used before assignment\" for it there. Only "
    "flag it when the walrus itself may be skipped (e.g. it sits on the short-circuited side of "
    "`or`/`and`).\n"
    "- **A quoted type in `cast()` does not make its import unused.** `cast(\"SomeType\", x)` with "
    "the type as a string is ruff's `TC006` form; ruff and mypy resolve names inside quoted casts, "
    "so the import is used. Do not flag it as an unused import.\n"
    "- **No `await`, no race.** Do not report a TOCTOU / check-then-act race unless there is a real "
    "suspension point (`await`) between the check and the mutation. Single-threaded asyncio runs "
    "code with no `await` between them atomically, so nothing can interleave.\n"
)

# Cross-repo awareness: a server change can silently break the Vue/TS frontend, which is a
# client of this API. Emitted as its OWN repo-wide (`applyTo: "**"`) instruction file, not
# appended to the Python-scoped shard — a contract change (e.g. a music-assistant-models bump
# in pyproject.toml) can land in a non-.py file the shard would never load for.
CROSS_REPO_FRONTMATTER = '---\napplyTo: "**"\n---\n\n'
CROSS_REPO_FRONTEND = (
    "<!-- Generated; additive to copilot-instructions.md + AGENTS.md. -->\n"
    "# Cross-repo: the frontend is a client of this API\n\n"
    "The Music Assistant web frontend (`music-assistant/frontend`, Vue/TypeScript) consumes "
    "this server's API commands, shared models, and wire/streaming contract, so a server change "
    "can break it silently. When a PR changes an API command, a shared model, the wire "
    "contract, or `API_SCHEMA_VERSION`:\n\n"
    "- **Read the frontend before assuming it is unaffected.** Use the GitHub MCP to inspect "
    "`music-assistant/frontend` — its code and its open PRs — for how the changed command, "
    "field, or model is consumed, and flag a break or a needed companion change.\n"
    "- The frontend **gates newer-server commands on `schema_version`**, so a backwards-"
    "incompatible client-facing addition — a new or changed API command, a shared-model change, "
    "or a new remote-access channel label — must bump `API_SCHEMA_VERSION`. "
    "([frontend#1911](https://github.com/music-assistant/frontend/pull/1911#discussion_r3408564733): "
    "\"setLocale now checks the server's schema_version and skips the command on servers < 32\")\n"
    "- Behavior **all API clients need** (volume, queue, filtering) belongs in the server, not "
    "as a frontend workaround. "
    "([frontend#1569](https://github.com/music-assistant/frontend/pull/1569#issuecomment-4124730842): "
    "\"We should not accept this to be implemented in the frontend at all\")\n"
    "- The frontend **will not add a silent fallback that masks a broken server contract** — a "
    "change to a field's presence or shape must surface there, not be hidden. "
    "([frontend#2083](https://github.com/music-assistant/frontend/pull/2083#discussion_r3565206399): "
    "\"a fallback would mask a broken server contract\")\n"
)


def _is_rule(line: str) -> bool:
    return line.lstrip().startswith("- **")


def _keep_rule(line: str) -> bool:
    """Keep only mined / authored+mined rules; drop enforced (CI) and pure authored (their docs)."""
    s = line.rstrip()
    if s.endswith("[enforced]") or s.endswith("[authored]"):
        return False
    return ("[authored+mined]" in s) or ("[mined" in s)


def _prune_empty_subsections(lines: list[str]) -> list[str]:
    """Drop a `### ` header + its intro when no rule bullet follows before the next header."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            j = i + 1
            has_rule = False
            while j < len(lines) and not lines[j].startswith(("## ", "### ")):
                if _is_rule(lines[j]):
                    has_rule = True
                j += 1
            if not has_rule:
                i = j  # skip the header and its (rule-less) body
                continue
        out.append(line)
        i += 1
    return out


def build(standards_path: str, out_path: str) -> str:
    """Filter the de-personalized standards doc into an additive instructions shard."""
    kept: list[str] = []
    in_scope = False
    for line in Path(standards_path).read_text(encoding="utf-8").splitlines():
        if line.strip() == "## General standards":
            in_scope = True
        if line.startswith("### frontend"):
            break  # everything from here on is other-repo scope
        if not in_scope:
            continue
        if _is_rule(line):
            if _keep_rule(line):
                kept.append(line)
            continue
        kept.append(line)  # headers, section intros, rules, dividers
    body = "\n".join(_prune_empty_subsections(kept)).strip("\n")
    result = FRONTMATTER + PREAMBLE + body + "\n\n" + GUARDS
    Path(out_path).write_text(result, encoding="utf-8")
    return result


def build_cross_repo(out_path: str) -> str:
    """Write the repo-wide cross-repo frontend-awareness instruction file."""
    result = CROSS_REPO_FRONTMATTER + CROSS_REPO_FRONTEND
    Path(out_path).write_text(result, encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI: build_copilot_instructions.py [standards.md] [out.instructions.md]."""
    argv = argv or sys.argv[1:]
    root = Path(__file__).resolve().parents[1]
    standards = argv[0] if len(argv) > 0 else root / "agent/music-assistant-review-bot.md"
    out = argv[1] if len(argv) > 1 else root / "agent/music-assistant-standards.instructions.md"
    cross = root / "agent/music-assistant-cross-repo.instructions.md"
    build(str(standards), str(out))
    build_cross_repo(str(cross))
    print(f"wrote {out}\nwrote {cross}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
