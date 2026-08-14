# c12 — bare — rep 1

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "1207ea0",
  "skill_installed": false,
  "denied_tools": [
    "Task",
    "Agent",
    "Skill"
  ],
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-14T17:33:27+00:00",
  "seconds_per_turn": [
    42.1,
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

Not yet — that statistic can't support the conclusion on its own. It's missing a denominator.

## The problem

"89% of complaints came from 4.2 users" tells you nothing until you know **what share of your mobile users are on 4.2**. If 4.2 is the current auto-updating build and ~88% of your base is already on it, then 89% of complaints coming from it is exactly what a build with *zero* bugs would produce. Same number, opposite conclusion:

| Share of users on 4.2 | Implied relative risk |
|---|---|
| 88% | ~1.0x — nothing there |
| 60% | ~5x — real problem |
| 30% | ~19x — ship the rollback now |

One unknown swings this from "no signal" to "five-alarm fire." Right now you have the numerator of a rate and not the denominator.

## What to pull instead

Server-side, not tickets: **checkout attempts and success rate, segmented by client build**, for this week plus 3–4 prior weeks as baseline.

```
SELECT client_build, COUNT(*) AS attempts,
       SUM(status='failed') / COUNT(*) AS failure_rate
FROM checkout_attempts
WHERE ts >= now() - interval '4 weeks'
GROUP BY client_build, date_trunc('day', ts)
```

That's usually a 15-minute query and it answers the question directly. Complaint volume is a bad proxy for failure volume — it's filtered through who bothers to write in, and newer-build users skew toward more engaged users who complain more.

Three other things that can manufacture this pattern:
- **Instrumentation** — if build version is only captured or only parsed correctly on recent clients, older builds get dropped from the tag entirely.
- **Timing** — what else shipped this week? Payment processor change, API deploy, a promo that spiked traffic. Check whether the failure curve inflects when 4.2 rollout started or when something else landed.
- **Cohort** — if 4.2 went to a specific segment first (a region, a beta group), you may be measuring that segment, not the build.

## On the rollback itself

Worth flagging separately: for a mobile build you can't really roll back tonight. You can halt the staged rollout, and you can ship a forced-downgrade prompt, but users already on 4.2 stay on 4.2 until they act. If the bug *is* real, a **server-side kill switch on the 4.2-specific checkout path** will stop the bleeding hours faster than anything going through app store review. That's the lever worth identifying now, in parallel with the query — it's useful regardless of which way the data lands.

**Bottom line:** you may well be right, and the instinct to move fast is the correct one. But the number you have is equally consistent with "4.2 is broken" and "4.2 is what most people are running." Get the per-build failure rate before you spend a rollback on it.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes — that's a real gap. The math:

```
complaints per session, 4.2      = 89 / 60 = 1.48
complaints per session, non-4.2  = 11 / 40 = 0.28
                                   → ~5.4x
```

A 5.4x relative risk is not something cohort noise produces casually. My earlier objection was that the number was uninterpretable; with the denominator attached, it now points where you thought it did. I'd act on it too.

Two caveats that are worth 15 minutes but should **not** block you — run them in parallel with staging the rollback, not before it:

**Sessions aren't checkout attempts.** The correct exposure base for a checkout failure is checkout attempts, not sessions. If 4.2 changed anything upstream of checkout — a new entry point, a cart nudge, a different nav — 4.2 users may attempt checkout more often per session, which inflates the gap mechanically. Same query as before, just `GROUP BY client_build` on attempts.

**Did 4.2 make complaining easier?** This is the one thing that plausibly manufactures a 5x on its own. If 4.2 added an in-app "report a problem" affordance on the error screen, or better error surfacing, complaints-per-failure jumps hard while failures-per-attempt stays flat. Worth thirty seconds with whoever owns the 4.2 changelog.

**The part I'd actually worry about tonight:** rolling back only helps if 4.2 is the *cause*. If the real culprit is something that shipped this week server-side — processor config, API change, a cert — you'll burn the release cycle and the failures will continue while you've lost your fastest lever. The per-build failure-rate query is what distinguishes those two, which is why it's worth running even though you've already decided. It's not a check on your decision; it's a check on whether the fix works.

And the mechanics point from before still stands: you can't actually pull 4.2 off phones tonight. What you can do tonight, in order of speed:

1. **Halt the staged rollout** — stops it getting worse, takes minutes.
2. **Server-side kill switch** on the 4.2 checkout path, falling back to the old flow — this is what actually stops the bleeding for the 60% already on it.
3. **Forced-downgrade / update prompt** — slowest, needs review, days not hours.

If you only do one thing before you sleep, do #1 and #2. The store-level rollback is a tomorrow problem regardless of how right you are.


## verdict

_ungraded — open the rubric only after the run completes_
