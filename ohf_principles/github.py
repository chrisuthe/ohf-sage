# ohf_principles/github.py
import json
import subprocess
import sys
import time


class GhError(RuntimeError):
    pass


_RATELIMIT_MARKERS = ("rate limit", "secondary rate", "abuse detection")


def _run(args, retries=4):
    for attempt in range(1, retries + 1):
        proc = subprocess.run(args, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return proc.stdout
        stderr = (proc.stderr or "").strip()
        if any(m in stderr.lower() for m in _RATELIMIT_MARKERS) and attempt < retries:
            wait = 30 * attempt
            print(f"  ... gh rate-limited, waiting {wait}s (attempt {attempt}/{retries})",
                  file=sys.stderr)
            time.sleep(wait)
            continue
        raise GhError(stderr or f"gh failed: {' '.join(args)}")


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
        try:
            reviews = list(gh_api_items(f"repos/{repo}/pulls/{number}/reviews?per_page=100"))
        except GhError as e:
            print(f"  ! reviews fetch failed for {repo}#{number}: {e}", file=sys.stderr)
            continue
        for review in reviews:
            if (review.get("body") or "").strip():
                yield review, number, title


def not_planned_issue_numbers(repo):
    nums = set()
    for issue in gh_api_items(f"repos/{repo}/issues?state=closed&per_page=100"):
        if issue.get("pull_request") is None and issue.get("state_reason") == "not_planned":
            nums.add(issue["number"])
    return nums


def fetch_file(repo, path):
    """Raw text of a file in the repo's default branch, or None if it 404s."""
    try:
        return _run(["gh", "api", f"repos/{repo}/contents/{path}",
                     "-H", "Accept: application/vnd.github.raw"])
    except GhError:
        return None


_REVIEW_THREADS_QUERY = (
    "query($owner:String!,$name:String!,$num:Int!){"
    "repository(owner:$owner,name:$name){"
    "pullRequest(number:$num){"
    "reviewThreads(first:100){nodes{isResolved comments(first:50){nodes{url}}}}}}}"
)


def _resolved_urls_from_graphql(data):
    urls = set()
    repo = (((data or {}).get("data") or {}).get("repository") or {})
    pr = repo.get("pullRequest") or {}
    threads = (pr.get("reviewThreads") or {}).get("nodes") or []
    for th in threads:
        if th and th.get("isResolved"):
            for c in (th.get("comments") or {}).get("nodes") or []:
                if c and c.get("url"):
                    urls.add(c["url"])
    return urls


def resolved_comment_urls(repo, pr_numbers):
    """Set of review-comment html_urls that sit in a resolved thread, across the PRs.

    Per-PR GraphQL failures are logged and skipped."""
    owner, name = repo.split("/", 1)
    resolved = set()
    for num in pr_numbers:
        try:
            out = _run(["gh", "api", "graphql",
                        "-f", "query=" + _REVIEW_THREADS_QUERY,
                        "-f", "owner=" + owner, "-f", "name=" + name,
                        "-F", "num=" + str(num)])
        except GhError as e:
            print(f"  ! reviewThreads query failed for {repo}#{num}: {e}", file=sys.stderr)
            continue
        resolved |= _resolved_urls_from_graphql(json.loads(out))
    return resolved
