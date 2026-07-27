import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_agent import build_agent  # noqa: E402


def _write(p, text):
    p.write_text(text, encoding="utf-8")
    return p


def test_build_agent_injects_between_markers(tmp_path):
    template = _write(tmp_path / "tpl.md", (
        "---\nname: x\n---\nHeader stays.\n"
        "<!-- PRINCIPLES:START -->\nOLD\n<!-- PRINCIPLES:END -->\nFooter stays.\n"
    ))
    principles = _write(tmp_path / "p.md", "# Title Drop\n\n## Overall\n- **MUST** do the thing.\n")
    out = tmp_path / "agent.md"
    result = build_agent(template, principles, out)
    assert "OLD" not in result
    assert "## Overall" in result
    assert "- **MUST** do the thing." in result
    assert "# Title Drop" not in result          # top header stripped
    assert "Header stays." in result and "Footer stays." in result
    assert "<!-- PRINCIPLES:START -->" in result and "<!-- PRINCIPLES:END -->" in result


def test_build_agent_requires_markers(tmp_path):
    template = _write(tmp_path / "tpl.md", "no markers here")
    principles = _write(tmp_path / "p.md", "# T\n\ncontent")
    import pytest
    with pytest.raises(ValueError):
        build_agent(template, principles, tmp_path / "o.md")
