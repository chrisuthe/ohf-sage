"""Post OHF Sage findings (the JSON array Copilot CLI printed to stdout) as a PR review.

Env: REPO=owner/name, PR_NUMBER=<n>, GH_TOKEN with pull-requests:write.
Usage: python sage_post_review.py findings.json
Findings anchored to a real diff line become inline comments; the rest go in the summary.
"""
import json
import os
import re
import subprocess
import sys

SEV = {"CRITICAL": 0, "PROBLEM": 1, "SUGGESTION": 2}


def gh(args, inp=None):
    p = subprocess.run(["gh"] + args, input=inp, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError(p.stderr.strip())
    return p.stdout


def extract_findings(raw):
    """Pull the first JSON array out of the CLI output (tolerant of stray prose)."""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def summary_line(f):
    cite = f.get("citation_url")
    loc = f"`{f.get('path','—')}`" + (f":{f['line']}" if isinstance(f.get("line"), int) else "")
    return (f"- **[{f.get('severity','SUGGESTION')}]** {loc} — {f.get('issue','')}"
            + (f" ([source]({cite}))" if cite else ""))


def main():
    repo, pr = os.environ["REPO"], os.environ["PR_NUMBER"]
    raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    findings = sorted(extract_findings(raw), key=lambda f: SEV.get(f.get("severity"), 3))

    header = ["## OHF Sage review", "",
              (f"{len(findings)} finding(s) against the project leads' cited principles."
               if findings else "No principle violations found."), ""]

    comments, overflow = [], []
    for f in findings:
        body = f"**[{f.get('severity','SUGGESTION')}]** {f.get('issue','')}"
        if f.get("citation_url"):
            body += f"\n\n_Principle: {f.get('principle','')} — {f['citation_url']}_"
        if f.get("path") and isinstance(f.get("line"), int):
            comments.append({"path": f["path"], "line": f["line"], "side": "RIGHT", "body": body})
        else:
            overflow.append(summary_line(f))

    body = header + (["### Not anchored to diff lines", *overflow] if overflow else [])

    def post(payload):
        gh(["api", f"repos/{repo}/pulls/{pr}/reviews", "-X", "POST", "--input", "-"],
           inp=json.dumps(payload))

    payload = {"body": "\n".join(body), "event": "COMMENT"}
    if comments:
        payload["comments"] = comments
    try:
        post(payload)
        print(f"posted review: {len(comments)} inline, {len(overflow)} in summary")
    except RuntimeError as e:
        # Inline comments 422 when a line isn't in the diff hunks — fall back to summary-only.
        print(f"inline post failed ({e}); posting summary-only", file=sys.stderr)
        post({"body": "\n".join(header + [summary_line(f) for f in findings]), "event": "COMMENT"})
        print("posted summary-only review")


if __name__ == "__main__":
    main()
