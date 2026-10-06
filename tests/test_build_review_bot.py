import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_review_bot import depersonalize  # noqa: E402


def test_depersonalize_rejects_a_stray_name():
    with pytest.raises(ValueError, match="Marcel"):
        depersonalize("- **MUST** do the thing, as Marcel asked.")


def test_depersonalize_lets_a_self_attributed_quote_through():
    line = '- **MUST** bump it. (Marcel: "the frontend ships in lockstep") [authored+mined]'
    assert depersonalize(line) == line


def test_depersonalize_still_rejects_a_name_beside_an_attributed_quote():
    with pytest.raises(ValueError, match="Marvin"):
        depersonalize('- **MUST** bump it. (Marcel: "the frontend ships in lockstep") per Marvin')
