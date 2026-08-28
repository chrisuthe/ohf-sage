# ruff: noqa: INP001, T201  # local showcase helper, prints to stdout
"""Render example_findings.json into a Markdown showcase of Automated PR Review output.

Reuses the exact HEADER / severity order / finding-body format from
``copilot/cli-reviewer/post_pr_review.py`` so the rendered body matches what the bot posts.
"""

import json
from pathlib import Path

REPO = "music-assistant/server"
HERE = Path(__file__).resolve().parent

# Mirrors post_pr_review.py exactly.
SEV = {"CRITICAL": 0, "PROBLEM": 1, "SUGGESTION": 2}
HEADER = (
    "## 🤖 Automated PR Review\n\n"
    "Reviewed against the project's coding standards. Each note links where the standard "
    "is documented.\n"
)

# Lead with the richest reviews; end on the two clean passes.
ORDER = ["5079", "5151", "5180", "5165", "5178", "5179", "5177"]


def finding_block(finding):
    """Render one finding the way the bot writes an inline review comment (+ its anchor)."""
    sev = finding.get("severity", "SUGGESTION")
    line = finding.get("line")
    loc = f"`{finding.get('path', '—')}`" + (f":{line}" if isinstance(line, int) else "")
    body = [f"- **[{sev}]** {loc}", f"  {finding.get('issue', '')}"]
    if finding.get("citation_url"):
        body.append(f"  _Standard: {finding.get('principle', '')} — {finding['citation_url']}_")
    return "\n".join(body)


def render_pr(number, entry):
    """Render one PR section: linked title + the review body the bot would post."""
    title = entry["title"]
    findings = sorted(entry["findings"], key=lambda f: SEV.get(f.get("severity"), 3))
    url = f"https://github.com/{REPO}/pull/{number}"

    out = [f"## [#{number} — {title}]({url})", ""]
    out.append("> " + HEADER.replace("\n", "\n> "))
    out.append("")
    if findings:
        out.append(f"**{len(findings)} finding(s)** against the project's coding standards.")
        counts = ", ".join(
            f"{sum(1 for f in findings if f['severity'] == s)}× {s}"
            for s in ("CRITICAL", "PROBLEM", "SUGGESTION")
            if any(f["severity"] == s for f in findings)
        )
        out.append(f"<sub>{counts}</sub>")
        out.append("")
        out += [finding_block(f) for f in findings]
    else:
        out.append("**No standards violations found.** "
                    "The change was reviewed against the standards and passed clean.")
    out.append("")
    return "\n".join(out)


def main():
    """Build the showcase document from example_findings.json."""
    data = json.loads((HERE / "example_findings.json").read_text(encoding="utf-8"))
    total = sum(len(data[n]["findings"]) for n in ORDER)
    clean = sum(1 for n in ORDER if not data[n]["findings"])

    header = [
        "# Automated PR Review — example output",
        "",
        "Sample reviews produced by running real open Music Assistant PRs through the "
        "**Automated PR Review** bot locally. Each review is checked against the project's "
        "own coding standards — distilled from this repo's review history, `AGENTS.md`, "
        "`copilot-instructions.md`, and the pre-commit config — and every finding links "
        "back to where that standard was established.",
        "",
        f"**{len(ORDER)} PRs reviewed · {total} findings raised · {clean} passed clean.** "
        "Findings map to the existing `[CRITICAL]` / `[PROBLEM]` / `[SUGGESTION]` taxonomy; "
        "when posted, line-anchored findings attach as inline review comments on the diff.",
        "",
        "The bot deliberately **skips anything pre-commit/CI already catches** and does not "
        "invent nitpicks — note the two clean passes at the end.",
        "",
        "---",
        "",
    ]
    body = "\n---\n\n".join(render_pr(n, data[n]) for n in ORDER)
    (HERE / "automated-pr-review-examples.md").write_text(
        "\n".join(header) + body, encoding="utf-8",
    )
    print(f"wrote automated-pr-review-examples.md — {len(ORDER)} PRs, {total} findings, {clean} clean")


if __name__ == "__main__":
    main()
