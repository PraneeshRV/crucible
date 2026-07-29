from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
YAML_PATH = REPO / "skill" / "crucible" / "agents" / "openai.yaml"


def load():
    return yaml.safe_load(YAML_PATH.read_text())


def test_parses_as_a_mapping():
    assert isinstance(load(), dict)


def test_short_description_within_25_to_64_chars():
    sd = load()["interface"]["short_description"]
    assert 25 <= len(sd) <= 64, f"short_description is {len(sd)} chars"


def test_default_prompt_names_the_skill():
    dp = load()["interface"]["default_prompt"]
    assert "$crucible" in dp


def test_implicit_invocation_declared_true():
    # Crucible is worthless if it only fires on explicit $crucible: the gate
    # matters most when the user would not think to reach for it.
    assert load()["policy"]["allow_implicit_invocation"] is True


def test_no_mcp_dependencies():
    # Nothing in the design requires a server.
    assert "dependencies" not in load()
