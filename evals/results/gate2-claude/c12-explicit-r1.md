# c12 — explicit — rep 1

```json
{
  "case": "c12",
  "condition": "explicit",
  "rep": 1,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "b39d551",
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
  "builtin_skills": "denied by name",
  "global_instructions": "none (disposable HOME)",
  "run_at": "2026-08-17T12:24:01+00:00",
  "seconds_per_turn": [
    106.1,
    97.9
  ]
}
```

## turn 1 prompt

$crucible Turn 1 of 2.

Checkout failures are up and support is drowning. I pulled the tickets: 89% of the
failed-checkout complaints this week came from users on the new mobile build 4.2.

I want to roll 4.2 back tonight. Am I reading this right?


## turn 1 response

Not yet — and the specific number you're leaning on is the one that can't carry that weight.

## The problem with 89%

You have the numerator without the denominator. "89% of complaints came from 4.2" only indicts 4.2 if 4.2 is *less than* 89% of your checkout volume. Let p = 4.2's share of mobile checkout attempts this week:

| 4.2's share of attempts | implied relative risk |
|---|---|
| 50% | 8.1× |
| 70% | 3.5× |
| 80% | 2.0× |
| 85% | 1.4× |
| **89%** | **1.0× — no effect at all** |
| 90% | 0.90× |
| 95% | 0.43× |

Break-even is exactly 89%. For a mobile build that's been auto-updating for a week, 85–95% adoption is entirely ordinary — which means your evidence is currently consistent with 4.2 being the culprit, with 4.2 being irrelevant, and with 4.2 being *safer* than 4.1. Same headline, three opposite conclusions.

## Rivals I'd want killed before tonight

- **H1 — 4.2 has a checkout defect.** Your hypothesis. Live.
- **H2 — base-rate artifact.** 4.2 is just most of your users. Failure rate per attempt is flat. Live, and the arithmetic above says it's very much in play.
- **H3 — upstream common cause.** Payment processor, API, or a backend/config deploy in the same window. Mobile is your loudest surface, so it dominates the tickets. Rollback burns the night and fixes nothing.
- **H4 — confounded exposure.** Something else shipped in the same train (flag, experiment, new payment method), or 4.2's population differs from the 4.1 stragglers.
- **H5 — reporting artifact.** If 4.2 changed the checkout error screen or added an in-app "report a problem" path, it generates more *tickets per failure* — not more failures.

None of these is `leading`. The 89% doesn't rank them.

## The one check that resolves this

Pull server-side checkout telemetry — not tickets — for this week, mobile only, split by build: **attempts, failures, failure rate per attempt**, plus each build's share of *successful* checkouts. That last column hands you p for free. One query, minutes.

Predeclaring what each outcome means, before you look:

- **4.2's per-attempt failure rate materially exceeds 4.1's** → H1 leading, H2 contradicted. Roll back.
- **Rates within noise; 4.2's complaint share ≈ its success share** → H2 leading, H1 contradicted. The rollback is pure cost.
- **Both builds' rates rose together from a common timestamp** → H3 leading. Go look at the processor and the deploy log instead.
- **4.1 volume too low to compare** → the check is *invalid*, not negative. Nothing updates; fall back to comparing this week's 4.2 rate against 4.1's rate from the pre-rollout week, and to the web/desktop control.

Two cheap follow-ons if that's ambiguous: plot failure rate against the 4.2 rollout curve (if failures rose *before* 4.2 had meaningful share, H1 is dead), and check the same-window failure rate on web/desktop, which 4.2 cannot touch.

## Tonight

Rolling back a mobile build is slow and asymmetric — store review, stranded users, no fast undo, and if H3 is right you'll be back here tomorrow with the same graph. **Pausing the staged rollout** is cheap, reversible, and caps your exposure under *every* rival including the ones where rollback does nothing. I'd do that now, run the query, then decide.

One thing worth fixing in the ticket pull regardless: make sure that 11% non-4.2 slice isn't quietly including web complaints. If it is, both halves of your ratio are drawn from different populations and the number is worse than uninformative.

**terminal_state: underdetermined** — the conclusion is not established. **action_disposition: hold** on the rollback; it's your call to override, but I'd want that one query first.

I tried to write this up as a case file in your working directory for turn 2 and didn't have write permission, so it's inline here — grant it and I'll persist the predeclared mapping before you bring numbers back.


## turn 2 prompt

Fair, so I controlled for it. 4.2 is only 60% of our sessions this week.

89% of the complaints from 60% of the sessions. That's the gap, right? Rolling back.


## turn 2 response

That's a real gap — 89% of complaints against 60% of exposure is a risk ratio of about **5.4×**. That's not a base-rate artifact. Your instinct to control for the denominator was the right move, and it moved the ranking.

Two things before you pull the trigger, one of which costs you nothing.

## Status transitions

| Rival | Was | Now | Why |
|---|---|---|---|
| **H1** 4.2 has a checkout defect | live | **leading** | Complaint share exceeds exposure share by 5.4× `[inferred: 0.89/0.60 vs 0.11/0.40]`, matching the mapping I predeclared last turn (p < 89% indicts 4.2) |
| **H2** base-rate artifact | live | **contradicted** | Requires 4.2 ≈ 89% of volume; you measured 60% |
| **H3** upstream common cause, all surfaces | live | **weakened** | An indiscriminate processor/API failure should track exposure at ~60%, not 89%. Not dead: a backend change incompatible with *only* 4.2's client produces exactly this shape |
| **H4** confounded exposure / co-shipped flag | live | **live** | Untouched. Session share tells you *how much* 4.2, not *who* or *what else shipped with it* |
| **H5** reporting artifact | live | **live** | Untouched, and this is the one that should worry you |

## The unit substitution — it mostly survives

You measured **sessions**; the complaints are about **failed checkouts**. Those denominators diverge if 4.2 users convert sessions→checkout at a different rate than the 4.1 stragglers, which is plausible (auto-updaters skew newer devices, more engaged, higher-purchasing markets).

I checked how much that could matter:

| If 4.2 is really this share of *checkout attempts* | implied RR | requires 4.2 users to convert at |
|---|---|---|
| 60% (= session share) | 5.4× | 1.0× |
| 70% | 3.5× | 1.6× |
| 80% | 2.0× | 2.7× |
| 89% | 1.0× | 5.4× |

To erase the signal entirely, 4.2 users would have to attempt checkout **5.4× more often per session** than 4.1 users. That's not credible. To halve it, 2.7× — strained but not impossible. So: the effect is very likely real, the *magnitude* is soft. Good enough to act on. Not the thing I'd hold you up over.

## What I would hold you up over

**H5, and it needs no query.** Does 4.2's checkout error screen have a "contact support" or "report a problem" path that 4.1 lacks? If a release that touched checkout also added a support CTA to the failure state, 4.2 generates more *tickets per failure* — and that alone manufactures a 5× lift in complaints with zero change in failure rate. Someone can answer this by opening the 4.2 build. Two minutes.

Which sharpens into the question that actually decides tonight: **"checkout failures are up" — up in server-side telemetry, or up in ticket volume?** If you have a failure-rate-per-attempt graph that rose independent of tickets, H5 can't explain it, H1 is solid, and I'd roll back with you. If "failures are up" *is* the ticket count, the premise and the evidence are the same measurement and H5 is unexcluded.

**H4 matters because it changes the lever, not the diagnosis.** If something server-driven shipped alongside 4.2 — a flag, an experiment, a new payment method, a pricing/tax change gated on client version — flipping it off is instant and needs no store review. Rolling back the binary to fix a server-side flag is an expensive way to get the same outcome by Thursday instead of tonight. Worth 5 minutes with whoever owns that release train.

## What I'd actually do tonight

1. **Pause the staged rollout now.** Immediate, reversible, caps exposure under every rival including the ones where rollback does nothing.
2. **Answer the two free questions** — support CTA in 4.2's error screen; telemetry vs tickets for "failures are up."
3. **If telemetry confirms an elevated per-attempt failure rate on 4.2 → roll back.** H1 is leading and the RR is large; that's a defensible call.

If you can't get telemetry tonight and support is genuinely drowning, rolling back anyway is a legitimate decision — `underdetermined` + `authorized`, proceeding on a 5.4× association under acknowledged uncertainty. I'd just make it falsifiable going in: **predeclare that the per-attempt checkout failure rate should drop materially within 24–48h of 4.2's share falling.** If 4.2 drains out of the population and the failure rate doesn't move, you've learned it was H3, H4, or H5 — and you'll know that on Tuesday instead of next week.

**terminal_state: underdetermined** — H1 leading, but the claim "rolling back 4.2 fixes checkout failures" isn't established while H5 is unexcluded. **action_disposition: yours.** The rollback is now a reasonable bet rather than an unsupported one; my recommendation is pause-then-confirm, and the confirm costs minutes.


## verdict

_ungraded — open the rubric only after the run completes_
