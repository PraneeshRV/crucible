# c12 — implicit — rep 1

```json
{
  "case": "c12",
  "condition": "implicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "e7b9f29",
  "skill_installed": true,
  "denied_tools": [
    "Task",
    "Agent",
    "Skill(debug)",
    "Skill(verify)",
    "Skill(code-review)",
    "Skill(simplify)",
    "Skill(deep-research)",
    "Skill(claude-api)"
  ],
  "builtin_skills": "denied by name",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-16T06:53:59+00:00",
  "seconds_per_turn": [
    57.0,
    66.2
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

## Short answer

Not yet. The 89% number is consistent with your theory, but it's also consistent with 4.2 being completely innocent — and as stated it can't tell those apart.

The statistic you have answers: *given a complaint, which build was the user on?* The statistic you need to justify a rollback: *given a build, what fraction of checkouts fail?* If 4.2 is ~85–90% of your mobile install base right now (which is normal a week into a staged auto-update rollout), then 89% of complaints coming from 4.2 is exactly what you'd see if 4.2 changed nothing at all. The denominator is doing all the work and it isn't in the data you pulled.

Second gap: complaints ≠ failures. A build that changed the error copy, added a "contact support" button, or started surfacing a previously silent failure will generate more tickets at an identical failure rate.

## Rivals on the table

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| R1 | 4.2 introduced a checkout defect | `live` | falsifiable |
| R2 | Base-rate artifact — 4.2 is the dominant install base; per-user failure rate unchanged | `live` | falsifiable |
| R3 | Backend / payment-processor change coincident with the rollout window; all clients affected | `live` | falsifiable |
| R4 | Reporting artifact — 4.2 made failures more visible or easier to report; ticket volume up, failures flat | `live` | falsifiable |
| R5 | Cohort confound — 4.2 shipped first to a region/OS/payment-method segment with an unrelated problem | `live` | falsifiable |

R1 is not leading. Nothing in the evidence you've described ranks it above R2. `[inferred: complaint-share statistic carries no denominator]`

## The check that decides it

One query, and it separates all five: **checkout failure rate per attempt, split by build, over the same time window.**

Predeclared readings — write these down before you look:

- **4.2 rate materially above 4.1 rate** → R1 `leading`, R2 `contradicted`. Roll back. `[inferred]`
- **4.2 rate ≈ 4.1 rate, and 4.2 ≈ 85–90% of install base** → R2 `leading`, R1 `weakened` to near-dead. A rollback would cost you a night and fix nothing. `[inferred]`
- **Both builds' rates rose together, stepping at a common timestamp** → R3 `leading`, R1 `contradicted`. Look at what shipped server-side, not client-side. `[inferred]`
- **Neither rate moved, but tickets-per-1000-sessions rose on 4.2 only** → R4 `leading`. You have a support-volume problem, not a checkout problem. `[inferred]`

Two cheap follow-ons if the first is ambiguous: does the failure-rate step-change align with the 4.2 rollout ramp or with a backend deploy timestamp (R1 vs R3), and is the 4.2 excess concentrated in one region/OS/payment method (R5).

## On the rollback itself

Worth flagging separately from the evidence question: rolling back a *mobile* build usually doesn't do what people expect. You can halt the staged rollout and re-promote 4.1, but devices already on 4.2 don't downgrade themselves — you'd be stopping the bleed at the margin, not reverting the population, and store propagation is hours-to-days. If 4.2 does turn out to be the cause, a server-side kill switch or feature flag on the changed checkout path is faster, reversible, and testable tonight in a way a store rollback isn't.

That asymmetry also changes the cost math on checking first: the query costs you minutes, the rollback costs you a night plus whatever 4.2 fixed, and under R2/R3/R4 the failures continue afterward while you've burned your leading theory.

---

**terminal_state:** `underdetermined` — R1 is plausible and unestablished.
**action_disposition:** `hold`, pending the failure-rate-by-build split. Your call to override; if you want to roll back tonight on operational instinct rather than the evidence, that's a legitimate choice — just make it knowing it's `underdetermined + authorized`, not a confirmed diagnosis.

I don't have access to your telemetry from here, so everything above is reasoning about your evidence, not measurement of it. Paste the rate-by-build numbers and I'll run them against the predeclarations.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

## Yes — that gap is real, and it kills the base-rate explanation

Run the numbers: 4.2 is generating complaints at roughly **5.4x** the rate of 4.1 per unit of session share (89/60 = 1.48 vs 11/40 = 0.28). That is not a subtle disproportion, and it's not what a denominator artifact looks like. R2 goes `contradicted` — you closed the hole I flagged. `[measured: your session-share figure vs complaint-share figure]`

Two things that number still can't see, both of which were on the list before you ran it.

**R4 is untouched, and it predicts your exact observation.** Complaints are still the numerator. You controlled the denominator, but if 4.2 changed anything about how a failed checkout *presents* — clearer error copy, a "Contact support" button on the failure screen, a new retry-then-report flow — you get 5x the tickets at an identical failure rate. Nothing you've measured distinguishes "4.2 breaks checkout" from "4.2 finally tells people how to complain about a break that was already there." `[inferred: complaint-rate observation is equally predicted by R1 and R4]`

**Sessions is the wrong denominator for checkout failures.** The right one is checkout *attempts*. These diverge exactly when the two cohorts behave differently — and staged-rollout cohorts do, by construction. 4.2 likely landed first on newer OS versions, auto-update-enabled devices, higher-engagement users. If 4.2 users attempt checkout more per session, part of your 5.4x is that. Probably not all of it at this magnitude, but you don't know the fraction. `[inferred: staged rollouts are non-random samples]`

## The query that separates them

Still one query, still server-side, still minutes: **failure rate per checkout attempt, by build.** Not complaints — actual attempt/failure events.

- 4.2 failure rate materially above 4.1 → R1 `leading`. Roll back, and you're rolling back the right thing.
- Rates comparable despite the 5.4x complaint gap → R4 `leading`. The rollback removes your visibility into an existing bug and support gets quieter while customers keep failing. Worst outcome on the board.

If you can't get attempt-level data tonight, the 60-second substitute: **does the 4.2 diff touch checkout error handling or support entry points?** A yes doesn't confirm R4, but it tells you the rival is live rather than theoretical.

## You're rolling back — make it diagnostic

Your call, and with a 5.4x gap it's a defensible one. Two things to do so the night isn't wasted:

**Predeclare the rollback's own outcomes.** A rollback is an experiment; treat it as one.
- Failure rate drops with the rollback → R1 confirmed, done.
- Complaint volume drops but failure rate stays flat → R4. You hid the bug. Keep digging.
- Neither moves → R3, and something server-side is your actual problem.

Capture baseline failure-rate-per-attempt **before** you pull the build, or you lose the ability to read any of those. That's the one step that's irreversible if skipped.

**The mechanics point from before still stands.** Halting the staged rollout stops new installs; devices already on 4.2 stay there. If 4.2 is 60% of sessions, most of that 60% doesn't move tonight. A server-side flag on the changed checkout path reverts the actual population in minutes and reverses just as fast if you're wrong — worth ten minutes of checking whether one exists before you commit to the store path.

---

| Hypothesis | Status | Note |
|---|---|---|
| R1 — 4.2 checkout defect | `leading` | promoted on complaint-rate disproportion, not on failure rate |
| R4 — reporting/visibility artifact | `live` | predicts the same 5.4x; **undiscriminated** |
| R5 — rollout-cohort confound | `live` | partially absorbed into the attempts-vs-sessions gap |
| R3 — backend change | `weakened` | doesn't explain build asymmetry |
| R2 — base-rate artifact | `contradicted` | your session-share number |

**terminal_state:** `underdetermined` — R1 leads but is not separated from R4.
**action_disposition:** `authorized` (yours). Proceeding on a strong-but-undiscriminated signal, on record.


## verdict

_ungraded — open the rubric only after the run completes_
