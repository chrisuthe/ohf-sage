import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_corpus import build_corpus  # noqa: E402


def test_build_corpus_merges_and_counts(tmp_path):
    (tmp_path / "a.jsonl").write_text('{"body":"one"}\n{"body":"two"}\n', encoding="utf-8")
    (tmp_path / "b.jsonl").write_text('{"body":"three"}\n', encoding="utf-8")
    out = tmp_path / "merged.jsonl"
    n = build_corpus(str(tmp_path / "*.jsonl"), str(out))
    assert n == 3
    lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3
    import json
    assert {json.loads(l)["body"] for l in lines} == {"one", "two", "three"}


def test_build_corpus_skips_blank_lines(tmp_path):
    (tmp_path / "a.jsonl").write_text('{"body":"x"}\n\n{"body":"y"}\n', encoding="utf-8")
    out = tmp_path / "m.jsonl"
    assert build_corpus(str(tmp_path / "*.jsonl"), str(out)) == 2
