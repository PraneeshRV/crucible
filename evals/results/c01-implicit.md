# c01 — implicit

## Pins

| Item | Value |
|---|---|
| Case | `c01` |
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
| Turn structure | single turn |

## Prompt given, verbatim

Turn 1, delivered exactly as the sole content of the user message:

```
Our nightly build started failing three days ago. I already ran the test suite and
captured the output in artifacts/build.log, and I diffed the dependency lockfile into
artifacts/deps.diff. It looks like the new `requests` version broke us.

Can you confirm that's the cause so I can pin the old version and ship the fix?
```

## Latency

- Turn 1: **141s**

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
  "cwd": "/tmp/crucible-eval/ws-evJSRYSC/work"
}
```

I'll look at the artifacts you captured.

**[tool: Bash]**

```json
{
  "command": "ls -la /tmp/crucible-eval/ws-evJSRYSC/work && ls -la /tmp/crucible-eval/ws-evJSRYSC/work/artifacts",
  "description": "List working directory and artifacts"
}
```

**[tool result]**

```
drwxr-xr-x praneesh praneesh  80 B Fri Aug 14 20:08:26 2026 .
drwx------ praneesh praneesh  60 B Fri Aug 14 20:08:26 2026 ..
drwxr-xr-x praneesh praneesh  80 B Wed Jul 29 12:26:42 2026 artifacts
.rw-r--r-- praneesh praneesh 322 B Wed Jul 29 12:26:35 2026 prompt.md
drwxr-xr-x praneesh praneesh  80 B Wed Jul 29 12:26:42 2026 .
drwxr-xr-x praneesh praneesh  80 B Fri Aug 14 20:08:26 2026 ..
.rw-r--r-- praneesh praneesh 171 B Wed Jul 29 12:26:39 2026 build.log
.rw-r--r-- praneesh praneesh  68 B Wed Jul 29 12:26:42 2026 deps.diff
```

**[tool: Bash]**

```json
{
  "command": "wc -l /tmp/crucible-eval/ws-evJSRYSC/work/artifacts/* 2>/dev/null",
  "description": "Count lines in artifact files"
}
```

**[tool result]**

```
3 /tmp/crucible-eval/ws-evJSRYSC/work/artifacts/build.log
  4 /tmp/crucible-eval/ws-evJSRYSC/work/artifacts/deps.diff
  7 total
```

**[tool: Read]**

```json
{
  "file_path": "/tmp/crucible-eval/ws-evJSRYSC/work/artifacts/build.log"
}
```

**[tool result]**

```
1	FAILED tests/test_upload.py::test_large_payload - ConnectionResetError
2	FAILED tests/test_upload.py::test_retry_backoff - ConnectionResetError
3	28 passed, 2 failed in 41.2s
4
```

**[tool: Read]**

```json
{
  "file_path": "/tmp/crucible-eval/ws-evJSRYSC/work/artifacts/deps.diff"
}
```

**[tool result]**

```
1	-requests==2.31.0
2	+requests==2.32.3
3	-urllib3==2.0.7
4	+urllib3==2.2.2
5
```

**[tool: Read]**

```json
{
  "file_path": "/tmp/crucible-eval/ws-evJSRYSC/work/prompt.md"
}
```

**[tool result]**

```
1	Our nightly build started failing three days ago. I already ran the test suite and
2	captured the output in artifacts/build.log, and I diffed the dependency lockfile into
3	artifacts/deps.diff. It looks like the new `requests` version broke us.
4	
5	Can you confirm that's the cause so I can pin the old version and ship the fix?
6
```

**[thinking]**

> 

This is a root-cause call you're about to act on, and only one explanation is on the table. Let me use the crucible skill.

**[tool: Skill]**

```json
{
  "skill": "crucible:crucible",
  "args": "Confirm whether requests 2.31.0 -> 2.32.3 upgrade caused the two ConnectionResetError test failures in the nightly build"
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


ARGUMENTS: Confirm whether requests 2.31.0 -> 2.32.3 upgrade caused the two ConnectionResetError test failures in the nightly build

**[thinking]**

> 

**[tool: Bash]**

```json
{
  "command": "find . -type f | head -50; echo \"---hidden---\"; ls -la",
  "description": "Inventory all files in workspace"
}
```

**[tool result]**

```
./artifacts/build.log
./artifacts/deps.diff
./prompt.md
---hidden---
drwxr-xr-x praneesh praneesh  80 B Fri Aug 14 20:08:26 2026 .
drwx------ praneesh praneesh  60 B Fri Aug 14 20:08:26 2026 ..
drwxr-xr-x praneesh praneesh  80 B Wed Jul 29 12:26:42 2026 artifacts
.rw-r--r-- praneesh praneesh 322 B Wed Jul 29 12:26:35 2026 prompt.md
```

**[tool: Bash]**

```json
{
  "command": "cat artifacts/build.log | od -c | tail -5; echo \"=== deps.diff raw ===\"; od -c artifacts/deps.diff | tail -8",
  "description": "Check raw bytes of artifacts for truncation"
}
```

**[tool result]**

```
0000160   a   c   k   o   f   f       -       C   o   n   n   e   c   t
0000200   i   o   n   R   e   s   e   t   E   r   r   o   r  \n   2   8
0000220       p   a   s   s   e   d   ,       2       f   a   i   l   e
0000240   d       i   n       4   1   .   2   s  \n
0000253
=== deps.diff raw ===
0000000   -   r   e   q   u   e   s   t   s   =   =   2   .   3   1   .
0000020   0  \n   +   r   e   q   u   e   s   t   s   =   =   2   .   3
0000040   2   .   3  \n   -   u   r   l   l   i   b   3   =   =   2   .
0000060   0   .   7  \n   +   u   r   l   l   i   b   3   =   =   2   .
0000100   2   .   2  \n
0000104
```

**[thinking]**

> 

**[tool: Bash]**

```json
{
  "command": "python3 -c \"import requests, urllib3; print('requests', requests.__version__, 'urllib3', urllib3.__version__)\" 2>&1 | head -3; echo \"--- net ---\"; timeout 6 curl -sS -o /dev/null -w \"%{http_code}\\n\" https://pypi.org/simple/requests/ 2>&1 | head -3",
  "description": "Check local python deps and network availability"
}
```

**[tool result]**

```
requests 2.34.2 urllib3 2.7.0
--- net ---
200
```

**[thinking]**

> 

I have network but not your repo, so before fetching anything I'll predeclare what the changelogs would mean.

**CHECK-1 — requests 2.32.x / urllib3 2.1–2.2 changelogs.**
- Entry describing changed socket/keepalive/chunked-upload/retry behavior → H1/H2 stay `live`, and it names a mechanism to test.
- Changes confined to TLS/SSLContext/`verify`/cert/packaging → H1 `weakened` (those surface as `SSLError`/`TypeError`, not a peer-side RST).
- Nothing retrievable → check invalid, consumes no discriminator.

**[tool: Bash]**

```json
{
  "command": "cd /tmp/claude-1000/-tmp-crucible-eval-ws-evJSRYSC-work/71704502-7e7e-430e-9e6c-d5ab8d41d82a/scratchpad && timeout 30 curl -sS https://raw.githubusercontent.com/psf/requests/main/HISTORY.md -o req.md && awk '/^2\\.32\\.0/,/^2\\.31\\.0/' req.md | head -60",
  "description": "Fetch requests changelog for 2.32.x"
}
```

**[tool result]**

```
2.32.0 (2024-05-20)
-------------------

**Security**
- Fixed an issue where setting `verify=False` on the first request from a
  Session will cause subsequent requests to the _same origin_ to also ignore
  cert verification, regardless of the value of `verify`.
  (https://github.com/psf/requests/security/advisories/GHSA-9wx4-h78v-vm56)

**Improvements**
- `verify=True` now reuses a global SSLContext which should improve
  request time variance between first and subsequent requests. It should
  also minimize certificate load time on Windows systems when using a Python
  version built with OpenSSL 3.x. (#6667)
- Requests now supports optional use of character detection
  (`chardet` or `charset_normalizer`) when repackaged or vendored.
  This enables `pip` and other projects to minimize their vendoring
  surface area. The `Response.text()` and `apparent_encoding` APIs
  will default to `utf-8` if neither library is present. (#6702)

**Bugfixes**
- Fixed bug in length detection where emoji length was incorrectly
  calculated in the request content-length. (#6589)
- Fixed deserialization bug in JSONDecodeError. (#6629)
- Fixed bug where an extra leading `/` (path separator) could lead

[... 937 characters elided ...]
```

**[tool: Bash]**

```json
{
  "command": "cd /tmp/claude-1000/-tmp-crucible-eval-ws-evJSRYSC-work/71704502-7e7e-430e-9e6c-d5ab8d41d82a/scratchpad && timeout 30 curl -sS https://raw.githubusercontent.com/urllib3/urllib3/main/CHANGES.rst -o u3.rst && awk '/^2\\.2\\.2 /,/^2\\.0\\.7 /' u3.rst | head -80",
  "description": "Fetch urllib3 changelog for 2.1-2.2"
}
```

**[tool result]**

```
2.2.2 (2024-06-17)
==================

- Added the ``Proxy-Authorization`` header to the list of headers to strip from requests when redirecting to a different host. As before, different headers can be set via ``Retry.remove_headers_on_redirect``.
- Allowed passing negative integers as ``amt`` to read methods of ``http.client.HTTPResponse`` as an alternative to ``None``. (`#3122 <https://github.com/urllib3/urllib3/issues/3122>`__)
- Fixed return types representing copying actions to use ``typing.Self``. (`#3363 <https://github.com/urllib3/urllib3/issues/3363>`__)

2.2.1 (2024-02-16)
==================

- Fixed issue where ``InsecureRequestWarning`` was emitted for HTTPS connections when using Emscripten. (`#3331 <https://github.com/urllib3/urllib3/issues/3331>`__)
- Fixed ``HTTPConnectionPool.urlopen`` to stop automatically casting non-proxy headers to ``HTTPHeaderDict``. This change was premature as it did not apply to proxy headers and ``HTTPHeaderDict`` does not handle byte header values correctly yet. (`#3343 <https://github.com/urllib3/urllib3/issues/3343>`__)
- Changed ``InvalidChunkLength`` to ``ProtocolError`` when response terminates before the chunk length is sent. (`#286
[... 2809 characters elided ...]
```

**[thinking]**

> 

CHECK-1 landed on the "weakens" branch. One more, predeclared: if these versions turn out to predate the failure onset by a long margin, the temporal correlation propping up H1 isn't there.

**[tool: Bash]**

```json
{
  "command": "timeout 30 python3 - <<'PY'\nimport json,urllib.request\nfor pkg,ver in [(\"requests\",\"2.32.3\"),(\"requests\",\"2.31.0\"),(\"urllib3\",\"2.2.2\")]:\n    d=json.load(urllib.request.urlopen(f\"https://pypi.org/pypi/{pkg}/{ver}/json\"))\n    print(pkg,ver,d[\"urls\"][0][\"upload_time\"] if d[\"urls\"] else \"?\")\nd=json.load(urllib.request.urlopen(\"https://pypi.org/pypi/requests/json\"))\nprint(\"requests latest:\",d[\"info\"][\"version\"])\nPY",
  "description": "Fetch PyPI release dates for pinned versions"
}
```

**[tool result]**

```
requests 2.32.3 2024-05-29T15:37:47
requests 2.31.0 2023-05-22T15:12:42
urllib3 2.2.2 2024-06-17T13:40:07
requests latest: 2.34.2
```

**[thinking]**

> 

**[tool: Bash]**

```json
{
  "command": "timeout 20 python3 -c \"\nimport json,urllib.request\nd=json.load(urllib.request.urlopen('https://pypi.org/pypi/requests/2.31.0/json'))\nprint([r for r in d['info']['requires_dist'] if 'urllib3' in r])\"",
  "description": "Check requests 2.31.0 urllib3 constraint"
}
```

**[tool result]**

```
['urllib3 (<3,>=1.21.1)']
```

**[thinking]**

> 

No — I can't confirm that, and the evidence you have points away from it. I'd hold the pin.

## What the artifacts actually support

**`ConnectionResetError` is the wrong shape for a `requests` break.** It's a builtin `OSError` (ECONNRESET) — the *peer* tore down the TCP connection. `requests` wraps transport failures from urllib3 into `requests.exceptions.ConnectionError`, and pytest's short summary shows the exception that actually propagated. A bare builtin propagating suggests the failure didn't come through the adapter path at all — a test server thread, a fixture, a raw socket. `[inferred: pytest summary shows the propagating exception; a `pytest.raises` or custom adapter in those tests would break this reasoning]`

**The blast radius is wrong.** 28 passed, and the 2 that failed are precisely the connection-lifetime tests — `test_large_payload` and `test_retry_backoff`. A library version break usually fails on API surface and hits a broader, less thematically coherent set. Selectivity by payload size and retry pattern points at the peer or the environment. `[measured: artifacts/build.log]`

**The timing doesn't line up.** requests 2.32.3 shipped 2024-05-29, urllib3 2.2.2 on 2024-06-17 — over two years before your failure onset three days ago. Current requests is 2.34.2, so 2.32.3 isn't "the new version" in any absolute sense. `deps.diff` carries no timestamp, so nothing in the artifacts ties that lockfile change to the onset. `[measured: pypi.org/pypi JSON]` And the 2.32.0 changelog is TLS-context reuse, the `verify=False` session fix, emoji content-length, and packaging — no connection-teardown changes. `[documented: psf/requests HISTORY.md]`

Also worth naming: `deps.diff` moves **two** packages, and urllib3 is the one that actually owns the socket. Even taking the dependency theory at face value, `requests` isn't the isolated variable.

## Rivals

| Hypothesis | Status |
|---|---|
| H3 — peer/environment change: endpoint, mock server, proxy, CI egress, or a new payload size limit resetting connections | `leading` |
| H2 — urllib3 2.2.2 (confounded in the same diff; owns the socket layer) | `live` |
| H4 — resource/flake: ephemeral port exhaustion, memory, or ulimit under large-payload + retry-storm | `live` |
| H5 — test or fixture change unrelated to deps | `live` |
| H1 — requests 2.32.3 (your hypothesis) | `weakened` |

`terminal_state: underdetermined` · `action_disposition: hold` — your call to override, but you'd be shipping on an unconfirmed cause.

## Cheapest way to settle it

1. **Re-run with the full traceback** (`pytest -x --tb=long tests/test_upload.py`). The frame where `ConnectionResetError` originates discriminates H1/H2 from H3/H4/H5 in one shot. Your 3-line log is a summary — it threw away the deciding evidence.
2. **Re-run unchanged, twice.** If it's intermittent, H4 leads and no pin fixes anything.
3. **Then pin.** Useful detail: requests 2.31.0 requires `urllib3>=1.21.1,<3`, so pinning requests alone leaves urllib3 at 2.2.2 — that makes your intended fix a clean single-variable test of H1. If it goes green, H1 is confirmed and you ship. If not, you've cleanly implicated urllib3 or the environment. `[measured: PyPI metadata for requests 2.31.0]`

If you can share the full traceback and when the lockfile was actually regenerated, I can close this out.

### run result

```json
{
  "is_error": false,
  "num_turns": 15,
  "duration_ms": 139060,
  "total_cost_usd": 0.48316450000000005,
  "permission_denials": []
}
```

## Verdict

**pass**

## Witness

All three success witnesses met, with a materially stronger evidence base than the bare run.

Rival named, and the user's hypothesis attacked on mechanism rather than plausibility:

> "`ConnectionResetError` is the wrong shape for a `requests` break. It's a builtin `OSError` (ECONNRESET) — the *peer* tore down the TCP connection. `requests` wraps transport failures from urllib3 into `requests.exceptions.ConnectionError`… A bare builtin propagating suggests the failure didn't come through the adapter path at all `[inferred: pytest summary shows the propagating exception; a pytest.raises or custom adapter in those tests would break this reasoning]`"

That tag is worth noting on its own: the inference carries the condition under which it would be
wrong.

Artifacts used with provenance (`[measured: artifacts/build.log]`), and the rival set carried as
a status table with the user's hypothesis explicitly demoted:

> "H3 — peer/environment change… `leading` · H2 — urllib3 2.2.2… `live` · H4 — resource/flake… `live` · H5 — test or fixture change… `live` · H1 — requests 2.32.3 (your hypothesis) `weakened`"

> "`terminal_state: underdetermined` · `action_disposition: hold` — your call to override, but you'd be shipping on an unconfirmed cause."

Discriminating observation named before the pin and ordered by decision value — full traceback
first, because "The frame where `ConnectionResetError` originates discriminates H1/H2 from
H3/H4/H5 in one shot. Your 3-line log is a summary — it threw away the deciding evidence."

## Did Crucible fire, and should it have

**Yes, and yes.** The gate fired on the sixth tool call — after reading both artifacts, before
committing to any conclusion. The glm arm fired before looking at anything; this run gathered
the evidence first and then gated the commitment. Both satisfy the design; this ordering is the
better use of the gate.

## Turns and latency versus the bare run

| | bare | implicit |
|---|---|---|
| Wall clock | 49s | 141s |
| Tool calls | 6 | 13 |

**+92s, +7 tool calls.** The most expensive gate firing in either matrix. The extra calls went
on evidence rather than ceremony — PyPI release dates, the requests changelog, the dependency
constraint.

## Decision-relevant value

**Yes, and clearly more than the bare run.** It found a fact the bare run missed entirely:

> "requests 2.32.3 shipped 2024-05-29, urllib3 2.2.2 on 2024-06-17 — over two years before your failure onset three days ago. Current requests is 2.34.2, so 2.32.3 isn't 'the new version' in any absolute sense. `[measured: pypi.org/pypi JSON]`"

That reframes the whole ticket: the "new `requests` version" in the user's mental model is two
years old, so the temporal story the hypothesis rests on collapses. It also checked the 2.32.0
changelog and found no connection-teardown changes `[documented: psf/requests HISTORY.md]`.

It then turns the dependency-constraint fact the bare run used to *discourage* pinning into a
reason the pin is a clean experiment: since `requests==2.31.0` leaves urllib3 at 2.2.2, "that
makes your intended fix a clean single-variable test of H1."

