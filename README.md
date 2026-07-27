# OHF Sage

A Claude Code agent that knows the **Open Home Foundation / Music Assistant**
project leads' engineering principles — mined from real PR reviews and rejected
feature requests, and cross-checked against the maintainers' own `AGENTS.md` and
tool configs. Point your other agents at it to get the leads' standards applied
automatically, with a citation for every call.

It has two modes:

- **Consult** — ask it *before* you build something: "should I do it this way
  or that way?", "would this be accepted upstream?", "is this in scope, or
  something the project won't support?"
- **Review** — hand it a diff, PR, or set of files and it checks the change
  against the principles, citing the PR/issue (or maintainer doc) behind each note.

Every answer is grounded in `principles/principles.md` — it doesn't invent
standards, it applies ones on record. **Home Assistant is out of scope.**

---

## Install

You only need one file: **`agent/ohf-sage.md`**.

**One project** (recommended) — from a clone of this repo:

```bash
git clone https://github.com/chrisuthe/ohf-sage.git
cd ohf-sage
python scripts/install.py /path/to/your/project
```

That drops the agent into `/path/to/your/project/.claude/agents/`.

**Everywhere** (all your projects) — copy it into your user-level agents folder:

```bash
mkdir -p ~/.claude/agents && cp agent/ohf-sage.md ~/.claude/agents/
```

**No clone** — pull just the agent file into a project:

```bash
mkdir -p .claude/agents
curl -L -o .claude/agents/ohf-sage.md \
  https://raw.githubusercontent.com/chrisuthe/ohf-sage/master/agent/ohf-sage.md
```

**Contributing to a repo you don't own** (e.g. a Music Assistant fork)? Add
`--local-exclude` so the agent is available locally but never tracked, committed,
or pushed:

```bash
python scripts/install.py /path/to/the/repo --local-exclude
```

More detail and platform-specific (PowerShell) commands: [INSTALL.md](INSTALL.md).
You don't need Python just to *use* the agent — the copy/`curl` routes are plain
file copies; only `install.py` uses Python (3.9+).

## Using it

Once installed, ask Claude Code to bring it in. Example prompts:

- "Run this approach past the **ohf-sage** before I build it."
- "Have the **ohf-sage** review my diff."
- "I want to add a music provider that caches streamed audio to disk — check it
  against the project principles first."

It responds with a **verdict first** (e.g. "won't be accepted as-is"), then the
governing principle(s), each linking to the PR/issue or maintainer doc it came
from, and separates hard `MUST` / "won't support" rules from softer preferences.

## Understanding its answers

Every rule the advisor cites ends with a **provenance marker** telling you how it
knows — weigh its confidence accordingly:

| Marker | Meaning |
|---|---|
| `[authored+mined]` | A maintainer doc **and** PR reviews agree — strongest |
| `[authored]` | Stated in a maintainer doc (`AGENTS.md`, `CONTRIBUTING.md`, …) — firm policy |
| `[enforced]` | Codified in a tool/CI config (`ruff`/`mypy`/`pre-commit`) — mechanically checked |
| `[mined · N PRs · 👍]` | Inferred from review history across N distinct PRs; `· 👍` when maintainers endorsed it |

## Whose principles these are

Principle strength depends on who said it:

- **marcelveldt** — authoritative across every OHF project.
- **MarvinSchenkel** — authoritative for Music Assistant.
- Other core maintainers per project (e.g. `OzGav`, `florianhorner` on the server).

Only these voices are treated as principle signal. The current pass covers the
Music Assistant repos (`server`, `support`, `frontend`, `mobile-app`,
`desktop-app`); the doc is honest about thin or unmined areas rather than
inventing rules.

## Regenerating or extending

This repo is also the pipeline that *produced* the agent. To refresh the
principles, mine additional OHF repos, or change how distillation works, see
[DEVELOPING.md](DEVELOPING.md).
