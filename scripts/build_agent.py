import sys
from pathlib import Path

START = "<!-- PRINCIPLES:START -->"
END = "<!-- PRINCIPLES:END -->"


def _principles_body(text):
    """Drop a leading top-level '# ' title line; keep the rest verbatim."""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip("\n")


def build_agent(template_path, principles_path, out_path):
    template = Path(template_path).read_text(encoding="utf-8")
    if START not in template or END not in template:
        raise ValueError("template missing PRINCIPLES markers")
    body = _principles_body(Path(principles_path).read_text(encoding="utf-8"))
    pre = template.split(START)[0]
    post = template.split(END)[1]
    result = f"{pre}{START}\n{body}\n{END}{post}"
    Path(out_path).write_text(result, encoding="utf-8")
    return result


def main(argv=None):
    argv = argv or sys.argv[1:]
    root = Path(__file__).resolve().parents[1]
    template = argv[0] if len(argv) > 0 else root / "agent/ohf-sage.template.md"
    principles = argv[1] if len(argv) > 1 else root / "principles/principles.md"
    out = argv[2] if len(argv) > 2 else root / "agent/ohf-sage.md"
    build_agent(template, principles, out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
