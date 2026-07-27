from ohf_principles.capture import resolve_url, fetch_by_url


def test_resolve_review_comment():
    r = resolve_url("https://github.com/music-assistant/server/pull/4804#discussion_r3582576959")
    assert r == {"api_path": "repos/music-assistant/server/pulls/comments/3582576959",
                 "kind": "review_comment", "repo": "music-assistant/server"}


def test_resolve_issue_comment_on_pull_and_issue():
    a = resolve_url("https://github.com/music-assistant/server/pull/4803#issuecomment-4974644693")
    b = resolve_url("https://github.com/music-assistant/support/issues/213#issuecomment-1134464508")
    assert a["api_path"] == "repos/music-assistant/server/issues/comments/4974644693"
    assert a["kind"] == "issue_comment"
    assert b["api_path"] == "repos/music-assistant/support/issues/comments/1134464508"


def test_resolve_review_summary():
    r = resolve_url("https://github.com/music-assistant/server/pull/3843#pullrequestreview-4785732510")
    assert r["api_path"] == "repos/music-assistant/server/pulls/3843/reviews/4785732510"
    assert r["kind"] == "review"


def test_resolve_bare_pull_and_issue():
    assert resolve_url("https://github.com/music-assistant/server/pull/4804") == {
        "api_path": "repos/music-assistant/server/pulls/4804", "kind": "pull_request",
        "repo": "music-assistant/server"}
    assert resolve_url("https://github.com/music-assistant/support/issues/213")["kind"] == "issue"


def test_resolve_specific_fragment_beats_bare_pull():
    # a discussion_r URL must NOT resolve to the bare-PR endpoint
    assert resolve_url(
        "https://github.com/o/r/pull/9#discussion_r5")["kind"] == "review_comment"


def test_resolve_junk_is_none():
    assert resolve_url("https://example.com/nope") is None
    assert resolve_url("not a url") is None


def test_fetch_by_url_none_on_unrecognized():
    assert fetch_by_url("https://example.com/nope") is None
