import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "evals"))

from materialize import materialize  # noqa: E402

SENTINEL = "RUBRIC-SENTINEL-DO-NOT-LEAK"


@pytest.fixture
def fake_case(tmp_path, monkeypatch):
    cases = tmp_path / "cases" / "c01"
    (cases / "artifacts").mkdir(parents=True)
    (cases / "prompt.md").write_text("Why did the build start failing?\n")
    (cases / "turn2.md").write_text("Here is the result.\n")
    (cases / "artifacts" / "build.log").write_text("error: exit 1\n")

    rubrics = tmp_path / "rubrics"
    rubrics.mkdir()
    (rubrics / "c01.md").write_text(f"Expected: constructs a rival. {SENTINEL}\n")

    monkeypatch.setattr("materialize.CASES", tmp_path / "cases")
    monkeypatch.setattr("materialize.RUBRICS", rubrics)
    return tmp_path


def test_prompt_and_artifacts_are_materialized(fake_case, tmp_path):
    dest = tmp_path / "workspace"
    out = materialize("c01", dest)
    assert (out / "prompt.md").read_text().startswith("Why did the build")
    assert (out / "artifacts" / "build.log").exists()


def test_turn2_materialized_when_present(fake_case, tmp_path):
    out = materialize("c01", tmp_path / "workspace")
    assert (out / "turn2.md").read_text().startswith("Here is the result")


@pytest.mark.parametrize(
    "bad_id",
    ["../rubrics", "c01/../../etc", "/etc", "c1", "c001", "", "c01;rm -rf /"],
)
def test_rejects_malformed_case_id(fake_case, tmp_path, bad_id):
    # case_id reaches rmtree() and path joins - validate before either.
    with pytest.raises(ValueError, match="invalid case id"):
        materialize(bad_id, tmp_path / "workspace")


def test_rubric_never_reaches_the_workspace(fake_case, tmp_path):
    dest = tmp_path / "workspace"
    out = materialize("c01", dest)
    leaked = [
        p.relative_to(out).as_posix()
        for p in out.rglob("*")
        if p.is_file() and SENTINEL in p.read_text(errors="ignore")
    ]
    assert leaked == [], f"rubric content leaked into: {leaked}"
    assert not (out / "rubrics").exists()


def test_workspace_is_outside_the_repo(fake_case, tmp_path):
    # The evaluated agent must never run from the Crucible repo, where
    # every rubric sits one directory away.
    dest = tmp_path / "workspace"
    out = materialize("c01", dest)
    assert REPO not in out.resolve().parents


def test_refuses_a_destination_inside_the_repo(fake_case):
    with pytest.raises(ValueError, match="inside the Crucible repo"):
        materialize("c01", REPO / "evals" / "workspace")
