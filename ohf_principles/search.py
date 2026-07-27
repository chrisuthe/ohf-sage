import argparse
import glob
import json
import re
import sys

_LEADS = {"marcelveldt", "marvinschenkel"}


def _tokens(query):
    return [t for t in re.split(r"[^\w]+", (query or "").lower()) if len(t) > 1]


def score(record, terms):
    body = (record.get("body") or "").lower()
    hits = sum(1 for t in terms if t in body)
    if hits == 0:
        return 0.0
    s = float(hits)
    if (record.get("author") or "").lower() in _LEADS:
        s += 2.0
    s += 0.1 * (record.get("reactions") or {}).get("plus", 0)
    return s


def _iter_records(corpus_paths):
    for path in corpus_paths:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def search(corpus_paths, query, repo=None, author=None, top=10):
    terms = _tokens(query)
    scored = []
    for rec in _iter_records(corpus_paths):
        if repo and rec.get("repo") != repo:
            continue
        if author and (rec.get("author") or "").lower() != author.lower():
            continue
        sc = score(rec, terms)
        if sc > 0:
            scored.append((sc, rec))
    scored.sort(key=lambda sr: sr[0], reverse=True)
    return [rec for _, rec in scored[:top]]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Search the mined review corpus.")
    ap.add_argument("query")
    ap.add_argument("--repo")
    ap.add_argument("--author")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--corpus", default="corpus/*.jsonl",
                    help="glob for corpus JSONL files (default: corpus/*.jsonl)")
    args = ap.parse_args(argv)
    paths = sorted(glob.glob(args.corpus))
    if not paths:
        print(f"no corpus files match {args.corpus}", file=sys.stderr)
        return 1
    hits = search(paths, args.query, repo=args.repo, author=args.author, top=args.top)
    for i, r in enumerate(hits, 1):
        snippet = " ".join((r.get("body") or "").split())[:160]
        print(f"{i:2d}. [{r.get('author')}] {r.get('html_url')}\n    {snippet}")
    if not hits:
        print("(no matches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
