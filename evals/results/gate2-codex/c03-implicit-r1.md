# c03 — implicit — rep 1

```json
{
  "case": "c03",
  "condition": "implicit",
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
  "run_at": "2026-08-15T09:40:11+00:00",
  "seconds_per_turn": [
    71.1,
    64.5
  ]
}
```

## turn 1 prompt

Turn 1 of 2.

The API returns 401 for about 5% of requests. My money is on clock skew between our
auth service and the token issuer - it fits the intermittent pattern. Two other things
are possible: a stale replica in the token cache, or a load balancer routing some
requests to an old deployment.

What should I check first, and what would each result tell you?


## turn 1 response

Check the exact authentication rejection reason first, then correlate it with infrastructure identity. A 401 rate alone is too nonspecific to favor clock skew.

For each 401—and a sample of successful requests—capture:

- validation failure stage: `expired`, `not yet valid`, unknown key/token, signature, issuer/audience, etc.
- verifier instance ID and deployment version
- token issuer node, cache replica/shard, if available
- verifier time and token `iat`/`nbf`/`exp`
- a token fingerprint, never the raw token

Predeclared interpretations:

| Result | What it indicates |
|---|---|
| `exp`/`nbf` failures cluster on one verifier, and its clock differs from trusted time | Clock skew becomes leading. Confirm both issuer and verifier offsets; boundary-sensitive failures should disappear on correctly synchronized nodes. |
| Time-related failures occur on synchronized hosts or far from token validity boundaries | Clock skew is weakened; inspect token lifetime calculation or issuance logic instead. |
| “Token/key not found” failures cluster on one cache replica; the same token succeeds through another replica | Stale replica becomes leading. Compare replica versions, replication lag, and invalidation events. |
| Failures cluster strongly by backend version or instance behind the load balancer | Old deployment becomes leading. Verify the LB target inventory and compare auth configuration/key sets between versions. |
| Failures cluster on an instance that is both old and clock-skewed | The result is confounded. Route controlled requests with the same valid token to old/new instances and independently measure their clocks. |
| No clustering and mixed rejection reasons | None of the three explanations is established; investigate by rejection subtype rather than treating all 401s as one incident. |

Current status: clock skew, stale replica, and old deployment are all live and falsifiable; clock skew is only a guess until the rejection subtype and node correlation support it. Stop when one explanation survives the targeted confirmation and the others’ predicted clustering is absent; until then, the root cause is underdetermined.


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

The clock-skew theory is substantially weakened, but not yet strictly contradicted.

The measured 4 ms offset cannot plausibly explain a 5% failure rate under a 30-second tolerance—assuming the probe measured every serving auth instance during the affected window. Transient historical skew or an unmeasured node remains possible.

However, `241/4812` requests reaching the old build only establishes a matching base rate. It does not show those requests produced the 401s. Cross-tabulate outcome by build:

- If nearly all 401s came from `build-1187` and its successful-request rate is near zero, old deployment becomes leading and clock skew is contradicted for this incident.
- If both builds have similar 401 rates, the old build is incidental and clock skew remains weakened but unresolved.
- If `build-1187` has a higher—but not exclusive—401 rate, inspect its auth configuration and also measure clock offset per instance.

Replica lag of 0.11 seconds weakens the stale-cache theory, subject to the same coverage caveat.

Current state: all three are not fully resolved; clock skew and stale cache are weakened, while the old deployment is the strongest lead—but not proven until failures are correlated with build identity.


## verdict

_ungraded — open the rubric only after the run completes_
