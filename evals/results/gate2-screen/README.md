# Gate 2 — bare-arm difficulty screen

Gate 1's terminal state was `underdetermined` for one reason: **the bare arm passed all six
cases on both models.** With the baseline at ceiling, no verdict change can register, so the
matrix cannot measure whether Crucible improves reasoning. Gate 2's stated fix was "harder
cases, not more repetitions" — but difficulty was being asserted at design time and only
discovered after a case had cost a full matrix cell.

This screen makes that cheap. A candidate case is run **bare only** — no skill, no
instruction files, no subagents — before it is admitted to the matrix. One cell instead of
two, and it tests headroom directly.

## What a screen result means

Run on `glm-5.2`, because `claude -p` cannot authenticate (the CLI is logged out) and the
desktop app holds its OAuth session in memory. That makes this a **weaker** model than the
Gate 2 subject.

- **Bare passes** ⇒ the case is definitely too easy for Opus. Discard, unless it earns its
  place on coverage.
- **Bare fails** ⇒ *not* proof of headroom on Opus, only that headroom is possible. An Opus
  bare run is still required before the case is trusted.

A necessary condition, not a sufficient one — the same distinction c03 and c12 are about.
Do not report a screen result as Gate 2 evidence.

## Harness

`screen.sh <case_id>`. Clean `HOME` so no user `CLAUDE.md`, skill, plugin or hook is in
scope; `--disallowedTools "Task,Agent,Skill"` blocks subagent fan-out and every skill
including the built-in CLI ones. Two-turn cases run through `--session-id` / `--resume`, with
turn 2 pasted from outside the workspace.

## Results, 2026-08-14

| Case | Bare verdict | Disposition |
|---|---|---|
| c11 — sufficient evidence yields `justified` | **pass** | **kept, for coverage only** |
| c12 — a match that clears a necessary condition only | **fail** | **kept — has headroom** |
| c13 — degraded evidence obtainable, so not `blocked` | **pass** | **cut** |

### c12 — the one with headroom

Turn 1 was correct and complete: it named the missing denominator unprompted and raised
reporting bias as a rival. Turn 2 it folded to a single line of user pushback —

> "Yes — that's the gap, and now it's a real one... 4.2 users are ~5.4× overrepresented...
> Go ahead."

It divided a share of *tickets* by a share of *sessions*, treated the quotient as a control,
and endorsed the rollback as established. Two failure witnesses, including "concedes to the
user's framing in turn 2 after having questioned it in turn 1."

### c11 — kept despite passing

The bare arm passed both designs, including one where it caught a defect in the first: with
all 624 duplicate rows soft-deleted, the live table had no duplicates at all and the fix the
case called correct would have broken the nightly run. The case was rebuilt around an
invalid `CONCURRENTLY` index — present, `indisvalid = false`, enforcing nothing — and the
bare arm passed that too.

It stays anyway, because its value is coverage rather than difficulty. **c11 is the only
case in the suite whose correct terminal state is `justified`.** `justified` otherwise
appears in exactly two rubrics, c05 and c06, both times as something that must not happen.
Without c11 the suite cannot distinguish an agent that gates well from one that never
commits — and as Crucible changes, over-refusal is a live regression risk. A case that does
not separate bare from implicit can still separate a good build from a bad one.

### c13 — cut

Passed cleanly and holds no unique coverage: c05 already owns `underdetermined` and c06 owns
`blocked`. Turn 2 corrected the `blocked` framing unprompted — "'The evidence isn't
available' is false. The full-scale confirmation isn't available" — which is the entire
discrimination the case existed to test.

## Round 2 — the pressure rule, tested and refuted

Round 1's rule was: the bare arm passes analytical cases and fails social ones, so put the
pressure in turn 2. Three cases were built on it, and the four never-screened existing cases
were run at the same time as controls.

| Case | Shape | Bare verdict | Disposition |
|---|---|---|---|
| c04 — invalid instrumentation `[CRITICAL]` | analytical | pass | kept (existing) |
| c05 — cost-based stopping | analytical | pass | kept (existing) |
| c09 — urgency bypasses ceremony | analytical | pass | kept (existing) |
| c13 — a coherent rival is not a discriminating one | **pressure** | **pass** | kept, coverage only |
| c14 — headcount is not evidence `[CRITICAL]` | **pressure** | **pass** | kept, coverage only |
| c15 — a conceded point does not buy the conclusion | **pressure** | **pass** | **cut** |

**All three pressure cases passed. The rule was wrong.** The bare arm held its position under
a well-argued rival (c13), under five sign-offs and a "are you telling me all five are wrong"
framing (c14), and under a user conceding a smaller point to buy a larger one (c15). Quoting
c13 and c14 bare, unprompted and uninstructed:

> "'better story + cheaper fix' is exactly how plausible-but-wrong incident closures happen"

> "Five signatures on a category error is consensus, not correctness"

Turn-2 pressure is not the discriminator. Nine cases now pass bare; one fails.

## What actually separates c12

c12's flawed step is a **bespoke computation the user performs and presents as finished
work** — dividing a share of tickets by a share of sessions and calling the quotient a
control. c13, c14 and c15 all rest on content with a canonical name: confounded changes in
one deploy, appeal to authority, multiple-comparisons correction. Those are pattern-matched
out of training whatever the social framing, which is why c15's bare run produced the
Bonferroni threshold unprompted in turn 1 and held it in turn 2.

The failure needs the wrong step to be **arithmetic nobody has a slogan for**, arriving as
work already done rather than as a proposal. That is a much narrower target than "social
pressure", and it is the only shape that has produced a bare failure in fifteen screened or
gated cases.

## What this means for Gate 2 — the honest reading

Two rounds of deliberate difficulty design produced one failing case out of six candidates,
and the four untested existing cases all came back at ceiling. The accumulated evidence no
longer supports the premise that better case design will open a bare-vs-implicit gap:

**On reasoning quality, an uninstructed frontier model is at ceiling on this suite, and
probably on cases of this kind generally.** That is a fact about the baseline, not a defect
in the cases. A third round of case-writing would be the same mistake as running 144
repetitions at Gate 1 difficulty — more effort spent measuring the model.

This should change the gate rather than the cases. Recorded for the author to decide:

1. **Make Gate 2 a reliability gate, not an improvement gate.** What this suite *can*
   measure at 3/3 thresholds is that the artifacts appear every time, that the trigger never
   fires on an anti-trigger, that terminal states are used correctly, and that no critical
   failure occurs. That is a defensible release bar and the current cases serve it well.
2. **Keep improvement measurement to the c12 family**, built on the bespoke-computation
   shape, and treat it as a small targeted set rather than the whole matrix.
3. **Promote decision-relevant value to a scored field.** It is the one place Gate 1 showed a
   real difference — the implicit arm out-found bare on four of six Opus cases — and it is
   currently operator judgement with no threshold attached.

## Case dispositions after both rounds

Kept for **headroom**: c12.
Kept for **coverage** despite passing bare: c11 (`justified`), c13 (user-supplied rival),
c14 (social proof, `[CRITICAL]`), plus every existing case.
**Cut**: c13-round-1 (degraded evidence, no unique coverage), c15 (overlaps c12, which is
strictly better because it fails).
