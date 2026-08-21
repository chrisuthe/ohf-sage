# scripts/install.py
import argparse
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


_RELEASE_REPO = "chrisuthe/ohf-sage"
_RELEASE_ASSETS = ["ohf-sage.md", "ohf-sage-corpus.jsonl"]
_CORPUS_REL_PATH = ".claude/agents/ohf-sage-corpus.jsonl"


def release_asset_url(repo, asset):
    return f"https://github.com/{repo}/releases/latest/download/{asset}"


def download_release_assets(repo, dest_dir):
    """Download the release assets into dest_dir; return local paths. Raises on failure."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for asset in _RELEASE_ASSETS:
        dest = dest_dir / asset
        urllib.request.urlretrieve(release_asset_url(repo, asset), dest)
        paths.append(dest)
    return paths


def install(agent_path, repo_dir):
    agent_path = Path(agent_path)
    dest_dir = Path(repo_dir) / ".claude" / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / agent_path.name
    shutil.copyfile(agent_path, dest)
    return dest


def point_at_corpus(agent_dest, corpus_dest):
    """Rewrite the agent's corpus references to where the corpus was actually
    installed. Returns True if the agent was rewritten.

    The agent ships a project-relative corpus path, which only resolves when it
    is installed into a project and consulted from that project's root. Installed
    anywhere else (e.g. ~/.claude/agents/, so the agent is available everywhere),
    the grep finds nothing and the agent reports "no matching review history"
    rather than "no corpus" - a silent loss of retrieval that looks like a
    genuine no-match.
    """
    agent_dest, corpus_dest = Path(agent_dest), Path(corpus_dest).resolve()
    text = agent_dest.read_text(encoding="utf-8")
    if str(corpus_dest) in text:
        return False
    if _CORPUS_REL_PATH not in text:
        return False
    agent_dest.write_text(text.replace(_CORPUS_REL_PATH, str(corpus_dest)), encoding="utf-8")
    return True


def _resolve_git_dir(repo_dir):
    """Return the git directory that conventionally holds info/, HEAD,
    objects/, etc. for repo_dir, or None if repo_dir isn't a git repo.

    Handles a plain repo (`.git` is a directory) as well as a worktree or
    submodule checkout (`.git` is a file containing `gitdir: <path>`),
    following that gitdir's `commondir` file (if present) back to the
    shared/main git dir so worktrees share one `info/exclude`.
    """
    repo_dir = Path(repo_dir)
    git_path = repo_dir / ".git"
    if git_path.is_dir():
        return git_path
    if not git_path.is_file():
        return None

    m = re.match(r"gitdir:\s*(.+)", git_path.read_text(encoding="utf-8").strip())
    if not m:
        return None
    gitdir = Path(m.group(1).strip())
    if not gitdir.is_absolute():
        gitdir = repo_dir / gitdir
    gitdir = Path(os.path.normpath(gitdir))

    commondir_file = gitdir / "commondir"
    if commondir_file.is_file():
        commondir = Path(commondir_file.read_text(encoding="utf-8").strip())
        if not commondir.is_absolute():
            commondir = gitdir / commondir
        return Path(os.path.normpath(commondir))
    return gitdir


def add_local_exclude(repo_dir, dest):
    """Append dest's repo-relative path to the resolved git dir's
    info/exclude so it's never tracked by that repo's git. Returns the
    exclude file's Path, or None if repo_dir isn't a git repo."""
    repo_dir = Path(repo_dir)
    git_dir = _resolve_git_dir(repo_dir)
    if git_dir is None or not git_dir.is_dir():
        print("note: not a git repo (.git not found) - skipping --local-exclude")
        return None

    info_dir = git_dir / "info"
    info_dir.mkdir(exist_ok=True)  # git_dir already exists; info/ is just a subdir of it

    rel_path = Path(dest).resolve().relative_to(repo_dir.resolve()).as_posix()
    exclude_path = info_dir / "exclude"
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    lines = existing.splitlines()
    if rel_path in lines:
        return exclude_path

    prefix = existing if existing.endswith("\n") or not existing else existing + "\n"
    with exclude_path.open("w", encoding="utf-8") as f:
        f.write(prefix + rel_path + "\n")
    return exclude_path


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Install the advisor agent into a repo's .claude/agents/.")
    ap.add_argument("repo_dir")
    ap.add_argument("--agent", default=str(root / "agent/ohf-sage.md"))
    ap.add_argument("--corpus", default=str(root / "agent/ohf-sage-corpus.jsonl"),
                    help="review-history corpus shipped alongside the agent for retrieval")
    ap.add_argument("--no-corpus", action="store_true",
                    help="install the agent only, without the retrieval corpus")
    ap.add_argument("--from-release", action="store_true",
                    help="download the agent + corpus from the latest GitHub release instead of local files")
    ap.add_argument("--release-repo", default=_RELEASE_REPO,
                    help="owner/repo to pull the release from (default: chrisuthe/ohf-sage)")
    ap.add_argument("--local-exclude", action="store_true",
                    help="keep the installed files out of the target repo's git tracking "
                         "via .git/info/exclude, without modifying .gitignore")
    args = ap.parse_args(argv)

    if args.from_release:
        try:
            fetched = download_release_assets(args.release_repo, tempfile.mkdtemp(prefix="ohf-sage-rel-"))
        except (urllib.error.URLError, OSError) as e:
            print(f"error: could not download release assets from {args.release_repo}: {e}", file=sys.stderr)
            return 1
        by_name = {p.name: str(p) for p in fetched}
        args.agent = by_name["ohf-sage.md"]
        args.corpus = by_name["ohf-sage-corpus.jsonl"]

    agent_dest = install(args.agent, args.repo_dir)
    installed = [agent_dest]
    corpus_path = Path(args.corpus)
    if not args.no_corpus and corpus_path.is_file():
        corpus_dest = install(str(corpus_path), args.repo_dir)
        installed.append(corpus_dest)
        point_at_corpus(agent_dest, corpus_dest)
    for dest in installed:
        print(f"installed -> {dest}")
    if args.local_exclude:
        for dest in installed:
            exclude_path = add_local_exclude(args.repo_dir, dest)
            if exclude_path:
                print(f"excluded -> {dest.name}")
    if not args.no_corpus and not args.from_release and not corpus_path.is_file():
        print("note: no local corpus found; installed the agent only. "
              "Run with --from-release to also fetch the review-history corpus.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
