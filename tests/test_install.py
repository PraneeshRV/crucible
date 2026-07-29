from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "skill" / "crucible"

TARGETS = [
    Path.home() / ".claude" / "skills" / "crucible",
    Path.home() / ".agents" / "skills" / "crucible",
]

# These assert on machine state, not repo content. A fresh clone has not
# installed anything, so skip rather than fail - this repo is public.
installed = pytest.mark.skipif(
    not any(t.exists() for t in TARGETS),
    reason="crucible not installed on this machine; see README",
)


@installed
@pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.parent.parent.name)
def test_symlink_exists_and_resolves_to_source(target):
    assert target.is_symlink(), f"{target} is not a symlink"
    assert target.resolve() == SOURCE.resolve()


@installed
@pytest.mark.parametrize("target", TARGETS, ids=lambda p: p.parent.parent.name)
def test_skill_md_readable_through_the_link(target):
    assert (target / "SKILL.md").read_text().startswith("---\n")
