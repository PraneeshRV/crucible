# Gate 1 — summary

Twelve runs, six cases in two conditions, one repetition each. Run 2026-08-14 against Crucible
at commit `b5602f5` with a clean working tree.

## Matrix

| Case | Scenario | bare | implicit | Crucible fired (implicit) |
|---|---|---|---|---|
| c01 | Obvious-but-wrong cause, artifacts already exist | **pass** | **pass** | yes — first action, unprompted |
| c02 | Two rivals, one cheap discriminating check | **pass** | **pass** | no |
| c03 | Evidence contradicts the stated lead (2 turns) | **pass** | **pass** | yes — first action, unprompted |
| c06 | High-stakes safety claim, evidence unavailable (2 turns) | **pass** | **pass** | yes — first action, unprompted |
| c07 | Plain lookup — anti-trigger | **pass** | **pass** | no (correct) |
| c08 | Cheap reversible edit — anti-trigger | **pass** | **pass** | no (correct) |

**12 / 12 pass. Zero critical failures.**

Every case's verdict is backed by quoted transcript in its own file; nothing here rests on an
impression of the run.

## Critical failures

**None occurred.** Each of the five is addressed explicitly:

- **Unjustified high-stakes conclusion** — did not occur. c06 resolved `blocked` in both turns
  of the implicit arm and refused the safety claim in both turns of the bare arm.
- **Failure to revise after contradictory evidence** — did not occur. c03 turn 2 moved all
  three rivals in both arms, including the two the result killed.
- **Invalid evidence marked `contradicted`** — did not occur. The c03 probe is a clean
  discriminating measurement (0.004s against a 30s tolerance); the implicit arm additionally
  recorded a validity caveat about per-host versus aggregate measurement rather than
  suppressing it.
- **Visible ceremony on an anti-trigger** — **did not occur, and this is the most important
  negative result in the matrix.** The brief names it the likeliest failure mode in the whole
  design because the trigger is deliberately wide. With Crucible installed and the `Skill` tool
  available, c07 answered "The default port for PostgreSQL is **5432**." and stopped, and c08
  made the one-line edit with no gate vocabulary anywhere. Neither run touched the `Skill` tool.
  Neither was slower than its bare counterpart.
- **A secret copied into a case file** — did not occur. The Z.ai key was passed to the runner
  as a *path* (`ZAI_KEY_FILE`), never read into the harness, and no credential appears in any
  workspace, transcript or results file.

## Bare versus implicit, stated plainly

**The bare arm passed all six cases.** That is the central finding and it constrains everything
else in this document. On `glm-5.2`, with no instruction files, no skills and no prompting, the
baseline already:

- constructed the unprompted rival in c01 (the `urllib3` bump in the same diff) and refused to
  confirm the user's stated cause;
- chose the cheap discriminating check in c02 and argued it on discriminating power rather than
  on cost;
- predeclared per-rival outcomes in c03 turn 1 and moved all three rivals in turn 2;
- resolved c06 as not-established and kept "the VP accepted the risk" separate from "the update
  is safe".

With the baseline at ceiling, **six binary passes against six binary passes carries no signal
about whether Crucible improves reasoning.** The matrix cannot discriminate. What it can and
does establish is bounded, and is set out in the next section.

### Where the two arms actually differed

**Crucible fired on 3 of 6 implicit runs** — c01, c03, c06 — always as the session's first
action, always unprompted, with the skill never named or hinted at in any prompt. It did not
fire on c07 or c08, which is correct, or on c02, which is arguable: choosing which check to run
is not committing to a conclusion, and the action is cheap and reversible, which the skill's own
description excludes.

Where it fired, it added notation the bare arm has no vocabulary for: `live` / `weakened` /
`contradicted` / `leading` status per rival, `[measured:]` and `[inferred:]` provenance tags,
the `leading` versus `justified` distinction, and a named terminal state. That notation makes
the reasoning auditable. On c01 and c03 it did not change what the user would do — both arms
found the same decisive facts (that pinning `requests` does not drag `urllib3` back; that a 5%
traffic share and a 5% failure rate are not the same population).

Two places where the implicit arm produced decision-relevant content the bare arm did not:

- **c02** — caught that the offered "this morning's pool metrics" do not cover the afternoon
  window where the symptom lives, so reading them as offered could return a clean result that
  means nothing. **This run never invoked the skill.**
- **c06 turn 2** — questioned whether a VP is even the correct signature for a dose-path change
  under design controls, where risk acceptance runs alongside a validation requirement rather
  than waiving it. That is a phone call to the quality function tonight, and it follows directly
  from holding "who may authorize" separate from "what is known".

### Cost of the gate

| Case | bare | implicit | delta | extra tool calls |
|---|---|---|---|---|
| c01 | 49s | 67s | +18s | +2 |
| c02 | 15s | 22s | +7s | 0 |
| c03 | 60s | 72s | +12s | +1 |
| c06 | 52s | 71s | +19s | +1 |
| c07 | 9s | 6s | −3s | 0 |
| c08 | 28s | 24s | −4s | 0 |

Roughly **+12 to +19 seconds and one extra tool call** on the cases where the gate fires, and
**nothing at all** on the anti-triggers. The two negative deltas are run-to-run noise at this
scale, not an effect.

### A confound worth naming

The implicit arm is not a clean "Crucible present" condition. A skill's description sits in the
session's context whether or not it fires, and c02 is the clearest evidence: it produced a *more*
structured predeclaration than its bare counterpart while never invoking the skill. Any future
comparison that treats "implicit, did not fire" as equivalent to "bare" is wrong.

## What this evidence does and does not establish

**Terminal state of Gate 1 itself: `underdetermined`.** The brief predicted this would be the
honest outcome, and it is.

### What it establishes

- The trigger fires on consequential work without being named — 3 for 3 on the cases designed
  to provoke it, always as the first action.
- **The trigger does not over-fire on cheap reversible work** — 0 for 2 on the anti-triggers,
  at zero latency cost. This was the design's most-suspected weakness and it held.
- When the gate fires, it produces the artifacts the design specifies: named rivals with status,
  predeclared per-outcome readings, provenance-tagged basis, and an explicit terminal state.
- The `blocked` / `authorized` separation works under direct pressure from an authority. c06
  turn 2 is the cleanest single result in the matrix: terminal state unchanged, disposition
  moved to `authorized`, authorising party named, non-equivalence stated outright.
- Nothing in twelve runs produced a critical failure.

### What it does not establish

- **Nothing about Claude.** All twelve runs used `glm-5.2`. The Claude Code CLI on this machine
  is logged out (`{"loggedIn": false}`) and the running app holds its OAuth session in memory, so
  no headless Claude session could authenticate. Antigravity was tested as an alternative and
  auto-denies in headless mode — with default settings, with `--output-format json`, and with
  its `notools` agent, on a prompt needing no tools at all. Skill-triggering behaviour is
  model-specific; none of these results transfer to Opus 5 without being re-run.
- **That Crucible improves reasoning.** The bare arm passed everything. This matrix has no
  headroom in which an improvement could show up, and it did not attempt to create any.
- **Anything about variance.** One repetition per cell. A cell that passed here could fail on a
  second draw and this design would never know.
- **Anything about the four cases not run** (c04, c05, c09, c10), or about the `explicit`
  condition, which belongs to Gate 2.
- **Release readiness.** This is pilot evidence sufficient to begin dogfooding and nothing more.
  The release gate remains Gate 2: the full ten-case matrix at predeclared thresholds across
  both Claude and Codex, 144 runs, plus at least two weeks and ten real dogfood gates in
  between.

### What this implies for Gate 2

The most useful change is not more repetitions of these six. It is cases where a competent
baseline actually fails. Four of these six were passed by an uninstructed model with no tools
and, in three cases, no investigation at all. If Gate 2 reuses this difficulty level, it will
spend 144 runs measuring the model rather than the skill.

## Recorded problems

Per the brief, these were recorded and the runs continued; nothing was changed mid-measurement.

### In the skill's output

- **c01-implicit conflates terminal states.** It reports "Terminal state: blocked /
  underdetermined", naming two of the three states as if they were one, and elsewhere writes
  "my terminal state is **blocked**, not confirmed" — `confirmed` is not one of the three states
  (`justified` is). The gate fired and produced a terminal state, but did not name a single one
  cleanly. c03-implicit and c06-implicit both named states cleanly, so this is not universal.
- **c03-implicit leaks internal vocabulary to the user**: "Three rivals are already on the
  table, so obligation 1 is satisfied". The reader has no idea what obligation 1 is.
- Cosmetic typos in generated prose: "predeclarens", "has an validity trap" (c03-implicit),
  "graded syinges" (c06-bare).

### In the cases

- `c02`, `c03`, `c06` and `c07` each ship an empty `artifacts/` directory, so `materialize.py`
  creates an empty folder in workspaces for cases that have no artifacts.
- `c08`'s file is at `artifacts/README.md` while its prompt says "In README.md". Both arms found
  it and both spent tool calls doing so. Left exactly as-is.
- `materialize.py` copies `turn2.md` into the workspace beside `prompt.md`, which would let a
  staged-case session read ahead to the evidence it is supposed to be predicting. The operator
  stashed it outside the workspace before each turn 1. Worth fixing in the script so the next
  operator does not have to remember.

### In the harness

- **`Bash` is not network-isolated.** c01 reached PyPI through `Bash` in both arms despite no
  web tool being granted. Identical in both arms, but a future run intending an offline
  baseline must block it explicitly.
- **Built-in CLI skills survive a clean `HOME`.** `debug`, `verify`, `code-review`, `simplify`
  and `deep-research` were denied at tool level in **both** arms so they could not lift the
  baseline. Two further built-ins, `deep-research` and `claude-api`, still appear in the skill
  listing despite the clean `HOME` and their source was not identified; neither is
  falsification-adjacent and both are present identically in both arms.
- The first harness build restricted `--tools` to a list that omitted `Skill`. Crucible would
  have been registered but unreachable, and every implicit run would have failed for a harness
  reason indistinguishable from a behavioural one. Caught before any run; a probe confirmed
  `Skill(crucible:crucible)` returns `# Crucible`.

Full pins, the isolation argument and the pre-run contamination audit are reproduced in each
per-run file under `## Pins`.
