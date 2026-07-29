---
name: crucible
description: Use when about to commit to a conclusion that is expensive to get wrong - a root cause, a security finding, an architecture decision, a claim that something is safe or correct - including when only one explanation has been considered. Forces a rival explanation, predeclared predictions, and an explicit terminal state before the conclusion is acted on. Do NOT use for lookups, single-fact retrieval, mechanical edits, cheap reversible actions, or work with no material downside if wrong.
metadata:
  short-description: Gate conclusions before acting on them
---

# Crucible

A gate, not a workflow. Crucible does not replace domain investigation. It governs which
check the enclosing agent or workflow executes, then resumes to update rivals and resolve
the gate.

## When this fires

A consequential commitment under decision-relevant uncertainty - including when only one
explanation has been stated.

Test for *consequential*: **would being wrong cause material cost, harm, or difficult
reversal, compared with the cost of the best plausible discriminating check?**

Do not fire for lookups, single-fact retrieval, mechanical edits, cheap reversible actions,
or work with no material downside if wrong.

"No plausible rival exists" is not a reason to skip. It is an exit available only *after*
obligation 1 has actually been attempted.

## Precedence with other skills

- Bug investigation -> `diagnosing-bugs` owns the workflow.
- General consequential conclusion -> Crucible.
- Inside debugging, at a costly commitment gate (a risky fix deploying, a system being
  declared safe) -> Crucible fires within that workflow.

Evidence and instrumentation another skill already produced **satisfy** these obligations.
Never re-run a check merely because a different skill produced it.

## Urgency

"Just tell me" and stated urgency bypass **ceremony, not epistemic safeguards**. Run a
compressed pass, or report the unresolved uncertainty. Never bypass evidence requirements
for high-stakes claims.

## The five obligations

1. **Construct a rival.** Produce a credible alternative or null hypothesis. If none can be
   constructed, say so on record.
2. **Name what would contradict each rival.** No discriminating observation means
   `testability: unfalsifiable`.
3. **Select the highest ordinal decision value per cost.** Judge on: does it distinguish the
   leading rivals; is it likely to change the next action; money, time, privacy, risk,
   reversibility; are its predicted outcomes grounded. This is ordinal judgement - do not
   claim to compute expected information gain.
4. **Predeclare, then update every rival.** Write what each outcome would mean *before*
   observing. Then record a status transition for every rival, including unchanged ones.
5. **Resolve into a declared terminal state.**

## Statuses

`leading` - `live` - `weakened` - `contradicted`

No probabilities. No decimals.

Testability is tracked separately, because unfalsifiability is not a degree of confidence:

`testability: falsifiable | unfalsifiable | unknown`

An **unfalsifiable** rival gains no support by surviving checks and never counts as
discriminated. Record it as an unresolved assumption. It prevents `justified` only when the
declared evidence standard requires resolving it.

## Basis tags

Attach to every prediction and every evidence-to-hypothesis link - never to a hypothesis as
a whole. Provenance goes inline:

- `[measured: artifact/command]` - direct observation
- `[documented: source]` - supported mapping or criterion
- `[inferred: premises]` - derived conclusion
- `[guess]` - unsupported assumption

A **predicted** transition is never `[measured]`: the observation has not happened yet.
Tagging an implication `measured` because the underlying observation was measured is
laundering, and it is the failure these tags exist to prevent.

### Hard constraints

1. Promotion to `leading` caused by a **new** check requires a predeclared outcome mapping.
   Evidence that existed before the gate opened may seed the initial ranking if its
   provenance is recorded. Never fabricate a retrospective predeclaration.
2. `contradicted` requires a grounded result matching a **predeclared** contradiction, with
   test validity and auxiliary assumptions stated. Valid evidence falling short may weaken.
3. **Invalid instrumentation weakens nothing.** A failed or invalid check yields no evidence
   about any hypothesis. Quarantine the result, mark the *check* failed rather than the
   hypothesis, and leave the predeclared discriminator unconsumed - it never ran. A
   hypothesis weakens only on residual signal that survives independent of the invalid part,
   with a basis tag reflecting the thinner grounding.

## Terminal state and authorization

Recorded separately. Knowing is not permission.

| `terminal_state` | Meaning |
|---|---|
| `justified` | The evidence standard is met. Nothing else produces this state. |
| `underdetermined` | Investigation stopped; the conclusion is NOT established. |
| `blocked` | Required evidence, access, or tooling is unavailable, or the evidence standard cannot be defined. |

| `action_disposition` | Meaning |
|---|---|
| `hold` | No action taken |
| `authorized` | Permitted to proceed |
| `declined` | Refused |

An authority sets `action_disposition`, never `terminal_state`. `underdetermined` +
`authorized` is a valid and honest state: proceeding under acknowledged uncertainty, on
record. **Missing approval is never `blocked`** - that is a permissions matter, not an
epistemic dead end.

| Kind | Examples | Role |
|---|---|---|
| Authority | the user, a designated approver | Sets `action_disposition` |
| Criterion | written spec, published standard | Defines what the evidence standard *is* |
| Evidence | a passing relevant test suite | Meets or fails that standard; never authorizes |

A test suite cannot declare a system safe or authorize a deployment.

## Stopping

Stop when any holds:

- remaining uncertainty cannot change the next action;
- one hypothesis survives all decision-relevant feasible discriminators required by the
  evidence standard - survival alone never produces `justified`;
- the best remaining check costs more than its decision value -> `underdetermined`;
- required evidence, access, or tooling is unavailable, or the evidence standard cannot be
  defined -> `blocked`.

`justified` requires the applicable evidence standard, at any stakes level. The absence of
affordable checks never produces it.

**High-stakes** means security or safety claims, irreversible actions, claims published
under the user's name, or plausible material harm to people other than the user.

## Case files

Stay inline by default. Escalate to `assets/case-template.md` only when the investigation
crosses turns, accumulates several checks, or needs audit or handoff. Otherwise the file is
paperwork.

Location:

- Prefer a user-specified location, or an existing project-notes location.
- Use `.crucible/cases/<slug>.md` only when the project is in scope **and its instructions
  permit local metadata** - scope and permission, not ownership.
- Never modify `.gitignore` automatically. Report whether the case is tracked and let the
  user choose.
- **Never copy secrets or sensitive raw evidence into a case.** Reference the secured
  artifact instead.
