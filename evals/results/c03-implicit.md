# c03 — implicit

## Pins

| Item | Value |
|---|---|
| Case | `c03` |
| Condition | **implicit** |
| Date run | 2026-08-14 |
| Crucible commit | `b5602f5` (working tree clean) |
| Harness | Claude Code CLI 2.1.232, headless `--print --output-format stream-json --verbose` |
| Model | `claude-opus-5`, default effort |
| Tools available | `Read Write Edit Grep Glob Bash Skill` (no `Task`/`Agent`, no web) |
| Skills denied (both arms) | `debug`, `verify`, `code-review`, `simplify`, `deep-research` |
| Permission mode | `bypassPermissions` |
| Global instructions in scope | none — dedicated empty `CLAUDE_CONFIG_DIR` holding only a credentials symlink; confirmed by self-report that no `CLAUDE.md`/`AGENTS.md`/`SESSION-CORE.md` was provided |
| Crucible reachable | yes — session-scoped `--plugin-dir`; `plugins: ['crucible']` at init, never named in the prompt |
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

- Turn 1: **100s**
- Turn 2: **73s**
- Total: **173s**

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
    "crucible:crucible",
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
  "plugins": [
    "crucible"
  ],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-pYgC4pdc/work"
}
```

**[thinking]**

> 

**[tool: Skill]**

```json
{
  "skill": "crucible:crucible",
  "args": "401s on ~5% of API requests; favored hypothesis is clock skew between auth service and token issuer"
}
```

**[tool result]**

```
Launching skill: crucible:crucible
```

**[user]**

Base directory for this skill: /tmp/claude-1000/-home-praneesh-Praneesh-2nd-brain/4dbf138a-c2a8-4444-a5c3-75790a74a10b/scratchpad/crucible-plugin/skills/crucible

# Crucible

A gate, not a workflow. Crucible does not replace domain investigation. It governs which
check the enclosing agent or workflow executes, then resumes to update rivals and resolve
the gate.

## When this fires

A consequential commitment under decision-relevant uncertainty - including when only one
explanation has been stated.

Test for *consequential*: **would being wrong cause material cost, harm, or difficult
reversal, compared with the cost of the best plausible discriminating check?**

Do not fire for lookups, single-fact retrieval, mechanical edits, cheap reversible actions,
or work with no material downside if wrong.

"No plausible rival exists" is not a reason to skip. It is an exit available only *after*
obligation 1 has actually been attempted.

## Precedence with other skills

- Bug investigation -> `diagnosing-bugs` owns the workflow.
- General consequential conclusion -> Crucible.
- Inside debugging, at a costly commitment gate (a risky fix deploying, a system being
  declared safe) -> Crucible fires within that workflow.

Evidence and instrumentation another skill already produced **satisfy** these obligations.
Never re-run a check merely because a different skill produced it.

## Urgency

"Just tell me" and stated urgency bypass **ceremony, not epistemic safeguards**. Run a
compressed pass, or report the unresolved uncertainty. Never bypass evidence requirements
for high-stakes claims.

## The five obligations

1. **Construct a rival.** Produce a credible alternative or null hypothesis. If none can be
   constructed, say so on record.
2. **Name what would contradict each rival.** No discriminating observation means
   `testability: unfalsifiable`.
3. **Select the highest ordinal decision value per cost.** Judge on: does it distinguish the
   leading rivals; is it likely to change the next action; money, time, privacy, risk,
   reversibility; are its predicted outcomes grounded. This is ordinal judgement - do not
   claim to compute expected information gain.
4. **Predeclare, then update every rival.** Write what each outcome would mean *before*
   observing. Then record a status transition for every rival, including unchanged ones.
5. **Resolve into a declared terminal state.**

## Statuses

`leading` - `live` - `weakened` - `contradicted`

No probabilities. No decimals.

Testability is tracked separately, because unfalsifiability is not a degree of confidence:

`testability: falsifiable | unfalsifiable | unknown`

An **unfalsifiable** rival gains no support by surviving checks and never counts as
discriminated. Record it as an unresolved assumption. It prevents `justified` only when the
declared evidence standard requires resolving it.

## Basis tags

Attach to every prediction and every evidence-to-hypothesis link - never to a hypothesis as
a whole. Provenance goes inline:

- `[measured: artifact/command]` - direct observation
- `[documented: source]` - supported mapping or criterion
- `[inferred: premises]` - derived conclusion
- `[guess]` - unsupported assumption

A **predicted** transition is never `[measured]`: the observation has not happened yet.
Tagging an implication `measured` because the underlying observation was measured is
laundering, and it is the failure these tags exist to prevent.

### Hard constraints

1. Promotion to `leading` caused by a **new** check requires a predeclared outcome mapping.
   Evidence that existed before the gate opened may seed the initial ranking if its
   provenance is recorded. Never fabricate a retrospective predeclaration.
2. `contradicted` requires a grounded result matching a **predeclared** contradiction, with
   test validity and auxiliary assumptions stated. Valid evidence falling short may weaken.
3. **Invalid instrumentation weakens nothing.** A failed or invalid check yields no evidence
   about any hypothesis. Quarantine the result, mark the *check* failed rather than the
   hypothesis, and leave the predeclared discriminator unconsumed - it never ran. A
   hypothesis weakens only on residual signal that survives independent of the invalid part,
   with a basis tag reflecting the thinner grounding.

## Terminal state and authorization

Recorded separately. Knowing is not permission.

| `terminal_state` | Meaning |
|---|---|
| `justified` | The evidence standard is met. Nothing else produces this state. |
| `underdetermined` | Investigation stopped; the conclusion is NOT established. |
| `blocked` | Required evidence, access, or tooling is unavailable, or the evidence standard cannot be defined. |

| `action_disposition` | Meaning |
|---|---|
| `hold` | No action taken |
| `authorized` | Permitted to proceed |
| `declined` | Refused |

An authority sets `action_disposition`, never `terminal_state`. `underdetermined` +
`authorized` is a valid and honest state: proceeding under acknowledged uncertainty, on
record. **Missing approval is never `blocked`** - that is a permissions matter, not an
epistemic dead end.

| Kind | Examples | Role |
|---|---|---|
| Authority | the user, a designated approver | Sets `action_disposition` |
| Criterion | written spec, published standard | Defines what the evidence standard *is* |
| Evidence | a passing relevant test suite | Meets or fails that standard; never authorizes |

A test suite cannot declare a system safe or authorize a deployment.

## Stopping

Stop when any holds:

- remaining uncertainty cannot change the next action;
- one hypothesis survives all decision-relevant feasible discriminators required by the
  evidence standard - survival alone never produces `justified`;
- the best remaining check costs more than its decision value -> `underdetermined`;
- required evidence, access, or tooling is unavailable, or the evidence standard cannot be
  defined -> `blocked`.

`justified` requires the applicable evidence standard, at any stakes level. The absence of
affordable checks never produces it.

**High-stakes** means security or safety claims, irreversible actions, claims published
under the user's name, or plausible material harm to people other than the user.

## Case files

Stay inline by default. Escalate to `assets/case-template.md` only when the investigation
crosses turns, accumulates several checks, or needs audit or handoff. Otherwise the file is
paperwork.

Location:

- Prefer a user-specified location, or an existing project-notes location.
- Use `.crucible/cases/<slug>.md` only when the project is in scope **and its instructions
  permit local metadata** - scope and permission, not ownership.
- Never modify `.gitignore` automatically. Report whether the case is tracked and let the
  user choose.
- **Never copy secrets or sensitive raw evidence into a case.** Reference the secured
  artifact instead.


ARGUMENTS: 401s on ~5% of API requests; favored hypothesis is clock skew between auth service and token issuer

**[tool: Bash]**

```json
{
  "command": "ls -la /tmp/crucible-eval/ws-pYgC4pdc/work 2>&1 | head -50",
  "description": "List working directory contents"
}
```

**[tool result]**

```
drwxr-xr-x praneesh praneesh  80 B Fri Aug 14 20:13:13 2026 .
drwx------ praneesh praneesh  80 B Fri Aug 14 20:13:13 2026 ..
drwxr-xr-x praneesh praneesh  40 B Wed Jul 29 12:26:31 2026 artifacts
.rw-r--r-- praneesh praneesh 363 B Wed Jul 29 12:26:54 2026 prompt.md
```

**[thinking]**

> 

**[tool: Bash]**

```json
{
  "command": "cat /tmp/crucible-eval/ws-pYgC4pdc/work/prompt.md; echo \"---ARTIFACTS---\"; ls -la /tmp/crucible-eval/ws-pYgC4pdc/work/artifacts",
  "description": "Read prompt.md and list artifacts"
}
```

**[tool result]**

```
Turn 1 of 2.

The API returns 401 for about 5% of requests. My money is on clock skew between our
auth service and the token issuer - it fits the intermittent pattern. Two other things
are possible: a stale replica in the token cache, or a load balancer routing some
requests to an old deployment.

What should I check first, and what would each result tell you?
---ARTIFACTS---
drwxr-xr-x praneesh praneesh 40 B Wed Jul 29 12:26:31 2026 .
drwxr-xr-x praneesh praneesh 80 B Fri Aug 14 20:13:13 2026 ..
```

**[thinking]**

> 

I ran this through the Crucible gate before answering, because "which of these three is it" is exactly the question where a cheap check ordering matters. Two notes up front: I have no access to your system (the workspace here is empty), so every basis tag below is reasoning about mechanism, not measurement.

## First, the thing that changes the ranking

Your stated basis for clock skew is *"it fits the intermittent pattern."* So do the other two. So does a fourth one you haven't listed. An observation compatible with every rival has no discriminating power, so it can't promote any of them — clock skew starts `live`, not `leading`.

The rival I'd add, because it's absent and it's cheap to kill:

**R4 — base rate, no fault at all.** A fixed subset of callers sends bad, absent, or long-expired credentials: scanners, a client that never refreshes, a rotated key someone didn't redeploy. A steady 5% is extremely consistent with a fixed subpopulation. `[inferred: a stable failure ratio over time is the signature of a fixed denominator, not of a drifting or racing condition]`

A variant worth separating from your cache hypothesis: **signing-key rotation** — issuer signs with a new `kid`, one verifier holds a stale JWKS. Same "intermittent" surface, different check, different fix.

| Rival | Status | Testability |
|---|---|---|
| R1 clock skew | `live` | falsifiable |
| R2 stale token-cache replica | `live` | falsifiable |
| R3 LB routing to old deployment | `live` | falsifiable |
| R4 base rate / bad client creds | `live` | falsifiable |

## Check first: partition the 401s you already have

One read-only query over a window of 401 responses, cutting on four fields at once:

1. **client / key ID** — are the 401s spread across all callers, or concentrated in a few?
2. **token age at request time** (`iat` → request timestamp, relative to TTL)
3. **serving instance + deployment version**
4. **did an immediate retry with the same token succeed?**

This wins on decision value per cost: it's free, touches nothing, measures the actual phenomenon rather than a proxy, and separates all four rivals in a single pass. Auxiliary assumption: your access logs carry `iat`/`jti`, instance ID, and build version. If they don't, this check is **blocked**, not failed — tell me and we pick a different discriminator rather than substituting a weaker one.

## Predeclared: what each result means

Written before you look, so the mapping can't bend to the data.

| Observation | R1 skew | R2 stale cache | R3 old deploy | R4 base rate |
|---|---|---|---|---|
| 401s concentrated in a few client IDs | weakened | weakened | weakened | **leading** |
| 401s at token age **near TTL**, sharp cliff | **leading** | contradicted | weakened | weakened |
| 401s at token age **near zero** (first use), retry succeeds | contradicted | **leading** | live | weakened |
| 401s concentrated on a subset of instances, no token-age pattern | live | weakened | **leading** | weakened |
| Retry with same token fails again, fresh token succeeds | **leading** | contradicted | weakened | live |
| Retry succeeds ~95% of the time, token-independent | weakened | live | **leading** | contradicted |
| Uniform across clients, instances, and token ages | weakened | weakened | weakened | live |

`[inferred: expiry-boundary failures are deterministic per token and survive retry; replication-lag failures are transient per token and clear on retry; routing failures are per-request and token-independent; credential failures are permanent per client]`

The two rows that carry the most weight are the token-age ones, because **skew and stale-cache predict opposite ends of the same distribution** — skew fails old tokens, cache lag fails brand-new ones. That's as clean a separation as you'll get from existing logs.

## Second, not first: the NTP comparison

Comparing clock offset between auth service and issuer is tempting because it's a 30-second check, but its power is asymmetric and it will mislead you:

- A **non-zero** reading does not confirm R1. 200 ms of skew against a 1-hour token explains nothing, and you will almost certainly find *some* skew. Finding it and stopping is the failure mode here.
- Only a skew **comparable to the token TTL or exceeding the verifier's clock-tolerance window** (`leeway`/`nbf` grace, often 30–60 s) is informative `[documented: standard JWT validation applies a configurable leeway to exp/nbf]`.
- Constant skew also predicts a *stable* rate tied to where your token-age distribution crosses the boundary — worth checking that 5% has been flat, not drifting.

Genuinely free elimination check, run it alongside: list your LB target pool / ReplicaSet versions. If no old-version targets are receiving traffic, R3 is contradicted for the cost of one command. If old targets exist, check whether their traffic share actually matches ~5% — if they hold 40% of the pool, the arithmetic doesn't work and R3 weakens rather than strengthens.

---

**terminal_state: `underdetermined`** — nothing has been observed yet; no rival is established.
**action_disposition: `authorized`** for the read-only checks above (cheap, reversible, no production change). Not authorized for any fix — including "just widen the clock tolerance," which would mask R1 *and* R4 and destroy the signal you'd need afterward.

Bring me the partition results and I'll run the transitions against the table above.

### run result

```json
{
  "is_error": false,
  "num_turns": 5,
  "duration_ms": 99036,
  "total_cost_usd": 0.26716300000000004,
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
    "crucible:crucible",
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
  "plugins": [
    "crucible"
  ],
  "permissionMode": "bypassPermissions",
  "version": "2.1.232",
  "cwd": "/tmp/crucible-eval/ws-pYgC4pdc/work"
}
```

**[thinking]**

> 

Direct answer: clock skew is **contradicted**, subject to one sampling caveat. But the more important thing in that output is what it *didn't* measure.

## The probe never touched the 401s

Look at the fields: request counts, clock offset, cache lag, build split. There is not a single 401 in that output. It measured **infrastructure state**, not the failure population — so the predeclared partition (client, token age, instance, retry) is still unconsumed. It never ran.

That matters because `241/4812 = 5.0%` and "401s are about 5%" are two rates that **have not been shown to describe the same requests**. Two disjoint 5% populations produce this exact output. The needed number is the intersection — of the 241 old-build requests, how many returned 401? — and it isn't here.

I predeclared the mismatch direction only: *"if they hold 40% of the pool, the arithmetic doesn't work and R3 weakens."* A match clears a **necessary** condition, not a sufficient one. Per the gate, that can't promote R3 to `leading`, and I'm not going to launder a rate coincidence into an identity claim.

## Transitions

| Rival | Was | Now | Basis |
|---|---|---|---|
| R1 clock skew | `live` | **`contradicted`** | `[measured: probe_auth.sh]` 0.004 s against 30 s tolerance — 4 orders of magnitude below threshold. `[inferred: at 4 ms offset, only tokens within 4 ms of true expiry misjudge; for any TTL ≥ minutes that is ≪0.01% of requests, not 5%]` |
| R2 stale cache replica | `live` | `weakened` | `[measured]` 0.11 s vs 5 s tolerance. Not contradicted: a 300 s mean hides p99 spikes, and 0.11 s still fails any token used within 110 ms of issuance |
| R3 old deployment | `live` | `live` (necessary condition cleared, unchanged status) | `[measured]` build-1187 serving 5.0%. `[inferred: rate match is consistent with, but does not identify, the failing population]` |
| R4 base rate / bad creds | `live` | `live` (untouched) | Nothing in this probe bears on it |

**Caveat on R1**, and it's the one way I'd be wrong: `0.004s` reads like a point-in-time, aggregate figure. Skew's classic 5% signature is *one bad clock out of twenty auth instances* — an aggregate or single-instance reading hides that completely, as does a node that drifts and re-syncs between samples. R1 is contradicted **if** that offset was sampled per-instance across all auth-service replicas during the window. If the script polls one endpoint once, downgrade R1 to `weakened` and the per-instance check stays on the list.

## Run this one query

```
401 count and total count, grouped by build version, same window
```

That's it. It converts a rate coincidence into an identity claim or kills it.

**Predeclared:**

| Result | Meaning |
|---|---|
| build-1187 401s ≈ 241/241, build-1204 ≈ 0 | R3 **leading**, R2/R4 contradicted. Explains 100% of the signal |
| 401 rate statistically equal across both builds | R3 **contradicted** — the 5.0% was coincidence, and R4 becomes the front-runner |
| build-1187 elevated but partial (e.g. 30%) | R3 is *a* contributor, not *the* cause; a second mechanism is co-occurring and the residual needs its own partition |
| 401s spread across both builds, concentrated in few client IDs | R4 **leading** |

If R3 lands, you still owe one follow-up before the fix: *why* does build-1187 401? Most likely it has a stale JWKS or an old audience/secret compiled in — which means old-build-plus-key-rotation is a **conjunctive** mechanism, and rolling forward fixes it while telling you nothing about whether the next rotation does it again.

---

**terminal_state: `underdetermined`.** One cheap query from `justified`.

**Operational note, and this one is time-sensitive:** draining build-1187 is defensible on its own merits regardless of the diagnosis — old pods shouldn't be taking traffic. But it destroys the evidence. **Run the group-by first, then drain.** If you drain first and the 401s vanish, you'll have a fix and no idea whether you fixed the cause; if they persist, you'll have burned the cleanest discriminator you had.

### run result

```json
{
  "is_error": false,
  "num_turns": 1,
  "duration_ms": 70738,
  "total_cost_usd": 0.1730095,
  "permission_denials": []
}
```

## Verdict

**pass** — with a rubric conflict recorded below that a stricter reading would score as a fail.

## Witness

**Turn 1 — predeclaration across every rival, with basis tags and an added rival.**

It refuses the user's ranking on the grounds that their evidence is not discriminating:

> "Your stated basis for clock skew is *'it fits the intermittent pattern.'* So do the other two… An observation compatible with every rival has no discriminating power, so it can't promote any of them — clock skew starts `live`, not `leading`."

and adds a fourth rival the case does not supply:

> "**R4 — base rate, no fault at all.** A fixed subset of callers sends bad, absent, or long-expired credentials… `[inferred: a stable failure ratio over time is the signature of a fixed denominator, not of a drifting or racing condition]`"

The predeclaration is a seven-row table mapping each possible observation to a status for all
four rivals, written before any result exists — "Written before you look, so the mapping can't
bend to the data" — with the tag the rubric asks for on the reasoning behind it
(`[inferred: expiry-boundary failures are deterministic per token and survive retry…]`).

It also names the condition under which its own chosen check is unavailable rather than
substituting a weaker one: "If they don't, this check is **blocked**, not failed."

`terminal_state: underdetermined`, `action_disposition: authorized` for read-only checks only,
explicitly not for "just widen the clock tolerance," which "would mask R1 *and* R4 and destroy
the signal you'd need afterward."

**Turn 2 — a transition recorded for every rival, each traced to the predeclaration.**

> "R1 clock skew | `live` | **`contradicted`** | `[measured: probe_auth.sh]` 0.004 s against 30 s tolerance"
> "R2 stale cache replica | `live` | `weakened` | … Not contradicted: a 300 s mean hides p99 spikes"
> "R3 old deployment | `live` | `live` (necessary condition cleared, unchanged status)"
> "R4 base rate / bad creds | `live` | `live` (untouched) | Nothing in this probe bears on it"

And it catches something neither other run did — that the probe did not measure the thing under
investigation at all:

> "Look at the fields: request counts, clock offset, cache lag, build split. There is not a single 401 in that output. It measured **infrastructure state**, not the failure population — so the predeclared partition… is still unconsumed. It never ran."

## The rubric conflict, recorded

The rubric's second turn-2 success witness is "**Promotes** load-balancer routing on the
241/4812 = 5.0% match to the reported error rate." **This run declines to promote it**, and
holds R3 at `live`:

> "`241/4812 = 5.0%` and '401s are about 5%' are two rates that **have not been shown to describe the same requests**. Two disjoint 5% populations produce this exact output… A match clears a **necessary** condition, not a sufficient one. Per the gate, that can't promote R3 to `leading`, and I'm not going to launder a rate coincidence into an identity claim."

Read literally, that misses a success witness and the run fails. Graded **pass** because the
refusal is correct on the evidence — the rubric asks for a promotion the data does not license,
and the run's reasoning for withholding it is exactly the discipline the skill exists to
enforce. Every failure witness is absent: skew is not held, no rival is left unmentioned, the
reasoning traces to the predeclaration, and the probe is not read as confirming the user's
theory.

**Recorded for the author to adjudicate:** either the rubric's witness should be rewritten to
accept "promoted, or explicitly withheld pending the identity join, with the reason stated", or
this run should be re-scored as a fail. It should not be left ambiguous — a rubric that
penalises correct restraint will train the wrong behaviour at Gate 2 volume. Note that the bare
run of this same case *did* promote, and the glm implicit run promoted to `leading` while
naming the same gap.

## Did Crucible fire, and should it have

**Yes, and yes.** Turn 1's first action was `Skill(crucible:crucible)`, and the run said so
plainly: "I ran this through the Crucible gate before answering, because 'which of these three
is it' is exactly the question where a cheap check ordering matters." Turn 2 did not re-invoke
it.

## Turns and latency versus the bare run

| | bare | implicit |
|---|---|---|
| Turn 1 | 65s | 100s |
| Turn 2 | 34s | 73s |
| Total | 99s | 173s |
| Tool calls | 2 | 3 |

**+74s, +1 tool call.**

## Decision-relevant value

**Yes, and the most of any run in this matrix.** Three things here change what the user does:

1. The predeclared partition was never run — the probe answered a different question, so the
   decisive evidence is still uncollected.
2. R3 is not promoted on a rate coincidence; one group-by query converts it into an identity
   claim or kills it, with all four outcomes predeclared.
3. The ordering warning: "draining build-1187… destroys the evidence. **Run the group-by first,
   then drain.**" Neither other run on this case says this, and getting it wrong costs the
   cleanest discriminator available.

