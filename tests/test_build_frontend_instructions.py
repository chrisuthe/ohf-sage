import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_frontend_instructions import _keep  # noqa: E402


def test_keep_drops_an_authored_rule_the_readme_already_covers():
    assert not _keep("- **MUST** support Python 3.11 for the packaged distribution. [authored]")


def test_keep_retains_an_authored_rule_the_maintainers_placed_in_the_shard():
    assert _keep(
        "- **MUST** style with Tailwind utility classes first; a scoped `<style>` block is for "
        'what utilities cannot express. See "Tailwind first" in the README. [authored]'
    )
