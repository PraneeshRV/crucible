# c12 — bare — rep 1

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 1,
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
  "run_at": "2026-08-16T06:50:17+00:00",
  "seconds_per_turn": [
    25.0,
    35.7
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not yet — that number can't distinguish "4.2 is broken" from "most of your users are on 4.2."

**The gap:** you have P(on 4.2 | complained). What justifies a rollback is P(checkout fails | on 4.2) vs. P(checkout fails | on 4.1). If 4.2 is already 85–90% of your mobile install base — normal a week into a staged rollout with auto-update on — then 89% of complaints coming from 4.2 users is exactly what a *bug-free* release looks like. Rolling back would cost you a night and fix nothing.

**The one check that settles it,** and it's a short query:

```
failure_rate = failed_checkouts / checkout_attempts, grouped by app_version
```

Rates, not counts, with the attempt count as the denominator. If 4.2 is at 6% and 4.1 is at 2% on the same days, you have your answer and you should roll back. If they're both at 3%, something else broke this week and 4.2 is just the version most people happen to be running.

**Three things that would otherwise mislead you:**

- **Timing.** Compare 4.2 users to 4.1 users *over the same window*, not 4.2-this-week to 4.1-last-week. If a payment processor, a certificate, or an API dependency changed on the same day 4.2 shipped, a before/after comparison blames the build for it.
- **Who's on which build.** Early upgraders skew newer devices and newer OS versions; laggards on 4.1 skew older hardware and often different regions. That's a real population difference, not a build difference. Segment by OS version and region if the top-line rates are close.
- **Complaint propensity.** Users who just got an update are primed to attribute anything that breaks to the update and report it. Ticket volume is a noisier signal than server-side checkout telemetry — if you have the latter, trust it over the tickets.

**What I'd suggest for tonight:** run the rate query before committing to the rollback. It's minutes of work, and it's the difference between a fix and an expensive no-op. If you genuinely can't get the data before your window and failures are severe, rolling back is a defensible risk-management call — just log it as "rolled back on incomplete evidence" so nobody later reads it as a confirmed 4.2 defect and stops looking for the real cause.

If you can point me at the ticket export or the analytics DB, I'll run the breakdown now.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes — that's a real signal now. You've got the comparison the first number was missing.

Working it in odds: complaints split 89/11 is 8.1:1 in favor of 4.2, while sessions split 60/40 is 1.5:1. Divide those and 4.2 users are complaining at roughly **5.4x the rate** of 4.1 users. Reporting bias from "new update, must be the update" is real but it buys you maybe 1.5–2x, not 5.4x. That's a defect-sized gap, and rolling back is a reasonable call.

Two things I'd check while the rollback is spinning up, because they change what you do rather than whether you act:

**1. What are the absolute counts?** 89/11 reads identically whether it's 890 vs. 110 tickets or 8 vs. 1. At 8 vs. 1, a single bad afternoon in one region produces that split by chance and you'd be shipping a rollback on noise. Glance at the raw N — if it's in the hundreds, you're solid and I'd stop questioning it there.

**2. Does a rollback actually reach the affected users?** This is the one I'd worry about tonight. Pulling 4.2 from the stores stops *new* updates — but the 60% already running 4.2 stay on 4.2. Mobile doesn't downgrade itself. So the rollback protects the 40% who haven't updated yet and does nothing for the population actually generating your tickets, unless you have forced-update machinery.

If the checkout break is reachable by a server-side flag or a kill switch — old payment path, previous API version, disabled feature — that fixes the 60% tonight, which the store rollback can't. I'd do both: flag off for the immediate bleeding, pull the build to stop the exposed population from growing.

One more thing worth ruling out in parallel: if anything server-side shipped alongside 4.2 (API version, payment SDK config, a new endpoint only 4.2 calls), the client rollback masks it rather than fixing it, and it'll come back with 4.3. Worth having someone check the deploy log for that window while the rollback runs.

Short version: your read holds up, go ahead — just confirm the raw counts aren't single digits, and don't count on the store rollback alone to help the users already complaining.


## verdict

_ungraded — open the rubric only after the run completes_
