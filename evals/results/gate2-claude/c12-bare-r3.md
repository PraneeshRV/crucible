# c12 — bare — rep 3

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 3,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "e7b9f29",
  "skill_installed": false,
  "denied_tools": [
    "Task",
    "Agent",
    "Skill"
  ],
  "builtin_skills": "denied by name",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-16T06:52:38+00:00",
  "seconds_per_turn": [
    33.8,
    43.7
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not quite — that number can't distinguish "4.2 is broken" from "most of your users are on 4.2."

**The problem with 89%**

You measured P(on 4.2 | complained). What you need to decide a rollback is P(checkout fails | on 4.2) vs. P(checkout fails | on 4.1). Those are different quantities, and the first one is dominated by how many people are on 4.2 at all.

If 4.2 is already 85% of your mobile install base, then 89% of complaints coming from it is roughly what you'd expect from a build that changed nothing. If 4.2 is 20% of the base, 89% is a five-alarm fire. Same statistic, opposite conclusions — and you can't tell which world you're in from the ticket data alone.

**The four numbers that actually answer it**

Pull a 2×2 from checkout telemetry, not tickets:

|  | 4.2 | 4.1 |
|---|---|---|
| checkout attempts | A | C |
| checkout failures | B | D |

Compare B/A to D/C. That's the whole decision. If B/A is meaningfully higher, roll back. If they're within noise, 4.2 is a bystander and rolling it back tonight costs you a night and leaves the real cause running.

**Three things that can fake a signal even in that table**

- *Rollout targeting.* If 4.2 went to newest-OS or a specific region/carrier first, you're comparing populations, not builds. Segment by device/OS/region, or restrict to a cohort that got both.
- *Reporting bias.* Users on a fresh update are primed to blame the update and are likelier to file. Telemetry doesn't have this problem; tickets do.
- *Timing coincidence.* If the failure curve started before 4.2's rollout ramp, look at what else shipped that week — payment processor changes, an API deploy, a cert rotation, a pricing/tax config push. Overlay the failure-rate curve against the 4.2 adoption curve; if failures rose while adoption was still at 10%, it isn't 4.2.

**What I'd do tonight**

The 2×2 is usually a single query against checkout events and should take minutes, not hours — worth running before you commit to the rollback. If your telemetry can't split failure rate by build version, that's the thing to fix first, because you'll hit this exact wall on the next incident too.

That said: if the query is genuinely unavailable and checkout revenue is bleeding right now, rolling back is a defensible risk-management call — just make it knowing it's a hedge, not a diagnosis. Keep 4.2 in a small holdout so you can still tell whether failures follow the build or stay flat. If they stay flat after rollback, you've learned something important and 4.2 is exonerated.

Happy to sketch the query if you tell me where checkout events land.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes — and the gap is considerably bigger than the way you framed it, which strengthens your case.

**Run the ratio, not the difference**

"89 vs 60" reads like a 1.5x lift, and that's the number people usually eyeball. But the right comparison is complaints-per-session across the two builds:

- 4.2: 89% of complaints ÷ 60% of sessions → 1.48
- 4.1: 11% of complaints ÷ 40% of sessions → 0.275

Ratio: **~5.4x**. Users on 4.2 are generating complaints at more than five times the per-session rate of users on 4.1. The 40% of sessions still on 4.1 are producing almost no tickets, and that's the part that carries the signal — it's the near-silence of the control group, not the loudness of 4.2, that makes this convincing.

That's not a subtle effect, and it survives the base-rate objection I raised. Your inference holds.

**Two things worth thirty seconds before you pull the trigger**

*Total complaint count.* The percentages behave very differently depending on N. At 100 complaints (89/11), this is overwhelming — p is effectively zero. At 20 (18/2), still solid, p≈0.008. At 9 (8/1), it's marginal, p≈0.08, and you could get that from chance. Anything north of ~15 total complaints and the result is real. Below that, you're reading noise.

*Reporting bias is the one confound left standing.* Freshly-updated users do file more readily. But to explain away 5.4x, they'd have to be 5.4x more likely to open a ticket for an identical failure — that's not plausible. A realistic 1.5–2x inflation still leaves you ~3x. The effect is real; just expect the true magnitude to land somewhat below 5.4x.

**Roll it back — with a holdout**

Keep 1–2% of users on 4.2 rather than reverting everyone. Two reasons: it converts the rollback into a clean experiment, and if failures *don't* drop after the rollback you'll find out from the data instead of from another week of tickets. Watch the checkout failure rate on the reverted population overnight; if it falls to 4.1 baseline, you're confirmed and you can hunt the regression in daylight against a known-guilty diff.

One thing to fix afterward, not tonight: you diagnosed this from support tickets because failure rate wasn't queryable by build version. Ticket volume lags the actual failure by hours and undercounts silent failures — the users who just abandoned the cart never wrote in, so your real blast radius is larger than 89% of anything. Emitting checkout success/failure tagged with build version turns the next one of these into a dashboard glance.


## verdict

_ungraded — open the rubric only after the run completes_
