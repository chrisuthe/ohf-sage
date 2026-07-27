import re
import sys

from . import github

# Order matters: fragment-specific patterns before the bare pull/issue patterns.
_PATTERNS = [
    (re.compile(r"github\.com/([^/]+)/([^/]+)/pull/\d+#discussion_r(\d+)"),
     lambda o, r, i: (f"repos/{o}/{r}/pulls/comments/{i}", "review_comment")),
    (re.compile(r"github\.com/([^/]+)/([^/]+)/(?:pull|issues)/\d+#issuecomment-(\d+)"),
     lambda o, r, i: (f"repos/{o}/{r}/issues/comments/{i}", "issue_comment")),
    (re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)#pullrequestreview-(\d+)"),
     lambda o, r, n, i: (f"repos/{o}/{r}/pulls/{n}/reviews/{i}", "review")),
    (re.compile(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:$|[?#])"),
     lambda o, r, n: (f"repos/{o}/{r}/pulls/{n}", "pull_request")),
    (re.compile(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:$|[?#])"),
     lambda o, r, n: (f"repos/{o}/{r}/issues/{n}", "issue")),
]


def resolve_url(url):
    """Map a GitHub PR/comment/issue URL to its gh api endpoint + kind, or None."""
    for pat, fn in _PATTERNS:
        m = pat.search(url or "")
        if m:
            owner, repo = m.group(1), m.group(2)
            api_path, kind = fn(*m.groups())
            return {"api_path": api_path, "kind": kind, "repo": f"{owner}/{repo}"}
    return None


def fetch_by_url(url):
    """Fetch the comment/PR/issue behind a GitHub URL. None on unrecognized URL / gh error."""
    resolved = resolve_url(url)
    if resolved is None:
        return None
    try:
        data = github.gh_api_json(resolved["api_path"])
    except github.GhError:
        return None
    return {
        "author": (data.get("user") or {}).get("login"),
        "body": data.get("body") or "",
        "html_url": data.get("html_url"),
        "repo": resolved["repo"],
        "kind": resolved["kind"],
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m ohf_principles.capture <github-url>", file=sys.stderr)
        return 2
    rec = fetch_by_url(argv[0])
    if rec is None:
        print("could not fetch (unrecognized URL or gh error)", file=sys.stderr)
        return 1
    print(f"author: {rec['author']}\nurl: {rec['html_url']}\nkind: {rec['kind']}\n\n{rec['body']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
