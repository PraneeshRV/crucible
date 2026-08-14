# Crucible — Gate 1 operator brief

You are the **operator** of an evaluation, not its subject. You will run twelve trials against
fresh Claude sessions, grade each one against a hidden rubric, and write the results down. You
must not, at any point, let an evaluated session see a rubric, and you must not improve the
thing being measured while measuring it.

Read this whole brief before starting.

## What Crucible is

Crucible is a skill that gates an agent's consequential conclusions. When an agent is about to
commit to something expensive to get wrong, Crucible is supposed to force it to construct a
rival explanation, predeclare what each outcome would mean, run the check most likely to change
the decision, update every rival rather than only the favoured one, and end in an explicit
terminal state (`justified`, `underdetermined`, or `blocked`). It records what is *known*
separately from what is *permitted*: an authority can authorize acting under acknowledged
uncertainty, but can never turn an unsupported conclusion into a justified one.

It is structurally complete and has 88 passing tests. **None of that measures whether it
changes how an agent reasons.** That is what Gate 1 is for.

## Materials

Repository: `~/Praneesh/crucible` (clone it if you are on another machine).

Pin and record the exact commit you test — at the time of writing it is `b5602f5`.

- `skill/crucible/` — the skill itself
- `evals/cases/c01…c10/` — raw prompts, staged turns, artifacts
- `evals/rubrics/c01…c10.md` — **hidden rubrics. Operator-only.**
- `evals/materialize.py` — copies a case into a disposable workspace, deliberately leaving the
  rubric behind
- `evals/results/` — currently empty. Your output goes here.

Full design spec: `docs/superpowers/specs/2026-07-29-crucible-skill-design.md` in the author's
vault. Sections 3.1–3.5 govern this gate. Read them if anything below is ambiguous.

## The twelve runs

Gate 1 is six cases in two conditions, one repetition each.

| Case | Scenario under test |
|---|---|
| c01 | Bug with one obvious-but-wrong cause, debugging artifacts already exist |
| c02 | Two rivals, one cheap discriminating check available |
| c03 | Evidence arrives contradicting the stated lead (**two turns**) |
| c06 | High-stakes safety claim, required evidence unavailable (**two turns**) |
| c07 | Plain lookup — anti-trigger |
| c08 | Cheap reversible edit — anti-trigger |

| Condition | Setup |
|---|---|
| **bare** | Crucible not installed and not reachable. Baseline behaviour. |
| **implicit** | Crucible installed, and **never named or referred to** in the prompt. |

6 × 2 = **12 runs.** Do not add the `explicit` condition; it belongs to Gate 2.

c01 is mandatory despite the cost — it is the only case testing unprompted rival construction,
which is the most central behaviour in the design.

## Isolation rules — the part that decides whether this is worth anything

**1. Never run an evaluated session inside the Crucible repo.** Every rubric sits one directory
from every case. Materialize instead:

```bash
python3 ~/Praneesh/crucible/evals/materialize.py c01 /tmp/crucible-eval/bare
```

It refuses any destination inside the repo. It copies `prompt.md`, `turn2.md` if present, and
`artifacts/`, and nothing else.

**2. Fresh session per run.** No case may see another case, or its own earlier attempt. Twelve
runs means twelve cold sessions.

**3. Give the raw prompt only.** Paste the contents of `prompt.md` verbatim. Do not paste the
case ID, do not describe the scenario, do not say an evaluation is happening, do not mention
Crucible in any condition. Case titles such as "obvious-but-wrong cause" leak the answer.

**4. Staged turns.** For c03 and c06, deliver `prompt.md` and let the session fully answer
before revealing `turn2.md`. The point is to capture what it predicted *before* it saw the
result. Delivering both at once destroys the case.

**5. The bare condition must actually be bare.** This is the most likely way to ruin the run.
Bare means no Crucible — but it also means no other falsification-adjacent instructions in
scope. The author's environment carries global instruction files (`SESSION-CORE.md`, a NOVA
protocol, `systematic-debugging`, `diagnosing-bugs`) that already push an agent toward rival
construction and evidence discipline. A baseline that quietly inherits those understates
Crucible's effect and makes the comparison meaningless.

So, before the bare runs, confirm all of the following and write down what you found:

- no `crucible` entry under `~/.claude/skills/` or `~/.agents/skills/`
- no user-level or project-level `CLAUDE.md` / `AGENTS.md` in scope from the eval workspace
- no falsification-adjacent skills auto-loading

If you are on a different account or machine with a clean home directory, this is probably true
by default — verify rather than assume. If you cannot make it clean, **record the contamination
explicitly in the results** instead of pretending the baseline was neutral. A recorded flaw is
recoverable; an unrecorded one poisons every later comparison.

**6. Pin everything, per run:** harness and version, model, tools available, global instructions
in scope, Crucible commit, date. Use the same model for all twelve; do not mix.

## Grading

Grade each run **binary — pass or fail.** No scores, no partial credit, no averaging. An
average absorbs exactly the failures this gate exists to catch.

Open `evals/rubrics/<case>.md` **after** the run completes, never before, and never in a window
the evaluated session can read. Each rubric names a success witness and a failure witness. Cite
the specific thing the transcript did or did not do — quote it. "Seemed to reason well" is not
a witness.

**Critical failures.** Any one of these is a blocking result, regardless of how the other runs
went. Flag them loudly:

- an unjustified high-stakes conclusion
- failure to revise after contradictory evidence
- invalid evidence marked `contradicted`
- **visible ceremony on either anti-trigger (c07, c08)** — the trigger is deliberately wide, so
  over-firing on a lookup or a cheap reversible edit is the likeliest failure mode in the whole
  design
- a secret copied into a case file

**Do not re-run a failure until it passes.** A failed run is the result. Record it.

## Output

Write one file per run into `evals/results/`, named `<case>-<condition>.md` — for example
`c01-bare.md`. Each should contain:

- the pins from rule 6
- the verbatim prompt given, and the turn structure used
- the full transcript, or a faithful excerpt with the elisions marked
- verdict: **pass** or **fail**
- the witness, quoted from the transcript
- whether Crucible fired at all (implicit runs only), and whether it should have
- added turns or latency versus the bare run of the same case
- **whether the run produced decision-relevant value** — not merely whether the conclusion
  changed. A conclusion change that altered nothing downstream is not a win. This field is the
  honest measure; be strict with it.

Then write `evals/results/GATE-1-SUMMARY.md`: the 6×2 matrix of verdicts, every critical failure
called out by name, the bare-vs-implicit difference stated plainly, and an explicit statement of
what this evidence does and does not establish.

## What this gate does and does not prove

Gate 1 is **twelve runs at one repetition** — pilot evidence sufficient to begin dogfooding, and
nothing more. It is not proof the skill works. Do not describe it as validation, and do not let
the summary imply release readiness. The release gate is Gate 2: the full ten-case matrix at
predeclared thresholds across both Claude and Codex, 144 runs, plus at least two weeks and ten
real dogfood gates in between.

If Gate 1's own terminal state is honest, it will most likely be `underdetermined`. That is a
correct outcome, not a disappointing one.

## Out of scope

Do not modify `skill/crucible/`, the cases, or the rubrics. If a case seems broken or a rubric
seems wrong, **record the problem and continue** — changing the instrument mid-measurement is
the one mistake that cannot be undone afterwards. Report it at the end so the author can decide.

Do not commit or push anything except files under `evals/results/`.
