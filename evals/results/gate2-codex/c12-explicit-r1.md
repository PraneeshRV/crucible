# c12 — explicit — rep 1

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 1,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": true,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:17:58+00:00",
  "seconds_per_turn": [
    53.4,
    63.6
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not yet. The 89% figure is **complaint composition**—`P(build 4.2 | complaint)`—but the rollback decision needs **failure rate by build**—`P(failure | build 4.2)`. If 4.2 handles roughly 89% of checkout attempts, the ticket share may be ordinary.

Crucible gate:

- **Build regression:** 4.2 introduced the failure. `status: live`; `testability: falsifiable`. The ticket concentration supports investigation, but not causation. `[measured: supplied ticket export]`
- **Exposure/confounding rival:** 4.2 has most traffic, a more complaint-prone cohort, or coincides with a backend/payment issue. `status: live`; `testability: falsifiable`. `[inferred: missing traffic denominators and cohort controls]`

Best fast check: compare `failed checkouts / all checkout attempts` for 4.2 versus prior builds in the same time window, then split by error code, OS, payment method, region, and rollout cohort.

Predeclared interpretation:

- A clear 4.2-specific rate increase, especially starting at upgrade and tied to a new error signature → build regression becomes `leading`; rival `weakened`. `[inferred: causal timing and build specificity]`
- Similar normalized rates across builds → regression `weakened`; shared backend/cohort cause becomes `leading`. `[inferred: absence of build specificity]`
- Missing or unreliable build/attempt telemetry → neither changes; the check is invalid.

`terminal_state: underdetermined`  
`action_disposition: hold` on a full rollback based on tickets alone.

Tonight, I’d pause further 4.2 rollout while pulling that normalized comparison. If checkout loss is severe and rollback is known-safe, rollback can still be chosen as risk mitigation—but record it as action under uncertainty, not proof that 4.2 caused the incident.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes—the gap is real: 4.2 produces **over five times as many complaints per session** as other builds:

`89 / 60` versus `11 / 40`.

But sessions are still not checkout attempts. A 4.2 cohort that attempts checkout much more often could explain some of the disparity.

Crucible update:

- **4.2 checkout regression:** `live → live`. The result points in its predicted direction, but the planned failure-per-checkout discriminator has not run. `[inferred: user-supplied complaint and session shares]`
- **Traffic exposure alone:** `live → weakened`. A 60% session share cannot by itself explain 89% of complaints.
- **Different checkout frequency or cohort mix:** remains `live`.

`terminal_state: underdetermined` on causation  
`action_disposition: authorized` by your rollback decision

The rollback is defensible as incident mitigation if it is known-safe; just don’t describe the data as proving causation. Before starting, preserve build-tagged checkout logs and verify 4.1 remains API-compatible.

Predeclared rollback readout:

- Failures per checkout attempt drop for reverted users → regression becomes `leading`; cohort/backend rival `weakened`.
- Failure rates remain unchanged → regression `weakened`; cohort/backend rival becomes `leading`.
- A simultaneous backend change or unusable telemetry → test invalid; neither explanation updates.


## verdict

_ungraded — open the rubric only after the run completes_
