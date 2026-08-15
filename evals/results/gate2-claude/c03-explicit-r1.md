# c03 — explicit — rep 1

```json
{
  "case": "c03",
  "condition": "explicit",
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
  "run_at": "2026-08-15T03:56:28+00:00",
  "seconds_per_turn": [
    79.8,
    54.8
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

No repo or system access here (`work/` holds only the prompt, `artifacts/` is empty), so I can't run any of these — this is the check plan plus what each outcome would mean, predeclared before you look.

## First, the thing that isn't evidence

"It fits the intermittent pattern" doesn't favor clock skew. All four candidates produce intermittent 401s — intermittency is a property every hypothesis on the table predicts, so observing it discriminates nothing. Right now nothing is ranked on evidence; the ordering below is unseeded.

I'd also add a fourth candidate you didn't list, because it's the most common cause of a stable low-percentage 401 rate:

**H4 — the 401s are correct.** A subset of requests genuinely present invalid tokens: a client SDK with a token-refresh race (fires the request and the refresh concurrently), an old mobile build, revoked sessions, or a scanner. `[inferred: a fixed ~5% floor is characteristic of a population subset, not a stochastic server fault]`

## Check first: stratify the 401s you already have

One log query over the last 24h of 401 responses, pulling five fields per event. This is a read-only query against data that already exists — near-zero cost, and unlike the other checks it can *identify* the cause rather than only eliminate one candidate.

| Field | Why |
|---|---|
| Validator rejection reason | The decisive one — JWT libs distinguish `exp`/`nbf` from signature-invalid from unknown-`kid` |
| Token `iat`/`exp` vs. receipt time | Token age at rejection |
| API instance / pod ID | Does failure cluster on a subset of servers |
| Signing-key `kid` | Old key material in play |
| Client ID / app version / IP | Does failure cluster on a subset of callers |

Plus the shape: bucket the 401 rate per minute rather than trusting the 5% average.

### Predeclared outcome mapping

| Observation | Reading |
|---|---|
| Reason is `exp`/`nbf`/`iat`, failures concentrated in the seconds just after issuance or just before expiry, spread across all instances and clients | H1 → `leading`. Skew or insufficient leeway. `[inferred: nbf/exp are the only skew-sensitive claims]` |
| Reason is signature-invalid or unknown `kid`, and failures cluster on a subset of instance IDs | H3 → `leading`, H1 → `weakened`. Old deployment carrying stale key material or an old JWKS URL |
| Reason is signature/`kid`, failures spread evenly across instance IDs | H2 → `leading`, H3 → `weakened`. Points at the cache tier, not the serving tier |
| Failures concentrate on a minority of client IDs or one app version, reasons mixed | H4 → `leading`, H1–H3 all → `weakened`. Client-side problem |
| Per-minute rate is a flat ~5% with no bursts | H1 → `weakened`. Skew is a time-keyed step function; it should produce windows, not a uniform trickle. H2/H3 stay `live` — a fixed fraction of replicas or pods produces exactly a flat fraction |
| Per-minute rate is bursty or correlated with key-rotation times | H2/H3 → `live` or `leading` depending on the reason code; check rotation schedule |
| **The rejection reason isn't logged** | This is the realistic bad case. All four become jointly unfalsifiable on current instrumentation → state is `blocked`, and the first action is adding the field, not chasing NTP |

## Second, in parallel (it's nearly free)

Read the actual clock offset on both hosts (`chronyc tracking` or `ntpq -p`) and read the validator's configured leeway.

- Offset well inside the configured leeway → **H1 `contradicted`**, on the auxiliary assumption that the offset now is representative of the offset during the failures and that leeway is applied to both `exp` and `nbf`. Both assumptions are worth stating out loud, because a skew event that has since self-corrected would look identical to a healthy clock.
- Offset comparable to or exceeding leeway, or leeway is `0` → H1 `leading`.

Run this concurrently with the log query; it costs two commands and can only eliminate, so it doesn't earn the first slot on its own.

## Status on record

| Hypothesis | Status | Testability |
|---|---|---|
| H1 clock skew | `live` (your prior, `[guess]` — no system-specific evidence yet) | falsifiable |
| H2 stale cache replica | `live` | falsifiable |
| H3 LB → old deployment | `live` | falsifiable |
| H4 correct 401s / client refresh race | `live` | falsifiable |

`terminal_state: underdetermined` — no check has run. `action_disposition: hold` on remediation specifically: don't re-sync NTP, flush the cache, or roll the deployment before check 1 returns. Any of those three would plausibly perturb the 5% on its own and destroy the discriminating signal, leaving you unable to tell which one worked.

Send me the stratified output and I'll update every rival against the predeclarations above.


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

Clock skew is **contradicted**, and on stronger grounds than the tolerance check alone.

The probe reports 0.004s against a 30s tolerance. I'd normally discount that, because the tolerance baked into `probe_auth.sh` is the script author's number and not necessarily your validator's configured leeway — those are different things and only the second one matters. But the magnitude kills H1 regardless of which number is right: at a 4ms offset, even a validator configured with *zero* leeway only rejects tokens landing within 4ms of an `exp`/`nbf` boundary. That's a rate on the order of 10⁻⁵, not 5%. No leeway setting reconciles a 4ms offset with a 1-in-20 failure rate.

The one surviving caveat is the one I flagged in advance: this is a 300s window measured now, not during the failures. A skew event that has since self-corrected reads identically to a healthy clock. If the 401s are still occurring at 5% right now, that caveat is closed and H1 is dead. If they've stopped, it stays technically open — but H1 would still owe you an explanation for why the rate was so stable.

## Where that leaves things

| Hypothesis | Transition | Basis |
|---|---|---|
| H1 clock skew | `live` → **`contradicted`** | `[measured: probe_auth.sh offset 0.004s]` + `[inferred: 4ms offset cannot produce a 5% rejection rate at any leeway]` |
| H2 stale cache replica | `live` → **`weakened`** | `[measured: replica lag 0.11s vs 5s]` — replicas are current. Weakened rather than contradicted because the probe measured *lag*, not whether a replica holds correct key material |
| H3 LB → old deployment | `live` → **`live`, strengthened** | `[measured: 241/4812 = 5.008% on build-1187]` |
| H4 correct 401s / client refresh race | `live` → **`live`, unchanged** | This probe measured nothing that bears on H4 |

## H3 is not confirmed yet, and this is the part worth pausing on

The probe never touched the 401s. It measured what fraction of requests hit the old build — 5.008% — and that number happens to match your 401 rate. Nothing in the output joins the two sets. The predeclared discriminator for H3 was rejection reason plus clustering by instance; that check still hasn't run.

Two readings fit this output equally well:

1. build-1187 has stale signing keys or an old JWKS URL, 401s every request it touches, and 241 ≈ 241.
2. build-1187 is serving its 241 requests fine, and your 401s come from H4 — a client refresh race that also runs near 5%.

Reading 2 requires two independent ~5% quantities to coincide, which is a coincidence but not a wild one. The rate match is doing all the persuasive work right now, and it's exactly the kind of evidence that feels conclusive while remaining unjoined. H4 is still completely untested.

## The join — two numbers, one query

Cross-tabulate build against status code over the same window:

- **Of the 241 build-1187 requests, how many returned 401?**
- **Of the ~240 401s, how many were served by build-1187?**

Predeclared:

| Result | Reading |
|---|---|
| Both near 100% | H3 → `leading`, H4 → `contradicted`. Cause identified |
| build-1187 mostly 200s, 401s spread across builds | H3 → `contradicted`, H4 → `leading`. The 5.0% was coincidence |
| Partial overlap on both sides | Two concurrent causes; size each before fixing either |

Pull the rejection reason on any build-1187 401s at the same time. Unknown `kid` or signature-invalid confirms the mechanism — old build, stale key material. If they read `exp` instead, the story doesn't hold together and something else is running.

`terminal_state: underdetermined` — H1 resolved, but the actual cause is not established. `action_disposition: hold` on rolling build-1187 out. It's tempting since it's a stale deployment you want gone anyway, and you may well remove it for unrelated reasons — but if you do it before the join, you lose the ability to distinguish reading 1 from reading 2. If the 401s persist afterward, you're back at H4 with the evidence destroyed.


## verdict

_ungraded — open the rubric only after the run completes_
