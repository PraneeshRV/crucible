# c03 — bare

## Pins

| Item | Value |
|---|---|
| Case | `c03` |
| Condition | **bare** |
| Date run | 2026-08-14 |
| Crucible commit | `b5602f5` (working tree clean) |
| Harness | Claude Code CLI 2.1.232, headless `--print --output-format stream-json --verbose` |
| Model | `claude-opus-5`, default effort |
| Tools available | `Read Write Edit Grep Glob Bash Skill` (no `Task`/`Agent`, no web) |
| Skills denied (both arms) | `debug`, `verify`, `code-review`, `simplify`, `deep-research` |
| Permission mode | `bypassPermissions` |
| Global instructions in scope | none — dedicated empty `CLAUDE_CONFIG_DIR` holding only a credentials symlink; confirmed by self-report that no `CLAUDE.md`/`AGENTS.md`/`SESSION-CORE.md` was provided |
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

- Turn 1: **65s**
- Turn 2: **34s**
- Total: **99s**

## Transcript

### Turn 1

### session init

```json
{
  "model": "claude-opus-5",
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
    "design-sync",
    "dataviz",
    "artifact-design",
    "artifact-diagramming",
    "artifact-capabilities",
    "update-config",
    "verify",
    "debug",
    "code-review",
    "simplify",
    "batch",
    "fewer-permission-prompts",
    "doctor",
    "loop",
    "schedule",
    "claude-api",
    "run",
    "run-skill-generator"
  ],
  "agents": [
    "claude",
    "claude-code-guide",
    "Explore",
    "general-purpose",
    "Plan",
    "statusline-setup"
  ],
  "plugins": [],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-8qK2neDe/work"
}
```

**[thinking]**

> 

**[tool: Bash]**

```json
{
  "command": "ls -la /tmp/crucible-eval/ws-8qK2neDe/work 2>&1 | head -30",
  "description": "List working directory contents"
}
```

**[tool result]**

```
drwxr-xr-x praneesh praneesh  80 B Fri Aug 14 20:11:34 2026 .
drwx------ praneesh praneesh  80 B Fri Aug 14 20:11:34 2026 ..
drwxr-xr-x praneesh praneesh  40 B Wed Jul 29 12:26:31 2026 artifacts
.rw-r--r-- praneesh praneesh 363 B Wed Jul 29 12:26:54 2026 prompt.md
```

**[thinking]**

> 

**[tool: Read]**

```json
{
  "file_path": "/tmp/crucible-eval/ws-8qK2neDe/work/prompt.md"
}
```

**[tool result]**

```
1	Turn 1 of 2.
2	
3	The API returns 401 for about 5% of requests. My money is on clock skew between our
4	auth service and the token issuer - it fits the intermittent pattern. Two other things
5	are possible: a stale replica in the token cache, or a load balancer routing some
6	requests to an old deployment.
7	
8	What should I check first, and what would each result tell you?
9
```

**[thinking]**

> 

No codebase here to inspect, so this is reasoning from the failure signature.

## Start by doubting clock skew

A steady ~5% is the wrong *shape* for skew. Skew is a drift process: the offset grows, stays under your validator's leeway (usually 30–60s) so failures are zero, then crosses it and failures climb toward 100%. It doesn't park at 5%. What parks at 5% is a partition — 1 bad instance out of ~20, or one cache replica out of a set, serving a fixed share of round-robin traffic. 5% ≈ 1/20 is suspiciously clean.

So the first question to answer isn't "is the clock wrong," it's **"are the 401s spread across all servers or concentrated on a few?"**

## First check: group the 401s by server identity

One query over the last hour, partitioning failures by auth-service instance, token-issuer instance, deployment version / build SHA, and the signing-key `kid` if your tokens carry one. Then compare per-instance failure rates.

- **Concentrated on a subset of instances or one build SHA, near-zero elsewhere** → routing or replica. Which one depends on the tier: bad instances in the API/auth tier means the load balancer is still feeding an old deployment; bad instances in the cache tier means the stale replica. This is the outcome I'd bet on.
- **Evenly smeared across every instance at ~5% each** → it's not a partition. Now skew or a token-lifetime issue is genuinely live, and the next two checks matter.
- **Concentrated by client or by token rather than by server** → none of your three. One caller has a bad credential and their traffic is simply 5% of the total.

Worth knowing before you run it: how many replicas are in each tier? If auth-service is 20 pods, one bad pod is exactly your number. If it's 3 pods, "one bad pod" would be 33% and the partition theory needs a different denominator.

## Second check: the rejection reason, not the status code

Run this in parallel — the three hypotheses leave different fingerprints in the validator logs:

- `token expired` / `nbf` in the future → skew or lifetime
- `signature verification failed` / unknown `kid` → stale key material, i.e. a cache replica or old deployment holding an outdated JWKS
- `token not found` / `revoked` → cache replica

If you're only logging the 401 and not the reason, fixing that is the highest-value ten minutes in this whole investigation.

## Third check: token age at the moment of rejection

Log `iat`/`exp` against receipt time for the failures. Skew concentrates rejections at the *edges* of token lifetime — a spike just after issuance (`nbf`) or just before expiry. If failing tokens' ages are uniformly distributed across the lifetime, skew is dead regardless of what the clocks say.

## The 30-second direct test of your hypothesis

`chronyc tracking` or `timedatectl show-timesync` on both fleets. Millisecond offsets against a 30–60s leeway means skew can't be the cause. Caveat: that measures *now*, so pair it with historical clock-offset metrics if you have them — a transient sync failure that's since recovered wouldn't show up.

One more cheap signal that separates drift from partition on its own: plot the 401 rate over time. Flat at 5% is structural. Bursty, or trending upward, points back toward your original theory.

### run result

```json
{
  "is_error": false,
  "num_turns": 3,
  "duration_ms": 62730,
  "total_cost_usd": 0.18858650000000002,
  "permission_denials": []
}
```

### Turn 2

### session init

```json
{
  "model": "claude-opus-5",
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
    "design-sync",
    "dataviz",
    "artifact-design",
    "artifact-diagramming",
    "artifact-capabilities",
    "update-config",
    "verify",
    "debug",
    "code-review",
    "simplify",
    "batch",
    "fewer-permission-prompts",
    "doctor",
    "loop",
    "schedule",
    "claude-api",
    "run",
    "run-skill-generator"
  ],
  "agents": [
    "claude",
    "claude-code-guide",
    "Explore",
    "general-purpose",
    "Plan",
    "statusline-setup"
  ],
  "plugins": [],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-8qK2neDe/work"
}
```

**[thinking]**

> 

Dead. Not "unlikely" — ruled out.

The offset is 0.004s against a 30s tolerance. That's nearly four orders of magnitude of headroom. There is no version of clock skew that produces a 401 at that offset, because the validator's leeway swallows it entirely. Same for the cache replica: 0.11s lag against a 5s tolerance, also not close.

And 241/4812 = 5.008%, which lands on your observed 401 rate. That's the partition signature — a fixed slice of round-robin traffic hitting instances that behave differently, exactly what a flat 5% predicted.

## One thing to confirm before you act on it

Matching *rates* isn't the same as matching *requests*. Right now you know two things are 5%; you don't yet know they're the same 5%. Join the 401s to build-1187 by request ID (or trace ID, or source instance) and check the overlap.

- **Near-total overlap** → confirmed, go fix the rollout.
- **Little or no overlap** → you have two separate 5% phenomena, build-1187 is serving fine, and the real cause is still open. Unlikely, but it's a cheap check and the failure mode of skipping it is chasing the wrong fix for a day.

## Then two separate questions

**Why does build-1187 reject tokens?** Most likely a signing key rotated in the 1187→1204 window and the old build is validating against a JWKS it no longer has, or an issuer/audience config change. The validator's error reason will say which — `unknown kid` or `signature verification failed` points at key material. This is worth knowing even after you fix the routing, because it tells you whether any other old artifact in your fleet is a landmine.

**Why is the load balancer still routing to it?** A rollout that reported success but left pods behind — an old ReplicaSet that never scaled down, instances still registered in the target group, or a deploy that partially failed and got marked complete. Removing those instances stops the bleeding in minutes. Finding out why they survived the deploy is what keeps it from recurring on build-1205.

Your instinct that "intermittent" implies "timing" is the trap worth naming: intermittent-but-*stable-rate* means a partition, and intermittent-and-*drifting* means timing. The rate curve tells you which before you touch a single clock.

### run result

```json
{
  "is_error": false,
  "num_turns": 1,
  "duration_ms": 32059,
  "total_cost_usd": 0.0629,
  "permission_denials": []
}
```

## Verdict

**pass**

## Witness

**Turn 1 — predeclaration across all three rivals.** It opens by attacking the *shape* of the
user's hypothesis rather than its plausibility:

> "A steady ~5% is the wrong *shape* for skew. Skew is a drift process: the offset grows, stays under your validator's leeway… then crosses it and failures climb toward 100%. It doesn't park at 5%. What parks at 5% is a partition — 1 bad instance out of ~20."

The chosen check is the server-identity partition, with every outcome mapped in advance:

> "**Concentrated on a subset of instances or one build SHA** → routing or replica… **Evenly smeared across every instance at ~5% each** → it's not a partition. Now skew or a token-lifetime issue is genuinely live… **Concentrated by client or by token rather than by server** → none of your three."

It also names the denominator assumption that would break its own reasoning: "If it's 3 pods,
'one bad pod' would be 33% and the partition theory needs a different denominator." As in the
glm arm, the rubric's basis-tag witness is notation this arm has no vocabulary for; every
prediction is stated conditionally and none is presented as an observation.

**Turn 2 — all three rivals moved.**

> "Dead. Not 'unlikely' — ruled out. The offset is 0.004s against a 30s tolerance… Same for the cache replica: 0.11s lag against a 5s tolerance, also not close."

> "241/4812 = 5.008%, which lands on your observed 401 rate. That's the partition signature… exactly what a flat 5% predicted."

The promotion traces directly to turn 1's predeclaration, and it names the trap in the user's
own reasoning: "intermittent-but-*stable-rate* means a partition, and intermittent-and-*drifting*
means timing."

No failure witness.

## Did Crucible fire

Not applicable — bare condition.

## Turns and latency

Turn 1, 65s; turn 2, 34s; 99s total; 2 tool calls (both in turn 1, both no-ops against an
empty workspace).

## Decision-relevant value

**Yes.** Turn 2 refuses to act on the rate match alone — "Matching *rates* isn't the same as
matching *requests*… you don't yet know they're the same 5%" — with a join and a predeclared
reading of each outcome. It then splits the fix into two separate questions: why build-1187
rejects tokens (key rotation, which tells you whether other stale artifacts are landmines) and
why the load balancer still routes to it.

