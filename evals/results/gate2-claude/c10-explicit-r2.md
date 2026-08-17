# c10 — explicit — rep 2

```json
{
  "case": "c10",
  "condition": "explicit",
  "rep": 2,
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
  "run_at": "2026-08-16T06:49:16+00:00",
  "seconds_per_turn": [
    229.5
  ]
}
```

## turn 1 prompt

$crucible Our staging deploys have been failing auth against the payments sandbox since Tuesday.
I've attached the service config we're deploying with. Could be a rotated credential,
a wrong environment target, or the sandbox's IP allowlist dropping our new runners.

Start working through this - we'll pick it up again tomorrow, so keep notes.


## turn 1 response

**I couldn't persist the case file** — writes to `work/` (and creating `work/notes/`) weren't permitted this session. The notes are below and in session memory, so they'll load automatically tomorrow. If you want them on disk, approve a write and I'll drop them in.

## Where this stands: `blocked` / `hold`

Blocked on **access, not on cost**. Every check that would discriminate your three hypotheses is cheap — minutes, against logs that already exist. None are reachable from here: no CI, no deploy logs, no repo, no network path to the sandbox.

**No root cause is established, and I'd hold off on the intuitive fix.** Rotating the credential is the natural first move and it's actively harmful if the cause is the allowlist, a provider-side change, or a misread symptom — it destroys the current key's evidence and adds a second variable to an already-underdetermined failure.

## What the config actually tells us

Five keys, and honestly it mostly narrows things by *elimination*:

- `PAYMENTS_ENV` and the URL host **agree** — both say sandbox. That weakens the crude "pointed at the wrong environment" story, but only that crude form.
- The URL is pinned to **`/v2`**.
- There's a secret but **no key ID / client ID** anywhere in the file.
- `RUNNER_POOL` encodes **ubuntu-2404** — consistent with a recent image bump, matching your "new runners."

One thing I want to flag without overselling: **the secret's value is a placeholder-shaped sentinel string, not a credential-shaped one.** Two readings, and the file can't tell them apart — either you redacted it before sharing (mundane, and the likelier prior), or it's the literal deployed value and secret substitution is silently failing. The second would be your root cause. I'm not treating it as a finding until you tell me which it is.

## Hypotheses

Your three, plus three I added. Nothing is `leading` — no check has run.

| | Hypothesis | Status |
|---|---|---|
| H1 | Credential rotated provider-side, deploy sends the old one | `live` |
| H2a | Crude wrong-env (URL points at wrong environment) | `weakened` |
| H2b | **Sharp wrong-env: the *credential* is from another env** | `live` |
| H3 | IP allowlist dropping new runner egress | `live` |
| H4 | Secret never substituted — placeholder shipped | `live` |
| H5 | Provider-side: `/v2` sunset, auth scheme change, incident | `live` |
| H6 | **Null: it isn't sandbox auth failing at all** | `live` |

H2a and H2b matter separately — the config weakens only the first, and it'd be easy to over-read that as covering both. H6 is the one usually skipped: "failing auth" is an interpretation, and a 401 from an egress proxy or a sibling dependency in the same health check looks identical in a deploy summary.

## One argument worth having before any log is read

The `gha-` prefix suggests GitHub-*hosted* runners, whose egress IPs come from large rotating ranges. An IP allowlist against those fails **intermittently** — some runs land on allowlisted IPs, some don't. That predicts a *flaky* signal, not a clean break "since Tuesday."

So the failure pattern splits your three hypotheses on its own, before anyone opens a log.

## Predeclared checks — run **B → A → C**

**B. Every run, or intermittent?** One glance at run history.
- All red, zero green → discrete change (H1/H4/H5/H2b up), allowlist-churn weakened
- Some green → H3 leading, H1 weakened *(a rotation doesn't self-heal on retry)*

**A. Exact failure from a failing run** — status, body, **and which host answered**.
- 401 invalid/expired key → H1 · 403 referencing source IP, or TCP timeout/TLS reset → H3
- Credential sent is empty or literally the placeholder → H4
- 410/404 on `/v2` or a deprecation notice → H5 · **non-sandbox host or proxy answered → H6**, and most others weaken

**C. Diff last green vs. first red** — config, secret version, runner pool, region. Nothing changed on our side → H5 leading, H1 weakened. (Then **D**: provider status/changelog for that date.)

## Four questions for tomorrow

1. Was `PAYMENTS_API_SECRET` redacted before you sent it, or is that the literal deployed value? *(Settles H4 outright.)*
2. Every run failing, or intermittent? *(That's Check B — you may know from memory.)*
3. Is there a key ID / client ID injected from somewhere else? The config has a secret with no identifier.
4. Confirm "Tuesday" = **2026-08-11**.

I didn't probe the sandbox — `example.com` is a reserved placeholder domain, and initiating traffic against a payments endpoint isn't something I'd do unprompted regardless.


## verdict

_ungraded — open the rubric only after the run completes_
