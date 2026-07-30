# Install the OHF Sage

A Claude Code agent that knows the Music Assistant / Open Home Foundation project leads' engineering principles — mined from real PR reviews and rejected feature requests. Point your other agents at it to **consult** before choosing an approach ("would this be accepted upstream?") or to **review** a change against the project's standards. Every answer cites the PR/issue the rule came from.

You only need one file: **`agent/ohf-sage.md`** (plus the corpus for fallback review history).

## Option A — get the latest (recommended)

Pull from the latest release:

```bash
python scripts/install.py /path/to/your/project --from-release
```

That drops the agent and corpus into `/path/to/your/project/.claude/agents/`. The corpus
is published via GitHub Releases (refreshed weekly by CI), not committed to git — so
`--from-release` always gets the newest.

## Option B — one project (from a clone)

From a clone of this repo, install it into whatever project you're working in:

```bash
git clone https://github.com/chrisuthe/ohf-sage.git
cd ohf-sage
python scripts/install.py /path/to/your/project
```

That drops the agent into `/path/to/your/project/.claude/agents/`. Open that project in Claude Code and the advisor is available.

**Contributing to a repo you don't own** (e.g. a Music Assistant fork)? Add `--local-exclude` so it's available locally but never tracked, committed, or pushed:

```bash
python scripts/install.py /path/to/the/repo --local-exclude
```

## Option C — everywhere (all your projects)

Copy the agent into your user-level agents folder:

```bash
# macOS / Linux
mkdir -p ~/.claude/agents && cp agent/ohf-sage.md ~/.claude/agents/
```

```powershell
# Windows (PowerShell)
New-Item -ItemType Directory -Force $HOME\.claude\agents | Out-Null
Copy-Item agent\ohf-sage.md $HOME\.claude\agents\
```

## Option D — no clone at all

Grab just the agent and corpus files straight into a project's `.claude/agents/` folder:

```bash
mkdir -p .claude/agents
curl -L -o .claude/agents/ohf-sage.md \
  https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage.md
curl -L -o .claude/agents/ohf-sage-corpus.jsonl \
  https://github.com/chrisuthe/ohf-sage/releases/latest/download/ohf-sage-corpus.jsonl
```

## Use it

Ask Claude Code things like:

- "Run this approach past the ohf-sage before I build it."
- "Have the ohf-sage review my diff."

Requirements: Claude Code. No Python needed just to *use* the agent — the install scripts use Python 3.9+, but Option B / the `curl` route are plain file copies.

---

Want to regenerate the principles or mine more OHF repos? See [DEVELOPING.md](DEVELOPING.md).
