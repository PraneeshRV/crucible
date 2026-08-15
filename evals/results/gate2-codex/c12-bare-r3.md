# c12 — bare — rep 3

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 3,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": false,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:14:49+00:00",
  "seconds_per_turn": [
    40.7,
    24.2
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not quite. You know **89% of complaints came from 4.2**, but not whether **4.2 users fail more often**. If 4.2 handles ~90% of mobile checkouts, that result may be normal.

Before a full rollback, compare:

- Failed checkout rate per attempt: 4.2 vs 4.1
- 4.2’s share of all checkout traffic
- Error codes, payment methods, OS versions, and rollout timing
- Whether the spike began immediately after 4.2 deployment

My read: this is enough to **halt further rollout now** and prepare the rollback, but not enough by itself to prove 4.2 caused the failures. If telemetry shows a clear material increase—or telemetry is unavailable and checkout impact is severe while rollback is low-risk—a targeted rollback tonight is reasonable.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes—that’s the relevant gap. Relative to session exposure, 4.2’s complaint rate is approximately:

\[
(89/60) \div (11/40) \approx 5.4\times
\]

So 4.2 sessions generate about **5.4 times the complaint rate** of other builds. Assuming complaints are correctly classified and the sample isn’t tiny, rollback is well justified.

Preserve 4.2 logs first, roll back, then monitor checkout-failure and complaint rates. A sharp decline after rollback will further confirm causality.


## verdict

_ungraded — open the rubric only after the run completes_
