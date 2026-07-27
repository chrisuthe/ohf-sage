import pytest
from ohf_principles import github, harvest
from ohf_principles.github import GhError


class _Proc:
    def __init__(self, rc, out="", err=""):
        self.returncode = rc; self.stdout = out; self.stderr = err


def test_run_retries_on_rate_limit_then_succeeds(monkeypatch):
    calls = {"n": 0}; sleeps = []
    def fake_run(args, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Proc(1, err="You have exceeded a secondary rate limit")
        return _Proc(0, out="OK")
    monkeypatch.setattr(github.subprocess, "run", fake_run)
    monkeypatch.setattr(github.time, "sleep", lambda s: sleeps.append(s))
    assert github._run(["gh", "x"]) == "OK"
    assert calls["n"] == 2
    assert sleeps == [30]


def test_run_fails_fast_on_non_rate_limit(monkeypatch):
    calls = {"n": 0}; slept = []
    monkeypatch.setattr(github.subprocess, "run",
                        lambda args, **kw: (calls.__setitem__("n", calls["n"] + 1) or _Proc(1, err="Not Found")))
    monkeypatch.setattr(github.time, "sleep", lambda s: slept.append(s))
    with pytest.raises(GhError):
        github._run(["gh", "x"])
    assert calls["n"] == 1
    assert slept == []


def test_fetch_reviews_skips_failing_pr(monkeypatch):
    monkeypatch.setattr(github, "search_reviewed_prs",
                        lambda repo, auth, limit: [{"number": 1, "title": "a"}, {"number": 2, "title": "b"}])
    def fake_items(path):
        if "/pulls/1/" in path:
            raise GhError("boom")
        yield {"body": "real review body", "user": {"login": "marcelveldt"},
               "html_url": "u", "submitted_at": "t"}
    monkeypatch.setattr(github, "gh_api_items", fake_items)
    out = list(github.fetch_reviews("r", ["marcelveldt"], 5))
    assert len(out) == 1
    assert out[0][1] == 2


def test_harvest_repo_keeps_comments_when_reviews_fail(monkeypatch):
    monkeypatch.setattr(github, "fetch_review_comments",
                        lambda repo: [{"user": {"login": "marcelveldt"}, "created_at": "t",
                                       "html_url": "u", "pull_request_url": "p",
                                       "body": "Do not block the event loop in providers, ever please."}])
    monkeypatch.setattr(github, "fetch_issue_comments", lambda repo: [])
    monkeypatch.setattr(github, "not_planned_issue_numbers", lambda repo: set())
    def boom(*a, **k):
        raise GhError("rate limited out")
    monkeypatch.setattr(github, "fetch_reviews", boom)
    cfg = {"global_authorities": ["marcelveldt"], "defaults": {"harvest_reviews": True}}
    records = harvest.harvest_repo({"repo": "music-assistant/server", "authorities": []}, cfg)
    assert len(records) == 1
    assert records[0]["kind"] == "review_comment"
    assert records[0]["author"] == "marcelveldt"


def test_harvest_repo_keeps_records_when_review_comments_fetch_fails(monkeypatch):
    def failing_review_comments(repo):
        yield {"user": {"login": "marcelveldt"}, "created_at": "t",
               "html_url": "u", "pull_request_url": "p",
               "body": "Do not block the event loop in providers, ever please."}
        raise GhError("secondary rate limit exceeded")
    monkeypatch.setattr(github, "fetch_review_comments", failing_review_comments)
    monkeypatch.setattr(github, "fetch_issue_comments", lambda repo: [])
    monkeypatch.setattr(github, "not_planned_issue_numbers", lambda repo: set())
    monkeypatch.setattr(github, "fetch_reviews", lambda repo, authorities, limit: [])
    cfg = {"global_authorities": ["marcelveldt"], "defaults": {"harvest_reviews": True}}
    records = harvest.harvest_repo({"repo": "music-assistant/server", "authorities": []}, cfg)
    assert len(records) == 1
    assert records[0]["kind"] == "review_comment"
    assert records[0]["author"] == "marcelveldt"


def test_harvest_repo_keeps_review_comments_when_issue_comments_fetch_fails(monkeypatch):
    monkeypatch.setattr(github, "fetch_review_comments",
                        lambda repo: [{"user": {"login": "marcelveldt"}, "created_at": "t",
                                       "html_url": "u", "pull_request_url": "p",
                                       "body": "Do not block the event loop in providers, ever please."}])
    def failing_issue_comments(repo):
        raise GhError("secondary rate limit exceeded")
    monkeypatch.setattr(github, "fetch_issue_comments", failing_issue_comments)
    monkeypatch.setattr(github, "not_planned_issue_numbers", lambda repo: set())
    monkeypatch.setattr(github, "fetch_reviews", lambda repo, authorities, limit: [])
    cfg = {"global_authorities": ["marcelveldt"], "defaults": {"harvest_reviews": True}}
    records = harvest.harvest_repo({"repo": "music-assistant/server", "authorities": []}, cfg)
    assert len(records) >= 1
    assert any(r["kind"] == "review_comment" and r["author"] == "marcelveldt" for r in records)
