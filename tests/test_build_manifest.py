import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_manifest import build_manifest  # noqa: E402


def test_build_manifest_counts_by_repo(tmp_path):
    (tmp_path / "a.jsonl").write_text(
        '{"repo":"music-assistant/server","body":"x"}\n'
        '{"repo":"music-assistant/server","body":"y"}\n', encoding="utf-8")
    (tmp_path / "b.jsonl").write_text(
        '{"repo":"music-assistant/support","body":"z"}\n\n', encoding="utf-8")
    m = build_manifest(str(tmp_path / "*.jsonl"), "2026-07-30")
    assert m["generated"] == "2026-07-30"
    assert m["total"] == 3
    assert m["repos"] == {"music-assistant/server": 2, "music-assistant/support": 1}


def test_build_manifest_skips_malformed(tmp_path):
    (tmp_path / "a.jsonl").write_text('{"repo":"r","body":"x"}\nNOT JSON\n', encoding="utf-8")
    m = build_manifest(str(tmp_path / "*.jsonl"), "2026-07-30")
    assert m["total"] == 1 and m["repos"] == {"r": 1}
