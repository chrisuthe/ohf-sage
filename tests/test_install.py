import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install import add_local_exclude, main  # noqa: E402


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


def test_install_ships_corpus_alongside_agent(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text("AGENT", encoding="utf-8")
    corpus = tmp_path / "ohf-sage-corpus.jsonl"
    corpus.write_text('{"body":"x"}\n', encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / ".git" / "info").mkdir(parents=True)

    main([str(repo), "--agent", str(agent), "--corpus", str(corpus)])

    assert (repo / ".claude" / "agents" / "ohf-sage.md").exists()
    assert (repo / ".claude" / "agents" / "ohf-sage-corpus.jsonl").exists()


def test_no_corpus_installs_agent_only(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text("AGENT", encoding="utf-8")
    corpus = tmp_path / "ohf-sage-corpus.jsonl"
    corpus.write_text('{"body":"x"}\n', encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()

    main([str(repo), "--agent", str(agent), "--corpus", str(corpus), "--no-corpus"])

    assert (repo / ".claude" / "agents" / "ohf-sage.md").exists()
    assert not (repo / ".claude" / "agents" / "ohf-sage-corpus.jsonl").exists()


def test_release_asset_url():
    from install import release_asset_url
    assert release_asset_url("chrisuthe/ohf-sage", "ohf-sage.md") == \
        "https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage.md"


def test_from_release_installs_downloaded_assets(tmp_path, monkeypatch):
    import install as inst
    # stub the network: "download" writes local placeholder files
    def fake_urlretrieve(url, dest):
        Path(dest).write_text("DOWNLOADED " + url, encoding="utf-8")
        return dest, None
    monkeypatch.setattr(inst.urllib.request, "urlretrieve", fake_urlretrieve)
    repo = tmp_path / "repo"; (repo / ".git" / "info").mkdir(parents=True)
    inst.main([str(repo), "--from-release"])
    assert (repo / ".claude" / "agents" / "ohf-sage.md").exists()
    assert (repo / ".claude" / "agents" / "ohf-sage-corpus.jsonl").exists()


def test_from_release_reports_failure(tmp_path, monkeypatch, capsys):
    import install as inst
    def boom(url, dest):
        raise inst.urllib.error.URLError("no network")
    monkeypatch.setattr(inst.urllib.request, "urlretrieve", boom)
    repo = tmp_path / "repo"; repo.mkdir()
    rc = inst.main([str(repo), "--from-release"])
    assert rc == 1
    assert "could not download" in capsys.readouterr().err.lower()
