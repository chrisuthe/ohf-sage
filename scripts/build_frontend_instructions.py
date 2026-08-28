"""Build the frontend Copilot code-review instructions shard.

Emits `.github/instructions/music-assistant-frontend-standards.instructions.md` for
`music-assistant/frontend`: the mined frontend rules that the repo's README
"Development Guidelines" does not already codify, scoped to Vue/TS files, plus a
cross-repo directive to consult the server via the GitHub MCP. Deliberately scaled
back and ADDITIVE to the README; the Python false-positive guards do not apply here.
"""

import re
import sys
from pathlib import Path

FRONTMATTER = '---\napplyTo: "**/*.{ts,vue}"\n---\n\n'

PREAMBLE = (
    "<!-- Generated from mined PR-review precedents; additive to the repo's README "
    '"Development Guidelines". -->\n'
    "# Music Assistant frontend — mined review precedents\n\n"
    "Standards distilled from this repository's own past pull-request review discussions; each "
    'links the PR where it was set. They are ADDITIVE to the "Development Guidelines" in '
    "`README.md` — where they overlap, the README is authoritative and these add the precedent "
    "and specifics; do not restate what the README already covers. Treat a **MUST** or "
    '"won\'t support" deviation as a problem worth blocking and a *Prefer* deviation as a '
    "suggestion, and cite the linked PR when you raise one.\n\n"
)

CROSS_REPO_SERVER = (
    "---\n\n"
    "## Cross-repo: the server owns the API\n\n"
    "This frontend is a client of `music-assistant/server` (Python). When a change depends on "
    "server behavior — an API command, a shared model, `schema_version`, or the wire contract — "
    "use the GitHub MCP to check `music-assistant/server` (its code and open PRs) rather than "
    "guessing. Gate newer-server commands on `schema_version`, and never implement server-owned "
    "logic (volume, queue, filtering) as a frontend workaround.\n"
)

# The repo's README "Development Guidelines" already codify these specific standards; keep them
# out of the shard so it stays additive. Matched by each rule's distinctive phrase (not by
# incidental keywords — e.g. the schema_version rule mentions "toasts" but is not the toast rule).
README_COVERED = re.compile(
    r"into a dedicated composable|extract shared or heavy logic into composables|"
    r"ship Vitest unit tests|"
    r"surface API-call failures|"
    r"computed properties for derived state|"
    r"custom interactive elements accessible|"
    r"comments that explain rationale",
    re.I,
)


def _is_rule(line: str) -> bool:
    return line.lstrip().startswith("- **")


def _keep(line: str) -> bool:
    """Keep mined frontend rules except those the README already codifies or enforced/authored."""
    s = line.rstrip()
    if s.endswith("[enforced]") or s.endswith("[authored]"):
        return False
    return not README_COVERED.search(s)


def build(standards_path: str, out_path: str) -> str:
    """Extract the `### frontend` section's mined rules into the frontend shard."""
    rules: list[str] = []
    in_frontend = False
    for line in Path(standards_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("### frontend"):
            in_frontend = True
            continue
        if in_frontend and line.startswith("### "):
            break  # next per-project section
        if in_frontend and _is_rule(line) and _keep(line):
            rules.append(line.rstrip())
    result = FRONTMATTER + PREAMBLE + "\n".join(rules) + "\n\n" + CROSS_REPO_SERVER
    Path(out_path).write_text(result, encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI: build_frontend_instructions.py [standards.md] [out.instructions.md]."""
    argv = argv or sys.argv[1:]
    root = Path(__file__).resolve().parents[1]
    standards = argv[0] if len(argv) > 0 else root / "agent/music-assistant-review-bot.md"
    out = argv[1] if len(argv) > 1 else root / "agent/music-assistant-frontend-standards.instructions.md"
    build(str(standards), str(out))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
