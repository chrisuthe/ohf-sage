# ruff: noqa: INP001, T201, E501  # local showcase helper
"""Render #5079 (broadened suggestions + test scaffolds) through the REAL post_pr_review.py.

Feeds the reviewer's findings into the poster in capture mode (no gh call) and writes the
exact review body + inline comments the bot would post, into a shareable Markdown file.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POSTER = Path("C:/CodeProjects/server-sage-pilot/.github/scripts/post_pr_review.py")

# The findings the reviewer produced on the broadened+scaffold re-run of #5079.
FINDINGS = [
    {
        "severity": "PROBLEM",
        "path": "music_assistant/providers/local_audio_source/provider.py",
        "line": None,
        "issue": "This PR adds a large new provider (708-line provider.py plus setup flow, PA capture wrappers, and helpers) with no tests under tests/. Deterministic logic such as _pcm_rms_dbfs (silence vs full-scale dBFS), enumerate_pa_sources sample_specification parsing (including the s24-32le=32 case the code comments call out), and _resolve_audio_format's bit-depth-to-ContentType mapping is readily unit-testable.",
        "principle": "New functionality MUST ship with tests added/updated under tests/, and pytest must stay green (a new provider follows the established tests/providers/<name>/ convention).",
        "citation_url": "https://github.com/music-assistant/server/blob/HEAD/.github/PULL_REQUEST_TEMPLATE.md",
        "suggestion": None,
        "scaffold": '"""Tests for the Local Audio Source plugin."""\n\nfrom __future__ import annotations\n\nfrom unittest.mock import patch\n\nimport numpy as np\n\nfrom music_assistant.providers.local_audio_source.pa_simple import enumerate_pa_sources\nfrom music_assistant.providers.local_audio_source.provider import _pcm_rms_dbfs\n\n\ndef test_pcm_rms_dbfs_silence_and_full_scale() -> None:\n    """Empty/silent PCM reads as -120 dBFS; a full-scale signal reads near 0 dBFS."""\n    assert _pcm_rms_dbfs(b"") == -120.0\n    silence = np.zeros(1024, dtype=np.int16).tobytes()\n    assert _pcm_rms_dbfs(silence) == -120.0\n    full_scale = np.full(1024, 32767, dtype=np.int16).tobytes()\n    assert _pcm_rms_dbfs(full_scale) > -0.5\n\n\ndef test_enumerate_pa_sources_parses_spec_and_flags_monitors() -> None:\n    """Sources parse bit depth from the PA format string and flag .monitor sources."""\n    fake = [\n        {"name": "alsa_input.usb", "description": "USB Mic", "sample_specification": "s24-32le 2ch 48000Hz"},\n        {"name": "alsa_output.hdmi.monitor", "description": "HDMI Monitor", "sample_specification": "s16le 2ch 44100Hz"},\n    ]\n    with patch(\n        "music_assistant.providers.local_audio_source.pa_simple.run_pactl_json",\n        return_value=fake,\n    ):\n        sources = enumerate_pa_sources()\n    assert sources[0]["bit_depth"] == 32\n    assert sources[0]["sample_rate"] == 48000\n    assert sources[1]["is_monitor"] is True\n',
    },
    {
        "severity": "SUGGESTION",
        "path": "music_assistant/providers/local_audio_source/helpers.py",
        "line": 21,
        "issue": "get_available_input_devices() catches FileNotFoundError/RuntimeError from pactl and silently returns [], so a missing or broken pactl surfaces to the user only as an empty device picker with no explanation. Its sibling _resolve_audio_format() in provider.py catches the same exception pair and logs a warning; this module-level function has no logger in scope, so it swallows the failure entirely.",
        "principle": "Never silently swallow errors or anomalous data — let it propagate or surface it; don't collapse a failure into a silent default.",
        "citation_url": "https://github.com/music-assistant/server/pull/1214#discussion_r1557137671",
        "suggestion": None,
        "scaffold": None,
    },
]


def render():
    """Drive the real poster in capture mode and write the demo Markdown."""
    spec = importlib.util.spec_from_file_location("ppr", POSTER)
    ppr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ppr)

    captured = {}
    ppr.post_review = lambda repo, pr, payload: captured.update(payload)  # noqa: ARG005
    tmp = HERE / "_scaffold_findings.json"
    tmp.write_text(json.dumps(FINDINGS), encoding="utf-8")
    os.environ["REPO"] = "music-assistant/server"
    os.environ["PR_NUMBER"] = "5079"
    sys.argv = ["p", str(tmp)]
    ppr.main()
    tmp.unlink()

    body = captured.get("body", "")
    comments = captured.get("comments", [])

    out = [
        "# Automated PR Review — broadened suggestions + test scaffolds",
        "",
        "Re-run of [#5079](https://github.com/music-assistant/server/pull/5079) with the widened "
        "rules, rendered through the actual `post_pr_review.py`. It shows two things at once:",
        "",
        "- a **test scaffold** attached to the missing-tests finding (a copy-paste pytest starter, "
        "not an auto-applied change);",
        "- the reviewer **declining** a logging suggestion where no logger is in scope — kept as "
        "prose instead of a wrong one-click fix.",
        "",
        "---",
        "",
        "## Review body (the summary the bot posts)",
        "",
        body,
        "",
        "---",
        "",
        f"## Inline comments ({len(comments)}) — anchored to diff lines",
        "",
    ]
    for c in comments:
        out.append(f"### `{c['path']}`:{c['line']}")
        out.append("")
        out.append(c["body"])
        out.append("")
    (HERE / "automated-pr-review-scaffold-demo.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote automated-pr-review-scaffold-demo.md — {len(comments)} inline, scaffold in body: {'```python' in body}")


if __name__ == "__main__":
    render()
