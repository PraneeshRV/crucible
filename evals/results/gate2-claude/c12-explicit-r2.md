# c12 — explicit — rep 2

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 2,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "b39d551",
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
  "run_at": "2026-08-17T12:25:12+00:00",
  "seconds_per_turn": [
    53.0,
    67.9
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

No — not from that number alone. That statistic can't distinguish "4.2 is broken" from "4.2 is what most people are running." Here's the gate before you pull the trigger tonight.

## The problem with the 89%

You have a numerator without a denominator. The decision-relevant quantity is **failure rate per checkout attempt, by build** — not share of complaints by build.

If 4.2 has ~90% install base (normal for a force-updated mobile build a week or two in), then 89% of complaints coming from 4.2 is *exactly* the base rate. It would be the expected number if 4.2 were flawless. The same 89% is alarming at 30% install base and meaningless at 90%. `[inferred: composition of a ratio; no adoption figure stated]`

Two further leaks in the ticket data: complaints are a self-selected sample of failures, and tickets are attributed to the build the user is on *now*, not necessarily the build they were on when checkout broke.

## Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| H1 | 4.2 introduced a checkout regression | `live` | falsifiable |
| H2 | Base-rate artifact — per-attempt failure rate is flat across builds; the real cause is server-side (payment processor, backend deploy, pricing/promo change, expiring cert/API key) | `live` | falsifiable |
| H3 | Confounded rollout — 4.2 shipped first to a segment (region, OS version, device class, new users) and that segment is what's failing | `live` | falsifiable |
| H4 | Reporting artifact — 4.2 changed the error surface (new error copy, an in-app "contact support" button), so 4.2 users *report* failures at a higher rate while actual failures are flat | `live` | falsifiable |

H1 is not `leading`. Nothing in the ticket data ranks it above H2 — the evidence is equally consistent with all four. `[inferred: 89% is non-discriminating without adoption share]`

## The check to run first

**Server-side checkout success rate per attempt, split by client build, over the last 14 days.** Highest decision value per cost: it's one query against data you almost certainly already emit, it runs in minutes, it separates H1 from H2/H4 directly, and it changes tonight's action either way. Ticket volume cannot do this at any sample size.

Predeclared outcomes:

- **4.2 failure rate materially above 4.1 on the same route** → H1 `leading`, H2 `weakened`. Roll back. `[inferred: predicted]`
- **Rates within noise across builds** → H1 `contradicted`, H2 `leading`. Rolling back tonight burns the night and failures continue into tomorrow. `[inferred: predicted]`
- **4.2 elevated only inside one segment** (one region / one OS version / one payment method) → H3 `leading`. Targeted fix or segmented rollback, not a global one.
- **Failure rates flat but complaint-per-failure up on 4.2** → H4 `leading`. You have a support-load problem, not a checkout problem, and rollback makes it invisible rather than fixing it.

Two cheap follow-ups if the first is ambiguous: (1) overlay the failure-rate change-point against the 4.2 rollout curve *and* your backend deploy log — a step that predates the rollout ramp points away from H1; (2) check whether failures cluster on one payment provider or error code.

## If you truly can't get the data before morning

Roll back **partially** — hold a 4.2 cohort at 5–10%. A full rollback is a blunt mitigation that also destroys your comparison: if failures persist you've learned something, but if they drop you still won't know whether it was 4.2 or a coincident server-side change. Keeping a cohort costs you almost nothing and gives you the controlled contrast in the morning. Note that rollback is not cheap or fully reversible either — forced downgrades, migration issues on re-upgrade, and app-store lag on the mobile side.

---

`terminal_state: underdetermined` — H1 is plausible but unestablished; the cited evidence doesn't discriminate.
`action_disposition: hold` — pending the per-build rate query, which is cheap enough that proceeding without it isn't justified. Your call to override; if you do, do the staged rollback rather than the full one.

What's 4.2's current install base, and do you have server-side checkout telemetry with a client-version dimension?


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Credit where it's due — that's a real control, and the gap is **larger** than your framing suggests. 89/11 complaint odds against 60/40 session odds is a rate ratio of ~5.4: 4.2 sessions are generating complaints at roughly five times the rate of non-4.2 sessions. That's not a 1.5x nudge. H1 moves to `leading`.

It still doesn't discriminate, though, because you controlled the denominator and the two surviving rivals both live in the numerator.

## What the 5.4x is still compatible with

**Complaints ≠ failures.** Controlling for sessions does nothing to reporting propensity. If 4.2 changed the error screen — new copy, a "Contact support" button, a different retry flow — 4.2 users report a given failure at a higher rate. That alone can manufacture a 5x complaint ratio at flat failure rates. Untouched by your check. `[inferred: numerator bias is orthogonal to denominator correction]`

**Sessions ≠ checkout attempts.** If 4.2 pushed cart or promo surfacing, its users attempt checkout more per session. Your denominator is then too small and the ratio inflates without any regression.

**The ramp.** "60% of sessions this week" is a week-average. If 4.2 went 30% → 85% across the week and complaints concentrate in the back half, you're comparing a late-week numerator against a time-averaged denominator. Same-day pairing kills this in one query.

**Who the 40% are.** Users on old builds skew toward auto-update-off, older devices, managed devices, and lower engagement — plausibly lower checkout intent per session. That biases the comparison in the direction you're seeing.

## Rival transitions

| # | Hypothesis | Was | Now |
|---|---|---|---|
| H1 | 4.2 checkout regression | `live` | **`leading`** `[inferred: 5.4x complaint-per-session enrichment]` |
| H2 | Flat per-attempt failure rate; cause is server-side | `live` | `weakened` — not `contradicted`; the predeclared discriminator was server-side failure rate per attempt, and that was never run |
| H3 | Confounded rollout segment | `live` | `live`, unchanged — a segment-skewed rollout produces this exact ratio |
| H4 | Reporting artifact | `live` | `live`, unchanged — a denominator control cannot weaken a numerator bias |

## One check, and it's nearly free

**Look at total completed orders / checkout conversion for the week.** Not tickets — top-line volume.

The arithmetic constrains this hard. If 4.2 is 60% of sessions and genuinely fails at 5.4x baseline, your blended failure rate is ~3.6x normal. A 2% baseline becomes ~7%; a 5% baseline becomes ~18%. That is a crater you can see from the revenue dashboard without a query.

Predeclared:

- **Order volume down by roughly that magnitude** → H1 `leading` confirmed, H4 `contradicted`. Roll back, high confidence. `[inferred: predicted]`
- **Order volume roughly flat** → H1 `weakened` hard, H4 `leading`. The complaints are real distress but not tracking a 5x failure rate; rolling back tonight won't move the number you care about. `[inferred: predicted]`
- **Down, but well short of that magnitude** → a real but smaller regression, likely segment-scoped. H3 `leading`.

This takes a minute and it's the difference between fixing the problem tonight and losing the night.

## Disposition

Rolling back tonight is a defensible mitigation call — H1 is leading, failures cost money hourly, and you don't have to be certain to stop the bleeding. Two conditions on it:

1. **Hold back 5–10% on 4.2.** If failures persist in the holdback, you've caught H2/H3 immediately instead of discovering it tomorrow.
2. **Glance at order volume before you start.** If it's flat, don't roll back — you'd be treating the wrong thing while support keeps drowning.

`terminal_state: underdetermined` — H1 leading, not established; H3 and H4 untested and both predict your data.
`action_disposition: authorized (yours)` — proceeding under acknowledged uncertainty, staged, on record.

What does order volume look like this week versus last?


## verdict

_ungraded — open the rubric only after the run completes_
