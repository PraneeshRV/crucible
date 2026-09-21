# Crucible

A falsification gate for AI agents.

Crucible does not replace domain investigation. It governs the investigation the enclosing
agent is already doing. It intercepts the moment that agent is about to commit to a
conclusion that is expensive to get wrong, and forces it to construct a rival explanation,
predeclare what each possible outcome would mean, run the check most likely to change the
decision, update every rival rather than the favoured one, and resolve into an explicit
terminal state.

It records what is *known* separately from what is *permitted*. An authority can authorize
acting under acknowledged uncertainty. It can never turn an unsupported conclusion into a
justified one.

## Install

```bash
git clone https://github.com/PraneeshRV/crucible ~/Praneesh/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.claude/skills/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.agents/skills/crucible
```

## Use

Invoke it explicitly on the conclusion you are about to act on:

```
$crucible the 401s are caused by the build-1187 deploy, rolling back
```

Explicit invocation is the supported path and the only one the evidence below covers.
Automatic invocation is enabled and does fire, but not reliably enough to depend on. If the
gate matters for a given decision, name it.

## Status

Pre-release, shipped narrow. Two evidence gates have run against this skill: Gate 1 (12 runs,
two models) and Gate 2 (65 cells per harness, 14 cases, Claude and Codex). The repository
carries 150 structural, packaging and harness tests. Every claim below is tagged with what
establishes it.

| Claim | State |
|---|---|
| Fires when invoked explicitly | **Established.** 14/14 gated cases, both arms, every rep `[measured]` |
| Stays silent on work that does not need it | **Established.** Both anti-trigger cases silent on every rep in both arms, which is the suite's one `[CRITICAL]` criterion `[measured]` |
| Produces correct terminal states | **Established on Claude.** Graded across the suite in `evals/results/GATE-2-GRADING-CLAUDE.md`, zero critical failures `[measured]` |
| Fires reliably without being named | **Not established.** Missed the predeclared 3/3 threshold on 5 of 14 cases `[measured]` |
| Improves the reasoning of a frontier model | **Not established.** An uninstructed model passed 14 of 15 cases with no gate at all `[measured]` |
| Behaves the same across harnesses | **Cannot be established.** The two arms ran under unequal write permissions, and the Codex arm cannot be completed `[blocked]` |

Terminal state of the release claim: **`justified` for explicit invocation on a single
harness**, `underdetermined` for everything else. Permission to ship the narrow claim is
recorded separately from what the evidence establishes, as the skill itself requires.

### What the automatic-trigger misses actually were

On the Claude arm the implicit trigger missed on c02, c04, c09, c10 and c14; on Codex, on
c02, c03 and c14. In every case the miss is a **correct answer reached without the gate**,
not a wrong one. `c02-implicit-r2` picks the cheap check, states what it can and cannot
settle, and names the discriminating outcome, in prose, with no rival table, no basis tags
and no declared terminal state. The skill did not engage and the model was good anyway.

Part of that spread is a harness artifact rather than the model: firing was scored on
structural markers in the response only, because the case-file half of the firing criterion
was unavailable to the Claude arm. See "Known limits".

### Known limits

- **The over-refusal guard is unproven, not passed.** `c11` is the suite's only case that is
  passed by committing rather than by holding, kept specifically to catch a build that
  refuses to commit when it should. Both Claude cells resolved `underdetermined` instead.
  They are graded as passes: the rubric was widened on 2026-09-21 to require an unhedged
  commitment on the *mechanism* that permitted the duplicates while allowing the *write path*
  to stay open when the settling check is named, and both cells meet that. Neither hedged
  blindly, and both declined for a substantive reason the original rubric did not anticipate,
  namely that the rebuild it asked them to certify would trade silent bad data for an aborted
  nightly job. That is nonetheless the third adjudication in the same direction, after Gate
  1's `c03` and `c06`, and the behaviour this case exists to catch has never once been
  observed, so it establishes nothing about over-refusal in either direction. Rubric:
  `evals/rubrics/c11.md`. Reasoning: `GATE-2-GRADING-CLAUDE.md` section 4.
- **Three Gate 2 cells are unwitnessed on turn 2**, not passed and not failed:
  `c12-bare-r2`, `c13-explicit-r1`, `c14-explicit-r2`. The harness captured what each cell
  printed and not what it wrote, and twelve of 65 cells persisted state to memory files the
  grader never saw. `run.py` now records every path a cell writes; the grades above predate
  that fix.
- **The Claude arm ran without `Write` and `Edit`.** `run.py` passed no permission mode, so
  the two arms are not cross-comparable and the Claude firing counts are a lower bound.
- **Improvement over an uninstructed model is measured in one case family.** `c12` is the
  only case where the ungated baseline fails, and it replicates at 2/3, not 3/3.

Evidence and open gates in full: `evals/results/GATE-2-SUMMARY.md`.

## Design

Full specification: `docs/superpowers/specs/2026-07-29-crucible-skill-design.md` in the
author's vault.
