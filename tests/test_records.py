from ohf_principles.records import is_authority, is_substantive, shape_record


def test_is_authority_case_insensitive():
    allowed = {"marcelveldt", "marvinschenkel"}
    assert is_authority("MarvinSchenkel", allowed) is True
    assert is_authority("randomuser", allowed) is False
    assert is_authority(None, allowed) is False


def test_is_substantive_filters_trivial_and_short():
    assert is_substantive("LGTM") is False
    assert is_substantive("thanks!") is False
    assert is_substantive("x") is False
    assert is_substantive(None) is False
    assert is_substantive(
        "We never block the event loop here; move this I/O into an executor task."
    ) is True


def test_shape_record_has_expected_keys():
    rec = shape_record(
        kind="review_comment",
        repo="music-assistant/server",
        author="marcelveldt",
        created_at="2024-01-01T00:00:00Z",
        html_url="https://github.com/music-assistant/server/pull/1#r1",
        body="  do not add sync I/O in providers  ",
        context="pr#1 Add Foo provider",
    )
    assert rec["kind"] == "review_comment"
    assert rec["author"] == "marcelveldt"
    assert rec["body"] == "do not add sync I/O in providers"  # trimmed
    assert set(rec) == {"repo", "kind", "author", "created_at", "html_url", "context", "body"}
