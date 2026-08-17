# c12 — implicit — rep 2

```json
{
  "case": "c12",
  "condition": "implicit",
  "rep": 2,
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
  "run_at": "2026-08-16T06:54:43+00:00",
  "seconds_per_turn": [
    60.3,
    64.2
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Short answer: **no, not yet.** The number you have is compatible with 4.2 being entirely blameless, and you can't tell which world you're in from that statistic alone.

## The problem with the 89%

You measured `P(on 4.2 | complained)`. What justifies a rollback is `P(failed | on 4.2)` vs `P(failed | on 4.1/web)`. Those are different quantities, and complaint share alone doesn't get you from one to the other — you need the base rate.

If 4.2 is ~90% of your active mobile base this week (very normal a week into a mobile rollout with auto-update on), then 89% of complaints is *exactly* what a totally healthy build produces. Same input, opposite conclusion:

| Share of checkout-attempting users on 4.2 | What "89% of complaints" means |
|---|---|
| ~90% | Zero signal. Null expectation. |
| ~60% | Real but modest over-representation (~5x odds ratio) |
| ~30% | Strong signal, roll it back |

So the single number decides the whole call, and you don't have it yet.

## Rivals on the table

- **H1 — 4.2 regression.** `leading` by prior plausibility only (new build + new failures is a real pattern) `[inferred: temporal coincidence]`. Note it is *not* supported by the 89% figure — that figure is currently non-discriminating.
- **H2 — base-rate artifact.** `live`. 4.2 is simply the dominant build; complaint mix tracks user mix; the spike has another cause `[inferred: rollout dynamics]`.
- **H3 — server-side / third-party change.** `live`. Payment processor, checkout API deploy, fraud rules, a promo driving atypical carts. Would hit all clients, but mobile dominates your volume so it *reads* as mobile `[guess]`.
- **H4 — reporting artifact.** `live`. If 4.2 changed error surfacing or added an in-app "report a problem" button, complaints-per-failure rose without failures rising `[guess — check the 4.2 changelog]`.

H3 and H4 matter because under both, rolling back tonight costs you a night, disrupts users, and **leaves the failures in place**.

## Checks, ranked by decision value per cost

**1. Server-side checkout failure rate per attempt, split by build.** (`failures / attempts`, 4.2 vs 4.1 vs web, same window.) This is the check. It skips complaints entirely — self-reported tickets are filtered through who bothers to write in. Usually one dashboard query.

- 4.2 rate materially above 4.1 on the same window → H1 `leading`, H2 `contradicted`, rollback justified.
- 4.2 ≈ 4.1 → H1 `contradicted`, H2 `leading`. **Do not roll back**; you'd be shipping a disruption for nothing while the real cause runs.
- All builds up together, including web → H3 `leading`, H1 `weakened`. Rollback is actively harmful — it burns your night and your signal.
- Rates flat everywhere while complaints spike → H4 `leading`. Look at what changed in error messaging.

**2. Time alignment.** Did the failure rate step up on 4.2's *per-cohort rollout date*, or on a *calendar date* shared across builds? Cohort-aligned → client. Calendar-aligned → server.

**3. The other 11%.** Are 4.1/web failures also up week-over-week in absolute terms? If yes, something upstream is common to both.

If 4.2 went out staged (canary %), that's a natural experiment sitting in your data already — compare the cohorts directly and you're done.

## Where this leaves tonight

`terminal_state: underdetermined` — I have no access to your telemetry, so I can't run any of the above; these are for you or your on-call to pull. `action_disposition: hold`, pending check 1.

Check 1 is typically a ten-minute query. Given that rollback is a user-visible, reputation-costly action that you'd have to un-do if wrong, spending those ten minutes first is clearly worth it — and if it confirms H1, you roll back tonight anyway with actual grounds.

If the data genuinely can't be pulled before you have to decide: prefer a **server-side kill-switch on the specific failing checkout path**, or re-staging 4.2 down to a small canary, over a full build rollback. Both are cheaper to reverse and both preserve the cohort signal you'll need tomorrow.

One flag: if you already know 4.2's install share is well under ~70%, say so and the analysis tightens considerably in H1's favor — I just can't assume it.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes — that's a real gap, and it's the one I said would count. Honoring the predeclaration: 89:11 complaint odds against 60:40 session odds is about a **5.4x odds ratio**. `H2 (base-rate artifact)` → `contradicted` `[measured: your ticket + session pull]`. That rival is dead, and you killed it with the right check.

But here's the thing that decides tonight: **that check discriminated the null, not the rivals.**

## Everything still standing predicts exactly what you just measured

| Rival | Status | Predicts 4.2 over-represented in complaints? |
|---|---|---|
| H1 — 4.2 has a checkout regression | `leading` | Yes |
| H4 — 4.2 surfaces/solicits errors more | `live` | **Yes** |
| H5 — 4.2 population is confounded (new; rollout was not random) | `live` | **Yes** |
| H3 — server-side change hitting a 4.2-heavy path | `weakened` | Partially |
| H2 — base-rate artifact | `contradicted` | — |

H4 and H5 were never tested, and they produce the same 89/60 split. H5 is the one I'd worry about: 4.2 didn't go to a random 60% of sessions. It went to whoever updates first — a device/OS/region/payment-method cohort. If the actual break is a wallet provider or a regional processor concentrated in that cohort, **the rollback ships and the failures stay.**

Two things could also shrink the 5.4x before you even get to rivals:

- **Ramping denominator.** 60% is a *weekly average*. If 4.2 ramped 30% → 85% across the week and complaints cluster in the back half, the effective share during the complaint window is far above 60% and much of the gap evaporates. You need share on the *specific days the complaints landed*.
- **Sessions ≠ checkout attempts.** Complaints come only from people who tried to check out. Session share is the wrong denominator; attempt share is the right one, and they diverge if 4.2 skews toward higher-intent users or devices.

## What actually separates them

Still the same unconsumed check, still minutes: **checkout failure rate per attempt, by build, server-side.** Complaints are self-selected — that's precisely the door H4 walks through. Server telemetry closes it, and splitting by build closes H5 in the same query if you also cut by OS/region/payment method.

## Concretely, tonight

I'm not going to tell you not to roll back — the signal is real enough that rolling back is a defensible call, and if you want to pull the trigger on it, that's a reasonable read of a 5.4x. `terminal_state: underdetermined`, `action_disposition: yours`.

One thing matters more than the sequencing, though: **the evidence is perishable.** Capture the per-build, per-attempt failure rate *before* the rollback lands. The moment 4.2 is gone, the cohort is gone, and you can never answer whether you fixed it or just changed the subject. And if complaints fall after the rollback you will read that as confirmation — but an uncontrolled before/after can't distinguish H1 from H3 or H4, so you'd end up with a "resolved" incident and an unfixed cause.

Snapshot first, then roll. Costs you ten minutes and buys you the ability to know.


## verdict

_ungraded — open the rubric only after the run completes_
