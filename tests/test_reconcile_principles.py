import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from reconcile_principles import (  # noqa: E402
    find_new_providers,
    find_reversals,
    load_snapshot,
    parse_prohibition_rules,
    provider_name_variants,
    render_report,
    save_snapshot,
)

MD = """\
## General standards
- **MUST** raise from MA's own typed exception hierarchy. ([server#1](url): "x") [mined · 2 PRs]
- **Won't support** acting as a general Plex client clone. ([server#2](url): "no") [mined · 1 PR]
- **Prefer** early returns over nested conditionals. [authored]
"""


def test_parse_prohibition_rules_selects_only_prohibitions():
    rules = parse_prohibition_rules(MD)
    assert len(rules) == 1
    assert "Won't support" in rules[0]
    assert "Plex" in rules[0]


def test_find_reversals_flags_prohibition_naming_a_shipped_provider():
    rules = ["- **Won't support** acting as a general Plex client clone. [mined · 1 PR]"]
    findings = find_reversals(rules, {"plex", "spotify"})
    assert len(findings) == 1
    assert findings[0]["provider"] == "plex"


def test_find_reversals_ignores_rule_that_acknowledges_the_provider_is_supported():
    # The line-81 shape: prohibition marker, but the text says these ARE supported.
    rules = [
        "- **Won't support** replicating HA features — media libraries "
        "(Plex, Emby, Jellyfin) are supported via dedicated providers. [mined · 1 PR]"
    ]
    findings = find_reversals(rules, {"plex", "emby", "jellyfin"})
    assert findings == []


def test_find_reversals_ignores_policy_prohibitions():
    rules = ["- **Won't support** bypassing a provider's DRM, paid tier, or ToS. [mined · 4 PRs]"]
    findings = find_reversals(rules, {"plex", "spotify"})
    assert findings == []


def test_find_reversals_ignores_provider_named_only_in_a_parenthetical_example():
    # real shape: bans the free *tier*, names Spotify only as an example
    rules = [
        "- **Won't support** free/basic streaming accounts (e.g. Spotify Free, "
        "YouTube Music free) — a paid account is required. [mined · 4 PRs]"
    ]
    assert find_reversals(rules, {"spotify"}) == []


def test_find_reversals_ignores_provider_named_as_the_endorsed_option():
    rules = [
        "- **Won't support** cloning LMS quirk-for-quirk — support only the "
        "reference client (e.g. squeezelite). [mined · 3 PRs]"
    ]
    assert find_reversals(rules, {"squeezelite"}) == []


def test_find_reversals_ignores_provider_named_as_the_preferred_alternative():
    rules = [
        "- **Won't support** fully fixing every quirk of flaky protocols (DLNA) — "
        "prefer AirPlay when a device offers both. [mined · 3 PRs]"
    ]
    assert find_reversals(rules, {"airplay"}) == []


def test_provider_name_variants_covers_opensubsonic_and_underscores():
    assert "subsonic" in provider_name_variants("opensubsonic")
    assert "apple music" in provider_name_variants("apple_music")


def test_find_new_providers_flags_a_new_unreferenced_provider():
    findings = find_new_providers({"plex", "newthing"}, {"plex"}, "principles text without it")
    assert [f["provider"] for f in findings] == ["newthing"]


def test_find_new_providers_ignores_new_provider_already_named_in_principles():
    findings = find_new_providers({"plex", "tidal"}, {"plex"}, "we support Tidal via a provider")
    assert findings == []


def test_find_new_providers_first_run_is_baseline_only():
    # Empty snapshot => first run: record the baseline, flag nothing.
    findings = find_new_providers({"plex", "tidal"}, set(), "text")
    assert findings == []


def test_find_new_providers_skips_demo_scaffolding():
    findings = find_new_providers({"_demo_music_provider"}, {"plex"}, "text")
    assert findings == []


def test_snapshot_roundtrip(tmp_path):
    state = tmp_path / "state.json"
    save_snapshot({"plex", "tidal"}, state)
    assert load_snapshot(state) == {"plex", "tidal"}


def test_load_snapshot_missing_file_returns_empty(tmp_path):
    assert load_snapshot(tmp_path / "nope.json") == set()


def _grow_section(report):
    return report.split("## GROW", 1)[1]


def test_render_report_lists_new_providers_without_spurious_none():
    report = render_report([], [{"provider": "foobar"}], first_run=False)
    assert "**foobar**" in report
    assert "_None._" not in _grow_section(report)


def test_render_report_shows_none_when_no_new_providers():
    report = render_report([], [], first_run=False)
    assert "_None._" in _grow_section(report)


def test_render_report_baseline_run_notes_snapshot():
    report = render_report([], [], first_run=True)
    assert "Baseline run" in _grow_section(report)
