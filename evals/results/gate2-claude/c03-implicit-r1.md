# c03 — implicit — rep 1

```json
{
  "case": "c03",
  "condition": "implicit",
  "rep": 1,
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
  "run_at": "2026-08-15T03:54:15+00:00",
  "seconds_per_turn": [
    85.1,
    54.5
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

## Short answer

Check none of the three first. Check **how the 5% partitions** — one query that discriminates all of them at once. Then do the arithmetic on clock skew, which you can probably do in two minutes from numbers you already have.

I have no access to your systems here, so everything below is `[inferred]` from the stated symptom — no observation has been made.

### First, the thing that makes "intermittent" misleading

Intermittency at ~5% is predicted equally well by all three of your hypotheses, plus the one you didn't name. So it's not evidence *for* skew — it's the observation that fails to distinguish anything. Your prior is resting on a non-discriminating fact.

### The rival you haven't named

**Null hypothesis: nothing is broken infrastructurally.** The 401s are concentrated in a small set of callers with genuinely invalid credentials — a revoked key, a wrong `audience`, a client that never refreshes, one misconfigured tenant that happens to send ~5% of your traffic. This is the most common explanation for a *stable* 5%, and it's the expensive one to miss because it sends you re-architecting NTP for a config bug. `testability: falsifiable`, `status: live`.

### Check 1 — free, do it before anything else: does skew survive arithmetic?

Clock skew produces failures at roughly `skew / token_TTL` (assuming clients refresh at expiry, uniformly distributed) `[inferred: uniform-refresh model]`.

- TTL = 1 hour → 5% requires **~3 minutes of skew**. That is enormous; any NTP monitoring would already be screaming, and you'd see far worse symptoms than 401s.
- TTL = 5 minutes → 5% requires ~15 seconds. Plausible.

If your TTL is long and your measured NTP offset is sub-second, clock skew is effectively contradicted before you instrument anything. Cost: one metric lookup.

### Check 2 — the discriminating query

Pull the 401s from the **auth service** (not the edge — see the trap below) and group them along five dimensions: `reason_code` from the issuer, `client_id`/principal, serving instance + build SHA, cache replica ID, and **token age at rejection**.

Predeclared mapping — what each signature would mean:

| Signature in the 401s | Reading |
|---|---|
| Reason is `exp`/`nbf`, ages cluster at the TTL boundary, uniform across callers and nodes | Skew → `leading`. Sign matters: clock ahead ⇒ `exp`; clock behind ⇒ `nbf`/future `iat`. |
| Reason is unknown `kid` or bad signature, concentrated on a subset of auth nodes, **decaying** over time after a key-rotation event | Stale replica → `leading`; skew → `weakened` |
| Concentrated on instances of one build SHA, and that build's share of the fleet ≈ 5% | Old deployment → `leading`. The share-matching is the tell; if old pods are 30% of the fleet, this is `contradicted` regardless of everything else. |
| Concentrated in a handful of `client_id`s, uniform across nodes and versions, flat over time | Null → `leading`; **all three of your hypotheses → `weakened`**, because each predicts caller-uniformity |
| Uniform on every dimension, constant rate | All four `weakened`; look at retry storms, a 429-mislabeled-as-401 path, or connection-pool reuse across identities |

The reason code alone does a lot of work: `exp` vs `invalid signature` vs `audience mismatch` splits the space before you look at anything else.

### The instrumentation trap

If your 401 logs come from the edge/CDN and don't record which backend served the request, the deployment-version question **cannot be answered** by that data. If that happens, mark the *check* failed and leave the deployment hypothesis at `live` — don't let a blind query read as exoneration. Same for the caller dimension if the principal isn't logged on failures.

### Why not "measure the clock skew" first

It's confirmatory, not discriminating. Some skew always exists, so finding it doesn't establish causation, and finding none eliminates one of four while telling you nothing about the rest. The partition query costs about the same and moves all four.

---

**Status board:** clock skew `leading` (on your prior, `[guess]` — the supporting observation is non-discriminating) · stale replica `live` · old deployment `live` · null/bad-credentials `live`. All `testability: falsifiable`.

`terminal_state: underdetermined` · `action_disposition: hold` — nothing measured yet; no fix should ship on the skew theory until Check 1's arithmetic and Check 2's partition come back.

If you paste the grouped 401 counts, I'll run them against the predeclared mapping above.


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

## Clock skew: contradicted

0.004s against a tolerance of 30s, and against the ~15–180s the arithmetic required to produce a 5% failure rate. That's three to four orders of magnitude short of the mechanism. `[measured: probe_auth.sh --window 300]` matching the predeclared quantitative prediction from last turn.

Stated auxiliary assumption: that's a spot reading of one auth host against the issuer. If you run multiple auth/validator hosts, it doesn't rule out one bad-clock host in the pool — but a single skewed host would show up as a *node*-concentrated failure, and you'd need that host to be ~5% of the fleet, which just re-derives the deployment hypothesis. Skew is dead as an independent explanation.

## But the probe didn't test what the `[!!]` implies

It measured **traffic share by build**, not **401s by build**. You now have two numbers that both round to 5% and no link between them. If the 401s were spread uniformly across both builds, this output would look exactly the same.

That leaves my predeclared discriminator — *401s grouped by build SHA* — unconsumed. It never ran.

Worth being precise about the match, too: 241/4812 is 5.008%. If the 401 rate is actually 4.6% or 5.4%, the builds can't be in one-to-one correspondence with the failures, and the "5% ≈ 5%" reasoning quietly breaks.

## The one query

401 rate **within** build-1187 vs within build-1204. Predeclared readings:

| Result | Meaning |
|---|---|
| 1187 ≈ 100%, 1204 ≈ 0% | Deployment `justified`. Old build can't validate current tokens at all. |
| 1187 ≈ 1204 ≈ 5% | Coincidence. Deployment `contradicted`, and the **null hypothesis — a few callers with bad credentials — is back to `leading`**, since nothing in this probe looked at callers. |
| 1187 strictly between, tracking a token attribute (`kid`, issue time) | Partial incompatibility: 1187 predates a key rotation and rejects only tokens signed with the new key. Still the deployment, but blast radius and fix differ — rollback isn't enough, you'd need the rotation story too. |

That third row is why "not 100%" wouldn't exonerate the build.

## Status board

- clock skew — `contradicted` `[measured: probe offset 0.004s vs ~15–180s required]`
- stale cache replica — `weakened` `[measured: 0.11s lag]`, not contradicted: a 300s window can't observe a key-rotation event, and a replica pinned to a stale signing key can show healthy replication lag
- old deployment — `live`, promoted in plausibility but **not** `leading`: the evidence is fleet composition, not failure attribution `[inferred: two unlinked 5% figures]`
- null / bad credentials — `live`, entirely untouched by this probe

`terminal_state: underdetermined`

On action: rolling back build-1187 is cheap and reversible, so `action_disposition: authorized` is a perfectly honest call here — just make it on record as *acting under uncertainty*, not as a diagnosis. It's also a clean test: 401s vanish → confirmed; 401s hold at 5% → the build was innocent and you still have the bug, with the null hypothesis waiting.


## verdict

_ungraded — open the rubric only after the run completes_
