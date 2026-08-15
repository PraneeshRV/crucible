# c03 — implicit — rep 3

```json
{
  "case": "c03",
  "condition": "implicit",
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
  "run_at": "2026-08-15T03:55:36+00:00",
  "seconds_per_turn": [
    105.2,
    90.2
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

## First, a correction to the reasoning that got you to clock skew

"It's intermittent, so it fits clock skew" isn't discriminating — **all three of your hypotheses produce intermittent 401s**, as does a fourth you haven't named. Intermittency has near-zero diagnostic value here, so it shouldn't be ranking skew first.

Two things that *are* informative, and cut against skew:

- **A steady ~5% looks like a fixed ratio, not a timing fault.** Clock offset drifts and gets stepped by NTP corrections, so a skew-driven failure rate should wobble and jump around. A flat 5% looks like a fixed *partition* — 1 pod in 20, or a fixed set of clients. `[inferred: NTP correction behavior vs. traffic-share arithmetic]`
- **The skew arithmetic is demanding.** To fail 5% of requests, offset must exceed your validator's leeway *plus* ~5% of token lifetime. Most JWT libraries default to 30–60s leeway `[documented: common JWT library defaults — verify yours, it varies]`. So with 1-hour tokens you'd need ~3 minutes of skew; with 5-minute tokens, ~15s on top of leeway. Milliseconds of offset on NTP-synced hosts cannot produce 5%.

**Rival #4, which your framing excludes by construction:** the 401s are *correct*. A handful of clients genuinely lack valid credentials — an expired refresh token, a bad key in one client build, scanners hitting your endpoints. All three of your hypotheses are infrastructure faults; none allows that the requests deserved the 401. This is the most common cause of a stable low-percentage 401 rate.

## Rivals

| # | Hypothesis | Status | Testability |
|---|---|---|---|
| A | Clock skew, auth service ↔ issuer | `live` | falsifiable |
| B | Stale token-cache replica | `live` | falsifiable |
| C | LB routing to old deployment | `live` | falsifiable |
| D | 401s are correct — bad client credentials | `live` | falsifiable |

None is `leading`. Your prior evidence doesn't separate them.

## Check first: one query, don't touch NTP yet

Over ~24h of auth-service logs, break down the 401s by four axes at once:

1. **Sub-reason code** (expired / signature invalid / unknown `kid` / no credentials / audience mismatch)
2. **Client or principal ID**
3. **Upstream host + build SHA** that served the request
4. **Token age at rejection** (`now − iat`)

Each hypothesis predicts concentration on a *different* axis, which is why this one query beats any single-hypothesis check on decision value per cost.

**Predeclared mapping — written before you look:**

| Observation | Meaning |
|---|---|
| 401s spread thin across *all* clients, concentrated in tokens near `iat` or near expiry; reason = expired/`nbf` in future | A → `leading` |
| 401s concentrate on tokens issued within the last few seconds; same token succeeds on retry moments later | B → `leading`, A → `weakened` |
| 401 rate is **bimodal by host** — a few pods near 100%, rest at 0%; bad pods' traffic share ≈ 5%; reason = unknown `kid` or audience mismatch | C → `leading`, A and B → `weakened` |
| A small set of client IDs accounts for nearly all 401s, and *those clients fail ~100% of the time* | D → `leading`, A/B/C → `weakened` |
| Reason is dominated by "no credentials presented" / malformed | D → `leading`; this is not an infra fault at all |

The single sharpest signal: **infrastructure faults sprinkle failures across clients; bad credentials clump by principal.** Thin-and-even vs. few-clients-always-failing separates D from A/B/C immediately.

All of these are `[inferred: failure-mode signatures]` — predictions, not measurements. I have no access to your systems and have measured nothing.

## Then, the decisive check for whichever survives

- **A (skew):** `chronyc tracking` / `ntpq -p` on *every* auth-service and issuer host, plus your validator's configured leeway and token lifetime. Contradicted if measured offset < leeway. ⚠️ Predeclare now that you'll also pull **historical** NTP offset metrics — otherwise "it was skewed earlier and has since corrected" turns A unfalsifiable, and a hypothesis that can't be contradicted gains nothing by surviving.
- **C (old deployment):** pod build SHAs + 401 rate per pod. **Ask this first, it's free:** is there a canary or blue/green split running at ~5% weight right now? If yes, that reframes everything.
- **B (stale replica):** replay a rejected token seconds later. Success on retry confirms; failure contradicts.

## Gate state

```
terminal_state: underdetermined
action_disposition: hold
```

Nothing is established. Don't start adjusting NTP config — that's a change to a system you haven't yet shown is faulty, and it would destroy the historical offset evidence you need to test A.

Paste the four-axis breakdown back to me and I'll run the update against the mapping above.


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

## Where it leaves clock skew: strongly weakened, effectively dead

0.004s against a 30s tolerance isn't marginal — it's four orders of magnitude under. I predeclared "contradicted if measured offset < leeway," and that condition is met. I'm not going to defend A further.

Two caveats I flagged *in advance* (not invented now): the reading is a single scalar, and I'd asked for per-host offsets — one bad auth-service instance could hide behind a healthy aggregate. And the window is 300s, whereas the 401s are a standing complaint. But for skew to survive, you'd need one instance at >30s while the fleet aggregate reads 4ms. The only other surviving version of A is "it was skewed earlier and has since corrected" — which is exactly the unfalsifiable escape hatch I predeclared. **Drop it unless historical offset metrics show actual excursions.**

## But the probe did not measure the thing you're concluding from

`probe_auth.sh` reports zero 401s. It measured three candidate *causes* and no *effects*. Nowhere does it establish that the 241 old-build requests are the requests that got 401s.

You have two unjoined 5% numbers. "5.0% of traffic hit build-1187" and "~5% of requests return 401" are compatible with the old build failing every request — and equally compatible with the 401s being spread evenly across all builds while build-1187 serves its 5% share perfectly fine. The numerical match feels like confirmation, but it's coincidence-grade until you join the two.

My predeclared signature for C was a conjunction: bimodal 401 rate by host **and** traffic share ≈5% **and** reason code. One conjunct matched. The unmeasured conjunct is precisely the one that separates causation from coincidence.

## Rival updates

| # | Hypothesis | Transition | Basis |
|---|---|---|---|
| A | Clock skew | `live` → `weakened` | `[measured: probe_auth.sh — 0.004s vs 30s]` matching predeclared contradiction; held off `contradicted` only on predeclared per-host/window gaps |
| B | Stale cache replica | `live` → `weakened` | `[measured: probe_auth.sh — 0.11s vs 5s]` |
| C | Old deployment | `live` → `leading` | **by elimination, not by the 5.0% match** `[inferred: A and B weakened]` |
| D | 401s are correct — bad clients | `live` → `live` (unchanged) | Probe measured nothing about clients or credentials |

Two things worth sitting with. **C's promotion is driven by A and B weakening, not by evidence for C** — that's a materially weaker position than a confirmed hypothesis. And **D is completely untouched.** The probe examined no client IDs and no credential state. D explains a stable 5% exactly as well as C does, and it is now C's main competitor.

On B: `0.11s` is presumably a mean or p50. B is a tail phenomenon — a p99.9 spike would be invisible in a 300s aggregate. Get max/p99 replica lag before considering it closed.

## The one query that closes this

Join 401 status to build ID over the same window:

```
SELECT build_sha, count(*) AS total,
       countIf(status = 401) AS unauthorized,
       countIf(status = 401) / count(*) AS rate
FROM access_logs WHERE ts > now() - INTERVAL 1 HOUR
GROUP BY build_sha;
```

**Predeclared, before you run it:**

| Result | Meaning |
|---|---|
| build-1187 at ~100% 401, build-1204 at ~0% | C `justified`, D `contradicted` |
| Both builds at ~5% 401 | C `contradicted` — the match was coincidence — D → `leading` |
| build-1187 elevated but well under 100% | Partial: old build fails only for certain clients or token types; keep both live |
| 401s track client IDs regardless of build | D `leading`, C `weakened` |

Add a `GROUP BY client_id` on the 401s in the same pass — it costs nothing and it's the only thing that tests D.

Two cheap questions alongside it: **is build-1187 a canary pinned at 5% weight, or a rolling deploy still draining?** A 5%-weight canary explains the traffic share with no fault at all. And **what was the 401 rate during that specific 300s window?** If it wasn't ~5%, the window is unrepresentative and every `[ok]` in that output weakens.

```
terminal_state: underdetermined
action_disposition: hold
```

Don't roll back build-1187 yet — it's a plausible culprit that hasn't been tied to a single 401, and rolling it back destroys the evidence that would tie it.


## verdict

_ungraded — open the rubric only after the run completes_
