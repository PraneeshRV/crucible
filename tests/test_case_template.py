from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "skill" / "crucible" / "assets" / "case-template.md"

REQUIRED_KEYS = [
    "commitment:",
    "stakes:",
    "state:",
    "opened:",
    "evidence_standard:",
    "decision_authority:",
    "justified_if:",
    "underdetermined_if:",
    "blocked_if:",
]

REQUIRED_SECTIONS = [
    "## Rivals",
    "## Predeclared checks",
    "## Evidence log",
    "## Resolution",
]


def text():
    return TEMPLATE.read_text()


def test_frontmatter_keys_present():
    body = text()
    missing = [k for k in REQUIRED_KEYS if k not in body]
    assert missing == [], f"missing frontmatter keys: {missing}"


def test_sections_present():
    body = text()
    missing = [s for s in REQUIRED_SECTIONS if s not in body]
    assert missing == [], f"missing sections: {missing}"


def test_rivals_table_tracks_testability():
    body = text()
    rivals = body.split("## Rivals", 1)[1].split("##", 1)[0]
    assert "Testability" in rivals


def test_predeclared_checks_never_use_measured():
    # A prediction cannot be measured - the observation has not happened.
    # Note: the section's own prose must therefore avoid the literal bracket
    # form too, or the template cannot satisfy its own rule.
    body = text()
    section = body.split("## Predeclared checks", 1)[1].split("## Evidence log", 1)[0]
    assert "[measured" not in section


def test_predeclared_checks_state_the_no_measured_rule():
    # Guards against "fixing" the test above by deleting or inverting the rule.
    body = text()
    section = body.split("## Predeclared checks", 1)[1].split("## Evidence log", 1)[0]
    assert "never tagged `measured`" in section


def test_evidence_log_uses_measured_with_provenance():
    body = text()
    section = body.split("## Evidence log", 1)[1].split("## Resolution", 1)[0]
    assert "[measured:" in section


def test_resolution_separates_knowing_from_doing():
    body = text()
    section = body.split("## Resolution", 1)[1]
    assert "action_disposition:" in section
    assert "authorized_by:" in section
    # terminal state lives in frontmatter `state:` so the two cannot drift
    assert "terminal_state:" not in section
