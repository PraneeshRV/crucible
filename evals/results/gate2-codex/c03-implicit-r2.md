# c03 — implicit — rep 2

```json
{
  "case": "c03",
  "condition": "implicit",
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
  "run_at": "2026-08-15T09:41:05+00:00",
  "seconds_per_turn": [
    99.0,
    40.7
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

Check request-level correlation first; don’t inspect clocks in isolation. Intermittency alone does not distinguish these hypotheses.

For a sample of 401s plus matched successful requests, capture:

- Rejecting instance/pod and deployment SHA
- Exact authentication failure reason
- Token `iat`, `nbf`, `exp`, and `kid`—never the raw token
- Verifier timestamp and measured clock offset
- Cache replica, entry version/age, and lookup result
- Ingress/LB target identifier

Then interpret the cohorts:

| Result | What it indicates |
|---|---|
| 401s concentrate on an old build or target pool | Load-balancer/old-deployment theory becomes leading. Confirm that current instances accept the same token. |
| 401s occur near `nbf` or `exp`, with “not yet valid”/“expired” errors and sufficient measured offset | Clock skew becomes leading. A verifier behind the issuer rejects newly issued tokens; one ahead rejects tokens early. |
| 401s concentrate on one cache replica, especially for newly issued tokens or after key/session changes | Stale-replica theory becomes leading. Confirm with a read-through/fresh lookup or an auth-only validation routed to a fresh replica. |
| Failures are spread across deployments but correlate with `kid`, issuer, audience, client, or token age | Look beyond the three theories—key rotation, claim/config mismatch, or a client-specific issuance problem is more likely. |
| No meaningful correlation | The current instrumentation is insufficient, or multiple faults coexist. Don’t select a root cause yet. |

Useful falsifiers:

- Large validity margins and correct verifier clocks weaken clock skew.
- No old deployment handling any failed request weakens the LB theory.
- Identical fresh cache state, with cache bypass producing the same rejection, weakens stale-cache theory.

If possible, validate one affected token through each verifier using an auth-only endpoint; don’t replay a state-changing API request. Until these observations exist, the diagnosis is underdetermined, with all three hypotheses still live.


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

Clock skew is now weakened, not fully contradicted. The measured 4 ms offset is far below the 30-second tolerance, assuming the probe measured every verifier—including `build-1187`—during failing requests.

The old deployment is now the leading hypothesis, but one correlation is still missing: were the 241 requests on `build-1187` the same requests that returned 401?

Run a status-by-build cross-tab:

- If `build-1187`: 241 requests, 241×401; `build-1204`: 4,571 requests, 0×401 → old deployment is strongly established; clock skew and stale cache are contradicted for this incident.
- If both builds show 401s → routing alone does not explain it; continue examining token validity margins and per-instance clocks.
- If `build-1187` requests succeeded → the matching 5% is coincidental.

Also verify that the clock measurement covered the old build. An aggregate measured only on current instances cannot clear `build-1187`.


## verdict

_ungraded — open the rubric only after the run completes_
