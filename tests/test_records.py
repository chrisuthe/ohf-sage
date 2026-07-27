from ohf_principles.records import is_authority, is_substantive, shape_record, extract_reactions


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
    assert set(rec) == {"repo", "kind", "author", "created_at", "html_url", "context", "body", "reactions", "adopted"}


def test_extract_reactions_reads_plus_and_total():
    item = {"reactions": {"+1": 3, "-1": 0, "total_count": 4}}
    assert extract_reactions(item) == {"plus": 3, "total": 4}


def test_extract_reactions_defaults_zero_when_absent():
    assert extract_reactions({}) == {"plus": 0, "total": 0}
    assert extract_reactions({"reactions": None}) == {"plus": 0, "total": 0}


def test_shape_record_includes_reactions_and_adopted():
    rec = shape_record(
        kind="review_comment", repo="r", author="a", created_at="t",
        html_url="u", body="a substantive body that is definitely long enough here",
        context="c", reactions={"plus": 2, "total": 2}, adopted=True,
    )
    assert rec["reactions"] == {"plus": 2, "total": 2}
    assert rec["adopted"] is True


def test_shape_record_reactions_default_when_omitted():
    rec = shape_record(
        kind="review_comment", repo="r", author="a", created_at="t",
        html_url="u", body="another sufficiently long substantive body text here",
        context="c",
    )
    assert rec["reactions"] == {"plus": 0, "total": 0}
    assert rec["adopted"] is None
