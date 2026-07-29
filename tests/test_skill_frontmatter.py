from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SKILL_MD = REPO / "skill" / "crucible" / "SKILL.md"


def load():
    text = SKILL_MD.read_text()
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body


def test_name_is_crucible():
    fm, _ = load()
    assert fm["name"] == "crucible"


def test_description_fits_the_loader_budget():
    fm, _ = load()
    assert len(fm["description"]) <= 1024


def test_description_carries_the_anti_triggers():
    # The description decides whether the skill loads, so anti-triggers
    # placed only in the body arrive too late.
    fm, _ = load()
    d = fm["description"].lower()
    assert "do not use" in d
    for anti in ["lookup", "mechanical", "reversible"]:
        assert anti in d, f"anti-trigger {anti!r} missing from description"


def test_description_covers_the_single_hypothesis_trigger():
    # The gate must fire precisely when the agent has already converged.
    fm, _ = load()
    d = fm["description"].lower()
    assert "only one explanation" in d


def test_body_defines_every_status_and_terminal_state():
    _, body = load()
    for token in ["leading", "live", "weakened", "contradicted"]:
        assert f"`{token}`" in body, f"status {token!r} missing"
    for token in ["justified", "underdetermined", "blocked"]:
        assert f"`{token}`" in body, f"terminal state {token!r} missing"


def test_body_defines_all_four_basis_tags_with_provenance():
    _, body = load()
    for token in ["[measured:", "[documented:", "[inferred:", "[guess]"]:
        assert token in body, f"basis tag {token!r} missing"


def test_body_states_the_load_bearing_rules():
    _, body = load()
    low = body.lower()
    assert "never `blocked`" in body or "never blocked" in low
    assert "invalid instrumentation" in low
    assert "unfalsifiable" in low
