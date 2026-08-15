# c03 — explicit — rep 3

```json
{
  "case": "c03",
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
  "run_at": "2026-08-15T09:45:38+00:00",
  "seconds_per_turn": [
    135.7,
    94.6
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

Check a request-level cohort matrix first. For the same time window, calculate the 401 rate—not merely the failure count—by:

- Auth/verifier instance and its independently measured NTP offset
- Validation reason code and distance from `nbf`/`exp`
- Cache replica actually consulted
- Backend deployment revision
- Token `issuer`/`kid` and a non-secret token identifier

Include successful requests as controls; never log raw tokens.

Predeclared interpretation:

- Failures concentrate near `nbf` or `exp` and follow verifier clock offsets, independent of cache replica and revision → clock skew becomes `leading`; stale cache and old deployment become `weakened`. `[inferred: time-validation failures should track claim boundaries and clock offset]`
- Failures concentrate on one cache replica, with the same token validating through other replicas → stale replica becomes `leading`; clock skew and old deployment become `weakened`. `[inferred: replica-local state should produce replica-local outcomes]`
- Failures concentrate on an old revision, especially when the same token succeeds on the current revision → old deployment becomes `leading`; the other two become `weakened`. `[inferred: revision-dependent validation should follow serving revision]`
- Failures concentrate only by issuer, `kid`, client, or token cohort across every backend → none of the three is leading; add a token/configuration-policy rival. `[inferred: infrastructure-independent clustering points to token inputs or shared policy]`
- Cache replica and deployment revision are correlated—for example, old pods always use one cache replica → the result is confounded; all three remain `live`. Hold the token constant and vary one dimension at a time next.
- Required identifiers are missing or unreliable → the check is invalid; weaken nothing.

Contradiction thresholds:

- Clock skew: failed tokens are comfortably valid against an independent time reference, affected hosts are synchronized, and outcomes instead follow replica or revision.
- Stale cache: failures occur without cache involvement or do not follow the actual replica used, across a window representing every replica.
- Old deployment: no old revision served the affected traffic, or identical requests behave identically across revisions with complete routing attribution.

Initial case state: all three hypotheses are `live` and falsifiable; intermittency alone does not distinguish them. The gate remains `open`, with `action_disposition: hold`. Observational clustering can select the next controlled test, but I would require a same-token reproduction with the suspected variable isolated before calling the root cause justified.


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

Clock skew is weakened, not contradicted. The measured 4 ms offset is strong evidence against persistent service-wide skew, assuming every verifier instance was covered during the failure window. `[measured: supplied probe output; inferred: 4 ms is immaterial against a 30 s tolerance]`

The exact 5% match does not yet prove the old build caused the 401s. You have two marginal rates, but not their intersection:

| Build | Requests | 401s | 401 rate |
|---|---:|---:|---:|
| build-1187 | 241 | ? | ? |
| build-1204 | 4,571 | ? | ? |

Status update:

- Clock skew: `live → weakened`; not contradicted until failed requests are tied to synchronized verifier clocks and tokens comfortably inside `nbf`/`exp`.
- Stale cache: `live → weakened`, provided 0.11 s is the worst-case lag across every relevant replica.
- Old deployment: `live → live`; highly suspicious, but the predeclared discriminator—401s concentrating on that revision—was not reported.

Next, produce that build-by-status cross-tab:

- Nearly all old-build requests are 401s while current-build requests succeed → old deployment becomes `leading`. `[inferred: outcome follows revision]`
- Similar 401 rates on both builds → old deployment becomes `weakened`. `[inferred: revision does not discriminate outcomes]`
- Zero 401s during this “clean run” → the incident was not reproduced, so the 5% routing observation does not discriminate any root cause.

Current root-cause conclusion: `underdetermined`; `action_disposition: hold`.


## verdict

_ungraded — open the rubric only after the run completes_
