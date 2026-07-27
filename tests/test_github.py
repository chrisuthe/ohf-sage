from ohf_principles.github import _resolved_urls_from_graphql


def test_resolved_urls_from_graphql_picks_only_resolved():
    data = {"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [
        {"isResolved": True, "comments": {"nodes": [{"url": "u-resolved"}]}},
        {"isResolved": False, "comments": {"nodes": [{"url": "u-open"}]}},
        {"isResolved": True, "comments": {"nodes": [{"url": "u-a"}, {"url": "u-b"}]}},
    ]}}}}}
    assert _resolved_urls_from_graphql(data) == {"u-resolved", "u-a", "u-b"}


def test_resolved_urls_from_graphql_handles_empty_or_missing():
    assert _resolved_urls_from_graphql({}) == set()
    assert _resolved_urls_from_graphql({"data": {"repository": {"pullRequest": None}}}) == set()
