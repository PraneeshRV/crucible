#!/usr/bin/env python3
"""Copy an eval case into a disposable workspace, leaving rubrics behind.

The evaluated agent must never see the rubric and must never run from the
Crucible repo, where every rubric sits one directory away from the cases.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CASES = HERE / "cases"
RUBRICS = HERE / "rubrics"

CASE_ID_RE = re.compile(r"^c\d{2}$")


def materialize(case_id: str, dest: Path) -> Path:
    """Copy case `case_id`'s prompt, staged turns and artifacts into `dest/<case_id>/`."""
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
    out.mkdir(parents=True)

    shutil.copy2(src / "prompt.md", out / "prompt.md")
    turn2 = src / "turn2.md"
    if turn2.is_file():
        shutil.copy2(turn2, out / "turn2.md")
    artifacts = src / "artifacts"
    if artifacts.is_dir():
        shutil.copytree(artifacts, out / "artifacts")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    print(materialize(args.case_id, args.dest))


if __name__ == "__main__":
    main()
