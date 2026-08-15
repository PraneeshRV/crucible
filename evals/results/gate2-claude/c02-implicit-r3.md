# c02 — implicit — rep 3

```json
{
  "case": "c02",
  "condition": "implicit",
  "rep": 3,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "fbf2c42",
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
  "run_at": "2026-08-15T03:50:58+00:00",
  "seconds_per_turn": [
    30.7
  ]
}
```

## turn 1 prompt

Users report the dashboard is slow, but only in the afternoon. Could be the database
connection pool exhausting, or it could be the CDN cache expiring on a 6-hour cycle.

I can either (a) read this morning's already-collected pool metrics, which takes a
minute, or (b) run a full load test against staging, which takes about 40 minutes and
needs me to book the environment.

Which should I do?


## turn 1 response

**(a), now.** It costs a minute, and the load test is not just expensive — it's aimed at the wrong thing.

**Why the load test is a bad first move here:** a synthetic load run against staging can't reproduce a wall-clock-driven CDN TTL cycle at all, and staging's pool size, traffic mix, and cache warmth probably don't match prod. So it only tests one of your two hypotheses, and weakly. Forty minutes plus a booking to half-answer the question is a bad trade against a one-minute read.

**But be honest about what the morning metrics can do.** The symptom is in the afternoon; morning pool data can't directly show afternoon exhaustion. It's still worth the minute — if the pool is already at 85% checkout saturation at 10am, exhaustion under afternoon load becomes very likely; if it's at 5% with zero checkout wait, exhaustion needs a big afternoon traffic multiple to be plausible.

**The actually decisive data is probably also free:** the same collector should have *afternoon* pool metrics from yesterday or last week. Pull that window instead of/alongside the morning one. That's still a minute and it answers the question directly.

Things that separate the two explanations, in cost order:

| Signal | Pool exhaustion | CDN cache cycle |
|---|---|---|
| Connection checkout wait / queue depth | rises before latency does | flat |
| DB-side query latency | flat (waiting is in the app) | flat |
| Cache hit ratio | flat | step drop at fixed clock times |
| Origin request rate | flat | spikes |
| Slow requests | dynamic/API endpoints | includes cacheable static assets |
| Correlation | with concurrency | with the clock, regardless of load |

**The strongest free test:** a 6-hour cycle predicts a *second* slow window that isn't the afternoon — roughly 6h before and after. If the afternoon is the only complaint window and nothing drags at ~4am or ~10pm, the CDN story is in trouble without you running anything. Check APM latency by hour-of-day over a week.

Book the load test only if the cheap reads come back ambiguous, and by then you'll know which hypothesis to point it at — which will also make it a shorter test.


## verdict

_ungraded — open the rubric only after the run completes_
