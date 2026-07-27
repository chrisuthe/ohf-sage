from ohf_principles.search import score, search, _tokens, main


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


def test_main_falls_back_to_shipped_corpus_when_no_local_harvest(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.chdir(tmp_path)
    # Create agent/ohf-sage-corpus.jsonl with one matching record
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    corpus_file = agent_dir / "ohf-sage-corpus.jsonl"
    rec = _rec("event loop blocking", author="marcelveldt")
    corpus_file.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    # No corpus/ directory exists
    # Run main with default corpus (no --corpus arg)
    result = main(["event"])
    assert result == 0, f"main() returned {result}, expected 0"
    captured = capsys.readouterr()
    # Verify output contains a hit
    assert "[marcelveldt]" in captured.out, f"expected author in output, got: {captured.out}"
    assert "event loop blocking" in captured.out or "blocking" in captured.out, f"expected snippet in output, got: {captured.out}"


def test_main_returns_1_when_explicit_corpus_glob_has_no_matches(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # Create a valid corpus file but search for something not in it
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    # No files in corpus/ that match the glob
    # Use an explicit --corpus glob that matches nothing
    result = main(["event", "--corpus", "nonexistent/*.jsonl"])
    assert result == 1, f"main() returned {result}, expected 1"
    captured = capsys.readouterr()
    assert "no corpus files match" in captured.err, f"expected error message, got: {captured.err}"
