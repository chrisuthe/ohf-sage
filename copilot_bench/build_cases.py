"""Build a benchmark test set of lead/maintainer-reviewed PRs.

Samples line-anchored review comments by the project leads/maintainers from the
mined corpus, then fetches each one's PR base SHA and the *commit the comment was
anchored to* (so reconstruction shows the code the lead actually reviewed, not the
PR's final head).
"""
import json
import re
import random
import sys

from ohf_principles import github

LEADS = {"marcelveldt", "marvinschenkel", "ozgav", "florianhorner"}
CORPUS = "agent/ohf-sage-corpus.jsonl"
OUT = "copilot_bench/cases.json"

# https://github.com/{owner}/{repo}/pull/{n}#discussion_r{id}
_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)#discussion_r(\d+)")


def _candidates():
    for line in open(CORPUS, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if (r.get("author") or "").lower() not in LEADS:
            continue
        m = _RE.match(r.get("html_url") or "")
        if not m:
            continue
        body = (r.get("body") or "").strip()
        if len(body) < 45:  # substantive only
            continue
        yield r, (m.group(1), int(m.group(2)), int(m.group(3)))


_ACK = re.compile(
    r"^(ok|okay|ah+|thanks|thx|good catch|fixed|all good|done|updated|nice|lgtm|"
    r"great|yes|yep|no problem|not an issue|agreed|correct|makes sense|sure|👍)",
    re.I,
)
_ISSUE = re.compile(
    r"\b(should|shouldn't|don't|do not|must|never|avoid|instead|why (are|is|do|would)|"
    r"broad|blocking|hammer|reuse|isn't|not needed|too (complex|verbose|much)|remove|"
    r"prefer|please (don't|do not|use|add|remove|keep|move)|this (is|will|would)|"
    r"we (don't|do not|can't|cannot|are not)|wrong|move this|belongs)\b",
    re.I,
)


def _is_issue_flag(c, body):
    if c.get("in_reply_to_id"):            # a reply in a thread, not a fresh flag
        return False
    if "```suggestion" in body:           # code suggestion, usually mechanical
        return False
    if _ACK.match(body.strip()):          # acknowledgement / resolution
        return False
    return bool(_ISSUE.search(body))      # reads like flagging a problem


def build(n=12, seed=7):
    pool = list(_candidates())
    random.seed(seed)
    random.shuffle(pool)
    cases = []
    for r, (repo, pr, cid) in pool:
        if len(cases) >= n:
            break
        try:
            c = github.gh_api_json(f"repos/{repo}/pulls/comments/{cid}")
        except github.GhError:
            continue
        body = (r.get("body") or "").strip()
        if not _is_issue_flag(c, body):
            continue
        try:
            prinfo = github.gh_api_json(f"repos/{repo}/pulls/{pr}")
        except github.GhError:
            continue
        review_commit = c.get("original_commit_id") or c.get("commit_id")
        if not review_commit:
            continue
        cases.append({
            "repo": repo,
            "pr": pr,
            "comment_id": cid,
            "author": r["author"],
            "base_sha": prinfo["base"]["sha"],
            "review_commit": review_commit,
            "path": c.get("path"),
            "line": c.get("line") or c.get("original_line"),
            "quote": " ".join((r.get("body") or "").split())[:220],
            "pr_state": prinfo.get("state"),
            "merged": prinfo.get("merged"),
        })
        print(f"  + {repo}#{pr} [{r['author']}] {c.get('path')}\n      {cases[-1]['quote'][:90]}",
              file=sys.stderr)
    json.dump(cases, open(OUT, "w"), indent=2)
    print(f"wrote {len(cases)} cases -> {OUT}")
    return cases


if __name__ == "__main__":
    build()
