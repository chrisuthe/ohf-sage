"""Reconcile principles.md against the current music-assistant/server dev tree.

Two on-demand checks, emitted as a review report (this never edits principles.md;
that stays human/distill-authored):

  RETRACT — scope/capability prohibitions the dev tree now contradicts: a rule that
            says we "won't support" a provider which has since shipped. Permanent
            *policy* stances (ToS, DRM, paid tier) are excluded — their reversal
            never manifests as code, so they must not be probed.
  GROW    — providers added since the last run that no rule names: new functionality
            that may want a standard. A snapshot (reconcile_state.json) makes this a
            delta, not a dump of all ~130 providers.

Provider dimension only for now; broader feature-area coverage is future work.

Usage:  python scripts/reconcile_principles.py   # prints the report, updates the snapshot
"""

import json
import re
from pathlib import Path

SERVER_REPO = "music-assistant/server"
PROVIDERS_PATH = "music_assistant/providers"
STATE_FILE = Path(__file__).resolve().parents[1] / "reconcile_state.json"
PRINCIPLES = Path(__file__).resolve().parents[1] / "principles" / "principles.md"

# A prohibition strength marker at the head of a rule bullet.
_PROHIBITION = re.compile(r"\*\*Won'?t support\*\*|\*\*MUST NOT\*\*", re.I)
# Permanent policy/value stances — their reversal never shows up as a provider.
_POLICY = re.compile(
    r"\b(bypass|drm|tos|terms of service|paid tier|piracy|pirated|illegal|"
    r"conventional[- ]commit|license header|copyright)\b",
    re.I,
)
# Language by which a rule acknowledges a provider IS supported (so it isn't a reversal).
_SUPPORTIVE = re.compile(
    r"\b(are|is) supported\b|\bsupported via\b|\bvia (?:a |dedicated )?provider", re.I
)


def _is_rule(line: str) -> bool:
    return line.lstrip().startswith("- **")


def parse_prohibition_rules(md_text: str) -> list[str]:
    """Return each rule bullet whose strength marker is a prohibition."""
    return [
        line.strip()
        for line in md_text.splitlines()
        if _is_rule(line) and _PROHIBITION.search(line)
    ]


def provider_name_variants(slug: str) -> set[str]:
    """Human-text forms a provider slug might appear as in prose (lowercased)."""
    variants = {slug, slug.replace("_", " "), slug.replace("_", "")}
    if slug.startswith("open") and len(slug) > 6:  # opensubsonic -> subsonic
        variants.add(slug[4:])
    return {v for v in variants if len(v) >= 3}


def _names_from(slugs: set[str]) -> dict[str, str]:
    """Map each recognizable provider name variant -> its slug (skips demo scaffolding)."""
    out: dict[str, str] = {}
    for slug in slugs:
        if slug.startswith("_demo"):
            continue
        for variant in provider_name_variants(slug):
            out.setdefault(variant, slug)
    return out


def _mentions(text: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", text, re.I) is not None


def _prohibited_object(rule: str) -> str:
    """The span naming what a prohibition targets: text after the strength marker,
    truncated at the first elaboration (em-dash), parenthetical example, sentence
    end, or citation. A provider named only *after* that boundary — as an endorsed
    alternative ("prefer AirPlay"), an example ("e.g. squeezelite"), or a tier
    qualifier ("Spotify Free") — is not what the rule prohibits."""
    match = _PROHIBITION.search(rule)
    text = rule[match.end():] if match else rule
    cut = len(text)
    for sep in ("—", " - ", "(", ". "):
        idx = text.find(sep)
        if idx != -1:
            cut = min(cut, idx)
    return text[:cut]


def find_reversals(rules: list[str], provider_slugs: set[str]) -> list[dict]:
    """Prohibition rules whose *prohibited object* names a provider now on dev."""
    names = _names_from(provider_slugs)
    findings = []
    for rule in rules:
        if _POLICY.search(rule) or _SUPPORTIVE.search(rule):
            continue  # permanent policy, or the rule already acknowledges support
        obj = _prohibited_object(rule)
        for name, slug in names.items():
            if _mentions(obj, name):
                findings.append({"provider": slug, "matched": name, "rule": rule})
                break  # one finding per rule
    return findings


def find_new_providers(current: set[str], snapshot: set[str], principles_text: str) -> list[dict]:
    """Providers added since the snapshot that no rule names. Empty snapshot = baseline run."""
    if not snapshot:
        return []
    findings = []
    for slug in sorted(current - snapshot):
        if slug.startswith("_demo"):
            continue
        if any(_mentions(principles_text, v) for v in provider_name_variants(slug)):
            continue
        findings.append({"provider": slug})
    return findings


def load_snapshot(path: Path = STATE_FILE) -> set[str]:
    """The provider set recorded on the last run, or empty if none."""
    path = Path(path)
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("providers", []))


def save_snapshot(current: set[str], path: Path = STATE_FILE) -> None:
    Path(path).write_text(
        json.dumps({"providers": sorted(current)}, indent=2) + "\n", encoding="utf-8"
    )


def list_providers(repo: str = SERVER_REPO) -> set[str]:
    """Provider subdirectory slugs on the repo's default branch (dev)."""
    from ohf_principles import github  # lazy: keeps the pure logic import-clean for tests

    data = github.gh_api_json(f"repos/{repo}/contents/{PROVIDERS_PATH}")
    return {e["name"] for e in data if e.get("type") == "dir"}


def render_report(reversals: list[dict], new_providers: list[dict], *, first_run: bool) -> str:
    out = ["# Principles reconcile report", ""]
    out.append(f"## RETRACT candidates ({len(reversals)})")
    out.append("Scope prohibitions the current dev tree contradicts — verify, then demote:")
    out.append("")
    if reversals:
        for f in reversals:
            out.append(f"- provider **{f['provider']}** ships on dev, but a rule prohibits it:")
            out.append(f"  > {f['rule']}")
    else:
        out.append("_None._")
    out.append("")
    out.append(f"## GROW — new providers ({len(new_providers)})")
    if first_run:
        out.append("_Baseline run: snapshot recorded, deltas start next run._")
    else:
        out.append("Providers added since the last run that no rule names — consider a standard:")
        out.append("")
        if new_providers:
            out.extend(f"- **{f['provider']}**" for f in new_providers)
        else:
            out.append("_None._")
    out.append("")
    return "\n".join(out)


def main() -> int:
    principles_text = PRINCIPLES.read_text(encoding="utf-8")
    snapshot = load_snapshot()
    current = list_providers()
    reversals = find_reversals(parse_prohibition_rules(principles_text), current)
    new_providers = find_new_providers(current, snapshot, principles_text)
    report = render_report(reversals, new_providers, first_run=not snapshot)
    out_path = Path(__file__).resolve().parents[1] / "reconcile-report.md"
    out_path.write_text(report, encoding="utf-8")  # report may carry emoji/em-dashes
    save_snapshot(current)
    grow = "baseline" if not snapshot else str(len(new_providers))
    print(f"RETRACT candidates: {len(reversals)} | GROW new providers: {grow} | "
          f"report: {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
