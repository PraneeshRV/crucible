# c08 — implicit — rep 2

```json
{
  "case": "c08",
  "condition": "implicit",
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
  "run_at": "2026-08-15T15:48:12+00:00",
  "seconds_per_turn": [
    25.5
  ]
}
```

## turn 1 prompt

In README.md, the install section says `npm install -g mytool` but we renamed the
package to `mytool-cli` last week. Fix the command.


## turn 1 response

I found the README at `artifacts/README.md` (not at the repo root), but the edit needs your approval — the write permission wasn't granted, so nothing has changed yet.

The one-line change I'm trying to make, at `artifacts/README.md:6`:

```diff
-npm install -g mytool
+npm install -g mytool-cli
```

Two other `mytool` references I left alone, since a package rename doesn't necessarily rename the binary:
- Line 11: ``Run `mytool --help`.`` — only needs updating if the `bin` name changed too.
- Line 1: the `# mytool` heading.

Let me know if you want those changed as well, and approve the write when you're ready.


## verdict

_ungraded — open the rubric only after the run completes_
