# OHF Sage reviewer on GitHub Copilot CLI

Runs the **native Sage review architecture** — a full-attention agent that greps the mined
review corpus and cites the leads' real PR discussions — but powered by **Copilot's models**
(billed to your Copilot subscription) instead of the paid Anthropic API. No hosted server: the
Copilot CLI's built-in `shell`/`read` tools grep the corpus locally.

Benchmarked equivalent (`claude-code-action` on Opus 4.8, same agent + corpus): **3/6 exact-issue
recall** with comprehensive, fully-cited reviews vs. 1/6 for the static Copilot review-bot skill.

## What's here

| File | Installs to (in the reviewed repo) |
|---|---|
| `sage-cli-review.yml` | `.github/workflows/sage-cli-review.yml` |
| `sage.agent.md` | `.github/agents/sage.agent.md` (optional — the idiomatic agent form) |
| `sage_post_review.py` | `.github/scripts/sage_post_review.py` |

The workflow is self-contained (it inlines the review prompt and reads the fetched `ohf-sage.md`),
so `sage.agent.md` is optional — switch the workflow to invoke it by name once you've confirmed
your CLI version auto-loads `.github/agents/`.

## Install

1. Copy the three files to the paths above in the target repo, on the branch PRs target
   (e.g. `dev`).
2. **Add a secret `COPILOT_GITHUB_TOKEN`** = a PAT (or org token) belonging to a **Copilot-licensed**
   identity. The default Actions `GITHUB_TOKEN` does *not* carry Copilot entitlement.
3. *(Optional)* set a repo/org **variable `SAGE_MODEL`** to the exact Claude model id your CLI
   offers — run `copilot` locally, then `/model`, to list them (e.g. `claude-opus-5` if available;
   default is `claude-opus-4.8`, the model the 3/6 benchmark used).

## Test it

- **Manual:** Actions → *OHF Sage review (Copilot CLI)* → *Run workflow*, enter a PR number.
- **Automatic:** it runs on every `opened`/`synchronize`/`reopened` PR.

To reproduce the benchmark, reconstruct a lead-reviewed PR from upstream SHAs (see
`copilot_bench/harness.py::reconstruct`) and run the workflow against it, then compare its
comments to the lead's original review.

## Important caveats

- **Advisory, not a gate.** An LLM reviewer is non-deterministic — keep deterministic CI checks as
  the merge gate; Sage is the judgment layer on top.
- **Billing.** Claude models are *premium* in Copilot (metered in AI Credits by token usage). A
  Copilot-sponsored **seat** does not automatically mean unlimited premium/agentic credits — each
  plan includes a monthly credit allowance, then overage (unless your sponsorship covers it or an
  admin sets a spend cap). Confirm your org's premium-credit terms before high-volume use. Each
  review also consumes GitHub Actions minutes.
- **Model id / CLI command** can change — verify `npm install -g @github/copilot`, the `copilot`
  invocation, and the `--model` id against current Copilot CLI docs if a run fails.
- **Prompt injection.** The PR diff is untrusted input. This runs the agent read-only
  (`read` + `shell(grep/cat)` only — no write, no network) and posts via a *separate* step, so the
  model never holds the write token. Keep it that way; don't grant broader tools.
- **Fork PRs.** From forks, the token is read-only, so posting won't work without `pull_request_target`
  hardening — restrict to same-repo/internal PRs first.
