import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "evals"))

from run import BUILTIN_SKILLS, CONDITIONS, build_home  # noqa: E402

MATRICES = sorted((REPO / "evals").glob("matrix-*.json"))


def test_bare_denies_the_skill_tool_outright():
    # Built-in CLI skills survive a clean HOME. If Skill is reachable in the bare arm they
    # lift the baseline and every bare-vs-implicit comparison is contaminated.
    assert CONDITIONS["bare"]["deny_skill_tool"] is True
    assert CONDITIONS["bare"]["install_skill"] is False


@pytest.mark.parametrize("condition", ["implicit", "explicit"])
def test_skill_conditions_can_actually_invoke_the_skill(condition):
    # Restricting the Skill tool in a condition that installs Crucible would look exactly
    # like a behavioural failure while being a harness bug.
    assert CONDITIONS[condition]["install_skill"] is True
    assert CONDITIONS[condition]["deny_skill_tool"] is False


def test_only_explicit_names_the_skill():
    assert CONDITIONS["explicit"]["prefix"].strip() == "$crucible"
    assert CONDITIONS["bare"]["prefix"] == ""
    assert CONDITIONS["implicit"]["prefix"] == ""


def test_builtin_skills_are_denied_by_name():
    for name in ("debug", "verify", "code-review", "simplify", "deep-research"):
        assert name in BUILTIN_SKILLS


@pytest.mark.parametrize("install", [True, False])
def test_build_home_is_disposable_and_isolated(tmp_path, install):
    home = build_home(tmp_path, install)
    assert not (home / "CLAUDE.md").exists()
    assert (home / ".claude" / "skills" / "crucible").is_dir() == install


def test_build_home_replaces_a_stale_home(tmp_path):
    home = build_home(tmp_path, False)
    (home / ".claude" / "skills" / "leftover").mkdir()
    assert not (build_home(tmp_path, False) / ".claude" / "skills" / "leftover").exists()


@pytest.mark.parametrize("path", MATRICES, ids=lambda p: p.name)
def test_matrix_files_are_runnable(path):
    cfg = json.loads(path.read_text())
    assert cfg["harness"] and cfg["model"]
    for case_id, plan in cfg["cases"].items():
        assert (REPO / "evals" / "cases" / case_id).is_dir(), f"{path.name}: no case {case_id}"
        assert plan["reps"] >= 1
        assert set(plan["conditions"]) <= set(CONDITIONS)


def test_anti_triggers_never_run_explicit():
    # Explicit invocation on a lookup tests nothing about firing (spec 3.1).
    cfg = json.loads((REPO / "evals" / "matrix-gate2.json").read_text())
    for case_id in ("c07", "c08"):
        assert "explicit" not in cfg["cases"][case_id]["conditions"]


def test_gate2_matrix_covers_every_case_in_the_suite():
    cfg = json.loads((REPO / "evals" / "matrix-gate2.json").read_text())
    on_disk = {p.name for p in (REPO / "evals" / "cases").iterdir() if p.is_dir()}
    assert on_disk == set(cfg["cases"]), "a case exists that Gate 2 would silently never run"
