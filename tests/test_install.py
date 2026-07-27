import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install import add_local_exclude  # noqa: E402


def test_local_exclude_appends_once_for_plain_git_dir(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git" / "info").mkdir(parents=True)
    dest = repo / ".claude" / "agents" / "ohf-sage.md"

    exclude_path = add_local_exclude(repo, dest)

    assert exclude_path == repo / ".git" / "info" / "exclude"
    lines = exclude_path.read_text(encoding="utf-8").splitlines()
    assert lines.count(".claude/agents/ohf-sage.md") == 1

    # Repeat install must not duplicate the line.
    add_local_exclude(repo, dest)
    lines = exclude_path.read_text(encoding="utf-8").splitlines()
    assert lines.count(".claude/agents/ohf-sage.md") == 1


def test_local_exclude_handles_gitdir_file_worktree(tmp_path):
    main_git = tmp_path / "main" / ".git"
    (main_git / "info").mkdir(parents=True)
    wt_gitdir = main_git / "worktrees" / "wt"
    wt_gitdir.mkdir(parents=True)
    (wt_gitdir / "commondir").write_text("../..\n", encoding="utf-8")

    wt_repo = tmp_path / "wt"
    wt_repo.mkdir()
    (wt_repo / ".git").write_text(f"gitdir: {wt_gitdir}\n", encoding="utf-8")
    dest = wt_repo / ".claude" / "agents" / "ohf-sage.md"

    exclude_path = add_local_exclude(wt_repo, dest)

    assert exclude_path == main_git / "info" / "exclude"
    lines = exclude_path.read_text(encoding="utf-8").splitlines()
    assert lines.count(".claude/agents/ohf-sage.md") == 1


def test_local_exclude_skips_non_git_dir(tmp_path):
    repo = tmp_path / "not_a_repo"
    repo.mkdir()
    dest = repo / ".claude" / "agents" / "ohf-sage.md"

    assert add_local_exclude(repo, dest) is None
