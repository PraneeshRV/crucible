# c03 — implicit — rep 2

```json
{
  "case": "c03",
  "condition": "implicit",
  "rep": 2,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "fbf2c42",
  "skill_installed": true,
  "denied_tools": [
    "Task",
    "Agent",
    "Skill(debug)",
    "Skill(verify)",
    "Skill(code-review)",
    "Skill(simplify)",
    "Skill(deep-research)",
    "Skill(claude-api)"
  ],
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-15T03:54:14+00:00",
  "seconds_per_turn": [
    80.1,
    55.2
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

## The check I'd run first isn't a test of any of your three

All three of your hypotheses predict "intermittent 401s." That's why they feel equally plausible — you're comparing them on the one dimension where they're identical. They differ sharply on **how the failures partition**, and that's nearly free to look at.

So before testing clock skew, I'd answer: *are the 401s random, or are they concentrated?*

### Rival set

I'm adding two you didn't list, because the first check discriminates them at no extra cost:

| | Hypothesis | Status | Testability |
|---|---|---|---|
| A | Clock skew, auth service vs. issuer | `live` | falsifiable |
| B | Stale replica in token cache | `live` | falsifiable |
| C | LB routing to an old deployment | `live` | falsifiable |
| D | **Null: the 401s are correct** — expired tokens, revoked/unmigrated clients, failed refreshes | `live` | falsifiable |
| E | **Stale JWKS / signing-key cache after a key rotation** | `live` | falsifiable |

Nothing is `leading` yet. You have a favorite, but the evidence supporting it so far is "it's intermittent," and all five explain that. `[inferred: shared prediction across rivals]`

E deserves separate billing from B. "Stale token cache" and "stale *public-key* cache" fail through different mechanisms and have different fixes, and the key-rotation version is one of the most common causes of exactly this symptom: rotation happens, a fraction of validators keep serving the old JWKS from cache, tokens signed with the new `kid` get rejected until the TTL expires. `[documented: standard JWKS caching failure mode]`

### Check 1 — partition the 401s (one log query, minutes)

Pull the 401s from a single window and group them along five axes:

1. **Error detail** — `expired_token` vs. `invalid_signature` vs. `unknown_kid` vs. `invalid_token`. Often already in the `WWW-Authenticate` header or the validator's log line.
2. **Serving instance** of the auth service (pod/host/AZ)
3. **`kid` and `iss`** of the rejected token
4. **Principal / client id**
5. **Token age at rejection** — `now − iat`, and `exp − now` at the moment of rejection

### Predeclared outcome mapping

Written before you look, so the result can't be reinterpreted after the fact:

| Observation | A skew | B cache | C old deploy | D null | E JWKS |
|---|---|---|---|---|---|
| Concentrated on a **subset of instances**, stable over time | live | live | **leading** | weakened | live |
| Concentrated by **`kid`**, or starts at a key-rotation timestamp | weakened | weakened | live | weakened | **leading** |
| **Token age** clusters just past `exp`, offset by a fixed interval | **leading** | weakened | weakened | live | weakened |
| Token age exceeds full TTL; error is `expired_token` | weakened | weakened | weakened | **leading** | weakened |
| Concentrated by **principal/client** | weakened | weakened | weakened | **leading** | weakened |
| Genuinely uniform across all five axes | weakened | weakened | **contradicted** | live | weakened |

That last row matters: C requires a partition. If the 401s are uniformly spread across instances, C is done — no further work. `[inferred: routing to a subset of hosts cannot produce instance-uniform failures]`

The "fixed interval" row is the specific signature of clock skew, and it's tighter than "intermittent." Skew rejects tokens whose `exp` (or `nbf`) sits within the offset window, so failures cluster at a *reproducible* token age — not at random ages. `[documented: JWT `exp`/`nbf` validation semantics]`

### Two things that would weaken your favorite before you measure anything

**A steady 5% doesn't look like drift.** Unchecked clock skew grows monotonically, so it should show a *rising* 401 rate, or 100% failure on one bad node — not a flat 5%. A flat 5% looks like a partition: 1 of ~20 instances, or one cache replica of ~20. If your fleet happens to be near that size, that's suggestive of B/C/E over A. `[inferred: drift is monotonic; steady fractions imply stable partitions — weak, and depends on your fleet size]`

**Skew has to beat the leeway.** Most JWT libraries ship 30–60s of clock tolerance by default. For A to be true, your actual offset must exceed that — or someone set leeway to 0. Worth confirming the configured leeway first; it's a config read, and if it's at the default, A needs a fairly large offset to survive. `[documented: common default `leeway`/`clockTolerance` settings]`

### If you skip to checking clocks anyway

Then note this trap: **running `chronyc tracking` now tells you nothing about the failure window.** A clean reading today doesn't weaken A — it's an invalid instrument for a question about the past. If you want to test A directly, the valid version is to take a *rejected token from the logs*, decode its `exp`/`nbf`, and compare against the receiving instance's clock at the recorded rejection timestamp. That's a real discriminator; a live NTP check is not.

### Then, and only then

- **A survives** → decode-and-compare as above; also check historical clock-offset metrics, not current state.
- **B survives** → query each cache replica directly with the same token; a disagreement between replicas is the confirmation.
- **C survives** → correlate 401s against the build SHA / version header in the response. If your responses don't carry one, add it — this is worth doing regardless.
- **E survives** → compare JWKS cache TTL against the last key-rotation timestamp.
- **D survives** → this is the good outcome. 5% baseline auth failure on a public API is not obviously anomalous, and you'd stop spending on this.

---

**terminal_state: `underdetermined`** — no check has run; nothing is established.
**action_disposition: `hold`**

The one thing that could turn this into `blocked`: if your 401 log lines don't carry the token `kid`, the serving instance, and the error detail, none of the above is answerable and the real first task is adding those three fields. Worth confirming they're there before you start querying.


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

## Your probe didn't measure what the headline implies

Look closely at the flagged line:

```
[!!] 241/4812 requests served by deployment build-1187
```

That says 241 requests **went to the old build**. It does not say those 241 requests **got 401s**. The probe reported a population share, not a failure join.

Two disjoint 5% populations produce exactly this output. So does one overlapping population. The rate match is suggestive — 241/4812 = 5.008%, against your ~5% 401 rate — but a matching *rate* is not a demonstrated overlap of *requests*.

My predeclared row was "401s concentrated on a subset of instances." That discriminator hasn't been consumed. It never ran. The probe answered an adjacent question.

### Status transitions

| | Hypothesis | Was | Now | Basis |
|---|---|---|---|---|
| C | LB → old deployment | live | **`leading`** | `[measured: probe, build split]` + `[inferred: rate coincidence, not a join]` |
| A | Clock skew | live | **`weakened`** | `[measured: 0.004s vs 30s tolerance]` — with a caveat below |
| B | Stale token-cache replica | live | **`weakened`** | `[measured: 0.11s vs 5s tolerance, contemporaneous window]` |
| D | Null — 401s are correct | live | **`live`, unchanged** | `[guess]` — probe carried no error detail or principal breakdown |
| E | Stale JWKS after key rotation | live | **`live`, unchanged** | `[guess]` — probe carried no `kid` breakdown |

C is `leading`, not `justified`. Nothing here contradicted anything.

### Where that leaves clock skew specifically

`weakened`, not `contradicted` — for one reason: **that offset is a single number for "auth-service," and the interesting population is a subset of it.**

If the probe read one instance, or a fleet median, a single badly-synced node is invisible in a 0.004s aggregate. And the suspicious subset here is *old-build instances*, which is precisely where you'd expect stale config — including NTP config, and including a `leeway` setting that differs from current. A and C aren't cleanly independent; the old build is a plausible carrier for both.

To actually contradict A, you'd need the offset measured **per instance, on build-1187 nodes specifically**. If that comes back sub-second too, A is done.

B I'd treat as more solidly weakened. Replica lag was measured in the same window as the sampling, against a 40× margin. That's clean evidence, not a "looks fine now" reading.

### The one query that closes this

Group 401s by build over the same window:

```
status=401 | count by deployment_build
```

Predeclared, before you look:

| Result | Meaning |
|---|---|
| ~241 401s on build-1187, ~0 elsewhere | C **`justified`**. A, D, E → `contradicted`. Done. |
| 401s spread proportionally across both builds | C **`contradicted`** — the 5.0% match was coincidence. A, D, E back to live, and you've learned the old build is a red herring. |
| 401s on build-1187 but well under 241 | Old build is a *contributing* factor, not the whole cause. Something else is also firing. |
| Old-build requests mostly succeed | C `contradicted`. |

Pull the error detail and `kid` on those 401s in the same query — it's free at that point, and it separates C-the-carrier from E-the-mechanism. If build-1187 predates a signing-key rotation, the failure is `unknown_kid`, and the real exposure is broader than one stale deployment: *any* validator with a stale JWKS cache is at risk, not just old builds. Same symptom, different blast radius, different fix.

### On mitigation

Draining build-1187 from the LB is cheap and reversible, and it's reasonable to do now regardless of the diagnosis — it's good hygiene independent of this incident.

One caveat if you do: it destroys the population you'd need for the join. If the 401s vanish, that's strong confirmation of C but leaves the C-vs-E mechanism question unanswerable from this incident. Run the query first — it costs a minute.

---

**terminal_state: `underdetermined`** — C leads on a rate coincidence that hasn't been converted into a join.
**action_disposition: `hold`** on the root-cause claim; mitigation is your call and doesn't depend on it.

One note on reading probe output: `[ok]` on the clock line means that check passed its threshold, not that skew is exonerated. Thresholds pass on the population sampled — which here may not include the population that's failing.


## verdict

_ungraded — open the rubric only after the run completes_
