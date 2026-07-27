# ohf_principles/harvest.py
import argparse
import json
import re
import sys
from pathlib import Path

from .config import load_config, authorities_for
from .records import is_authority, is_substantive, shape_record
from . import github

_ISSUE_NUM = re.compile(r"/issues/(\d+)")


def _issue_number(url):
    m = _ISSUE_NUM.search(url or "")
    return int(m.group(1)) if m else None


def harvest_repo(repo_cfg, config):
    repo = repo_cfg["repo"]
    allowed = authorities_for(repo_cfg, config)
    defaults = config.get("defaults", {})
    records = []

    def keep(item):
        author = (item.get("user") or {}).get("login")
        return is_authority(author, allowed) and is_substantive(item.get("body"))

    # Inline review comments
    try:
        for c in github.fetch_review_comments(repo):
            if keep(c):
                records.append(shape_record(
                    "review_comment", repo, c["user"]["login"], c["created_at"],
                    c["html_url"], c["body"], context=c.get("pull_request_url", "")))
    except github.GhError as e:
        print(f"  ! review_comment harvest incomplete for {repo}: {e}", file=sys.stderr)

    # Rejected-feature issue numbers (for wont_support tagging)
    try:
        not_planned = github.not_planned_issue_numbers(repo)
    except github.GhError as e:
        print(f"  ! not_planned lookup failed for {repo}: {e}", file=sys.stderr)
        not_planned = set()

    # Issue + PR-thread comments
    try:
        for c in github.fetch_issue_comments(repo):
            if keep(c):
                n = _issue_number(c.get("issue_url"))
                kind = "wont_support" if n in not_planned else "issue_comment"
                records.append(shape_record(
                    kind, repo, c["user"]["login"], c["created_at"],
                    c["html_url"], c["body"], context=c.get("issue_url", "")))
    except github.GhError as e:
        print(f"  ! issue_comment harvest incomplete for {repo}: {e}", file=sys.stderr)

    # Review summaries (targeted via search, capped per authority)
    if defaults.get("harvest_reviews", True):
        limit = defaults.get("review_pr_limit", 250)
        try:
            for review, number, title in github.fetch_reviews(repo, sorted(allowed), limit):
                author = (review.get("user") or {}).get("login")
                if is_authority(author, allowed) and is_substantive(review.get("body")):
                    records.append(shape_record(
                        "review", repo, author, review.get("submitted_at", ""),
                        review["html_url"], review["body"], context=f"pr#{number} {title}"))
        except github.GhError as e:
            print(f"  ! review harvest incomplete for {repo}: {e}", file=sys.stderr)

    return records


def suggest_authorities(repo):
    counts = {}
    for c in github.fetch_review_comments(repo):
        login = (c.get("user") or {}).get("login")
        if login and not login.endswith("[bot]") and login != "Copilot":
            counts[login] = counts.get(login, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def _write_corpus(repo, records, out_dir):
    out = Path(out_dir) / (repo.replace("/", "__") + ".jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Harvest OHF principle signal from GitHub.")
    ap.add_argument("--config", default="config/sources.yaml")
    ap.add_argument("--repo", action="append", help="limit to this repo (repeatable)")
    ap.add_argument("--suggest-authorities", metavar="REPO")
    ap.add_argument("--out-dir", default="corpus")
    ap.add_argument("--review-limit", type=int, default=None,
                    help="override defaults.review_pr_limit (PRs/authority scanned for review summaries)")
    args = ap.parse_args(argv)

    if args.suggest_authorities:
        for login, n in suggest_authorities(args.suggest_authorities):
            print(f"{n:5d}  {login}")
        return 0

    config = load_config(args.config)
    if args.review_limit is not None:
        config.setdefault("defaults", {})["review_pr_limit"] = args.review_limit
    repos = config["repos"]
    if args.repo:
        wanted = set(args.repo)
        repos = [r for r in repos if r["repo"] in wanted]

    for repo_cfg in repos:
        repo = repo_cfg["repo"]
        try:
            records = harvest_repo(repo_cfg, config)
        except github.GhError as e:
            print(f"! skipping {repo}: {e}", file=sys.stderr)
            continue
        out = _write_corpus(repo, records, args.out_dir)
        print(f"{repo}: {len(records)} records -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
