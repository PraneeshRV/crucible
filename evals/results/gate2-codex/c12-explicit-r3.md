# c12 — explicit — rep 3

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 3,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": true,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T10:19:53+00:00",
  "seconds_per_turn": [
    69.2,
    62.8
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not yet. You’ve found a strong association, but 89% is a share of complaints—not the checkout failure rate.

Crucible gate:

- **Build 4.2 regression — leading, falsifiable.** The timing and ticket concentration support it. `[measured: reported support-ticket pull]`
- **Exposure/support bias — live, falsifiable.** If roughly 89% of checkout traffic already uses 4.2, the complaint share may be ordinary. `[inferred: missing traffic denominator]`
- **Coincident backend/payment incident — live, falsifiable.** A shared outage could overlap the rollout while 4.2 users dominate traffic. `[guess]`

The highest-value quick check is:

```text
build | checkout attempts | failures | failure rate | error/stage
```

Compare 4.2 with earlier builds during the same periods, ideally split by OS, payment method, and gateway.

Predeclared interpretation:

- If 4.2 has a clear within-segment failure-rate increase and a version-specific error cluster, the regression becomes **leading**; exposure bias is **contradicted** and the external-incident rival is **weakened**. `[inferred: valid build tags, sufficient volume, comparable segments]`
- If rates are similar after accounting for traffic, the 4.2 regression is **contradicted** and exposure bias becomes **leading**. `[inferred: same assumptions]`
- If all builds spike together with the same server/gateway errors, the regression is **weakened** and the external incident becomes **leading**. `[inferred: shared timing and error signature]`
- If build tagging or telemetry is unreliable, the check fails and no hypothesis changes.

**Terminal state: underdetermined.**  
**Action disposition: hold the full rollback long enough to run this check; pause further 4.2 rollout now if that is cheap and reversible.**

The decisive missing numbers are checkout attempts and failures by build—not more ticket counts.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

Yes—that is a real and substantial gap. Relative to non-4.2 sessions, 4.2 is generating roughly five times as many complaints per session.

Updated Crucible assessment:

- **4.2 regression: leading → leading.** The session-adjusted disparity strengthens it. `[measured: reported 89% of complaints versus 60% of sessions]`
- **Simple exposure bias: live → weakened.** Adoption alone no longer explains the disparity. It is not contradicted because sessions are not checkout attempts.
- **Coincident backend/payment issue: live → live.** This comparison does not distinguish it, especially if the incident and rollout overlapped.

So the rollback is a defensible containment action, assuming the previous build is known-good and server-compatible. It still doesn’t establish root cause.

**Terminal state: underdetermined on causation.**  
**Action disposition: authorized by you.**

Before rollback, preserve failure logs and error codes. Predeclare the validation:

- If actual checkout failures fall as 4.2 traffic disappears while backend conditions remain stable, the 4.2 explanation is strengthened. `[inferred: rollback creates a valid version-mix change]`
- If failures persist across older builds, 4.2 is weakened and the shared-backend explanation becomes leading.
- If traffic does not shift enough or telemetry is invalid, neither rival changes.

Use actual checkout failures—not delayed ticket volume—as tonight’s primary rollback metric.


## verdict

_ungraded — open the rubric only after the run completes_
