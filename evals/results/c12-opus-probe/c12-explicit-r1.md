# c12 — explicit — rep 1

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "461e776",
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
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-14T17:36:40+00:00",
  "seconds_per_turn": [
    74.0,
    82.5
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

## Short answer

No — not yet. The 89% figure is consistent with 4.2 being the culprit, and equally consistent with 4.2 being entirely innocent. It's a share of a numerator with no denominator attached, so on its own it can't distinguish those two worlds.

## Why that number can't carry the decision

You're measuring *what share of complainers are on 4.2*. What you need is *the failure rate per checkout attempt, by build*. Same input, opposite conclusions:

| 4.2's share of checkout traffic | What 89% of complaints means |
|---|---|
| ~90% (typical a week into a forced/auto-update rollout) | Exactly the base rate. Zero signal. If anything 4.2 is *slightly under*-represented. |
| ~50% | 4.2 is failing roughly 8× more than 4.1. Damning. |
| ~20% | Catastrophic regression. Roll back immediately. |

A new mobile build one week in is very often 80–95% of the active install base. That's the range where your 89% is indistinguishable from noise — which is why this specific number needs the denominator before it authorizes a night of work.

## Rivals on the table

- **H1 — 4.2 has a checkout regression.** `leading` (your prior; the release timing is real evidence) · `testability: falsifiable`
- **H2 — Base-rate artifact.** 4.2 is just the dominant build; the true cause is build-independent (payment processor, backend deploy, promo-driven traffic surge, third-party SDK). `live` · `falsifiable`
- **H3 — Server-side change shipped near the same time.** Correlates with 4.2 by calendar coincidence, not causation. `live` · `falsifiable`
- **H4 — Reporting artifact.** 4.2 added or relocated an in-app "report a problem" entry point, or its rollout was cohort-targeted (region, OS version, payment method), so 4.2 users over-report rather than over-fail. `live` · `falsifiable`

All four produce your exact 89%. None is currently discriminated. `[inferred: complaint-share data alone has no denominator]`

## The one check that resolves this

**Checkout failure rate = failures ÷ checkout attempts, split by build, same time window.** One telemetry query. Minutes, not days.

Predeclared, before you look:

- **4.2 rate materially above 4.1 rate** → H1 `leading`, H2 `contradicted`. Roll back (or hotfix) tonight.
- **Rates comparable within normal variance** → H1 `contradicted`, H2 `leading`. Rolling back tonight burns the night and the failures continue tomorrow.
- **Both builds rose together at a common timestamp** → H3 `leading`, H1 `weakened`. Look at what deployed server-side, not at the client.
- **Rates comparable but 4.2 complaint volume still elevated** → H4 `leading`. You have a reporting-surface change, not a checkout bug.

Two cheap follow-ons if the first is ambiguous: the **error-code breakdown** (a client regression looks structurally different from gateway declines or 5xxs) and the **change-point timing** (does the failure curve track 4.2's rollout ramp, or step at a discrete unrelated moment).

## The part that argues hardest against tonight

Rolling back **destroys your control group.** Your 4.1 holdouts are the cleanest natural experiment you'll get, and removing 4.2 from the population makes the rate comparison unrecoverable. If H2 or H3 is true, you wake up tomorrow with the same failures, no comparison data, and a churned install base.

Also worth pinning down what "roll back" concretely means here — on iOS you can't retract a build from users who already updated. Halting the phased release only stops *new* updaters; everyone already on 4.2 stays there until you ship 4.2.1. If most of your 4.2 population has already updated, tonight's rollback may not move the failure count much regardless of who's guilty. If there's a server-side flag that can disable the 4.2 checkout path, that's faster and far more reversible than a build action.

## Where this lands

- **terminal_state: `underdetermined`** — the discriminating check hasn't run. This is not "you're wrong"; it's "the evidence you have doesn't yet separate four live explanations."
- **action_disposition: `hold`, pending the rate query** — recommendation only. The call is yours, and `underdetermined + authorized` is a legitimate place to stand if you decide the risk of waiting outweighs the risk of acting blind.

**If you can get the denominator tonight:** run it, apply the mapping above, and you'll have a defensible decision within the hour.

**If telemetry is genuinely unavailable tonight** and the bleeding is severe enough that you'd rather act blind than wait: halt the phased rollout (stops new exposure, preserves the 4.2 population as comparison data) rather than pushing a full reversal — then run the rate query at first light. That's the version of your instinct that keeps the diagnosis alive.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

## Yes — that's a real gap. Here's its size

```
4.2:      89% of complaints ÷ 60% of sessions  →  1.48
non-4.2:  11% of complaints ÷ 40% of sessions  →  0.28
                                    ratio ≈ 5.4×
```

4.2 users are generating failed-checkout complaints ~5.4× more often per session than everyone else. That is not noise, and it is not a base-rate artifact. **H2 is `contradicted`** — session share can no longer explain complaint share. You closed that off cleanly.

## What that check did and didn't reach

The predeclared discriminator was *measured checkout failure rate ÷ checkout attempts*. What you brought is *complaints ÷ sessions*. Close, and it did real work — but two substitutions survived it:

**The numerator is still complaints, not failures.** Nothing in either turn's data has touched actual checkout telemetry. A build that changed where the "report a problem" button lives — or added one to the checkout error screen — produces a 5× complaint-rate jump with the failure rate flat. Support entry-point changes routinely move complaint volume by multiples.

**The denominator is sessions, not checkout attempts.** If 4.2's redesign moves more users into the funnel per session, more attempts means more failures per session at an identical per-attempt failure rate.

And the 60/40 split raises something neither turn has examined:

**H5 — cohort confounding.** *Is 4.2's 60% a random 60%?* Staged rollouts almost never are. If 4.2 went out first by region, OS version, or device tier, and the real fault is a payment processor in that region or an SDK bug on that OS, you get exactly 89/60 with 4.2's checkout code entirely innocent. Rolling back would not touch it.

## Status

| Rival | Was | Now |
|---|---|---|
| H1 — 4.2 checkout regression | `leading` | `leading`, now with actual support `[measured: complaint rate per session, 5.4× — proxy for failure rate]` |
| H2 — base-rate artifact | `live` | **`contradicted`** `[measured: 89% ≫ 60% expected]` |
| H3 — concurrent server-side change | `live` | `weakened` — doesn't easily explain build-correlated concentration `[inferred]` |
| H4 — reporting-surface artifact | `live` | **`live`, undiscriminated** — predicts this exact number |
| H5 — cohort confounding | *new* | **`live`, undiscriminated** — predicts this exact number |

H4 and H5 both output 89/60. The gap discriminates against base rate; it doesn't separate these three.

## What I'd actually do tonight

**Start staging the rollback.** At 5.4× you have enough to justify the prep, and the staging time is free.

While it stages, two questions — call them ten minutes each:

1. **To whoever cut the release:** was 4.2's rollout randomized, or staged by region / OS / device? *Kills or confirms H5 outright.*
2. **To the mobile team, or just the 4.2 changelog:** did 4.2 add or move any support/report entry point, especially on checkout error screens? *Kills or confirms H4 outright.*

If both come back clean, ship the rollback with a clear conscience. If either comes back dirty, you've saved the night and you're looking in the right place instead.

## Make the rollback its own test

Predeclare this before you pull the trigger — if H1 is fully true and you remove 4.2, total failed-checkout complaints should fall to roughly the non-4.2 rate:

> **Expected: ~70% drop in total failed-checkout complaint volume within 24h.**

- Drops ~70% → H1 confirmed, done.
- Drops ~20–30% → 4.2 was a contributor, not the cause. Keep digging.
- Barely moves → H4 or H5 was right. You now know that in a day instead of a week.

That converts a night of work into a measurement either way, which is worth more than rolling back and eyeballing the queue.

---

**terminal_state: `underdetermined`** — two rivals predict your data and neither has been tested.
**action_disposition: recommend `authorized` to proceed with rollback prep, contingent on those two questions.** You've moved this a long way in one step; I just don't want you to spend the night on a lever that isn't connected to the problem.


## verdict

_ungraded — open the rubric only after the run completes_
