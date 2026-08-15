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


# A quota refusal arrives as a short, ordinary-looking answer on stdout with exit 0. On
# 2026-08-15 that put "You've hit your session limit" into 47 of 65 Gate 2 transcripts,
# every one of them recorded as a completed cell. Nothing about the exit status or the
# output length distinguishes it from a terse correct answer, so it is matched by text.
REFUSAL_SENTINELS = (
    "hit your session limit",
    "usage limit reached",
    "rate limit",
    "quota exceeded",
)


def refusal_in(response: str) -> str | None:
    """The sentinel a harness refusal matched, or None for a real answer."""
    low = response.lower()
    return next((s for s in REFUSAL_SENTINELS if s in low), None)


REAL_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
REAL_CODEX_AUTH = Path.home() / ".codex" / "auth.json"
# Codex re-materializes its six `.system` skills into any CODEX_HOME that lacks this marker
# — the same baseline-lifting problem BUILTIN_SKILLS solves for claude. Pre-seeding it
# leaves `.system` empty. Copied from the live CODEX_HOME rather than written from a
# constant because the file holds a version hash: after a codex upgrade a hardcoded marker
# would stop matching and the built-ins would silently come back.
CODEX_SYSTEM_MARKER = Path.home() / ".codex" / "skills" / ".system" / ".codex-system-skills.marker"


def build_home(root: Path, install_skill: bool, harness: str) -> Path:
    """A disposable HOME. Empty means no user CLAUDE.md or AGENTS.md, no skills, no hooks."""
    home = root / ("home-skill" if install_skill else "home-bare")
    if home.exists():
        shutil.rmtree(home)

    if harness == "codex":
        skills = home / ".codex" / "skills"
        (skills / ".system").mkdir(parents=True)
        shutil.copy(CODEX_SYSTEM_MARKER, skills / ".system")
        # Symlink, never copy — same rule as the claude credentials below.
        (home / ".codex" / "auth.json").symlink_to(REAL_CODEX_AUTH)
        if install_skill:
            shutil.copytree(SKILL_SRC, skills / "crucible")
        return home

    (home / ".claude" / "skills").mkdir(parents=True)
    if install_skill:
        shutil.copytree(SKILL_SRC, home / ".claude" / "skills" / "crucible")
    if harness == "claude":
        # The `claude` harness authenticates from $HOME/.claude/.credentials.json, which a
        # disposable HOME does not have. Symlink, never copy: the token stays in one place
        # and no secret is written into an eval directory. Note that an eval session with
        # Bash can read through this link, so the harness trades that exposure for a clean
        # HOME. Acceptable for first-party cases; revisit before running untrusted prompts.
        (home / ".claude" / ".credentials.json").symlink_to(REAL_CREDENTIALS)
    return home


def harness_cmd(cfg: dict, prompt: str, turn: int, sid: str, work: Path, deny: list[str]) -> list[str]:
    harness, model = cfg["harness"], cfg["model"]
    if harness in ("glm", "claude"):
        session = ["--session-id", sid] if turn == 1 else ["--resume", sid]
        cmd = [harness, "-p", prompt, *session]
        # glm selects its model through the wrapper's env; claude needs the flag.
        if harness == "claude":
            cmd += ["--model", model]
        if deny:
            cmd += ["--disallowedTools", ",".join(deny)]
        return cmd
    if harness == "codex":
        # Turn 2 resumes with --last rather than by id. Every cell gets its own CODEX_HOME,
        # so exactly one session is recorded there and --last has nothing to race against.
        head = ["codex", "exec"] if turn == 1 else ["codex", "exec", "resume", "--last"]
        # `resume` accepts neither --sandbox nor -C, so the sandbox goes through -c and the
        # working directory is left to the subprocess cwd. Both turns then take identical
        # options, which is also what keeps resume's own cwd filter pointing at the cell.
        return head + [
            # Without this the operator's config.toml supplies the model and the reasoning
            # effort, and the run would not be reproducible from the matrix alone.
            "--ignore-user-config",
            "--skip-git-repo-check",  # a materialized workspace is not a git repo
            "-m", model,
            "-c", f"sandbox_mode={cfg.get('sandbox', 'workspace-write')!r}",
            "-c", f"model_reasoning_effort={cfg.get('reasoning_effort', 'xhigh')!r}",
            prompt,
        ]
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

    home = build_home(ws, spec["install_skill"], harness=cfg["harness"])
    env = dict(os.environ)
    env["HOME"] = str(home)
    env.setdefault("ZAI_KEY_FILE", str(Path.home() / ".config" / "zai.key"))
    if cfg["harness"] == "claude":
        # The parent is a Claude session; its OAuth plumbing would otherwise be inherited
        # by the child and override the disposable HOME.
        for var in [k for k in env if k.startswith(("CLAUDE_", "ANTHROPIC_"))]:
            del env[var]
    if cfg["harness"] == "codex":
        # Codex reads CODEX_HOME, not $HOME/.codex, so setting HOME alone isolates nothing.
        # The parent may also be running under the codex companion, whose CODEX_* variables
        # would follow the child in.
        for var in [k for k in env if k.startswith("CODEX_")]:
            del env[var]
        env["CODEX_HOME"] = str(home / ".codex")

    if cfg["harness"] == "codex":
        # Codex has no --disallowedTools. The bare arm is enforced by not installing the
        # skill, and the built-ins by the marker in build_home, so nothing is denied by name.
        deny = []
    else:
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
        started = time.monotonic()
        proc = subprocess.run(
            harness_cmd(cfg, prompt, n, sid, work, deny),
            cwd=work, env=env, capture_output=True, text=True,
            # Codex appends piped stdin to the prompt as a <stdin> block. Whatever the
            # parent's stdin happens to be, it is not part of the case.
            stdin=subprocess.DEVNULL,
        )
        elapsed.append(round(time.monotonic() - started, 1))
        refusal = refusal_in(proc.stdout)
        if refusal:
            return f"FAIL {out.name} turn {n}: harness refused ({refusal}) — quota, not behaviour"
        if proc.returncode != 0 or not proc.stdout.strip():
            # Deliberately write nothing. The resume check treats any non-empty file as a
            # finished cell, so recording the failure would make the rerun that is supposed
            # to repair it skip the cell instead — and a harness error would be graded as
            # behaviour. A missing file is retried; a bad one is not.
            said = (proc.stderr or proc.stdout or "").strip().splitlines()
            why = said[-1] if said else f"exit {proc.returncode}, no output"
            return f"FAIL {out.name} turn {n}: {why}"
        # Record what was actually sent, not the source file. In the explicit condition
        # they differ by the `$crucible` prefix, and a transcript that hides the prefix
        # misrepresents the condition it was run under.
        turns.append((prompt, proc.stdout))

    pins = {
        "case": case_id, "condition": condition, "rep": rep,
        "harness": cfg["harness"], "model": cfg["model"],
        **({"sandbox": cfg.get("sandbox", "workspace-write"),
            "reasoning_effort": cfg.get("reasoning_effort", "xhigh")}
           if cfg["harness"] == "codex" else {}),
        "crucible_commit": cfg["commit"],
        "skill_installed": spec["install_skill"],
        "denied_tools": deny,
        # How the harness's own bundled skills were kept out of the baseline. The two
        # harnesses achieve it differently, and a transcript that did not say which was
        # used could not be audited for a contaminated baseline.
        "builtin_skills": (
            "suppressed by .system marker" if cfg["harness"] == "codex" else "denied by name"
        ),
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
    # Gate 2 runs the same case plan on both harnesses. Overriding here rather than
    # keeping a second matrix file means the two arms cannot drift apart in which cases,
    # conditions and reps they ran.
    ap.add_argument("--harness", help="override the matrix harness")
    ap.add_argument("--model", help="override the matrix model")
    args = ap.parse_args()

    cfg = json.loads(args.matrix.read_text())
    for key in ("harness", "model"):
        if getattr(args, key):
            cfg[key] = getattr(args, key)
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
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_cell, c, cond, r, cfg, args.outdir, args.workroot)
                   for c, cond, r in cells]
        for f in futures:
            results.append(f.result())
            print(results[-1], flush=True)

    # Exit non-zero on any failure. A partial matrix that reports success is how a gate
    # gets graded on cells that never ran.
    failed = [r for r in results if r.startswith("FAIL")]
    if failed:
        print(f"\n{len(failed)} of {len(cells)} cells failed; rerun the same command to retry them")
        sys.exit(1)


if __name__ == "__main__":
    main()
