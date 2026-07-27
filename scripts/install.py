# scripts/install.py
import argparse
import shutil
from pathlib import Path


def install(agent_path, repo_dir):
    agent_path = Path(agent_path)
    dest_dir = Path(repo_dir) / ".claude" / "agents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / agent_path.name
    shutil.copyfile(agent_path, dest)
    return dest


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Install the advisor agent into a repo's .claude/agents/.")
    ap.add_argument("repo_dir")
    ap.add_argument("--agent", default=str(root / "agent/ohf-principles-advisor.md"))
    args = ap.parse_args(argv)
    dest = install(args.agent, args.repo_dir)
    print(f"installed -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
