# CI Auto-Refresh + Release Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the published corpus/agent current automatically — a scheduled GitHub Action re-harvests, rebuilds the corpus, and opens a reviewable manifest PR that (on merge) promotes a prerelease to the `latest` Release; the corpus is distributed as a Release asset (out of git); principles re-distill stays a local human step.

**Architecture:** The corpus (`agent/ohf-sage-corpus.jsonl`) is un-tracked from git and shipped as a GitHub Release asset. `refresh.yml` (weekly + manual) does a paced harvest → `build_corpus`/`build_manifest`/`build_agent` → publishes a prerelease + opens a PR touching only `corpus-manifest.json` (the reviewable stat deltas). `publish.yml` promotes that prerelease to `latest` when the PR merges. `install.py --from-release` fetches the assets over plain HTTPS.

**Tech Stack:** Python 3 (stdlib + existing `ohf_principles`), GitHub Actions, the `gh` CLI (in CI), `peter-evans/create-pull-request`. No LLM/`ANTHROPIC_API_KEY` in CI.

## Global Constraints

- **No third-party secrets** — only the built-in `${{ secrets.GITHUB_TOKEN }}` (reads public repos, writes PRs/releases in this repo). **No Claude/LLM in CI.**
- **Corpus is a Release asset, not a git blob** — `agent/ohf-sage-corpus.jsonl` is gitignored and un-tracked; CI ships it via Releases. `agent/ohf-sage.md` stays committed.
- **`corpus-manifest.json` is the reviewable diff** — per-repo record counts + total + date, committed.
- **Paced harvest in CI** — sequential per-repo with brief sleeps + a modest `--review-limit`, to stay under GitHub's secondary rate limits.
- **`--from-release` uses plain HTTPS** (stdlib `urllib`) on the public `releases/latest/download/` URLs — no `gh`, no auth.
- No new dependencies (stdlib only for code). Commit messages: no `Co-Authored-By` / AI attribution.
- Workflows validated with `python -c "import yaml; yaml.safe_load(...)"` (actionlint isn't available locally); the first real GitHub run is the end-to-end acceptance test.

## File Structure

```
scripts/build_manifest.py       # Task 1: corpus-manifest.json generator
tests/test_build_manifest.py    # Task 1
corpus-manifest.json            # Task 1: generated, committed
.gitignore                      # Task 1: + agent/ohf-sage-corpus.jsonl (un-tracked)
scripts/install.py              # Task 2: --from-release
tests/test_install.py           # Task 2
.github/workflows/refresh.yml   # Task 3
.github/workflows/publish.yml   # Task 3
README.md, INSTALL.md, DEVELOPING.md  # Task 4
```

---

### Task 1: `build_manifest.py` + un-track the corpus

**Files:**
- Create: `scripts/build_manifest.py`
- Test: `tests/test_build_manifest.py`
- Create (generated): `corpus-manifest.json`
- Modify: `.gitignore`
- Un-track: `agent/ohf-sage-corpus.jsonl`

**Interfaces:**
- `build_manifest(corpus_glob: str, now: str) -> dict` → `{"generated": now, "total": int, "repos": {repo: count}}` (repos sorted). Consumed by CI (Task 3).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_manifest.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_build_manifest.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement `scripts/build_manifest.py`**

```python
# scripts/build_manifest.py
import glob
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def build_manifest(corpus_glob, now):
    """Per-repo record counts (+ total, + generated date) across the corpus glob."""
    counts = Counter()
    for path in sorted(glob.glob(corpus_glob)):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            counts[rec.get("repo", "unknown")] += 1
    return {"generated": now, "total": sum(counts.values()),
            "repos": dict(sorted(counts.items()))}


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    argv = argv if argv is not None else sys.argv[1:]
    corpus_glob = argv[0] if len(argv) > 0 else str(root / "corpus" / "*.jsonl")
    out_path = argv[1] if len(argv) > 1 else str(root / "corpus-manifest.json")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    manifest = build_manifest(corpus_glob, now)
    Path(out_path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    print(f"manifest: {manifest['total']} records across {len(manifest['repos'])} repos -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_build_manifest.py -v`
Expected: 2 passed.

- [ ] **Step 5: Generate the initial manifest (from the local corpus)**

Run: `python scripts/build_manifest.py`
Expected: writes `corpus-manifest.json`; prints a total (~10.5k across the MA repos). If the local `corpus/` is empty, note it — the manifest will be generated for real in CI / on the first harvest.

- [ ] **Step 6: Un-track the shipped corpus + gitignore it**

```bash
git rm --cached agent/ohf-sage-corpus.jsonl
printf 'agent/ohf-sage-corpus.jsonl\n' >> .gitignore
```
(This removes the 6 MB blob from tracking going forward; the working file stays for local installs. Confirm: `git check-ignore agent/ohf-sage-corpus.jsonl` → prints the path.)

- [ ] **Step 7: Commit**

```bash
git add scripts/build_manifest.py tests/test_build_manifest.py corpus-manifest.json .gitignore
git rm --cached agent/ohf-sage-corpus.jsonl  # ensure staged as a deletion if not already
git commit -m "Add corpus manifest; ship corpus via releases instead of git"
```

---

### Task 2: `install.py --from-release`

**Files:**
- Modify: `scripts/install.py`
- Test: `tests/test_install.py`

**Interfaces:**
- `release_asset_url(repo, asset) -> str` — pure: `https://github.com/{repo}/releases/latest/download/{asset}`.
- `download_release_assets(repo, dest_dir) -> list[Path]` — downloads `ohf-sage.md` + `ohf-sage-corpus.jsonl` via `urllib.request.urlretrieve`; returns the local paths; raises on failure.
- `main()` gains `--from-release` and `--release-repo` (default `chrisuthe/ohf-sage`): when set, download the assets to a temp dir and install those (instead of local `agent/` files); a download failure prints an error and returns 1.

- [ ] **Step 1: Write the failing tests (append to `tests/test_install.py`, matching its existing `from install import …` style)**

```python
def test_release_asset_url():
    from install import release_asset_url
    assert release_asset_url("chrisuthe/ohf-sage", "ohf-sage.md") == \
        "https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage.md"


def test_from_release_installs_downloaded_assets(tmp_path, monkeypatch):
    import install as inst
    # stub the network: "download" writes local placeholder files
    def fake_urlretrieve(url, dest):
        Path(dest).write_text("DOWNLOADED " + url, encoding="utf-8")
        return dest, None
    monkeypatch.setattr(inst.urllib.request, "urlretrieve", fake_urlretrieve)
    repo = tmp_path / "repo"; (repo / ".git" / "info").mkdir(parents=True)
    inst.main([str(repo), "--from-release"])
    assert (repo / ".claude" / "agents" / "ohf-sage.md").exists()
    assert (repo / ".claude" / "agents" / "ohf-sage-corpus.jsonl").exists()


def test_from_release_reports_failure(tmp_path, monkeypatch, capsys):
    import install as inst
    def boom(url, dest):
        raise inst.urllib.error.URLError("no network")
    monkeypatch.setattr(inst.urllib.request, "urlretrieve", boom)
    repo = tmp_path / "repo"; repo.mkdir()
    rc = inst.main([str(repo), "--from-release"])
    assert rc == 1
    assert "could not download" in capsys.readouterr().err.lower()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_install.py -k "release" -v`
Expected: FAIL (`release_asset_url`/`--from-release` missing).

- [ ] **Step 3: Modify `scripts/install.py`**

Add imports at the top: `import tempfile`, `import urllib.request`, `import urllib.error`.
Add near the other module constants / helpers:

```python
_RELEASE_REPO = "chrisuthe/ohf-sage"
_RELEASE_ASSETS = ["ohf-sage.md", "ohf-sage-corpus.jsonl"]


def release_asset_url(repo, asset):
    return f"https://github.com/{repo}/releases/latest/download/{asset}"


def download_release_assets(repo, dest_dir):
    """Download the release assets into dest_dir; return local paths. Raises on failure."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for asset in _RELEASE_ASSETS:
        dest = dest_dir / asset
        urllib.request.urlretrieve(release_asset_url(repo, asset), dest)
        paths.append(dest)
    return paths
```

In `main()`, add the two arguments (after `--corpus`/`--no-corpus`, before `--local-exclude`):

```python
    ap.add_argument("--from-release", action="store_true",
                    help="download the agent + corpus from the latest GitHub release instead of local files")
    ap.add_argument("--release-repo", default=_RELEASE_REPO,
                    help="owner/repo to pull the release from (default: chrisuthe/ohf-sage)")
```

And immediately after `args = ap.parse_args(argv)`, before `installed = [...]`:

```python
    if args.from_release:
        try:
            fetched = download_release_assets(args.release_repo, tempfile.mkdtemp(prefix="ohf-sage-rel-"))
        except (urllib.error.URLError, OSError) as e:
            print(f"error: could not download release assets from {args.release_repo}: {e}", file=sys.stderr)
            return 1
        by_name = {p.name: str(p) for p in fetched}
        args.agent = by_name["ohf-sage.md"]
        args.corpus = by_name["ohf-sage-corpus.jsonl"]
```

(Also add `import sys` if it isn't already imported.)

- [ ] **Step 4: Run to verify tests pass**

Run: `python -m pytest tests/test_install.py -v`
Expected: all pass (existing + 3 new).

- [ ] **Step 5: Full suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/install.py tests/test_install.py
git commit -m "Add --from-release to install the agent + corpus from the latest release"
```

---

### Task 3: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/refresh.yml`
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Create `.github/workflows/refresh.yml`**

```yaml
name: Refresh corpus

on:
  schedule:
    - cron: "0 6 * * 1"   # Mondays 06:00 UTC
  workflow_dispatch:
    inputs:
      review_limit:
        description: "PRs per authority to scan for review summaries"
        default: "15"

permissions:
  contents: write
  pull-requests: write

jobs:
  refresh:
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      REVIEW_LIMIT: ${{ github.event.inputs.review_limit || '15' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install package
        run: pip install -e .
      - name: Harvest (paced)
        run: |
          set -e
          repos=$(python -c "from ohf_principles.config import load_config; print('\n'.join(r['repo'] for r in load_config('config/sources.yaml')['repos']))")
          while IFS= read -r repo; do
            [ -z "$repo" ] && continue
            echo "=== $repo ==="
            python -m ohf_principles.harvest --repo "$repo" --review-limit "$REVIEW_LIMIT" || echo "  (skipped $repo)"
            sleep 12
          done <<< "$repos"
      - name: Build corpus, manifest, agent
        run: |
          python scripts/build_corpus.py
          python scripts/build_manifest.py
          python scripts/build_agent.py
      - name: Detect manifest change
        id: diff
        run: |
          if git diff --quiet -- corpus-manifest.json; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
      - name: Publish prerelease with assets
        if: steps.diff.outputs.changed == 'true'
        run: |
          tag="corpus-$(date +%Y%m%d-%H%M%S)"
          gh release create "$tag" --prerelease \
            --title "Corpus refresh $tag" \
            --notes-file corpus-manifest.json \
            agent/ohf-sage.md agent/ohf-sage-corpus.jsonl
      - name: Open manifest PR
        if: steps.diff.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v6
        with:
          add-paths: corpus-manifest.json
          branch: corpus-refresh
          delete-branch: true
          commit-message: "Refresh corpus manifest"
          title: "Corpus refresh"
          body: |
            Automated corpus refresh. Review the per-repo record deltas in `corpus-manifest.json`.

            The rebuilt corpus + agent are staged as the newest `corpus-*` **prerelease**;
            merging this PR promotes them to the `latest` Release (see `publish.yml`).
```

- [ ] **Step 2: Create `.github/workflows/publish.yml`**

```yaml
name: Publish release

on:
  push:
    branches: [master]
    paths:
      - corpus-manifest.json

permissions:
  contents: write

jobs:
  publish:
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - name: Promote newest corpus prerelease to latest
        run: |
          tag=$(gh release list --limit 30 --json tagName,isPrerelease \
            --jq '[.[] | select(.isPrerelease and (.tagName | startswith("corpus-")))][0].tagName')
          if [ -z "$tag" ] || [ "$tag" = "null" ]; then
            echo "no corpus prerelease to promote"; exit 0
          fi
          gh release edit "$tag" --prerelease=false --latest
          echo "promoted $tag to latest"
```

- [ ] **Step 3: Validate the workflow YAML**

Run:
```bash
python - <<'PY'
import yaml
for f in [".github/workflows/refresh.yml", ".github/workflows/publish.yml"]:
    with open(f, encoding="utf-8") as fh:
        d = yaml.safe_load(fh)
    assert "jobs" in d, f
    print(f, "OK - jobs:", list(d["jobs"]))
PY
```
Expected: both print `OK` with their job names. (Note: this checks YAML validity, not Actions schema — actionlint isn't available; the first real GitHub run is the acceptance test.)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/refresh.yml .github/workflows/publish.yml
git commit -m "Add scheduled corpus-refresh and release-promote workflows"
```

---

### Task 4: Docs — release install + local principles refresh

**Files:**
- Modify: `README.md`, `INSTALL.md`, `DEVELOPING.md`

- [ ] **Step 1: `README.md` + `INSTALL.md` — the release-based install**

- Add `--from-release` as the recommended "get the latest" install:
  ```bash
  python scripts/install.py /path/to/your/project --from-release
  ```
  and note the no-clone route now points at the **release** asset:
  ```bash
  curl -L -o .claude/agents/ohf-sage.md \
    https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage.md
  curl -L -o .claude/agents/ohf-sage-corpus.jsonl \
    https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage-corpus.jsonl
  ```
- Note that the corpus is now published via **GitHub Releases** (refreshed weekly by CI), not committed to git — so `--from-release` / the release URLs always give the latest.

- [ ] **Step 2: `DEVELOPING.md` — the CI + local-refresh model**

Add a **"Staying current"** section:
- CI (`.github/workflows/refresh.yml`) re-harvests weekly, rebuilds the corpus, and opens a PR touching only `corpus-manifest.json`; merging it promotes the prerelease to the `latest` Release (`publish.yml`).
- **Refreshing the principles is a local, human step** (CI never runs Claude): re-harvest, run the full distillation (chunk the corpus → extract → synthesize → critic), review `principles/principles.md`, `python scripts/build_agent.py`, and open a PR. On merge, the next refresh bundles the new agent into the release.

- [ ] **Step 3: Structural verification**

Run:
```bash
grep -c "from-release\|releases/latest/download" README.md   # >=1
grep -c "Staying current\|corpus-manifest" DEVELOPING.md      # >=1
python -m pytest -q
```
Expected: counts ≥1 and the suite passes.

- [ ] **Step 4: Commit**

```bash
git add README.md INSTALL.md DEVELOPING.md
git commit -m "Document release-based install and the CI refresh / local principles model"
```

---

### Task 5: Validate, cut the initial release, final review *(controller-orchestrated)*

- [ ] **Step 1:** Re-validate both workflow YAMLs (Task 3 Step 3) and run the full suite.
- [ ] **Step 2: Cut an initial `latest` Release** so `--from-release` works immediately: from the branch (with the built local corpus present), `gh release create v0.1.0 --latest --title "OHF Sage v0.1.0" --notes "Initial release: agent + review-history corpus." agent/ohf-sage.md agent/ohf-sage-corpus.jsonl`. (Do this after the PR merges, or against the repo directly — controller decides timing so the assets match master.)
- [ ] **Step 3: Verify `--from-release`** end to end once the release exists: `python scripts/install.py <tmp> --from-release` downloads both assets into `<tmp>/.claude/agents/`.
- [ ] **Step 4:** Final whole-branch review; adjudicate residuals; finishing-a-development-branch → PR. Note in the PR that the two Actions can only be fully verified by their first GitHub run (schedule or manual dispatch).

---

## Self-Review Notes

- **Spec coverage:** manifest generator + un-track corpus (T1) · `--from-release` HTTPS install (T2) · refresh + publish workflows (T3) · release-install + local-principles docs (T4) · initial release + validation + final review (T5). All spec sections map to a task.
- **Type consistency:** `build_manifest(glob, now)->dict` (T1) called by CI (T3); `release_asset_url`/`download_release_assets` (T2) used by `main --from-release` (T2); `corpus-manifest.json` is the PR-diff artifact across T1/T3/publish trigger.
- **Untestable-locally flag:** the two Actions' end-to-end behavior can only be confirmed on GitHub; the plan validates YAML syntax + reviews logic, and the first scheduled/dispatched run is the acceptance test (called out in T5 and the PR).
