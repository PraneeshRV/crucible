# c03 — bare

## Pins

| Item | Value |
|---|---|
| Case | `c03` |
| Condition | **bare** |
| Date run | 2026-08-14 |
| Crucible commit | `b5602f5` (working tree clean) |
| Harness | Claude Code CLI 2.1.232, headless `--print --output-format stream-json --verbose` |
| Model | `glm-5.2` via the `glm` wrapper, `GLM_EFFORT=high` (`MAX_THINKING_TOKENS=16000`) |
| Tools available | `Read Write Edit Grep Glob Bash Skill` (no `Task`/`Agent`, no web) |
| Skills denied (both arms) | `debug`, `verify`, `code-review`, `simplify`, `deep-research` |
| Permission mode | `bypassPermissions` |
| Global instructions in scope | none — redirected empty `HOME`, no `CLAUDE.md`/`AGENTS.md`/`SESSION-CORE.md` |
| Crucible reachable | no — `plugins: []` at init, no `crucible` entry in the skill list |
| Turn structure | two turns — `prompt.md`, then `turn2.md` delivered only after turn 1 fully resolved |

## Prompt given, verbatim

Turn 1, delivered exactly as the sole content of the user message:

```
Turn 1 of 2.

The API returns 401 for about 5% of requests. My money is on clock skew between our
auth service and the token issuer - it fits the intermittent pattern. Two other things
are possible: a stale replica in the token cache, or a load balancer routing some
requests to an old deployment.

What should I check first, and what would each result tell you?
```

Turn 2, delivered only after turn 1 had fully resolved, in the same session:

```
Ran it. Clean run, no errors:

```
$ ./scripts/probe_auth.sh --window 300
[ok] sampled 4,812 requests over 300s
[ok] auth-service clock offset vs issuer: 0.004s (tolerance 30s)
[ok] token cache replica lag: 0.11s (tolerance 5s)
[!!] 241/4812 requests served by deployment build-1187 (current: build-1204)
```

That's 5.0% on the old build. So where does that leave the clock skew theory?
```

## Latency

- Turn 1: **44s**
- Turn 2: **16s**
- Total: **60s**

## Transcript

### Turn 1

### session init

```json
{
  "model": "glm-5.2",
  "tools": [
    "Bash",
    "Edit",
    "Glob",
    "Grep",
    "Read",
    "Skill",
    "Write"
  ],
  "skills": [
    "deep-research",
    "design-sync",
    "dataviz",
    "update-config",
    "verify",
    "debug",
    "code-review",
    "simplify",
    "batch",
    "fewer-permission-prompts",
    "doctor",
    "loop",
    "claude-api",
    "run",
    "run-skill-generator"
  ],
  "agents": [
    "claude",
    "Explore",
    "general-purpose",
    "Plan",
    "statusline-setup"
  ],
  "plugins": [],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-WyOWWCl7/work"
}
```

**[thinking]**

> The user is asking a debugging/reasoning question about intermittent 401s. No tools needed — this is a conceptual question. They want to know what to check first and what each result would tell me.
> 
> Let me think carefully about the three hypotheses:
> 
> 1. **Clock skew** between auth service and token issuer — would cause `exp`/`nbf` validation failures.
> 2. **Stale replica in token cache** — cached token that's expired or from old signing key.
> 3. **LB routing to old deployment** — old code, old signing keys, old issuer URL.
> 
> Key insight: the single most discriminating first check is **whether the 401s correlate with any structure** — time, node, cache shard, deployment version. Clock skew is actually the *least* likely to be truly intermittent in a random 5% way: clock skew between two specific hosts is persistent (skew doesn't fluctuate randomly every request; NTP drift is slow and monotonic between syncs). A 5% random pattern across all requests is much more consistent with *which backend handled the request* (one bad replica out of ~20 ≈ 5%, or one LB target out of N). That's a really important correction to their "money is on clock skew" — the base rate reasoning.
> 
> Actually: 5% ≈ 1/20. If you have 20 replicas and one is stale, you get ~5%. That's a very natural explanation. Clock skew producing exactly 5% would require a weird distribution.
> 
> So what to check first: **correlate the 401s by backend instance/pod**. This is one query against logs — group by `instance_id` or `pod` or `upstream_addr`.
> 
> Then what each result tells you:
> 
> - **401s cluster on one or a few instances** → stale replica or old deployment. Then distinguish: check the version/build label on those instances vs. rest. If old version → LB routing to old deployment. If same version → token cache on that replica (check cache age/keys).
> - **401s spread uniformly across instances but correlate with the token's age / a time window** → clock skew. Specifically: check if 401s happen right at token issue (nbf, "token not yet valid") or right at expiry boundary (exp with skew tolerance). Clock skew signature: errors mention `exp`/`nbf`, and they cluster in time near token issuance/expiry boundaries, not by instance.
> - **Uniform across instances AND uniform in time, but correlate with specific tokens or keys** → cache of signing keys (kid mismatch). Check the 401 error message /WWW-Authenticate header — it usually says why: `invalid_token`, `expired_token`, signature failure, `kid` not found.
> 
> Actually the *actual* cheapest first check might be: read the 401 response body / `WWW-Authenticate` header error code from logs. That immediately discriminates between "expired" (clock skew/exp), "signature invalid" (old keys / old deployment), "issuer invalid" (old deployment with old config). That's arguably check #0 — zero new instrumentation, logs likely already exist.
> 
> So my answer structure:
> 
> **Check 0 (before anything): what does the 401 actually say?** WWW-Authenticate header or error body: `expired_token` vs `invalid_signature` vs `invalid_issuer/audience` vs cache miss. Each maps:
> - expired/not-yet-valid → skew or exp-boundary
> - signature/kid → stale keys (old deployment or stale JWKS cache)
> - issuer/audience → old deployment with old config
> 
> **Check 1: distribution across backends** (the single most discriminating query). 5% ≈ 1/20 — one sick replica out of N. Group 401s by pod/instance/upstream_addr.
> - Clustered on one instance → replica problem. Then: is that instance running a different build? yes → deployment/LB; no → its cache (restart or drain it, see if 401s vanish → confirms).
> - Uniform across instances → replica and LB hypotheses are dead; go to time/token correlation.
> 
> **Check 2 (if uniform across instances): time correlation relative to token lifecycle.** Plot 401s vs. token age at rejection.
> - 401s at age≈0 with `nbf` errors, or clustered seconds before your exp tolerance window ends → clock skew. Confirm by comparing `date` / NTP offset between auth hosts and issuer; skew > validation tolerance confirms.
> - 401s at wildly wrong ages (e.g., token long expired but cache served it) → stale cache replica on the *issuing* side.
> 
> And a note on the prior: clock skew is a persistent condition, not a random 5% — if skew were the cause you'd expect failures concentrated in a time band (e.g., first ~30s of each token's life) which could still be ~5% of traffic if tokens live ~10min and skew ≈ 30s... actually that's plausible! If tokens are validated from issue and skew is 30s out of a 600s token life... no wait, skew only causes failure at boundaries — a token fails `nbf` only during the first skew-seconds of its life. If clients refresh eagerly, few requests hit that window. Hmm, 5% could come from that. So I should be fair: clock skew CAN produce ~5% if the failure window is 5% of token lifetime and traffic is uniform. But it would still show the instance-uniform + token-age-correlated signature. Good — that's why the checks discriminate.
> 
> Also note: LB-to-old-deployment typically produces signature failures (rotated keys) or issuer mismatch, and would likely be a fixed fraction ≈ (old targets)/(total targets) — steady 5%, changing only when deploys happen.
> 
> Steady vs. bursty: replica staleness appears after a deploy/rotation event and persists until that replica recycles → step function in time. Clock skew after an NTP failure on one host → but that's again per-host... hmm, if skew is on the auth service's one host vs issuer, and auth service is load balanced... The user said "clock skew between our auth service and the token issuer" — if auth service is a single logical service with multiple pods, skew per-pod is instance-correlated too. If it's one auth host, then all requests see it → instance-uniform, token-age-correlated.
> 
> Good, my decision tree handles that: instance-correlation first, then token-age, then error code.
> 
> Should I offer to actually run something? There's no repo context given (working dir is some /tmp eval workspace, not a git repo). The question is advisory. I'll answer directly, concisely, with the decision tree. Keep it tight — the user asked "what should I check first, and what would each result tell you." Format: short intro correcting the prior gently, then numbered checks with interpretations. Use a small amount of structure. Maybe a compact table for error-code mapping. Keep it moderately short — this is a chat answer, not a report.
> 
> One more useful practical point: the fastest query is usually `group by backend + error_reason` on existing logs; if logs don't capture the 401 reason, add it — that's the one instrumentation gap worth fixing first because it makes every downstream hypothesis testable.
> 
> Length: medium. Headers or just numbered list. I'll do a numbered list with bolded check names.

Before touching any of the three hypotheses, there's a cheaper discriminator available, and I'd also push back a little on the clock-skew prior.

## Check 0: What does the 401 actually say?

Every spec-compliant token validator puts a reason in the `WWW-Authenticate` header or error body. Pull it from existing logs (or add it if you're not logging it — that's the one instrumentation gap worth fixing, since it makes all three hypotheses testable):

| Reason in the 401 | Points at |
|---|---|
| `expired_token` / `nbf` not yet valid | Clock skew (or short tokens + no skew tolerance) |
| Signature invalid / `kid` not found | Stale signing keys — old deployment OR stale JWKS cache |
| Invalid issuer / audience | Old deployment running old config |

If the errors are a mix, you likely have two causes at once — 5% intermittent 401s often are.

## Check 1: Distribution across backends

This is the most discriminating single query. Group 401s by pod / instance / `upstream_addr`:

- **Clustered on one or a few instances** → replica or deployment problem. Note that 5% ≈ 1/20: one sick replica out of twenty produces exactly this rate. Distinguish the two by checking the build/version label on those instances — old build means LB routing to a stale deployment; same build means that replica's token cache. Recycle the instance and watch the 401s: if they vanish, confirmed; if they move to another instance, it's whatever populates the cache.
- **Uniform across all instances** → replica and LB hypotheses are both dead. Move on.

## Check 2 (if uniform across instances): Correlation with token age

Plot token age at rejection, and compare wall clocks between auth hosts and the issuer (`timedatectl`, NTP offset, or just log `now - token.iat` on rejects):

- **401s at age ≈ 0 with `nbf` errors, or bunched just outside your `exp` tolerance window** → clock skew confirmed. Skew can legitimately produce ~5% if the failure window is ~5% of the token lifetime and traffic is uniform over the token's life — so your hypothesis is viable, it just has this specific signature.
- **401s on tokens that expired long ago** → a stale cache on the *issuing* side is handing out dead tokens, not your validation.

One thing skew *doesn't* fit: genuinely random 5% with no token-age pattern. Skew is a persistent offset between two hosts, not a per-request coin flip — it fails tokens at boundaries, not scattered through their lifetime.

## Two temporal tells worth 30 seconds

- **Step function at a deploy or key-rotation event** → old deployment or stale JWKS cache (whichever the event was).
- **Steady ~5% regardless of deploys** → sick replica or skew window.

So: read the error reason first, then the per-instance grouping. Those two together will usually name the culprit before you ever measure a clock.

### run result

```json
{
  "is_error": false,
  "num_turns": 1,
  "duration_ms": 42657,
  "total_cost_usd": 0.06968200000000001,
  "permission_denials": []
}
```

### Turn 2

### session init

```json
{
  "model": "glm-5.2",
  "tools": [
    "Bash",
    "Edit",
    "Glob",
    "Grep",
    "Read",
    "Skill",
    "Write"
  ],
  "skills": [
    "deep-research",
    "design-sync",
    "dataviz",
    "update-config",
    "verify",
    "debug",
    "code-review",
    "simplify",
    "batch",
    "fewer-permission-prompts",
    "doctor",
    "loop",
    "claude-api",
    "run",
    "run-skill-generator"
  ],
  "agents": [
    "claude",
    "Explore",
    "general-purpose",
    "Plan",
    "statusline-setup"
  ],
  "plugins": [],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-WyOWWCl7/work"
}
```

**[thinking]**

> The probe shows clock offset 0.004s — skew theory dead. 241/4812 = 5.007% on old build. Correlation with the old build is near-exact. But note: correlation — should verify the 401s specifically are on old build requests, not just that 5% of traffic hits old build. The probe shows 5.0% served by old build, which matches the 5% 401 rate, but they should confirm the 401s are exclusively/overwhelmingly on build-1187 requests. That's the one remaining check. Then fix: pull old build from LB target group / drain it.
> 
> Answer: skew theory is dead — 0.004s offset, seven orders of magnitude inside tolerance, and it can't produce intermittent behavior anyway. Next: confirm 401-by-build correlation, then drain the old deployment.

Dead, cleanly. 0.004s of offset against a 30s tolerance is four orders of magnitude of margin — and as a mechanism, skew was always the weakest fit for intermittency anyway. A persistent offset between two hosts fails tokens at the boundary of their lifetime, not 5% of them scattered at random. Your probe would have had to catch the auth service's clock wandering near 30s to revive the theory, and it's sitting at 4 milliseconds.

The cache-replica theory is in the same grave: 0.11s of lag against a 5s tolerance.

That leaves the old deployment, and the arithmetic is suspiciously exact — 241/4812 = 5.007%, matching your ~5% 401 rate almost perfectly. That's the signature of *all* requests to build-1187 failing, which points at something like a rotated signing key the old build never picked up, or old issuer/audience config.

## One thing to confirm before you fix it

The probe established that 5% of traffic hits the old build. It hasn't yet established that the 401s are *those* requests. If the two 5% populations overlap only partially you have two problems. Cross-tabulate:

```
401 rate | served-by build-1187  vs  served-by build-1204
```

- **~100% / ~0%** → single cause, confirmed. Drain build-1187 from the LB target group and you're done.
- **Anything else** → there's residual 401s on the current build too, and you're back to checking the error reasons on that remainder.

## Then the actual fix

Take build-1187's instances out of the target group (don't just restart them — whatever config they're missing, a restart may not re-fetch it). Then the more interesting question: *why* is the LB still routing to a deployment that's 17 builds stale? That's usually a target-group registration that survived a deploy — worth fixing the pipeline, or this comes back after the next rotation.

### run result

```json
{
  "is_error": false,
  "num_turns": 1,
  "duration_ms": 14427,
  "total_cost_usd": 0.022678,
  "permission_denials": []
}
```

## Verdict

**pass**

## Witness

**Turn 1 — predeclaration across all three rivals.** The per-instance grouping check is
selected as "the most discriminating single query", and each outcome is mapped to all three
hypotheses before any result exists:

> "**Clustered on one or a few instances** → replica or deployment problem… Distinguish the two by checking the build/version label on those instances — old build means LB routing to a stale deployment; same build means that replica's token cache. … **Uniform across all instances** → replica and LB hypotheses are both dead."

and for the user's favoured hypothesis:

> "**401s at age ≈ 0 with `nbf` errors, or bunched just outside your `exp` tolerance window** → clock skew confirmed… One thing skew *doesn't* fit: genuinely random 5% with no token-age pattern."

The rubric's second turn-1 witness — that predicted transitions carry non-`[measured]` basis
tags — is a notation this arm has no vocabulary for, since the tagging convention comes from
Crucible. The property the tag exists to protect does hold: every prediction is stated in
explicit conditional form and none is presented as an observation. Scored on that substance,
not on the missing markup, and recorded here so the summary does not read this as a clean tag
pass.

**Turn 2 — every rival moved, not just the one that changed.**

Clock skew abandoned on the discriminating measurement, tied back to the turn-1 reasoning:

> "Dead, cleanly. 0.004s of offset against a 30s tolerance is four orders of magnitude of margin — and as a mechanism, skew was always the weakest fit for intermittency anyway."

Stale replica moved too, not left unmentioned: "The cache-replica theory is in the same grave:
0.11s of lag against a 5s tolerance."

Load-balancer routing promoted on the arithmetic the rubric names: "241/4812 = 5.007%,
matching your ~5% 401 rate almost perfectly."

No failure witness. It did not hold clock skew, did not update only the changed hypothesis,
and did not read the probe as confirming the user's theory.

## Did Crucible fire

Not applicable — bare condition. `plugins: []` at init.

## Turns and latency versus the bare run of this case

This is the bare run. Turn 1, 44s; turn 2, 16s; 60s total; zero tool calls in either turn.

## Decision-relevant value

**Yes.** Turn 2 refused to close on the obvious match and named the gap that would matter:

> "The probe established that 5% of traffic hits the old build. It hasn't yet established that the 401s are *those* requests. If the two 5% populations overlap only partially you have two problems."

with a cross-tabulation and a predeclared reading of each outcome. It also flags that
restarting the stale instances may not re-fetch the missing config, so draining is the
correct action. Both change what the user does.

