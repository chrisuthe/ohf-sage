"""Copilot review benchmark harness.

Automates the smoke-test loop across configs and cases:
  setup   -> for each (case, config): reconstruct the PR at the review commit,
             (C1) attach the Sage skill to BOTH branches (so it is present for
             Copilot but not in the reviewed diff), open the PR, request Copilot.
  collect -> poll the opened PRs, scrape Copilot's review + inline comments.

Configs:  c0 = baseline Copilot (no Sage)   c1 = + Sage skill + bundled principles
State/results are JSON files under copilot_bench/ so setup and collect are separate
runs (Copilot takes minutes to review).
"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

from ohf_principles import github

FORK = "chrisuthe/server"
SKILL_DIR = ".github/skills/ohf-sage"
LOCAL_SKILL = "copilot/skills/ohf-sage/SKILL.md"
LOCAL_PRINCIPLES = "principles/principles.md"
INSTRUCTIONS_PATH = ".github/instructions/music-assistant-standards.instructions.md"
LOCAL_INSTRUCTIONS = "agent/music-assistant-standards.instructions.md"
LOCAL_INSTRUCTIONS_CAL = "agent/music-assistant-standards.calibrated.instructions.md"
COPILOT_BOT = "copilot-pull-request-reviewer[bot]"

CASES = "copilot_bench/cases.json"
STATE = "copilot_bench/bench_state.json"
RESULTS = "copilot_bench/results.json"


def _create_ref(branch, sha):
    github._run(["gh", "api", f"repos/{FORK}/git/refs",
                 "-f", f"ref=refs/heads/{branch}", "-f", f"sha={sha}"])


def _put_file(path, branch, local_file, message):
    content = base64.b64encode(Path(local_file).read_bytes()).decode()
    payload = {"message": message, "content": content, "branch": branch}
    # If the file already exists on this branch (the shard is now in dev), the contents
    # API requires the current blob sha to overwrite it rather than create.
    try:
        existing = github.gh_api_json(f"repos/{FORK}/contents/{path}?ref={branch}")
        if isinstance(existing, dict) and existing.get("sha"):
            payload["sha"] = existing["sha"]
    except github.GhError:
        pass
    proc = subprocess.run(
        ["gh", "api", f"repos/{FORK}/contents/{path}", "-X", "PUT", "--input", "-"],
        input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise github.GhError(proc.stderr.strip())


def _attach_skill(branch):
    _put_file(f"{SKILL_DIR}/SKILL.md", branch, LOCAL_SKILL, "add ohf-sage skill (bench)")
    _put_file(f"{SKILL_DIR}/principles.md", branch, LOCAL_PRINCIPLES, "add ohf-sage principles (bench)")


def _attach_instructions(branch):
    _put_file(INSTRUCTIONS_PATH, branch, LOCAL_INSTRUCTIONS,
              "add MA review-standards instructions (bench)")


def _attach_instructions_cal(branch):
    _put_file(INSTRUCTIONS_PATH, branch, LOCAL_INSTRUCTIONS_CAL,
              "add calibrated MA review-standards instructions (bench)")


def _open_pr(head, base, title, body):
    out = github._run(["gh", "api", f"repos/{FORK}/pulls", "-X", "POST",
                       "-f", f"title={title}", "-f", f"head={head}",
                       "-f", f"base={base}", "-f", f"body={body}", "--jq", ".number"])
    return int(out.strip())


def _request_copilot(pr):
    github._run(["gh", "api", f"repos/{FORK}/pulls/{pr}/requested_reviewers",
                 "-X", "POST", "-f", f"reviewers[]={COPILOT_BOT}"])


def reconstruct(case, config, idx, seed=0):
    tag = f"bench-{idx}-{config}-s{seed}"
    base_br, head_br = f"{tag}-base", f"{tag}-head"
    _create_ref(base_br, case["base_sha"])
    _create_ref(head_br, case["review_commit"])
    if config == "c4":  # native path-scoped instructions shard (Phase 1 deliverable)
        _attach_instructions(base_br)
        _attach_instructions(head_br)
    elif config == "c5":  # c4 + reachability-calibration guard (A/B against c4)
        _attach_instructions_cal(base_br)
        _attach_instructions_cal(head_br)
    elif config != "c0":  # c1 = base skill, c2 = prescriptive skill (whatever is in LOCAL_SKILL)
        _attach_skill(base_br)
        _attach_skill(head_br)
    title = f"[{tag}] {case['repo']}#{case['pr']} ({case['author']})"
    body = (f"Benchmark {config}. Repro of {case['repo']}#{case['pr']} at "
            f"{case['review_commit'][:10]}. Safe to close.")
    pr = _open_pr(head_br, base_br, title, body)
    _request_copilot(pr)
    return pr


def collect(pr):
    reviews = github.gh_api_json(f"repos/{FORK}/pulls/{pr}/reviews")
    comments = github.gh_api_json(f"repos/{FORK}/pulls/{pr}/comments")
    cr = [r for r in reviews if "copilot" in (r.get("user") or {}).get("login", "").lower()]
    cc = [c for c in comments if "copilot" in (c.get("user") or {}).get("login", "").lower()]
    return {
        "n_reviews": len(cr),
        "review_body": cr[0]["body"] if cr else None,
        "comments": [{"path": c.get("path"), "line": c.get("line"), "body": c.get("body")} for c in cc],
    }


def cmd_setup(idxs, configs, nseeds=1):
    cases = json.load(open(CASES, encoding="utf-8"))
    state = []
    for i in idxs:
        case = cases[i]
        for cfg in configs:
            for seed in range(nseeds):
                try:
                    pr = reconstruct(case, cfg, i, seed)
                    state.append({"idx": i, "config": cfg, "seed": seed, "pr": pr})
                    print(f"  [{cfg} s{seed}] case {i} {case['repo']}#{case['pr']} -> PR #{pr}", file=sys.stderr)
                except github.GhError as e:
                    print(f"  ! case {i} {cfg} s{seed} FAILED: {e}", file=sys.stderr)
    json.dump(state, open(STATE, "w"), indent=2)
    print(f"opened {len(state)} bench PRs -> {STATE}")


def cmd_collect(max_wait=600, interval=25):
    state = json.load(open(STATE, encoding="utf-8"))
    cases = json.load(open(CASES, encoding="utf-8"))
    done, waited = {}, 0
    while len(done) < len(state) and waited <= max_wait:
        for s in state:
            key = f"{s['idx']}-{s['config']}-{s.get('seed', 0)}"
            if key in done:
                continue
            r = collect(s["pr"])
            if r["n_reviews"] > 0 or r["comments"]:
                done[key] = {**s, "result": r}
                print(f"  collected {key} (PR #{s['pr']}): {len(r['comments'])} comments", file=sys.stderr)
        if len(done) < len(state):
            time.sleep(interval)
            waited += interval
    results = []
    for s in state:
        key = f"{s['idx']}-{s['config']}-{s.get('seed', 0)}"
        case = cases[s["idx"]]
        entry = {"idx": s["idx"], "config": s["config"], "seed": s.get("seed", 0), "pr": s["pr"],
                 "repo": case["repo"], "src_pr": case["pr"], "author": case["author"],
                 "ground_truth": case["quote"], "path": case["path"]}
        entry["result"] = done.get(key, {}).get("result", {"n_reviews": 0, "review_body": None, "comments": [], "timed_out": True})
        results.append(entry)
    json.dump(results, open(RESULTS, "w"), indent=2)
    print(f"collected {len(done)}/{len(state)} -> {RESULTS}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "setup":
        idxs = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else []
        configs = sys.argv[3].split(",") if len(sys.argv) > 3 else ["c0", "c1"]
        nseeds = int(sys.argv[4]) if len(sys.argv) > 4 else 1
        cmd_setup(idxs, configs, nseeds)
    elif cmd == "collect":
        cmd_collect()
    else:
        print("usage: harness.py setup <idx,idx,...> [c0,c1] | collect")
