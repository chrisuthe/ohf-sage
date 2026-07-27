# scripts/install.py
import argparse
import os
import re
import shutil
from pathlib import Path


def install(agent_path, repo_dir):
    agent_path = Path(agent_path)
    dest_dir = Path(repo_dir) / ".claude" / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / agent_path.name
    shutil.copyfile(agent_path, dest)
    return dest


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
    ap.add_argument("--agent", default=str(root / "agent/ohf-principles-advisor.md"))
    ap.add_argument("--local-exclude", action="store_true",
                    help="keep the installed agent out of the target repo's git tracking "
                         "via .git/info/exclude, without modifying .gitignore")
    args = ap.parse_args(argv)
    dest = install(args.agent, args.repo_dir)
    print(f"installed -> {dest}")
    if args.local_exclude:
        exclude_path = add_local_exclude(args.repo_dir, dest)
        if exclude_path:
            print(f"excluded -> {exclude_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
