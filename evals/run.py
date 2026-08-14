#!/usr/bin/env python3
"""Execute an eval matrix cell-by-cell and write one transcript file per run.

The matrix is data (`matrix.json`), not code: which cases, which conditions, how many
reps. Gate 1, the Gate 2 bare-arm screen and whatever Gate 2 finally becomes are the same
runner with different matrix files.

Resumable by design. A cell whose output file already exists and is non-empty is skipped,
so an interrupted run is restarted with the same command. The existence check happens at
dispatch, not at loop start, because a check-at-start loop lets two workers pick up the
same cell and the later finish silently overwrites the earlier.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from materialize import CASES, materialize

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILL_SRC = REPO / "skill" / "crucible"

# Built-in CLI skills survive a clean HOME. They must be denied in every condition or they
# lift the bare baseline and pollute the comparison.
BUILTIN_SKILLS = ["debug", "verify", "code-review", "simplify", "deep-research", "claude-api"]

CONDITIONS = {
    # bare: Crucible unavailable, and Skill denied wholesale so nothing else stands in.
    "bare": {"install_skill": False, "deny_skill_tool": True, "prefix": ""},
    # implicit: installed, never named. Skill must be invocable or the trigger cannot fire.
    "implicit": {"install_skill": True, "deny_skill_tool": False, "prefix": ""},
    # explicit: invoked by name; tests workflow quality independent of the trigger.
    "explicit": {"install_skill": True, "deny_skill_tool": False, "prefix": "$crucible "},
}


REAL_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"


def build_home(root: Path, install_skill: bool, link_credentials: bool = False) -> Path:
    """A disposable HOME. Empty means no user CLAUDE.md, no skills, no plugins, no hooks."""
    home = root / ("home-skill" if install_skill else "home-bare")
    if home.exists():
        shutil.rmtree(home)
    (home / ".claude" / "skills").mkdir(parents=True)
    if install_skill:
        shutil.copytree(SKILL_SRC, home / ".claude" / "skills" / "crucible")
    if link_credentials:
        # The `claude` harness authenticates from $HOME/.claude/.credentials.json, which a
        # disposable HOME does not have. Symlink, never copy: the token stays in one place
        # and no secret is written into an eval directory. Note that an eval session with
        # Bash can read through this link, so the harness trades that exposure for a clean
        # HOME. Acceptable for first-party cases; revisit before running untrusted prompts.
        (home / ".claude" / ".credentials.json").symlink_to(REAL_CREDENTIALS)
    return home


def harness_cmd(harness: str, model: str, prompt: str, session: list[str], deny: list[str]) -> list[str]:
    if harness in ("glm", "claude"):
        cmd = [harness, "-p", prompt, *session]
        # glm selects its model through the wrapper's env; claude needs the flag.
        if harness == "claude":
            cmd += ["--model", model]
        if deny:
            cmd += ["--disallowedTools", ",".join(deny)]
        return cmd
    raise ValueError(f"unsupported harness: {harness!r}")


def run_cell(case_id: str, condition: str, rep: int, cfg: dict, outdir: Path, workroot: Path) -> str:
    out = outdir / f"{case_id}-{condition}-r{rep}.md"
    if out.is_file() and out.stat().st_size > 0:
        return f"skip {out.name}"

    spec = CONDITIONS[condition]
    ws = workroot / f"{case_id}-{condition}-r{rep}"
    if ws.exists():
        shutil.rmtree(ws)
    work = materialize(case_id, ws)
    staged_turn2 = work.parent / "turn2.md"

    home = build_home(ws, spec["install_skill"], link_credentials=cfg["harness"] == "claude")
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.setdefault("ZAI_KEY_FILE", str(Path.home() / ".config" / "zai.key"))
    if cfg["harness"] == "claude":
        # The parent is a Claude session; its OAuth plumbing would otherwise be inherited
        # by the child and override the disposable HOME.
        for var in [k for k in env if k.startswith(("CLAUDE_", "ANTHROPIC_"))]:
            del env[var]

    deny = ["Task", "Agent"] + (
        ["Skill"] if spec["deny_skill_tool"] else [f"Skill({s})" for s in BUILTIN_SKILLS]
    )

    sid = str(uuid.uuid4())
    turns, elapsed = [], []
    for n, src in enumerate([work / "prompt.md", staged_turn2], start=1):
        if not src.is_file():
            continue
        # The prefix marks the explicit condition and belongs on turn 1 only.
        prompt = (spec["prefix"] if n == 1 else "") + src.read_text()
        session = ["--session-id", sid] if n == 1 else ["--resume", sid]
        started = time.monotonic()
        proc = subprocess.run(
            harness_cmd(cfg["harness"], cfg["model"], prompt, session, deny),
            cwd=work, env=env, capture_output=True, text=True,
        )
        elapsed.append(round(time.monotonic() - started, 1))
        # Record what was actually sent, not the source file. In the explicit condition
        # they differ by the `$crucible` prefix, and a transcript that hides the prefix
        # misrepresents the condition it was run under.
        turns.append((prompt, proc.stdout or proc.stderr))

    pins = {
        "case": case_id, "condition": condition, "rep": rep,
        "harness": cfg["harness"], "model": cfg["model"],
        "crucible_commit": cfg["commit"],
        "skill_installed": spec["install_skill"],
        "denied_tools": deny,
        "global_instructions": "none (disposable HOME)",
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seconds_per_turn": elapsed,
    }

    body = [f"# {case_id} — {condition} — rep {rep}", "", "```json",
            json.dumps(pins, indent=2), "```", ""]
    for n, (prompt, response) in enumerate(turns, start=1):
        body += [f"## turn {n} prompt", "", prompt, "", f"## turn {n} response", "", response, ""]
    body += ["## verdict", "", "_ungraded — open the rubric only after the run completes_", ""]
    out.write_text("\n".join(body))
    return f"done {out.name} ({round(sum(elapsed), 1)}s)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("matrix", type=Path, help="path to a matrix JSON file")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--workroot", type=Path, default=Path("/tmp/crucible-evals"))
    ap.add_argument("--jobs", type=int, default=3,
                    help="concurrent cells; the Z.ai plan rate-limits above ~3")
    args = ap.parse_args()

    cfg = json.loads(args.matrix.read_text())
    cfg["commit"] = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    args.outdir.mkdir(parents=True, exist_ok=True)
    args.workroot.mkdir(parents=True, exist_ok=True)

    cells = [
        (case_id, condition, rep)
        for case_id, plan in cfg["cases"].items()
        for condition in plan["conditions"]
        for rep in range(1, plan["reps"] + 1)
    ]
    missing = [c for c, _, _ in cells if not (CASES / c).is_dir()]
    if missing:
        sys.exit(f"matrix names cases that do not exist: {sorted(set(missing))}")

    print(f"{len(cells)} cells, {cfg['harness']}/{cfg['model']}, crucible {cfg['commit']}")
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_cell, c, cond, r, cfg, args.outdir, args.workroot)
                   for c, cond, r in cells]
        for f in futures:
            print(f.result(), flush=True)


if __name__ == "__main__":
    main()
