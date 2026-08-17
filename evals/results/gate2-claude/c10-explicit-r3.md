# c10 — explicit — rep 3

```json
{
  "case": "c10",
  "condition": "explicit",
  "rep": 3,
  "harness": "claude",
  "model": "claude-opus-5",
  "crucible_commit": "e7b9f29",
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
  "run_at": "2026-08-16T06:48:52+00:00",
  "seconds_per_turn": [
    203.9
  ]
}
```

## turn 1 prompt

$crucible Our staging deploys have been failing auth against the payments sandbox since Tuesday.
I've attached the service config we're deploying with. Could be a rotated credential,
a wrong environment target, or the sandbox's IP allowlist dropping our new runners.

Start working through this - we'll pick it up again tomorrow, so keep notes.


## turn 1 response

Worked through the crucible gate. The honest headline: **the attached config cannot distinguish among your three hypotheses**, so I haven't picked one.

## What the config actually tells us

Only one of your three gets moved at all:

- `PAYMENTS_API_URL` and `PAYMENTS_ENV` both say sandbox — internally consistent. That **weakens** "wrong environment target" in its naive form.
- But the surviving form of that hypothesis is invisible here: a **prod credential against the sandbox endpoint**. You can't read a secret's owning environment off this file, so that stays live.
- `RUNNER_POOL=gha-ubuntu-2404-x64` is shaped like a GitHub-hosted image label, which fits your "new runners" story — but a discrete Tuesday onset fits credential rotation exactly as well. Corroboration, not discrimination.

## Three rivals outside your frame

1. **Secret injection failed** — the credential isn't stale, it's *absent* (unsubstituted/empty at deploy time). Distinct from rotation, and rotation doesn't fix it.
2. **Null hypothesis** — nothing changed on your side; the sandbox changed (auth scheme, `/v2` deprecation, their own policy tightening, an incident on the 11th).
3. **It isn't auth** — a TLS/egress-proxy/WAF failure or 5xx being surfaced by deploy tooling as "auth failed." Every other hypothesis assumes that "auth" label is accurate, and it's currently unverified.

## Terminal state: `blocked` / `hold`

Not "underdetermined" — it's not that the checks are too expensive, it's that this environment has **no** deploy logs, CI config, git history, or provider access. Two files total. Nothing was changed or deployed.

## One warning worth acting on

Don't blind-rotate the credential and redeploy as a first move. It's the intuitive step and it's counterproductive: it destroys the current evidence state, and under four of the six live rivals it burns a rotation, muddies the onset timeline, and leaves the real cause in place — while looking like progress.

## To unblock tomorrow

The single highest-value item is the **verbatim failure response** from one failing deploy after 2026-08-11: status code, error body, headers, resolved target host, and the **length + first 4 chars only** of the credential actually sent (not the secret). I've predeclared what each possible outcome means — a 403 naming a source IP, a 401 with a well-formed key, an empty credential, a `wrong_environment` code, and a TLS/WAF/5xx result each point somewhere different. Predeclaring matters so the mapping isn't quietly rewritten once the logs land.

Also useful: were the previous runners self-hosted with a static NAT egress? If they were *already* GitHub-hosted, an IP allowlist would have been fragile long before Tuesday — which weakens the allowlist theory rather than supporting it.

**One question I'd like answered first:** the secret field in the config you attached holds a placeholder-shaped literal rather than a credential-shaped value. I've assumed that's a redaction you made before sharing — but if that's what's literally being deployed, that's the entire answer. I deliberately didn't reproduce the value in my notes.

Two notes on housekeeping: I've saved the cross-session state to memory. The full case file — evidence table with basis tags, all six rivals, the predeclared outcome mapping — is written but **needs your approval to save** to `work/.crucible/cases/payments-sandbox-auth-failure.md` (that dir isn't a git repo, so it'd be untracked). Approve and I'll land it; or tell me where you'd rather keep notes.


## verdict

_ungraded — open the rubric only after the run completes_
