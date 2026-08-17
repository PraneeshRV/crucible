# c12 — explicit — rep 3

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 3,
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
  "run_at": "2026-08-17T12:26:07+00:00",
  "seconds_per_turn": [
    68.1,
    57.9
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

No — or more precisely, not yet. The 89% figure is consistent with 4.2 being the culprit, but it's *also* consistent with 4.2 being completely innocent, and as written it can't distinguish those. One number you probably already have decides it.

## The problem with 89%

That's a numerator without a denominator. "89% of complaints came from 4.2 users" tells you about the composition of your complaint pile, not about 4.2's failure rate. The comparison it needs is **4.2's share of your checkout attempts**:

| If 4.2 is this share of mobile checkouts | Then 89% of complaints means |
|---|---|
| ~90% (typical for a build a week or two into rollout) | 4.2 is performing at or slightly *better* than baseline — signal is zero |
| ~60% | Meaningfully over-represented — real signal |
| ~25% | Damning |

New mobile builds routinely reach 85–95% of the active base within days via auto-update, so the null result is the *likely* one until you check. And there's a second gap: a spike in total failures and a lopsided complaint mix are two separate facts. Even if 4.2 is somewhat elevated, the spike itself could be driven mostly by something else.

## Rival explanations (all live)

1. **H1 — 4.2 defect.** A client-side regression in the checkout path. *Status: leading only by default, on unweighted evidence.*
2. **H2 — Base-rate artifact.** 4.2 is simply what almost everyone is running; complaint share ≈ population share. The spike has another cause entirely.
3. **H3 — Backend / third-party.** Payment processor, tokenization, 3DS, tax or pricing service, gateway config, an expired cert, a feature flag. Coincident with the rollout in time, unrelated in cause.
4. **H4 — Reporting artifact.** If 4.2 added or surfaced an in-app "report a problem" flow, 4.2 users file more tickets *per failure*. Same real failure rate, inflated complaint share. Also check whether ticket tagging auto-stamps the current build.
5. **H5 — Cohort confound.** Staged rollout hit a specific region, carrier, OS version, or payment method first, and *that* segment is what's broken.

## What to check before tonight (minutes, not hours)

**Check 1 — failure rate per checkout attempt, segmented by client version, same window.** Server-side, not tickets. This is the whole decision.
- 4.2 rate materially above 4.1's in the same week → H1 leading, H2 contradicted, rollback justified.
- 4.2 rate ≈ 4.1 rate → H1 weakened hard, H2/H3 leading, **rollback does nothing but cost you a night and a second support wave.**

**Check 2 — web/desktop checkout failure rate, same window.** Web isn't running 4.2. If web failures are up too → H3 leading, H1 largely contradicted.

**Check 3 — error-code distribution.** Client-shaped errors (validation, serialization, timeouts, malformed requests) point to H1. Gateway-shaped ones (issuer declines, 3DS challenges, tokenization failures) point to H3.

**Check 4 — did total failures start rising before 4.2 reached meaningful adoption?** Overlay the failure curve on the rollout curve. Failures leading the rollout → not the build.

Checks 1 and 2 are usually one dashboard query each. That's cheap next to a rollback.

## Why the asymmetry matters

Rolling back isn't a cheap, reversible probe. It costs an app store cycle, it can't actually downgrade users who already updated, it burns team hours overnight — and if the cause is H3, **failures continue after the rollback while everyone believes the fix shipped**, which is worse than doing nothing because it retires your leading hypothesis falsely. It also destroys the natural experiment: once 4.2 is gone, you can't compare rates by build anymore.

One clarification that shifts things: is 89% of *mobile* complaints, or 89% of *all* checkout complaints including web? If it's all channels and mobile is well under 89% of your checkout volume, that's a genuinely stronger signal and moves H1 up.

---

**terminal_state:** `underdetermined` — H1 is plausible but undiscriminated from H2/H3.
**action_disposition:** `hold` on rollback, pending Checks 1 and 2.

To be clear about where the authority sits: this is your call, and "roll back tonight anyway, as insurance, while we investigate" is a defensible decision if the revenue bleed outweighs the cost of a wasted rollback. I'd just want it on record as a hedge under acknowledged uncertainty rather than as a fix — because if the numbers come back flat, the real cause is still out there and support is still drowning tomorrow.

Want me to write out the specific queries for Checks 1 and 2 against your analytics setup?


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

That's a real gap. Let me update on record, because it moves things substantially.

**The arithmetic:** 89% of complaints from 60% of sessions means 4.2 generates roughly **5.4× the complaints per session** as everything else (1.48 vs 0.28 per session-unit). That is not a base-rate artifact. H2 is contradicted, exactly as predeclared.

But note what the check actually measured. I predeclared *failure rate per checkout attempt, server-side*. You ran *complaints per session, from tickets*. Both terms differ, and two rivals live entirely in that gap:

**H4 (reporting artifact) is completely untouched — and it can account for the whole 5.4× by itself.** Complaints = failures × propensity-to-complain. If 4.2 shipped or surfaced an in-app "report a problem" flow, a 5× lift in reporting propensity is unremarkable — that's the difference between tapping a button and hunting for a support email. Same failure rate, five times the tickets. This is the one that would make tonight wasted.

**Sessions isn't the right denominator — attempts is.** If 4.2 moved checkout somewhere more prominent, 4.2 sessions contain more checkout attempts each, and more attempts produce more failures at an identical per-attempt rate.

**H5 (cohort) also survives.** A staged rollout weighted toward one region, carrier, or payment method reproduces this signal precisely.

## The check that settles it

One query, server-side: **checkout failures ÷ checkout attempts, grouped by client version, this week.** That swaps complaints for failures and sessions for attempts simultaneously — it kills H4, H5, and the denominator problem in a single shot. If your funnel telemetry exists at all, this is ten minutes.

- Ratio holds near 5× → H1 `justified`. Roll back without reservation.
- Ratio collapses toward 1 → you were reading ticket-filing behavior, not checkout behavior. H4 leading.

## And one that changes *which lever you pull*

Pull the **error-code split** at the same time. Even granting 4.2 is implicated, that doesn't establish the app binary is the thing to revert:

- **Client-shaped errors** (validation, serialization, timeouts) → roll back the app.
- **Gateway-shaped errors** (issuer declines, 3DS, tokenization) → 4.2 is calling a new backend path or API version, and the broken thing is server-side. **A flag flip or backend revert fixes it in minutes and is reversible** — versus an app store cycle that still can't downgrade anyone who already updated.

That distinction is worth ten minutes on its own. Rolling back a binary when the fix was a config flag is the expensive version of being right.

---

**H1** — `leading` `[inferred: 5.4× complaint concentration, ticket-derived]`
**H2** — `contradicted` `[measured: 60% session share vs 89% complaint share]`
**H3'** — `live`, narrowed to client-specific backend interaction; uniform-backend variant weakened
**H4** — `live`, undiscriminated; sufficient alone to explain the observation
**H5** — `live`, undiscriminated

**terminal_state:** `underdetermined`, but materially closer — the remaining rivals share one cheap discriminator.

My call: run those two queries first. If the telemetry doesn't exist or you can't get it tonight, roll back anyway — the evidence of real harm is now strong enough to justify a hedge — but **keep H4 and H5 open** and watch failure rates after the rollback lands, because under either of those the failures don't stop and you'll want to know that Tuesday morning rather than Thursday.

Want me to draft the two queries? Tell me what you're using — Amplitude, Datadog, BigQuery, Snowflake — and I'll write them concretely.


## verdict

_ungraded — open the rubric only after the run completes_
