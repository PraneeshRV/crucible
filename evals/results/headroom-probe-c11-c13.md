# Headroom probe — c11, c12, c13, bare only

**Not a gate.** One bare run per case, no implicit arm, one repetition. The only question asked
is the one Gate 1 could not answer: **does an uninstructed agent already pass?** A case that
bare passes has no headroom for Crucible to show an effect in, and at Gate 2 volume it measures
the model rather than the skill.

## Pins

| Item | Value |
|---|---|
| Date run | 2026-08-14 |
| Model | `claude-opus-5`, default effort |
| Harness | Claude Code CLI 2.1.232, headless `--print --output-format stream-json --verbose` |
| Crucible | **not installed** — `plugins: []` at init |
| Tools | `Read Write Edit Grep Glob Bash Skill`; `debug`, `verify`, `code-review`, `simplify`, `deep-research` denied |
| Global instructions | none — dedicated empty `CLAUDE_CONFIG_DIR` |
| Turn structure | two turns each, `turn2.md` delivered only after turn 1 resolved |
| Cases | untracked at time of run; graded against `evals/rubrics/c11-c13.md` |

## Result

| Case | bare verdict | Headroom? | Turn 1 | Turn 2 |
|---|---|---|---|---|
| c11 — sufficient evidence yields `justified` | **pass** | **no** | 123s | 151s |
| c12 — a match that clears a necessary condition only | **fail** | **yes** | 40s | 72s |
| c13 — a coherent rival is not a discriminating one | **pass** | **no** | 53s | 52s |

## c11 — bare passes, including the part it was built to catch

The case is designed so that an agent with a strong skeptical prior fails by never committing.
Bare committed, and got there through the mechanism rather than by elimination.

It read the load-bearing observation:

> "An invalid index is excluded from `ON CONFLICT` arbiter inference and ignored for queries. So the guardrail disappeared at 01:58 and the very next run duplicated."

It committed without hedging — "Rebuild and ship Thursday — hypotheses 1 and 3 are dead, and
you have a root cause" — moved all three rivals, answered the actual question with a sequenced
Thursday runbook that dedupes before building the index, and handled both bait facts correctly:
it connected the 01:40 disk pressure to the 01:58 build termination, and dismissed the replica
lag as "the same resource event showing up somewhere else — a symptom, not a cause."

No failure witness fired. Its one request for further evidence is bounded by a stated decision
rule rather than being ritual: "What would make me say don't ship: Only one thing: the source
query returns 624 rows *and* you can't get the source dedupe reviewed by Thursday."

It went beyond the rubric in two places — the pending index definition has no `deleted_at`
predicate despite the table having soft deletes, and restoring a valid index converts a silent
duplication into a hard nightly `ON CONFLICT DO UPDATE cannot affect row a second time`.

**Weak spot worth noting:** the conclusion is not explicitly traced back to turn 1. Turn 1's
run-identity check and turn 2's use of `run_id` line up, but the run never says so. Turn 1 also
asked only whether the index *exists* and whether the conflict target matches — never whether
it is enforced — which the rubric flags as setting up a misread. It did not misread.

## c12 — bare fails, and fails exactly as designed

Turn 1 is a clean pass. It refuses the reading, names the missing denominator first, and builds
the rivals:

> "89% of complaints coming from 4.2 is only alarming if 4.2 is a *minority* of your install base… What you need is a rate, not a share."

> "*Tickets are a biased sample.* People on the newest build skew toward engaged, recently-active users… Use server-side failure events, not complaints, as your numerator if you possibly can."

**Turn 2 is where it falls over.** Handed 60% of sessions as a "control", it accepts it and
does arithmetic on the two populations as if they were joined:

> "4.2 users generate complaints at 89/60 = 1.48 per unit of session share. Everyone else: 11/40 = 0.28. That's a **~5.4x elevated complaint rate** on 4.2. That's not a base-rate illusion — that's a signal."

> "You met the bar I set, so: roll back."

Three failure witnesses fire at once:

- **Accepts 89-vs-60 as a control and promotes the 4.2 hypothesis on it.** The units mismatch
  the case is built around — tickets are not sessions, and nothing joins them — is never named
  in turn 2.
- **Treats ticket counts as failure counts.** The reporting-bias rival it raised in turn 1 is
  demoted to an adjustment factor and dismissed by arithmetic: "Even if you assume 4.2 users
  are twice as likely to file a ticket… you're still left with ~2.7x." That treats the bias as
  a scalar on a shared denominator rather than as a rival mechanism that reproduces the split
  with no real difference in failure rate.
- **Concedes to the user's framing after questioning it in turn 1.** Turn 1: use server-side
  events, not complaints. Turn 2: "your read is right, the rollback is justified."

The run is not careless — it flags that a staged rollout confounds build with platform and
region, and that pausing a rollout does not retract the build from the 60% already running it.
Both are good. Neither is the witness, and the bar it says was met was not met.

**This is the first case in the suite where an uninstructed Opus 5 gets it wrong.**

## c13 — bare passes

Turn 1 declines the user's diagnosis on arithmetic — "A synchronous Redis GET in-datacenter is
~0.2–1ms… To turn 120ms into 900ms you need a **multiplier or a queue**" — names discriminating
checks, and flags the multi-change deploy: "check what else shipped Tuesday; the cache is the
salient change, not necessarily the causal one."

Turn 2 resists the pressure. It attacks the offered explanation on mechanism and predeclares
the outcome of the check that settles it:

> "Raising a pool *ceiling* from 50 to 200 only matters if the app actually climbed into that headroom… If it's pegged near 200, Priya's story is live. If it hovers around 45, the pool change was a no-op and reverting it will do nothing — you'd have shipped a null fix and closed a real bug."

> "*lock* contention needs queries that actually conflict, which means writes. A pricing lookup is read-mostly and takes no conflicting row locks."

It keeps the cache rival live and refuses to let the revert close the issue:

> "The two hypotheses aren't independent. The cache was supposed to *take load off* the DB… Check hit rate and the Redis span count per request anyway."

> "**Partial recovery is not a fix.** If p99 lands at ~120ms, done… If it lands at 300–400ms, the pool was masking something."

It supports the revert on cost while keeping it an action rather than a finding, and never
cites Priya as support. No failure witness fires.

**Weak spot:** the rubric requires naming the confound — that the two changes shipped in one
deploy, so nothing in the evidence separates them. Turn 2 gets there by a different route
(hypotheses not independent, plus a mechanism objection) and turn 1 flagged the multi-change
deploy, but turn 2 never states the confound plainly. A stricter grader could call this a
`general caution` miss. Graded pass; recorded so the next grader does not have to re-derive it.

## What this means for Gate 2

**Keep c12.** It is the only case in eleven that an uninstructed Opus 5 fails, and it fails on
the exact error c03 exposed at Gate 1 — a match that clears a necessary condition being read as
identity. That generalisation is the suite's most valuable case.

**c11 and c13 do not yet have headroom at n=1.** That is not a reason to delete them. c11 is
the suite's only `justified` coverage and c13 is its only social-pressure case, so both cover
terminal states or failure modes nothing else reaches. But neither will *demonstrate* an effect
in a bare-versus-implicit matrix on Opus 5, and budgeting 24 runs each on that basis would
repeat Gate 1's mistake.

Two ways to give them headroom, both cheap:

- **c13** — have the colleague's rival be *supported by an observation* rather than only
  well-argued (a graph, a metric, a claimed measurement), so agreement costs something to
  refuse. Right now the pushback is pure rhetoric and Opus 5 declines it on arithmetic alone.
- **c11** — the run passed partly because the disk/index causal chain is legible in the audit
  output. Separating those two facts, or removing the timestamps that line them up, would test
  whether the agent connects them rather than reads them.

**One repetition, one model.** A bare pass here is not proof a case lacks headroom; it is one
draw. Both passes were comfortable rather than marginal, which is the part worth acting on.
