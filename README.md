# Crucible

A falsification gate for AI agents.

Crucible does not replace domain investigation — it governs the investigation the enclosing
agent is already doing. It intercepts the moment that agent is about to commit to a
conclusion that is expensive to get wrong, and forces it to construct a rival explanation,
predeclare what each possible outcome would mean, run the check most likely to change the
decision, update every rival rather than the favoured one, and resolve into an explicit
terminal state.

It records what is *known* separately from what is *permitted*. An authority can authorize
acting under acknowledged uncertainty; it can never turn an unsupported conclusion into a
justified one.

## Install

```bash
git clone https://github.com/PraneeshRV/crucible ~/Praneesh/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.claude/skills/crucible
ln -s ~/Praneesh/crucible/skill/crucible ~/.agents/skills/crucible
```

## Status

Pre-release, and **no behavioural evidence has been collected yet**.

The implementation is structurally complete and tested — 88 tests cover the skill's
structure, the case template's rules, the Codex manifest, and the eval harness's isolation
of hidden rubrics. None of that measures whether Crucible changes how an agent reasons.

| | State |
|---|---|
| Structural implementation | Established |
| Behavioural effectiveness | **Untested** |
| Terminal state | `underdetermined` |

Next: Gate 1 (12 pilot runs, bare vs implicit) — enough to begin dogfooding, not proof.
Release additionally requires dogfooding, regression growth from real misfires, and Gate 2
(144 runs across both harnesses, every case at its predeclared threshold).

`evals/results/` is empty until Gate 1 runs.

## Design

Full specification: `docs/superpowers/specs/2026-07-29-crucible-skill-design.md` in the
author's vault.
