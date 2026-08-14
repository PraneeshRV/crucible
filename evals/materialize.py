#!/usr/bin/env python3
"""Copy an eval case into a disposable workspace, leaving rubrics behind.

The evaluated agent must never see the rubric and must never run from the
Crucible repo, where every rubric sits one directory away from the cases.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CASES = HERE / "cases"
RUBRICS = HERE / "rubrics"

CASE_ID_RE = re.compile(r"^c\d{2}$")


def materialize(case_id: str, dest: Path) -> Path:
    """Copy case `case_id` into `dest/<case_id>/`, returning the session's workspace.

    The prompt and artifacts go in `dest/<case_id>/work/`, which is the directory the
    evaluated session runs in. A staged `turn2.md` is deliberately left *outside* it, at
    `dest/<case_id>/turn2.md`: the whole point of a staged case is to capture what the
    session predicted before it saw the result, and a session that can read turn 2 from
    its own working directory has already seen it.
    """
    # case_id reaches rmtree() and path joins below. Validate before either.
    if not CASE_ID_RE.fullmatch(case_id or ""):
        raise ValueError(f"invalid case id: {case_id!r} (expected c01-c99)")

    dest = Path(dest).resolve()
    if dest == REPO or REPO in dest.parents:
        raise ValueError(
            f"refusing to materialize inside the Crucible repo: {dest}. "
            "The evaluated agent must not have the rubrics within reach."
        )

    src = CASES / case_id
    if not src.is_dir():
        raise FileNotFoundError(f"no such case: {src}")

    out = dest / case_id
    if out.exists():
        shutil.rmtree(out)
    work = out / "work"
    work.mkdir(parents=True)

    shutil.copy2(src / "prompt.md", work / "prompt.md")
    turn2 = src / "turn2.md"
    if turn2.is_file():
        shutil.copy2(turn2, out / "turn2.md")
    artifacts = src / "artifacts"
    if artifacts.is_dir():
        shutil.copytree(artifacts, work / "artifacts")

    return work


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    work = materialize(args.case_id, args.dest)
    print(work)
    staged = work.parent / "turn2.md"
    if staged.is_file():
        # stderr: stdout is the workspace path and a harness will capture it.
        print(
            f"staged turn 2 (deliver only after turn 1 resolves, do not put it in the workspace): {staged}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
