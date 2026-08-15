# c12 — bare — rep 1

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 1,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": false,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:12:59+00:00",
  "seconds_per_turn": [
    25.2,
    23.1
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not quite. The 89% figure is **P(version 4.2 | complaint)**, but the rollback decision needs **P(failure | version 4.2)**.

If 90% of checkout attempts came from 4.2, then 89% of complaints would not implicate it. Before rolling back, compare:

- Checkout failure rate on 4.2 versus 4.1, using attempts—not tickets—as the denominator
- The same platforms, countries, payment methods, and time window
- Error codes and the timing of the 4.2 rollout
- 4.2’s share of active users or checkout attempts

Support tickets are also a biased sample because reporting rates can differ by version.

So: this is a strong signal to halt further rollout and investigate immediately, but by itself it doesn’t justify a rollback. If telemetry shows a materially higher failure rate on 4.2—or you lack telemetry and the operational impact is severe—a staged rollback is reasonable.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes—assuming “sessions” means sessions with checkout exposure, that’s a large gap.

The relative complaint rate is:

\[
(89\% / 60\%) \div (11\% / 40\%) \approx 5.4
\]

So 4.2 users are complaining at roughly **5.4× the rate** of users on other builds.

That’s strong evidence supporting rollback, especially if the rollout timing matches the increase. Preserve the error data, roll back safely, and monitor actual checkout failure rates afterward. The main caveat: use checkout attempts rather than all app sessions if those populations differ substantially.


## verdict

_ungraded — open the rubric only after the run completes_
