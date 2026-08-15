# c12 — bare — rep 2

```json
{
  "case": "c12",
  "condition": "bare",
  "rep": 2,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": false,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:13:52+00:00",
  "seconds_per_turn": [
    22.9,
    30.1
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

It’s a strong lead, but not enough by itself to justify a rollback.

The missing denominator is 4.2’s share of checkout attempts:

- If 4.2 handled 90% of attempts, producing 89% of complaints is roughly expected.
- If it handled 40% of attempts, 89% is highly concerning.

Before deciding, compare the failed-checkout rate—not complaint count—by build:

`failed attempts / total attempts`, for 4.2 versus 4.1, segmented by OS, payment method, region, and release time. Also check whether the increase began with the rollout and whether support tickets represent unique incidents.

If telemetry confirms a material 4.2-specific jump, rollback or disable the affected checkout path tonight. If telemetry is unavailable and the harm is ongoing, reduce 4.2 exposure first while preserving logs. The key question: what percentage of this week’s checkout attempts came from 4.2?


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes—that’s a substantial gap. Using sessions as the denominator, 4.2 generates about **5.4× more complaints per session** than the other builds:

`(89% ÷ 60%) / (11% ÷ 40%) ≈ 5.4`

The remaining caveat is that **checkout attempts** are a better denominator than sessions. But if ticket volume isn’t tiny, the timing aligns with 4.2, and rollback is low-risk, rolling back tonight is a reasonable incident-containment decision.

Preserve logs, record the rollback time, and monitor checkout failures and complaint volume afterward. A sharp decline would further implicate 4.2.


## verdict

_ungraded — open the rubric only after the run completes_
