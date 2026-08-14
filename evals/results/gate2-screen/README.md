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

## The design rule this produced

The two cases the bare arm passed are both **analytical**: the answer is derivable by reading
the supplied evidence carefully. The one it failed is **social** — it requires holding a
correct position against the user's confident pushback.

That is where the headroom is. Gate 1 hints at the same thing: the c03 conflict was a turn-2
pressure moment, and c06's authority pressure was handled precisely because authority is
*explicit* and easy to name. Peer-level pressure — "I already controlled for that" — is what
actually breaks an uninstructed model, because conceding looks like updating on evidence.

**Remaining Gate 2 cases should put the pressure in turn 2 and make conceding feel like
good epistemic behaviour.** Analytical difficulty alone will keep producing ceiling passes.
