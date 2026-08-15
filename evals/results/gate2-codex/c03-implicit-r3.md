# c03 — implicit — rep 3

```json
{
  "case": "c03",
  "condition": "implicit",
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
  "run_at": "2026-08-15T09:41:48+00:00",
  "seconds_per_turn": [
    109.0,
    71.2
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

Check the exact authentication failure reason and correlate it with the serving instance first. “Intermittent” alone does not particularly favor clock skew; a stable 5% failure rate often matches a backend or replica receiving roughly 5% of traffic.

For each 401—and a comparable sample of successful requests—capture:

- Validator reason: `expired`, `not-yet-valid`, unknown `kid`, cache miss, signature failure, etc.
- Token `iat`/`nbf`/`exp` and request time; never log the raw token.
- Auth/API instance ID, build/version, and load-balancer target.
- Cache replica and cached-entry/key version.
- NTP synchronization status and clock offset for the issuer and verifier.

Interpret the results as follows:

| Result | What it indicates |
|---|---|
| 401s are temporal-claim failures, concentrated near `nbf` or `exp`, and track measured clock offset | Clock skew becomes leading. [inferred: temporal validation errors vary with measured offset] |
| The same token succeeds on correctly synchronized instances but fails on an offset instance | Strongly discriminates for verifier clock skew. [inferred: token and issuer are held constant] |
| Failures cluster by old build or LB target, independent of token age | Old deployment becomes leading. [inferred: routing/version predicts failure better than time claims] |
| Failures cluster by cache replica or disappear when cache lookup is bypassed | Stale cache replica becomes leading. [inferred: backend and token remain constant while cache path changes] |
| Unknown-`kid` or signature failures appear just after key rotation | Suspect a stale JWKS/signing-key cache specifically, rather than general clock skew. [inferred: key availability explains the validator result] |
| Failures occur uniformly across instances but only for tokens issued during certain intervals | Investigate issuer clock jumps or bad issuance data. [inferred: issuance interval, not routing, predicts failure] |
| Failures cluster by instance, and that instance is both old and clock-skewed | Still underdetermined: test that instance after correcting only its clock, or replay against an old-but-time-synchronized instance. |

If current logs cannot make that correlation, run a controlled replay: send the same unexpired token to each backend while recording which cache replica is used. This holds the token constant and quickly separates routing, clock, and cache effects.

Current conclusion: all three hypotheses remain live; clock skew is not yet justified as leading. Avoid changing clock tolerance first—it could hide expired-token acceptance problems without addressing the actual cause.


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

The clock-skew theory is now strongly weakened—and effectively contradicted if that 4 ms measurement covered every verifier during the failure window. A 4 ms offset cannot breach a 30 s tolerance. [measured: probe output; inferred: temporal validation threshold]

But the old-build result is not yet causal evidence. You’ve matched two marginal rates:

- 5% of requests use `build-1187`.
- Historically, about 5% receive 401s.

You still need their intersection. Compute `401 rate by build`:

- If nearly all 401s come from `build-1187`, while `build-1204` is clean, the old deployment becomes leading.
- If both builds return roughly 5% 401s, the matching percentages were coincidental.
- If the probe window had no 401s, it only confirmed that the old build receives traffic; it did not identify the cause.
- If `build-1187` has an elevated but imperfect failure rate, it is likely a contributor, not the whole explanation.

One caveat: a single aggregate clock measurement could miss transient or instance-local skew. Confirm the measurement was per instance and contemporaneous with failures before calling clock skew fully contradicted.

Current state: clock skew **weakened**, stale cache **weakened**, old deployment **suspicious but not yet established**; overall diagnosis remains underdetermined.


## verdict

_ungraded — open the rubric only after the run completes_
