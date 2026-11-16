import http.client
import io
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install as inst  # noqa: E402
from install import add_local_exclude, main, point_at_corpus  # noqa: E402

MEMORY_URL = "https://music-assistant.github.io/pr-triage"


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Every test gets an empty home folder and no network."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    def no_network(url, timeout=None):
        raise urllib.error.URLError("network disabled in tests")
    monkeypatch.setattr(inst.urllib.request, "urlopen", no_network)
    return home


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


AGENT_WITH_CORPUS_REF = (
    "See `.claude/agents/ohf-sage-corpus.jsonl` next to you.\n"
    'Grep with path=".claude/agents/ohf-sage-corpus.jsonl".\n'
)


def test_install_points_agent_at_installed_corpus(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text(AGENT_WITH_CORPUS_REF, encoding="utf-8")
    corpus = tmp_path / "ohf-sage-corpus.jsonl"
    corpus.write_text('{"body":"x"}\n', encoding="utf-8")
    repo = tmp_path / "elsewhere"

    main([str(repo), "--agent", str(agent), "--corpus", str(corpus)])

    installed_corpus = repo / ".claude" / "agents" / "ohf-sage-corpus.jsonl"
    text = (repo / ".claude" / "agents" / "ohf-sage.md").read_text(encoding="utf-8")
    assert text.count(str(installed_corpus.resolve())) == 2
    assert 'path=".claude/agents' not in text


def test_no_corpus_leaves_the_relative_path_alone(tmp_path):
    # Without a corpus the agent must keep saying the history is unavailable,
    # not point at a file that was never installed.
    agent = tmp_path / "ohf-sage.md"
    agent.write_text(AGENT_WITH_CORPUS_REF, encoding="utf-8")
    repo = tmp_path / "repo"

    main([str(repo), "--agent", str(agent), "--no-corpus"])

    text = (repo / ".claude" / "agents" / "ohf-sage.md").read_text(encoding="utf-8")
    assert text == AGENT_WITH_CORPUS_REF


def test_point_at_corpus_is_idempotent(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text(AGENT_WITH_CORPUS_REF, encoding="utf-8")
    corpus = tmp_path / "ohf-sage-corpus.jsonl"
    corpus.write_text("", encoding="utf-8")

    assert point_at_corpus(agent, corpus) is True
    once = agent.read_text(encoding="utf-8")
    assert point_at_corpus(agent, corpus) is False
    assert agent.read_text(encoding="utf-8") == once


def test_point_at_corpus_skips_an_agent_without_the_reference(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text("AGENT", encoding="utf-8")

    assert point_at_corpus(agent, tmp_path / "ohf-sage-corpus.jsonl") is False


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


def test_note_when_corpus_absent(tmp_path, capsys):
    import install as inst
    agent = tmp_path / "ohf-sage.md"; agent.write_text("A", encoding="utf-8")
    repo = tmp_path / "repo"; repo.mkdir()
    inst.main([str(repo), "--agent", str(agent), "--corpus", str(tmp_path / "nope.jsonl")])
    assert "no local corpus" in capsys.readouterr().err.lower()


class _Response(io.BytesIO):
    """What urlopen returns: the body, and the address it finally came from."""

    def __init__(self, body, url):
        super().__init__(body)
        self.url = url


def _install(tmp_path):
    agent = tmp_path / "ohf-sage.md"
    agent.write_text("AGENT", encoding="utf-8")
    repo = tmp_path / "repo"
    return repo, inst.main([str(repo), "--agent", str(agent), "--no-corpus"])


def test_install_fetches_the_shared_memory(tmp_path, monkeypatch, home):
    timeouts = []

    def fake_urlopen(url, timeout=None):
        timeouts.append(timeout)
        return _Response(b"BODY " + url.encode() + b"\n", url)
    monkeypatch.setattr(inst.urllib.request, "urlopen", fake_urlopen)

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert (home / ".claude/skills/ma-shared-memory/SKILL.md").read_bytes() == \
        f"BODY {MEMORY_URL}/skill/SKILL.md\n".encode()
    assert (home / ".ma-shared-memory/index.md").read_bytes() == f"BODY {MEMORY_URL}/index.md\n".encode()
    assert (home / ".ma-shared-memory/memory.md").read_bytes() == f"BODY {MEMORY_URL}/memory.md\n".encode()
    assert len(timeouts) == 3 and all(t and t > 0 for t in timeouts)


@pytest.mark.parametrize("error", [
    urllib.error.URLError("no network"),
    TimeoutError("timed out"),
    http.client.IncompleteRead(b"half"),
])
def test_failed_downloads_do_not_fail_the_install(tmp_path, monkeypatch, capsys, home, error):
    def boom(url, timeout=None):
        raise error
    monkeypatch.setattr(inst.urllib.request, "urlopen", boom)

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert (repo / ".claude" / "agents" / "ohf-sage.md").exists()
    assert not (home / ".ma-shared-memory").exists()
    assert not (home / ".claude").exists()
    err = capsys.readouterr().err
    assert err.count("could not download") == 3
    assert f"{MEMORY_URL}/index.md" in err


def test_one_failed_download_does_not_stop_the_others(tmp_path, monkeypatch, home):
    def fake_urlopen(url, timeout=None):
        if url.endswith("/index.md"):
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return _Response(b"BODY", url)
    monkeypatch.setattr(inst.urllib.request, "urlopen", fake_urlopen)

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert (home / ".claude/skills/ma-shared-memory/SKILL.md").exists()
    assert (home / ".ma-shared-memory/memory.md").exists()
    assert not (home / ".ma-shared-memory/index.md").exists()


class _DroppedConnection:
    """A response whose body never arrives whole."""

    url = MEMORY_URL

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, *args):
        raise http.client.IncompleteRead(b"half")


def test_failed_download_keeps_the_copy_on_disk(tmp_path, monkeypatch, home):
    saved = home / ".ma-shared-memory" / "index.md"
    saved.parent.mkdir()
    saved.write_bytes(b"OLD")
    monkeypatch.setattr(inst.urllib.request, "urlopen", lambda url, timeout=None: _DroppedConnection())

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert saved.read_bytes() == b"OLD"


def test_unwritable_destination_does_not_fail_the_install(tmp_path, monkeypatch, capsys, home):
    (home / ".ma-shared-memory").write_text("a file where the folder should be", encoding="utf-8")
    monkeypatch.setattr(inst.urllib.request, "urlopen", lambda url, timeout=None: _Response(b"BODY", url))

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert (home / ".claude/skills/ma-shared-memory/SKILL.md").exists()
    assert capsys.readouterr().err.count("could not download") == 2


def test_download_redirected_off_https_is_refused(tmp_path, monkeypatch, capsys, home):
    monkeypatch.setattr(inst.urllib.request, "urlopen",
                        lambda url, timeout=None: _Response(b"TAMPERED", "http://example.org/SKILL.md"))

    repo, rc = _install(tmp_path)

    assert rc == 0
    assert not (home / ".claude").exists()
    assert not (home / ".ma-shared-memory").exists()
    err = capsys.readouterr().err
    assert err.count("could not download") == 3
    assert "not HTTPS" in err
