import glob
import sys
from pathlib import Path


def build_corpus(corpus_glob, out_path):
    """Concatenate every *.jsonl matched by corpus_glob into out_path,
    one record per line. Returns the number of records written."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for path in sorted(glob.glob(corpus_glob)):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    f.write(line if line.endswith("\n") else line + "\n")
                    n += 1
    return n


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    argv = argv if argv is not None else sys.argv[1:]
    corpus_glob = argv[0] if len(argv) > 0 else str(root / "corpus" / "*.jsonl")
    out_path = argv[1] if len(argv) > 1 else str(root / "agent" / "ohf-sage-corpus.jsonl")
    n = build_corpus(corpus_glob, out_path)
    print(f"wrote {n} records -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
