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
