from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skill" / "crucible"

REQUIRED = [
    "skill/crucible/SKILL.md",
    "skill/crucible/assets/case-template.md",
    "skill/crucible/agents/openai.yaml",
    "evals/materialize.py",
    "README.md",
]


def test_required_files_exist():
    missing = [p for p in REQUIRED if not (REPO / p).exists()]
    assert missing == [], f"missing: {missing}"


def test_shipped_skill_contains_no_code():
    # The installed skill must ship no executable code.
    offenders = [
        p.relative_to(REPO).as_posix()
        for p in SKILL.rglob("*")
        if p.is_file() and p.suffix in {".py", ".sh", ".js", ".ts"}
    ]
    assert offenders == [], f"code inside shipped skill: {offenders}"


def test_evals_are_outside_the_shipped_skill():
    assert not (SKILL / "evals").exists()
    assert (REPO / "evals").is_dir()
