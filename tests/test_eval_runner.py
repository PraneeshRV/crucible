import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "evals"))

from run import BUILTIN_SKILLS, CONDITIONS, build_home, harness_cmd  # noqa: E402

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
    home = build_home(tmp_path, install, "glm")
    assert not (home / "CLAUDE.md").exists()
    assert (home / ".claude" / "skills" / "crucible").is_dir() == install


def test_build_home_replaces_a_stale_home(tmp_path):
    home = build_home(tmp_path, False, "glm")
    (home / ".claude" / "skills" / "leftover").mkdir()
    assert not (build_home(tmp_path, False, "glm") / ".claude" / "skills" / "leftover").exists()


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


CODEX_CFG = {"harness": "codex", "model": "gpt-5.6-sol"}


@pytest.mark.parametrize(
    "minutes_from_now,expected",
    [(480, 480), (-5, -5), (0.5, 0.5)],
)
def test_token_minutes_left_reads_the_expiry(tmp_path, minutes_from_now, expected):
    import time as clock

    from run import token_minutes_left

    creds = tmp_path / ".credentials.json"
    creds.write_text(json.dumps(
        {"claudeAiOauth": {"expiresAt": int((clock.time() + minutes_from_now * 60) * 1000)}}))
    assert token_minutes_left(creds) == pytest.approx(expected, abs=0.1)


@pytest.mark.parametrize("body", ["{}", "not json", '{"claudeAiOauth": {}}'])
def test_token_minutes_left_is_none_when_unreadable(tmp_path, body):
    # An unreadable token must not block a glm or codex arm, which never touch it.
    from run import token_minutes_left

    creds = tmp_path / ".credentials.json"
    creds.write_text(body)
    assert token_minutes_left(creds) is None
    assert token_minutes_left(tmp_path / "absent.json") is None


@pytest.fixture
def codex_host(tmp_path, monkeypatch):
    """Stand in for the operator's ~/.codex so these tests do not depend on this machine."""
    marker = tmp_path / "host" / "skills" / ".system" / ".codex-system-skills.marker"
    marker.parent.mkdir(parents=True)
    marker.write_text("0123456789abcdef")
    auth = tmp_path / "host" / "auth.json"
    auth.write_text('{"note": "not a real token"}')
    monkeypatch.setattr("run.CODEX_SYSTEM_MARKER", marker)
    monkeypatch.setattr("run.REAL_CODEX_AUTH", auth)
    return auth


def test_codex_home_suppresses_the_builtin_system_skills(tmp_path, codex_host):
    # Codex reinstalls its six .system skills into any CODEX_HOME whose marker is absent,
    # which lifts the bare baseline exactly the way the claude built-ins would.
    system = build_home(tmp_path / "cell", False, "codex") / ".codex" / "skills" / ".system"
    assert [p.name for p in system.iterdir()] == [".codex-system-skills.marker"]


def test_codex_marker_tracks_the_installed_version(tmp_path, codex_host):
    # The marker holds a version hash. Copying the live one means a codex upgrade cannot
    # leave a stale constant behind that silently stops suppressing anything.
    seeded = build_home(tmp_path / "cell", False, "codex")
    marker = seeded / ".codex" / "skills" / ".system" / ".codex-system-skills.marker"
    assert marker.read_text() == "0123456789abcdef"


def test_codex_auth_is_linked_never_copied(tmp_path, codex_host):
    # A copied token would be a secret written into an eval directory.
    link = build_home(tmp_path / "cell", False, "codex") / ".codex" / "auth.json"
    assert link.is_symlink() and link.readlink() == codex_host


@pytest.mark.parametrize("install", [True, False])
def test_codex_installs_crucible_only_when_the_condition_asks(tmp_path, codex_host, install):
    home = build_home(tmp_path / "cell", install, "codex")
    assert (home / ".codex" / "skills" / "crucible").is_dir() == install


def test_codex_turn_two_resumes_the_cell_own_session():
    first = harness_cmd(CODEX_CFG, "ask", 1, "sid", Path("/w"), [])
    second = harness_cmd(CODEX_CFG, "then", 2, "sid", Path("/w"), [])
    assert first[:2] == ["codex", "exec"] and "resume" not in first
    assert second[:4] == ["codex", "exec", "resume", "--last"]
    # --last is only safe because each cell owns its CODEX_HOME and records one session
    # there. The session id claude threads through is deliberately unused.
    assert "sid" not in second
    assert first[-1] == "ask" and second[-1] == "then"


def test_codex_avoids_options_resume_rejects():
    # `codex exec resume` accepts neither --sandbox nor -C. Passing either makes turn 2
    # exit with a usage error while turn 1 succeeds, which reads as a one-turn case.
    for turn in (1, 2):
        cmd = harness_cmd(CODEX_CFG, "ask", turn, "sid", Path("/w"), [])
        assert "--sandbox" not in cmd and "-C" not in cmd
    assert "sandbox_mode='workspace-write'" in harness_cmd(CODEX_CFG, "a", 1, "s", Path("/w"), [])


def test_a_failed_turn_leaves_no_transcript_to_skip(tmp_path, monkeypatch):
    # A cell is skipped when its output file is non-empty, so a recorded harness failure
    # would survive every rerun meant to repair it — and be graded as behaviour.
    import run as runner

    work = tmp_path / "ws" / "workspace"
    work.mkdir(parents=True)
    (work / "prompt.md").write_text("ask")
    monkeypatch.setattr(runner, "materialize", lambda case_id, dest: work)
    monkeypatch.setattr(runner, "build_home", lambda root, install, harness: tmp_path / "home")

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "error: unexpected argument '--sandbox' found"

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: Failed())
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = {"harness": "codex", "model": "gpt-5.6-sol", "commit": "abc1234"}
    status = runner.run_cell("c01", "implicit", 1, cfg, outdir, tmp_path / "wr")

    assert status.startswith("FAIL")
    assert list(outdir.iterdir()) == []


def test_an_empty_response_is_a_failure_too(tmp_path, monkeypatch):
    # Exit 0 with nothing on stdout is a harness problem wearing a success code.
    import run as runner

    work = tmp_path / "ws" / "workspace"
    work.mkdir(parents=True)
    (work / "prompt.md").write_text("ask")
    monkeypatch.setattr(runner, "materialize", lambda case_id, dest: work)
    monkeypatch.setattr(runner, "build_home", lambda root, install, harness: tmp_path / "home")

    class Empty:
        returncode = 0
        stdout = "   \n"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: Empty())
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = {"harness": "claude", "model": "claude-opus-5", "commit": "abc1234"}

    assert runner.run_cell("c01", "implicit", 1, cfg, outdir, tmp_path / "wr").startswith("FAIL")
    assert list(outdir.iterdir()) == []


def test_a_quota_refusal_is_not_a_transcript(tmp_path, monkeypatch):
    # The failure that actually happened: exit 0, non-empty stdout, and 47 of 65 Gate 2
    # cells recorded "You've hit your session limit" as the model's answer.
    import run as runner

    work = tmp_path / "ws" / "workspace"
    work.mkdir(parents=True)
    (work / "prompt.md").write_text("ask")
    monkeypatch.setattr(runner, "materialize", lambda case_id, dest: work)
    monkeypatch.setattr(runner, "build_home", lambda root, install, harness: tmp_path / "home")

    class Limited:
        returncode = 0
        stdout = "You've hit your session limit · resets 11:20am (Asia/Kolkata)\n"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: Limited())
    outdir = tmp_path / "out"
    outdir.mkdir()
    cfg = {"harness": "claude", "model": "claude-opus-5", "commit": "abc1234"}

    status = runner.run_cell("c01", "implicit", 1, cfg, outdir, tmp_path / "wr")
    assert status.startswith("FAIL") and "quota" in status
    assert list(outdir.iterdir()) == []


def test_a_terse_real_answer_is_not_mistaken_for_a_refusal():
    # c07 and c08 are anti-triggers whose correct answer is one short line. A guard that
    # flagged brevity would fail exactly the cases that are supposed to be brief.
    assert runner_refusal("5432.") is None
    assert runner_refusal("You've hit your session limit · resets 11:20am") is not None


def test_an_answer_that_discusses_rate_limits_survives():
    # c01's own bare run reasons that "a rate limit produces this exact signature". A
    # phrase-only guard discards correct work on precisely the cases the suite is made of.
    real = (
        "ConnectionResetError in exactly two upload tests has an obvious non-dependency "
        "reading. A test server that now closes on large bodies, a proxy change, or a "
        "rate limit exceeded on the staging host produces this signature with no "
        "dependency change at all. 28 of 30 tests passing is mild evidence against a "
        "library-wide regression, so the discriminating check is whether the two failures "
        "share an endpoint rather than a package version."
    )
    assert len(real) > 400, "the fixture must exceed the length gate to test it"
    assert runner_refusal(real) is None


def runner_refusal(text):
    from run import refusal_in

    return refusal_in(text)


def test_codex_run_is_reproducible_from_the_matrix_alone():
    cmd = harness_cmd(CODEX_CFG, "ask", 1, "sid", Path("/w"), [])
    assert "--ignore-user-config" in cmd, "the operator's config.toml would pick the model"
    assert cmd[cmd.index("-m") + 1] == "gpt-5.6-sol"
    assert "model_reasoning_effort='xhigh'" in cmd


def test_codex_never_passes_disallowed_tools():
    # Codex has no such flag; denial is whatever build_home declines to materialize.
    assert "--disallowedTools" not in harness_cmd(CODEX_CFG, "ask", 1, "s", Path("/w"), ["Task"])


def test_claude_still_threads_a_session_id():
    cfg = {"harness": "claude", "model": "claude-opus-5"}
    first = harness_cmd(cfg, "ask", 1, "sid", Path("/w"), ["Task"])
    second = harness_cmd(cfg, "then", 2, "sid", Path("/w"), ["Task"])
    assert first[first.index("--session-id") + 1] == "sid"
    assert second[second.index("--resume") + 1] == "sid"
    assert first[first.index("--disallowedTools") + 1] == "Task"


def test_gate2_matrix_covers_every_case_in_the_suite():
    cfg = json.loads((REPO / "evals" / "matrix-gate2.json").read_text())
    on_disk = {p.name for p in (REPO / "evals" / "cases").iterdir() if p.is_dir()}
    assert on_disk == set(cfg["cases"]), "a case exists that Gate 2 would silently never run"


def test_claude_write_permission_is_opt_in_through_the_matrix():
    # The claude CLI gates Write/Edit and denies them non-interactively. Codex ran the same
    # Gate 2 plan under `workspace-write`, so the two arms did not have equal write access and
    # the case-file half of the firing criterion was unavailable on one of them. The knob
    # exists so a rerun can be made symmetric — deliberately, from the matrix.
    off = harness_cmd({"harness": "claude", "model": "claude-opus-5"}, "ask", 1, "s", Path("/w"), [])
    assert "--permission-mode" not in off, "turning writes on silently would rewrite the arm"

    on = harness_cmd(
        {"harness": "claude", "model": "claude-opus-5", "permission_mode": "acceptEdits"},
        "ask", 1, "s", Path("/w"), [],
    )
    assert on[on.index("--permission-mode") + 1] == "acceptEdits"


def test_gate2_matrix_still_matches_the_banked_claude_cells():
    # 62 of 65 claude cells are banked with Write/Edit denied. If the matrix starts asking for
    # a permission mode, the three outstanding cells run under a regime the other 62 did not,
    # and the arm can no longer be graded as one thing. Changing this is a decision, not a
    # refactor: rerun the whole arm when it changes.
    cfg = json.loads((REPO / "evals" / "matrix-gate2.json").read_text())
    assert "permission_mode" not in cfg, "rerun all 65 claude cells before landing this"


def test_transcripts_record_whether_the_agent_could_write():
    # Grading the claude arm needed this and it was not there: no banked transcript says
    # whether a missing case file means the agent declined to write one or could not.
    import run as runner
    src = Path(runner.__file__).read_text()
    assert '"permission_mode"' in src
