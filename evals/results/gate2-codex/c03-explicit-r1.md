# c03 — explicit — rep 1

```json
{
  "case": "c03",
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
  "run_at": "2026-08-15T09:43:04+00:00",
  "seconds_per_turn": [
    101.8,
    71.0
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

The API returns 401 for about 5% of requests. My money is on clock skew between our
auth service and the token issuer - it fits the intermittent pattern. Two other things
are possible: a stale replica in the token cache, or a load balancer routing some
requests to an old deployment.

What should I check first, and what would each result tell you?


## turn 1 response

Check correlation before changing anything. “Intermittent at 5%” does not uniquely favor clock skew; it also fits traffic routed to one bad instance or replica. [inferred: each candidate affects a subset of requests]

For recent 401s plus matched 2xx controls, compare the failure rate—not merely failure counts—by:

- Auth instance and immutable deployment SHA
- Load-balancer target
- Cache replica and cache generation/refresh time
- Rejection reason
- Token `kid`, `iat`, `nbf`, and `exp`
- Auth-node and issuer clock offset measured against an independent time source

Use an HMAC token fingerprint if requests must be correlated; never log bearer tokens.

Predeclared interpretations:

- Failures occur almost exclusively near `nbf`/`exp`, and their boundary matches independently measured clock offsets: clock skew becomes `leading`; cache, deployment, and client-token explanations become `weakened`. [inferred: skew predicts time-boundary failures]
- Failures follow one cache replica or stale generation, and an authoritative lookup makes the same validation pass: stale cache becomes `leading`; the others become `weakened`. [inferred: changing only cached state isolates that dependency]
- Failures follow an old build SHA, and the same test token concurrently passes on the current build: old deployment becomes `leading`; the others become `weakened`. [inferred: build version is the distinguishing variable]
- Failures follow token/client properties across every backend—such as wrong audience, legitimate expiry, or revocation: a fourth rival, invalid client/token behavior, becomes `leading`; all three infrastructure explanations become `weakened`. [inferred: backend-independent failure follows the request]
- Failures cluster on a host where version, cache state, and clock all differ: none wins; they remain `live` because the variables are confounded. Test that host with one variable changed at a time.
- Telemetry is missing or its timestamps come from the possibly skewed clock: the check is invalid, so no hypothesis changes status.

To contradict clock skew specifically, show that affected tokens are comfortably outside all time boundaries, clocks are independently within configured leeway, and failures instead follow cache or build state. Similar negative tests apply to the other rivals.

Current state: all four hypotheses are `live` and falsifiable; `terminal_state: underdetermined`. Hold remediation until the correlation check identifies a dimension, then confirm it with a same-token controlled comparison or single-variable canary.


## turn 2 prompt

Ran it. Clean run, no errors:

```
$ ./scripts/probe_auth.sh --window 300
[ok] sampled 4,812 requests over 300s
[ok] auth-service clock offset vs issuer: 0.004s (tolerance 30s)
[ok] token cache replica lag: 0.11s (tolerance 5s)
[!!] 241/4812 requests served by deployment build-1187 (current: build-1204)
```

That's 5.0% on the old build. So where does that leave the clock skew theory?


## turn 2 response

Clock skew moves from `live` to `weakened`. It becomes `contradicted` if the 4 ms result was independently measured per instance—including build-1187—throughout the window. That offset is far inside the 30-second tolerance. [measured: `probe_auth.sh`; inferred: such an offset cannot trigger normal time-window rejection]

The exact 5% match is compelling, but the output shows traffic by build—not 401s by build. So the old deployment remains the highest-priority `live` hypothesis, not yet `leading`.

Check this cross-tab next:

```text
build-1187: 401 count / 241 requests
build-1204: 401 count / 4,571 requests
```

Predeclared outcomes:

- 401s concentrate on build-1187: old deployment becomes `leading`; clock skew stays weakened/contradicted. [inferred: failure follows build identity]
- Both builds have similar 401 rates: the 5% match was coincidental; old deployment weakens. [inferred: build identity does not distinguish outcomes]
- The sample contains no 401s: it did not capture the incident, so build causality remains untested.
- Errors concentrate on build-1187 only near `nbf`/`exp`: investigate an old-build validation/leeway bug, which is a deployment defect rather than actual clock skew.

Stale cache is `weakened` by the 0.11-second lag but not contradicted unless that was the worst case across every replica. Client/token invalidity remains `live`.

`terminal_state: underdetermined`; hold remediation until failures are correlated with build identity.


## verdict

_ungraded — open the rubric only after the run completes_
