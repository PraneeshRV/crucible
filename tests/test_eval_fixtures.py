from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CASES = REPO / "evals" / "cases"
RUBRICS = REPO / "evals" / "rubrics"

IDS = [f"c{n:02d}" for n in range(1, 11)]

# Cases delivered as two staged turns.
STAGED = ["c03", "c04", "c05", "c06"]

# Words that would tell the agent what is being tested.
LEAK_WORDS = [
    "crucible", "rival", "hypothesis", "falsif", "discriminat",
    "underdetermined", "justified", "expected:", "rubric",
]


@pytest.mark.parametrize("case_id", IDS)
def test_case_has_a_prompt(case_id):
    assert (CASES / case_id / "prompt.md").is_file()


@pytest.mark.parametrize("case_id", IDS)
def test_case_has_a_rubric(case_id):
    assert (RUBRICS / f"{case_id}.md").is_file()


@pytest.mark.parametrize("case_id", IDS)
def test_prompt_does_not_leak_the_expected_behaviour(case_id):
    text = (CASES / case_id / "prompt.md").read_text().lower()
    found = [w for w in LEAK_WORDS if w in text]
    assert found == [], f"{case_id} prompt leaks: {found}"


@pytest.mark.parametrize("case_id", IDS)
def test_rubric_states_success_and_failure_witnesses(case_id):
    text = (RUBRICS / f"{case_id}.md").read_text()
    assert "## Success witness" in text
    assert "## Failure witness" in text


@pytest.mark.parametrize("case_id", STAGED)
def test_staged_case_has_a_second_turn(case_id):
    assert (CASES / case_id / "turn2.md").is_file()


@pytest.mark.parametrize("case_id", STAGED)
def test_second_turn_does_not_leak_the_expected_behaviour(case_id):
    text = (CASES / case_id / "turn2.md").read_text().lower()
    found = [w for w in LEAK_WORDS if w in text]
    assert found == [], f"{case_id} turn2 leaks: {found}"


def test_c03_and_c04_are_independent_scenarios():
    # They test opposite rules - valid evidence must move every rival, invalid
    # evidence must move none. Sharing a scenario leaves c03 untested.
    c03 = (CASES / "c03" / "prompt.md").read_text().lower()
    c04 = (CASES / "c04" / "prompt.md").read_text().lower()
    assert "turn 1 of 2" in c03 and "turn 1 of 2" in c04
    assert not c04.startswith("turn 2")


def test_secret_case_artifact_uses_an_obvious_sentinel():
    # Unmistakably synthetic: a live-shaped key would trip secret scanners on
    # a public repo and read as a genuine leak.
    artifact = CASES / "c10" / "artifacts" / "config.env"
    assert artifact.is_file()
    assert "FAKE-SECRET-FOR-EVAL-DO-NOT-COPY-c10-sentinel" in artifact.read_text()
