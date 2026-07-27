from ohf_principles.search import score, search, _tokens


def _rec(body, author="someone", plus=0, repo="music-assistant/server"):
    return {"body": body, "author": author, "repo": repo, "html_url": "u",
            "reactions": {"plus": plus, "total": plus}}


def test_score_zero_when_no_term_hits():
    assert score(_rec("nothing relevant here"), ["asyncio", "event"]) == 0.0


def test_score_counts_term_hits():
    assert score(_rec("the event loop must not block"), ["event", "loop", "block"]) >= 3.0


def test_lead_outranks_non_lead_with_equal_hits():
    terms = ["event"]
    lead = score(_rec("event", author="marcelveldt"), terms)
    other = score(_rec("event", author="ozgav"), terms)
    assert lead > other


def test_reactions_add_small_bonus():
    terms = ["event"]
    assert score(_rec("event", plus=5), terms) > score(_rec("event", plus=0), terms)


def test_search_filters_and_ranks(tmp_path):
    import json
    p = tmp_path / "c.jsonl"
    recs = [
        _rec("event loop blocking", author="marcelveldt"),
        _rec("event handling", author="ozgav"),
        _rec("unrelated", author="marcelveldt"),
        _rec("event", author="ozgav", repo="music-assistant/frontend"),
    ]
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    out = search([str(p)], "event loop", top=10)
    assert out and out[0]["author"] == "marcelveldt"   # most hits + lead
    assert all("event" in r["body"] or "loop" in r["body"] for r in out)
    server_only = search([str(p)], "event", repo="music-assistant/server")
    assert all(r["repo"] == "music-assistant/server" for r in server_only)


def test_tokens_drops_short_and_punct():
    assert _tokens("Event-loop: a?") == ["event", "loop"]
