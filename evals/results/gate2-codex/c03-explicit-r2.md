# c03 — explicit — rep 2

```json
{
  "case": "c03",
  "condition": "explicit",
  "rep": 2,
  "harness": "codex",
  "model": "gpt-5.6-sol",
  "sandbox": "workspace-write",
  "reasoning_effort": "xhigh",
  "crucible_commit": "20a6583",
  "skill_installed": true,
  "denied_tools": [],
  "builtin_skills": "suppressed by .system marker",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T09:45:36+00:00",
  "seconds_per_turn": [
    143.2,
    128.0
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

Check a matched cohort of failed and successful requests first. Intermittency alone does not favor clock skew over replica, deployment, or client/token cohorting.

For each request, correlate:

- Auth rejection reason
- Hashed token ID—never the raw bearer token
- `iat`, `nbf`, and `exp`
- Verifier timestamp plus independently measured clock offset
- Auth instance and build SHA
- Load-balancer target
- Cache replica and entry version/age

Prefer retries of the same token, then match controls by issuer, endpoint, and time window.

Current hypotheses are all `live` and `testability: falsifiable`. I’d add a fourth rival: a client/token cohort sending missing, malformed, expired, or otherwise invalid credentials.

Predeclared result mapping:

- Temporal-validation failures cluster near `nbf`/`exp`, and the measured verifier offset explains the rejection: clock skew becomes `leading`; client/token error becomes `weakened`; cache and deployment remain `live` until their dimensions are excluded. `[inferred: temporal claims plus independent offset explain the decisions]`

- The same token fails through one stale cache replica/version and succeeds through a current one: stale cache becomes `leading`; clock skew and client/token error become `weakened`; old deployment remains `live` if cache placement and build are confounded. `[inferred: outcome changes with cache state while the credential is held constant]`

- The same token fails only on an old build or LB target and succeeds on current builds: old deployment becomes `leading`; clock skew and client/token error become `weakened`; cache remains `live` unless cache routing is independently controlled. `[inferred: outcome changes with deployment while the credential is held constant]`

- Failures follow particular tokens or clients across healthy clocks, current builds, and cache replicas, with a concrete malformed/expired/missing-token reason: client/token error becomes `leading`; the three infrastructure hypotheses become `weakened`. `[inferred: failure follows the credential rather than infrastructure]`

- No usable correlation, or missing/untrustworthy instance, clock, or cache labels: the check is invalid or non-discriminating; all hypotheses remain `live`. Invalid instrumentation weakens nothing.

Strong contradiction criteria:

- Clock skew: independently synchronized clocks, ample temporal margin on the exact rejected tokens, and a non-temporal rejection reason.
- Stale cache: verified current/coherent cache reads—or a cache bypass—still reproduce the rejection.
- Old deployment: complete routing evidence shows no old build served the failures.
- Client/token defect: the exact valid credential succeeds or fails solely according to infrastructure target.

`terminal_state: underdetermined`  
`action_disposition: hold` on corrective changes; perform the read-only cohort check first.


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

The clock-skew theory is `weakened`, not yet `contradicted`.

The reported 4 ms offset is far inside the 30-second tolerance, assuming the probe covered every auth instance—including the old deployment—rather than reporting a fleet average. `[documented: supplied probe output] [inferred: ordinary issuer/verifier skew would be too small to cause temporal rejection]`

Current updates:

- Clock skew: `live → weakened`
- Stale cache: `live → weakened`, assuming every replica was sampled
- Old deployment: `live → live`; it is now the highest-priority lead, but not yet `leading`
- Client/token defect: `live → live`

The important catch: “5% of traffic used the old build” and “5% of requests fail” are marginal totals. They do not show that the same requests overlap.

Check this contingency table next:

| Build | 401 | Successful |
|---|---:|---:|
| build-1187 | ? | ? |
| build-1204 | ? | ? |

Predeclared interpretation:

- Every old-build request is a 401 and current-build requests succeed: old deployment becomes `leading`; cache and client/token theories become `weakened`. Clock skew becomes `contradicted` only if build-1187’s own clock was measured and rejected tokens had safe `nbf`/`exp` margins. `[inferred: outcome follows deployment while credentials are controlled]`
- Both builds show similar failure behavior: old deployment becomes `weakened`; clock remains `weakened`; client/token or another shared cause remains `live`. `[inferred: failures do not follow deployment]`
- Failures cluster on build-1187 but have temporal rejection reasons: investigate old validation code, leeway configuration, and that instance’s clock separately. That supports an old-deployment defect, not necessarily actual clock skew.

`terminal_state: underdetermined`  
`action_disposition: hold` until the 401-by-build correlation is shown.


## verdict

_ungraded — open the rubric only after the run completes_
