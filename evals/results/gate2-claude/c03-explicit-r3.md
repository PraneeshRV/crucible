# c03 — explicit — rep 3

```json
{
  "case": "c03",
  "condition": "explicit",
  "rep": 3,
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
  "run_at": "2026-08-15T03:58:35+00:00",
  "seconds_per_turn": [
    106.7,
    72.1
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

No artifacts here — `artifacts/` is empty and there's no repo, so everything below is reasoning from the mechanisms you described, not measurement. Tagged accordingly.

## First, a rival you didn't list

Your three hypotheses share a hidden assumption: that the 5% is a *random* slice created by infrastructure. Two candidates outside that family:

**H4 — Signing-key rotation with a stale JWKS cache.** The issuer rotated to a new `kid`; validators holding a cached key set reject tokens signed by the new key until they refresh. `[inferred: standard JWKS caching behavior]` This is the single most common thing misdiagnosed as clock skew, because it's intermittent, time-correlated, and self-heals on cache refresh.

**H5 (null) — The 401s are correct.** A subset of callers is genuinely sending expired, absent, or wrong-audience credentials: an old SDK, a scanner, an unauthenticated health check. Nothing is broken. `[inferred: null hypothesis]`

## The number you already have is doing work

5% ≈ 1/20. Fleet-partition failures produce a rate equal to bad_nodes/total_nodes, so a suspiciously round 1-in-20 is the signature of *one bad member of a ~20-member fleet* `[inferred: 0.05 = 1/20]`. Notice all three of your hypotheses are that same shape — one drifted clock, one stale replica, one old pod — differing only in *which fleet*.

That also argues against skew as a *global* condition. If clocks were broadly drifted, the failure fraction would be roughly skew/TTL: with a 1-hour token, 5% implies ~3 minutes of drift, which is far past normal NTP behavior and past the 30–60s leeway most JWT validators allow by default `[inferred: skew/TTL arithmetic; typical library leeway defaults]`. So H1 survives mainly in its one-host form, not its fleet-wide form. That's an analytical demotion, not evidence — it reorders your prior, it doesn't contradict anything.

## The check to run first

**One query over logs you already have: cross-tabulate the 401 set against four dimensions at once.** Cost is near zero, it's read-only, and it discriminates all five rivals simultaneously — which is why it beats measuring NTP offset directly, even though that's cheaper.

Partition the 401s by: (a) responding instance/pod ID and image version, (b) client ID / user-agent / tenant, (c) token `kid`, (d) token age at request time (`request_time − iat`, and `exp − request_time`). Also record *which component emitted the 401* — gateway, auth service, or app.

Predeclared mappings, written before you look:

| Result | Reading |
|---|---|
| 401s concentrate on one or two **pod/instance IDs**, all on the **current** version | H1 promoted, but specifically as *one drifted host* — go measure NTP offset on exactly those hosts |
| 401s concentrate on pods carrying an **older image tag**, onset aligns with a deploy timestamp | H3 promoted; H1/H2 weakened |
| 401s spread evenly across instances but concentrate on one **cache node ID** | H2 promoted |
| 401s spread evenly across instances, and **all carry one `kid`**, onset aligns with a key rotation | H4 promoted; H1, H2, H3 all weakened |
| 401s concentrate on **specific client IDs**, each failing ~100% of the time | H5 promoted — it's a client problem, not a fleet problem; all four others weakened |
| 401s cluster at **token age < ~60s or within ~60s of `exp`**, evenly across all instances | H1 promoted in its fleet-wide form; check validator leeway config, since a nonzero leeway would rule this out |
| 401s **uniform on every dimension** | Every hypothesis above weakened; the partition isn't in these dimensions and you need request-level tracing |

Two things worth running alongside, since they're nearly free:

- **Retry the same token immediately.** Succeeds → server-side partition (H1-one-host / H2 / H3). Fails identically → a property of the token itself (H4 / H5). This splits the space in about two minutes.
- **`chronyc tracking` / NTP offset across all auth hosts, plus the validator's configured leeway.** Clean clocks everywhere *and* nonzero leeway would contradict H1 outright. Drifted clocks would only weakly support it — drift inside the leeway window causes no 401s at all, so a positive result here proves much less than a negative one disproves.

## Status

| Hypothesis | Status | Testability |
|---|---|---|
| H1 clock skew | `live` (demoted from your `leading`, on inferred arithmetic only) | falsifiable |
| H2 stale cache replica | `live` | falsifiable |
| H3 old deployment behind LB | `live` | falsifiable |
| H4 JWKS/key-rotation cache miss | `live` | falsifiable |
| H5 401s are correct (null) | `live` | falsifiable |

`terminal_state: underdetermined` — no hypothesis is established, and nothing has been measured. `action_disposition: authorized` for the diagnostic itself; it's read-only.

The main thing I'd push back on: "it fits the intermittent pattern" is not evidence for clock skew, because *all five* of these produce intermittency. The pattern that actually discriminates is how the 401s partition — which is why one cross-tab is worth more than a targeted test of your favorite.


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

Clock skew is **contradicted** — that's a clean match to what I predeclared (clean clocks *and* nonzero leeway rules it out), and 0.004s against a 30s tolerance is four orders of magnitude inside the window. Your prior was wrong, and the probe was the right thing to run.

One caveat on that verdict, worth thirty seconds: the output reads `auth-service clock offset` singular. In turn 1 the surviving form of H1 was *one drifted host out of ~20*, not fleet-wide drift. If the script sampled one host or an aggregate, it contradicts fleet-wide skew but leaves the one-bad-host form merely weakened. If it looped over every auth host, H1 is dead outright. Check which the script does — it changes the status, not the plan.

## The more important problem: you have two 5% numbers, not one

The probe did not report a 401 count anywhere. It reported that **5.0% of requests were served by an old build**. Your failure rate is **~5% of requests return 401**. Those are two separate measurements that nobody has joined.

That is exactly the fleet-partition coincidence I flagged in turn 1 — "5% ≈ 1/20" is the signature of *any* single bad member of a fleet, which is why all your hypotheses predicted it. Finding a second thing that is also 5% is suggestive, but the overlap between the two sets is currently unmeasured. It could be 100%, or it could be 0% with two independent causes each partitioning traffic ~1/20.

Also note: old ≠ broken. The `[!!]` fires on version mismatch, not on errors. build-1187 being 17 builds behind makes it a stuck pod set rather than a canary, but nothing yet shows it returns 401s.

And three of my four predeclared cross-tab dimensions never ran — no `kid`, no client ID, no token-age data came back. Those discriminators are unconsumed, so H4 and H5 have not been tested at all.

| Hypothesis | Status | Basis |
|---|---|---|
| H1 clock skew | `contradicted` (fleet-wide) / `weakened` (single host, pending per-host sampling) | `[measured: probe_auth.sh — 0.004s vs 30s tolerance]` |
| H2 stale cache replica | `weakened` | `[measured: probe_auth.sh — 0.11s vs 5s tolerance]`; not per-replica, and lag now ≠ lag during the 401s |
| H3 old deployment | `leading`, not established | `[measured: 5.0% traffic on build-1187]` + `[inferred: rate coincidence only — no join to 401 status]` |
| H4 JWKS / key rotation | `live`, untested | discriminator never ran |
| H5 null (401s are correct) | `live`, untested | discriminator never ran |

## The one check that settles it

A 2×2 contingency table from logs you already have: `{401, non-401}` × `{build-1187, build-1204}`. Free, read-only, instant.

| Result | Reading |
|---|---|
| ~241/241 old-build requests are 401, ~0 on new build | H3 `justified` — locus found |
| Old-build 401 rate ≈ new-build 401 rate | H3 `contradicted` — the two 5%s are independent and build-1187 is a red herring; go run the `kid` and client-ID cross-tabs for H4/H5 |
| Old build 401s at some intermediate rate | Mixed — something co-varies within the old build; partition further by `kid` |

Cheap corroborator from the same logs: does the 401 onset align with when build-1187 started serving? Your 401 rate is presumably a long-baseline figure while this probe covered 300 seconds, so confirm the old-build share is persistent and not a moving deploy front.

## Ordering, if you're tempted to just drain the pods

Draining build-1187 is cheap, reversible, and would probably stop the bleeding — and "401s go to zero after drain" is a legitimate intervention test, arguably stronger evidence than the log join. But do the join first anyway: it costs nothing, and draining destroys the state you'd need to explain *why* 1187 fails. Before recycling those pods, pull the auth config diff between 1187 and 1204 — audience, issuer URL, JWKS endpoint, signing secret, leeway setting. Without a mechanism you won't know whether recycling is a fix or a mask, and H3 and H4 may turn out to be the same bug wearing two hats: an old build pinning a stale JWKS endpoint would produce precisely this.

`terminal_state: underdetermined` — H1 is resolved, the actual cause is not. `action_disposition: authorized` for the join and the config diff; I'd hold the drain until the old pod's config and logs are captured.


## verdict

_ungraded — open the rubric only after the run completes_
