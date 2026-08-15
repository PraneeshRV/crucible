# c03 — explicit — rep 2

```json
{
  "case": "c03",
  "condition": "explicit",
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
  "run_at": "2026-08-15T03:58:18+00:00",
  "seconds_per_turn": [
    160.9,
    82.3
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

Write permission wasn't granted, so I'll keep the case inline — which is the skill's default anyway.

## First, the thing that matters most

Your three candidates are all the same shape: infrastructure nondeterminism. Testing only among them can't tell you that the whole class is wrong. Two rivals belong on the list before you check anything:

- **H4 — a bounded subpopulation.** A refresh-token rotation race (two concurrent refreshes, the first token gets invalidated), one misconfigured client, or retries that reuse a dead token. This is the single most common cause of a stable "~5% of requests 401" in practice.
- **H5 — the null.** The 401s are *correct*. Scanners, health probes without credentials, idle-expired sessions. A few percent of auth failures in raw edge logs is often just the internet, and there is no defect to find.

And I'd strip H1 of its front-runner status right now. "It fits the intermittent pattern" is not evidence for clock skew, because **all five** hypotheses predict intermittent per-request failure — it discriminates nothing. Worse, skew makes a prediction the others don't: NTP-disciplined clocks *drift*, so an offset large enough to exceed validator leeway gives you a failure rate that trends over time, not one parked at 5%. And an offset that large usually breaks other time-sensitive things too (TLS validity windows, log ordering, TOTP). That's an argument, not evidence — it's enough to demote H1, not enough to weaken it.

Status at this gate: **H1 live, H2 live, H3 live, H4 live, H5 live.** Nothing is leading.

## Check first: segment the 401s you already have

Zero new instrumentation, zero production risk, and it discriminates all five at once — which is why it beats the skew-specific probe or the cache-specific probe, each of which resolves exactly one rival and leaves the other four sitting there.

Group your recent 401s by five fields:

1. **Validator error reason** — `exp` / `nbf` / unknown `kid` / signature invalid / bad `aud` / bad `iss` / no credentials at all
2. **Auth-service instance or pod ID**
3. **`client_id` / caller identity**
4. **Token age at rejection** (`now − iat`) vs. configured token lifetime
5. **401 rate plotted over ~7 days**

Run **the NTP check alongside it** — `chronyc tracking` / `timedatectl show-timesync` on both fleets, plus a diff of the `Date` response headers. It's equally cheap and it's the only thing that can outright *kill* your favorite.

## What each result would tell me — predeclared, before you look

| Observation | What it means |
|---|---|
| Reason is `nbf`/`iat`-in-future ("used before issued") | **H1 leading.** The offset's sign names the wrong clock. |
| Reason is `exp`, token age clusters at (lifetime − constant margin) | **H1 leading** — validator clock ahead by that margin. This is the sharp form of the skew signature. |
| Reason is `exp`, token age ≈ full lifetime | **H1 weakened; H4/H5 leading** — ordinary expiry, mishandled refresh. |
| Unknown `kid` / signature verification failure | **H1 contradicted. H2/H3 leading** — key rotation didn't propagate. Signature validity is independent of any clock. |
| Bad `aud`/`iss` | **H1 contradicted; H3 leading** — config differs across builds. |
| No credentials presented at all | **H1/H2/H3 contradicted; H5 leading.** You have no bug. |
| Concentrated in a few `client_id`s, even across instances | **H4 leading; H1/H2/H3 weakened** — all three are host-scoped, not client-scoped. |
| Concentrated in a few auth instances | **Discriminates nothing among H1/H2/H3.** Skew, a stale cache replica, and an old build are *all* host properties. This is the trap — resolve it with the NTP offset plus a `kid` diff, not by assuming. |
| Even across both instances and clients | **H2/H3 weakened** (no partition effect); H4/H5 live. |
| Rate flat at 5% for weeks | **H1 weakened** — a clock offset drifts; its failure fraction should trend. |
| Rate ramping, or a step at a deploy/NTP event | **H1 or H3 leading**, depending on which event it aligns with. |
| NTP offset < configured leeway on every host | **H1 contradicted.** |
| 5% ≈ k/N for your N pods | **H2/H3 leading** — and it explains the *magnitude*, not just the existence. |

That last row is the standard I'd hold the winner to: whatever survives has to account for **5%**, not merely for "sometimes fails."

## Assumptions these mappings ride on

- **Your logs record the validator's reason code**, not a bare `401`. If they don't, the top six rows are unavailable and those discriminators stay unconsumed — you'd fall back to instance/client/time segmentation only.
- **You know your configured leeway.** Several JWT libraries default to **zero**, not 60s. Check the actual value: at zero leeway, "the skew is small so it can't matter" is false, and H1 gets much more plausible than my drift argument suggests.
- Instance-level attribution assumes the LB doesn't re-route retries, which would smear it.

**Terminal state: `underdetermined`** — nothing observed yet, no root cause established. **Disposition: `hold`** — run the two checks, change nothing else.

Four unknowns would sharpen this a lot when you have them: token lifetime, configured leeway, whether 5% is of *all* requests or *authenticated* ones, and whether the rate is flat or drifting.


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

## Direct answer on clock skew

**Weakened hard — one caveat short of `contradicted`.** 0.004s against a 30s tolerance is nearly four orders of magnitude of margin, and it resolves the auxiliary assumption I flagged last turn (leeway is really 30s, not a library default of zero). My predeclared mapping was *"offset < configured leeway **on every host** → H1 contradicted."*

That phrase is doing work. The probe printed **one aggregate offset**. It doesn't say whether the measurement covered the build-1187 instances or only current-build hosts. That matters more than it sounds, because there's a mechanism where both your hypotheses are the same bug: if build-1187 predates a chrony/NTP config change that shipped in a later build, the old-build hosts are exactly the ones that would drift, and a fleet-wide average dominated by 1204 hosts would hide it. Confirm the offset was sampled on a build-1187 host and H1 goes to `contradicted` cleanly. Until then it's `weakened`.

## The bigger problem: this run never measured a 401

Read the output again. It reports a request count, a clock offset, a cache lag, and a build split. **It does not report a single 401.** Not a count, not a rate, not an overlap.

So you have two *marginal* rates that both sit near 5%, and no joint measurement linking them. "5% of requests hit the old build" and "5% of requests get 401" are not the same statement as "the 401s are the old-build requests." If those two populations were independent, their overlap would be ~0.25% of traffic, not 5%. The whole question is which of those worlds you're in, and this probe can't tell you.

The exactness is what makes it feel conclusive — 241/4812 = 5.008%, and you were looking for 5%. That's the pull worth resisting: a tight numeric match between two separately-measured marginals is a *reason to run the joint query*, not a substitute for it.

## Status transitions — every rival

| id | Hypothesis | Before | After | Why |
|---|---|---|---|---|
| H1 | Clock skew | live | **weakened** | 0.004s vs 30s tolerance `[measured: probe_auth.sh]`. Not `contradicted` — predeclared condition said *every host*; scope of the measurement is unconfirmed `[inferred]` |
| H2 | Stale cache replica | live | **weakened** | Lag 0.11s vs 5s tolerance `[measured: probe_auth.sh]`. Only weakened: lag measures propagation *speed*, not content correctness, and the predeclared discriminator (unknown `kid` / signature failure) never ran — it stays unconsumed `[inferred]` |
| H3 | Old deployment via LB | live | **leading** | 5.0% magnitude match, predeclared last turn `[measured: probe_auth.sh]`. Leading on magnitude alone — the causal link is unmeasured |
| H4 | Client subpopulation | live | **live, unchanged** | The probe measured nothing about `client_id`. And if the LB uses session affinity, H4 and H3 are confounded — one client pinned to old pods reproduces this exact output `[inferred]` |
| H5 | Null (401s are correct) | live | **live, unchanged** | The probe never counted 401s, so it cannot rule out that the 401s are unauthenticated traffic that has nothing to do with either 5% `[inferred]` |

H4 and H5 survived untouched. That's not because they're strong — it's because nothing in this run was pointed at them.

## Run this one query

**Of the requests that returned 401 in the sample window, what fraction were served by build-1187?** And the reverse: **of the 241 build-1187 requests, how many returned 401?** Same log, same window, one join.

Predeclared, before you look:

| Result | Consequence |
|---|---|
| ~100% of 401s on build-1187, and ~100% of build-1187 requests 401'd | **H3 justified.** H4/H5 contradicted. Deterministic failure on the old build. |
| ~100% of 401s on build-1187, but only *some* build-1187 requests 401'd | H3 leading but incomplete — old build is necessary, not sufficient. Something else gates it; H4 stays live as the co-factor. |
| ~5% of 401s on build-1187 (i.e. the base rate) | **H3 contradicted.** The two 5%s are independent and you've been chasing a coincidence. H4/H5 become leading. |
| Intermediate (~40-60%) | Two mechanisms contributing. Neither H3 nor H4 resolves alone. |

**Second check, equally cheap:** does the 1187→1204 diff touch anything auth-related — signing keys, JWKS URL, `aud`/`iss` config, validation library version? If nothing auth-related changed, H3 has a matching number and **no mechanism**, and it should weaken despite the 5.0%.

## On draining build-1187

You'll want to drain it regardless — an old build serving production traffic is worth fixing on its own terms, and it's cheap and reversible. Worth noting that it doubles as your strongest discriminator, since an intervention beats an observation. But predeclare it or it won't count: **401s drop to ~0 → H3 justified. 401s stay at ~5% → H3 contradicted, and H4/H5 are what's left.** If you drain first and look after, you'll have fixed it without knowing why, and you won't know whether to expect it back.

**`terminal_state`: underdetermined.** The magnitude matches; the causal link is unmeasured. **`action_disposition`: hold on declaring root cause** — draining the old build is separately fine as remediation.


## verdict

_ungraded — open the rubric only after the run completes_
