# Automated PR Review — broadened suggestions + test scaffolds

Re-run of [#5079](https://github.com/music-assistant/server/pull/5079) with the widened rules, rendered through the actual `post_pr_review.py`. It shows two things at once:

- a **test scaffold** attached to the missing-tests finding (a copy-paste pytest starter, not an auto-applied change);
- the reviewer **declining** a logging suggestion where no logger is in scope — kept as prose instead of a wrong one-click fix.

---

## Review body (the summary the bot posts)

## 🤖 Automated PR Review

Reviewed against the project's coding standards. Each note links where the standard is documented.


**2 finding(s)** against the project's coding standards.

### Notes (not anchored to diff lines)

- **[PROBLEM]** `music_assistant/providers/local_audio_source/provider.py` — This PR adds a large new provider (708-line provider.py plus setup flow, PA capture wrappers, and helpers) with no tests under tests/. Deterministic logic such as _pcm_rms_dbfs (silence vs full-scale dBFS), enumerate_pa_sources sample_specification parsing (including the s24-32le=32 case the code comments call out), and _resolve_audio_format's bit-depth-to-ContentType mapping is readily unit-testable. ([source](https://github.com/music-assistant/server/blob/HEAD/.github/PULL_REQUEST_TEMPLATE.md))

<details><summary>Starter test — copy into tests/ and adapt</summary>

```python
"""Tests for the Local Audio Source plugin."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np

from music_assistant.providers.local_audio_source.pa_simple import enumerate_pa_sources
from music_assistant.providers.local_audio_source.provider import _pcm_rms_dbfs


def test_pcm_rms_dbfs_silence_and_full_scale() -> None:
    """Empty/silent PCM reads as -120 dBFS; a full-scale signal reads near 0 dBFS."""
    assert _pcm_rms_dbfs(b"") == -120.0
    silence = np.zeros(1024, dtype=np.int16).tobytes()
    assert _pcm_rms_dbfs(silence) == -120.0
    full_scale = np.full(1024, 32767, dtype=np.int16).tobytes()
    assert _pcm_rms_dbfs(full_scale) > -0.5


def test_enumerate_pa_sources_parses_spec_and_flags_monitors() -> None:
    """Sources parse bit depth from the PA format string and flag .monitor sources."""
    fake = [
        {"name": "alsa_input.usb", "description": "USB Mic", "sample_specification": "s24-32le 2ch 48000Hz"},
        {"name": "alsa_output.hdmi.monitor", "description": "HDMI Monitor", "sample_specification": "s16le 2ch 44100Hz"},
    ]
    with patch(
        "music_assistant.providers.local_audio_source.pa_simple.run_pactl_json",
        return_value=fake,
    ):
        sources = enumerate_pa_sources()
    assert sources[0]["bit_depth"] == 32
    assert sources[0]["sample_rate"] == 48000
    assert sources[1]["is_monitor"] is True
```

</details>

---

## Inline comments (1) — anchored to diff lines

### `music_assistant/providers/local_audio_source/helpers.py`:21

**[SUGGESTION]** get_available_input_devices() catches FileNotFoundError/RuntimeError from pactl and silently returns [], so a missing or broken pactl surfaces to the user only as an empty device picker with no explanation. Its sibling _resolve_audio_format() in provider.py catches the same exception pair and logs a warning; this module-level function has no logger in scope, so it swallows the failure entirely.

_Standard: Never silently swallow errors or anomalous data — let it propagate or surface it; don't collapse a failure into a silent default. — https://github.com/music-assistant/server/pull/1214#discussion_r1557137671_
