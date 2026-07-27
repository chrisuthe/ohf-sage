# ohf_principles/github.py
import json
import subprocess
import sys


class GhError(RuntimeError):
    pass


def _run(args):
    proc = subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise GhError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return proc.stdout


def gh_api_items(path):
    """Yield each element of a paginated array endpoint."""
    out = _run(["gh", "api", "--paginate", "--jq", ".[]", path])
    for line in out.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def gh_api_json(path):
    return json.loads(_run(["gh", "api", path]))


def fetch_review_comments(repo):
    yield from gh_api_items(f"repos/{repo}/pulls/comments?per_page=100")


def fetch_issue_comments(repo):
    yield from gh_api_items(f"repos/{repo}/issues/comments?per_page=100")


def search_reviewed_prs(repo, authority, limit):
    """The `limit` most-recently-updated PRs in `repo` reviewed by `authority`.

    Returns a list of dicts with `number` and `title`. `gh search prs --json`
    emits a single JSON array, so parse it whole.
    """
    out = _run([
        "gh", "search", "prs", "--repo", repo, "--reviewed-by", authority,
        "--sort", "updated", "--limit", str(limit), "--json", "number,title",
    ])
    return json.loads(out)


def fetch_reviews(repo, authorities, limit):
    """Yield (review_dict, pr_number, pr_title) for reviews with a non-empty body,
    across the deduped union of PRs reviewed by any authority (each capped at
    `limit`, newest-first). A search that fails for one authority is skipped."""
    titles = {}
    for authority in authorities:
        try:
            for pr in search_reviewed_prs(repo, authority, limit):
                titles.setdefault(pr["number"], pr.get("title", ""))
        except GhError as e:
            print(f"  ! review search failed for {repo} reviewed-by:{authority}: {e}",
                  file=sys.stderr)
    for number, title in titles.items():
        for review in gh_api_items(f"repos/{repo}/pulls/{number}/reviews?per_page=100"):
            if (review.get("body") or "").strip():
                yield review, number, title


def not_planned_issue_numbers(repo):
    nums = set()
    for issue in gh_api_items(f"repos/{repo}/issues?state=closed&per_page=100"):
        if issue.get("pull_request") is None and issue.get("state_reason") == "not_planned":
            nums.add(issue["number"])
    return nums
